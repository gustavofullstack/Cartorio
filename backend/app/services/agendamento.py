"""Serviços de agendamento (business logic).

Camada de serviço para gerenciamento de agendamentos, com:
- Validação de negócio
- Integração com protocolos
- Controle de conflitos de horário
- Audit log (LGPD art. 37)
- Notificações (via N8N)

Integra com:
- app.models.agendamento.Agendamento
- app.models.protocolo.Protocolo
- app.services.audit.AuditService
"""

from __future__ import annotations

import datetime
from typing import Any, cast

from fastapi import Request

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agendamento import Agendamento, StatusAgendamento, TipoAtendimento
from app.models.cliente import Cliente
from app.models.protocolo import Protocolo
from app.services.audit import AuditService
from app.services.audit_context import audit_kwargs
from app.services.pii import hash_pii
from app.config import settings


class AgendamentoConflictError(ValueError):
    """Erro quando há conflito de horário."""

    def __init__(self, existing: Agendamento) -> None:
        self.existing = existing
        super().__init__(
            f"Conflito de horário com agendamento #{existing.id} "
            f"({existing.data_hora} - {existing.titulo})"
        )


class ClienteNotFoundError(ValueError):
    """Erro quando cliente não é encontrado."""

    def __init__(self, cliente_id: int) -> None:
        super().__init__(f"Cliente #{cliente_id} não encontrado")


class ProtocoloNotFoundError(ValueError):
    """Erro quando protocolo não é encontrado."""

    def __init__(self, protocolo_id: int) -> None:
        super().__init__(f"Protocolo #{protocolo_id} não encontrado")


class AgendamentoService:
    """Serviço de agendamentos."""

    @staticmethod
    def _validar_horario_disponivel(
        db: Session,
        data_hora: datetime.datetime,
        duration_minutes: int = 30,
        local: str = "balcao_1",
    ) -> None:
        """Valida se horário está disponível para o local.

        Args:
            db: Sessão do banco
            data_hora: Horário desejado para o agendamento
            duration_minutes: Duração em minutos (default 30)
            local: Local físico do atendimento

        Raises:
            AgendamentoConflictError: Se houver conflito
        """
        data_hora_fim = data_hora + datetime.timedelta(minutes=duration_minutes)

        # Verifica sobreposição: outro agendamento que começa durante este
        # ou que termina durante este
        # IMPORTANTE: agendamentos SEM data_hora_fim (ainda nao concluidos)
        # tambem bloqueiam - assumimos duration_minutes default para deteccao
        from sqlalchemy import or_

        # Calcula janela de conflito: [data_hora - duration, data_hora_fim]
        # Outro agendamento B conflitante se:
        #   B.data_hora < data_hora_fim (B comeca antes do fim de A)
        #   E (B.data_hora_fim > data_hora OU B.data_hora_fim IS NULL E
        #      B.data_hora + duration_minutes > data_hora)
        # Para SQLite (e Postgres comecando simples), comparamos
        # somente data_hora de B com a janela de A, ja que todos os
        # agendamentos ativos tem a mesma duracao default de 30 min.
        janela_inicio = data_hora - datetime.timedelta(minutes=duration_minutes)
        stmt = select(Agendamento).where(
            Agendamento.local == local,
            Agendamento.status.in_(
                [
                    StatusAgendamento.AGENDADO,
                    StatusAgendamento.CONFIRMADO,
                    StatusAgendamento.EM_ATENDIMENTO,
                ]
            ),
            or_(
                # Caso 1: B tem data_hora_fim definido
                ((Agendamento.data_hora < data_hora_fim) & (Agendamento.data_hora_fim > data_hora)),
                # Caso 2: B NAO tem data_hora_fim - conflito se B.data_hora
                # cai dentro da janela [janela_inicio, data_hora_fim]
                (
                    Agendamento.data_hora_fim.is_(None)
                    & (Agendamento.data_hora >= janela_inicio)
                    & (Agendamento.data_hora < data_hora_fim)
                ),
            ),
        )

        existing = db.execute(stmt).scalar_one_or_none()
        if existing is not None:
            raise AgendamentoConflictError(existing)

    @staticmethod
    def _validar_cliente_existe(db: Session, cliente_id: int) -> Cliente:
        """Valida existência do cliente.

        Args:
            db: Sessão do banco
            cliente_id: ID do cliente

        Returns:
            Instância do cliente

        Raises:
            ClienteNotFoundError: Se cliente não existir
        """
        cliente = db.execute(select(Cliente).where(Cliente.id == cliente_id)).scalar_one_or_none()
        if cliente is None:
            raise ClienteNotFoundError(cliente_id)
        return cliente

    @staticmethod
    def _validar_protocolo_existe(db: Session, protocolo_id: int | None) -> Protocolo | None:
        """Valida existência do protocolo (se fornecido).

        Args:
            db: Sessão do banco
            protocolo_id: ID do protocolo (opcional)

        Returns:
            Instância do protocolo ou None

        Raises:
            ProtocoloNotFoundError: Se protocolo não existir
        """
        if protocolo_id is None:
            return None

        protocolo = db.execute(
            select(Protocolo).where(Protocolo.id == protocolo_id)
        ).scalar_one_or_none()
        if protocolo is None:
            raise ProtocoloNotFoundError(protocolo_id)
        return protocolo

    @staticmethod
    def criar_agendamento(
        db: Session,
        *,
        cliente_id: int,
        cliente_cpf: str,
        data_hora: datetime.datetime,
        titulo: str,
        descricao: str | None = None,
        tipo: TipoAtendimento = TipoAtendimento.NORMAL,
        local: str = "balcao_1",
        protocolo_id: int | None = None,
        duration_minutes: int = 30,
        request: Request | None = None,
    ) -> Agendamento:
        """Cria um novo agendamento com validações completas.

        Args:
            db: Sessão do banco
            cliente_id: ID do cliente
            cliente_cpf: CPF do cliente (texto puro, será hasheado)
            data_hora: Data/hora do agendamento
            titulo: Título descritivo
            descricao: Descrição opcional
            tipo: Tipo de atendimento
            local: Local físico
            protocolo_id: ID do protocolo associado (opcional)
            duration_minutes: Duração em minutos
            request: Objeto request para audit context (opcional)

        Returns:
            Agendamento criado e persistido

        Raises:
            AgendamentoConflictError: Conflito de horário
            ClienteNotFoundError: Cliente não encontrado
            ProtocoloNotFoundError: Protocolo não encontrado
        """
        # Validações (raise se cliente/protocolo nao existem)
        AgendamentoService._validar_horario_disponivel(db, data_hora, duration_minutes, local)
        AgendamentoService._validar_cliente_existe(db, cliente_id)
        AgendamentoService._validar_protocolo_existe(db, protocolo_id)

        # Cria agendamento
        agendamento = Agendamento.criar(
            cliente_id=cliente_id,
            cliente_cpf=cliente_cpf,
            data_hora=data_hora,
            titulo=titulo,
            descricao=descricao,
            tipo=tipo,
            local=local,
            protocolo_id=protocolo_id,
        )

        db.add(agendamento)
        db.flush()  # Obtém ID para audit log

        # Audit log (LGPD art. 37)
        audit_kwargs_dict = audit_kwargs(request) if request else {}
        AuditService.log(
            db,
            actor_id=f"cliente:{cliente_id}",
            actor_type="user",
            action="agendamento.created",
            resource=f"agendamento:{agendamento.id}",
            payload={
                "cliente_id": cliente_id,
                "cliente_cpf_hash": hash_pii(cliente_cpf, salt=settings.audit_hmac_key[:32]),
                "data_hora": data_hora.isoformat(),
                "titulo": titulo,
                "tipo": tipo.value,
                "local": local,
                "protocolo_id": protocolo_id,
            },
            **audit_kwargs_dict,
        )

        db.commit()
        db.refresh(agendamento)

        # A26: Invalida cache após criação de novo agendamento
        from app.services.agendamento_cache import invalidate_agendamento_cache

        invalidate_agendamento_cache()

        return agendamento

    @staticmethod
    def listar_agendamentos_cliente(
        db: Session,
        cliente_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Agendamento]:
        """Lista agendamentos de um cliente.

        Args:
            db: Sessão do banco
            cliente_id: ID do cliente
            limit: Limite de resultados
            offset: Offset para paginação

        Returns:
            Lista de agendamentos
        """
        stmt = (
            select(Agendamento)
            .where(Agendamento.cliente_id == cliente_id)
            .order_by(Agendamento.data_hora.desc())
            .limit(limit)
            .offset(offset)
        )
        return cast(list[Agendamento], db.execute(stmt).scalars().all())

    @staticmethod
    def listar_agendamentos_data(
        db: Session,
        data: datetime.date,
        *,
        local: str | None = None,
    ) -> list[Agendamento]:
        """Lista agendamentos para uma data específica.

        Args:
            db: Sessão do banco
            data: Data desejada
            local: Filtrar por local (opcional)

        Returns:
            Lista de agendamentos
        """
        data_inicio = datetime.datetime.combine(data, datetime.time.min)
        data_fim = datetime.datetime.combine(data, datetime.time.max)

        stmt = select(Agendamento).where(
            Agendamento.data_hora >= data_inicio,
            Agendamento.data_hora <= data_fim,
        )

        if local:
            stmt = stmt.where(Agendamento.local == local)

        stmt = stmt.order_by(Agendamento.data_hora)

        return cast(list[Agendamento], db.execute(stmt).scalars().all())

    @staticmethod
    def cancelar_agendamento(
        db: Session,
        agendamento_id: int,
        *,
        request: Request | None = None,
    ) -> Agendamento:
        """Cancela um agendamento.

        Args:
            db: Sessão do banco
            agendamento_id: ID do agendamento
            request: Objeto request para audit context (opcional)

        Returns:
            Agendamento cancelado

        Raises:
            ValueError: Se agendamento não puder ser cancelado
        """
        agendamento = db.execute(
            select(Agendamento).where(Agendamento.id == agendamento_id)
        ).scalar_one_or_none()

        if agendamento is None:
            raise ValueError(f"Agendamento #{agendamento_id} não encontrado")

        if agendamento.status not in (
            StatusAgendamento.AGENDADO,
            StatusAgendamento.CONFIRMADO,
        ):
            raise ValueError(
                f"Agendamento #{agendamento_id} não pode ser cancelado "
                f"(status: {agendamento.status})"
            )

        agendamento.cancelar()
        db.add(agendamento)

        # Audit log
        audit_kwargs_dict = audit_kwargs(request) if request else {}
        AuditService.log(
            db,
            actor_id=f"cliente:{agendamento.cliente_id}",
            actor_type="user",
            action="agendamento.cancelled",
            resource=f"agendamento:{agendamento.id}",
            payload={
                "status_anterior": "agendado"
                if agendamento.status == StatusAgendamento.AGENDADO
                else "confirmado",
                "status_novo": agendamento.status.value,
            },
            **audit_kwargs_dict,
        )

        db.commit()
        db.refresh(agendamento)

        # A26: Invalida cache após cancelamento de agendamento
        from app.services.agendamento_cache import invalidate_agendamento_cache

        invalidate_agendamento_cache()

        return agendamento

    @staticmethod
    def confirmar_agendamento(
        db: Session,
        agendamento_id: int,
        *,
        request: Request | None = None,
    ) -> Agendamento:
        """Confirma um agendamento.

        Args:
            db: Sessão do banco
            agendamento_id: ID do agendamento
            request: Objeto request para audit context (opcional)

        Returns:
            Agendamento confirmado

        Raises:
            ValueError: Se agendamento não puder ser confirmado
        """
        agendamento = db.execute(
            select(Agendamento).where(Agendamento.id == agendamento_id)
        ).scalar_one_or_none()

        if agendamento is None:
            raise ValueError(f"Agendamento #{agendamento_id} não encontrado")

        if agendamento.status != StatusAgendamento.AGENDADO:
            raise ValueError(
                f"Agendamento #{agendamento_id} não pode ser confirmado "
                f"(status: {agendamento.status})"
            )

        agendamento.confirmar()
        db.add(agendamento)

        # Audit log
        audit_kwargs_dict = audit_kwargs(request) if request else {}
        AuditService.log(
            db,
            actor_id=f"cliente:{agendamento.cliente_id}",
            actor_type="user",
            action="agendamento.confirmed",
            resource=f"agendamento:{agendamento.id}",
            payload={
                "status_anterior": "agendado",
                "status_novo": agendamento.status.value,
            },
            **audit_kwargs_dict,
        )

        db.commit()
        db.refresh(agendamento)

        # A26: Invalida cache após confirmação de agendamento
        from app.services.agendamento_cache import invalidate_agendamento_cache

        invalidate_agendamento_cache()

        return agendamento

    @staticmethod
    def listar_agendamentos_pendentes(db: Session) -> list[dict[str, Any]]:
        """Lista agendamentos pendentes de notificacao (status AGENDADO).

        Usado pelo NotificationService para disparar lembretes.
        Recriado em 2026-06-25 (E1.S4.T2 cleanup) - estava duplicado e
        foi removido junto com os duplicates por engano no sed.

        A26: Cache Redis 60s para reduzir carga DB em pico.
        """
        from app.models.agendamento import StatusAgendamento
        from app.services.agendamento_cache import (
            get_agendamentos_pendentes_cached,
            set_agendamentos_pendentes_cached,
        )

        # A26 - Cache Redis: tenta buscar do cache primeiro
        cached = get_agendamentos_pendentes_cached()
        if cached is not None:
            return cached

        stmt = (
            select(Agendamento)
            .where(
                Agendamento.status == StatusAgendamento.AGENDADO,
            )
            .order_by(Agendamento.data_hora)
        )

        agendamentos = db.execute(stmt).scalars().all()

        # A26: cacheia resultado para proximas chamadas
        # Converte para dict para cache (a API ja retorna dict)
        agendamentos_dicts = []
        for agendamento in agendamentos:
            agendamentos_dicts.append(
                {
                    "id": agendamento.id,
                    "titulo": agendamento.titulo,
                    "data_hora": agendamento.data_hora,
                    "cliente_id": agendamento.cliente_id,
                    "local": agendamento.local,
                    "tipo": agendamento.tipo.value
                    if hasattr(agendamento.tipo, "value")
                    else agendamento.tipo,
                    "status": agendamento.status.value
                    if hasattr(agendamento.status, "value")
                    else agendamento.status,
                }
            )

        set_agendamentos_pendentes_cached(agendamentos_dicts)

        return agendamentos_dicts

    @staticmethod
    def listar_agendamentos_proximos(db: Session) -> list[dict[str, Any]]:
        """Lista agendamentos das proximas 24h para disparo de lembretes.

        Retorna agendamentos com status AGENDADO ou CONFIRMADO entre agora
        e as proximas 24h.

        Recriado em 2026-06-25 (E1.S4.T2 cleanup).

        A26: Cache Redis 60s para reduzir carga DB em pico.
        """
        import datetime as _dt
        from app.models.agendamento import StatusAgendamento
        from app.services.agendamento_cache import (
            get_agendamentos_proximos_cached,
            set_agendamentos_proximos_cached,
        )

        # A26 - Cache Redis: tenta buscar do cache primeiro
        cached = get_agendamentos_proximos_cached()
        if cached is not None:
            return cached

        agora = _dt.datetime.now(_dt.timezone.utc)
        proximas_24h = agora + _dt.timedelta(hours=24)

        stmt = (
            select(Agendamento)
            .where(
                Agendamento.status.in_(
                    [
                        StatusAgendamento.AGENDADO,
                        StatusAgendamento.CONFIRMADO,
                    ]
                ),
                Agendamento.data_hora >= agora,
                Agendamento.data_hora <= proximas_24h,
            )
            .order_by(Agendamento.data_hora)
        )

        agendamentos = db.execute(stmt).scalars().all()

        # A26: cacheia resultado para proximas chamadas
        # Converte para dict para cache (a API ja retorna dict)
        agendamentos_dicts = []
        for agendamento in agendamentos:
            agendamentos_dicts.append(
                {
                    "id": agendamento.id,
                    "titulo": agendamento.titulo,
                    "data_hora": agendamento.data_hora,
                    "cliente_id": agendamento.cliente_id,
                    "local": agendamento.local,
                    "tipo": agendamento.tipo.value
                    if hasattr(agendamento.tipo, "value")
                    else agendamento.tipo,
                    "status": agendamento.status.value
                    if hasattr(agendamento.status, "value")
                    else agendamento.status,
                }
            )

        set_agendamentos_proximos_cached(agendamentos_dicts)

        return agendamentos_dicts
