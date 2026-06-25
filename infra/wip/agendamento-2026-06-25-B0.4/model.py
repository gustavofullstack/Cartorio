"""Modelo de Agendamento para atendimentos presenciais.

Agendamentos representam slots de tempo reservados para atendimento
presencial no cartório. Integra com o sistema de protocolos e
controle de fluxo de atendimento.

LGPD: dados pessoais (CPF) são hasheados antes de persistir.
"""

from __future__ import annotations

import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.cliente import Cliente
from app.models.protocolo import Protocolo
from app.utils.pii import hash_pii


class StatusAgendamento(str, Enum):
    """Status do agendamento no ciclo de vida."""

    AGENDADO = "agendado"  # Confirmado, aguardando data/hora
    CONFIRMADO = "confirmado"  # Cliente confirmou presença
    EM_ATENDIMENTO = "em_atendimento"  # Em andamento no balcão
    CONCLUIDO = "concluido"  # Atendimento finalizado
    CANCELADO = "cancelado"  # Cancelado pelo cliente ou cartório
    FALTOU = "falta"  # Cliente não compareceu (no-show)


class TipoAtendimento(str, Enum):
    """Tipo de atendimento agendado."""

    NORMAL = "normal"  # Atendimento padrão
    PRIORITARIO = "prioritario"  # Idosos, gestantes, PcD
    URGENTE = "urgente"  # Urgência judicial ou administrativa


class Agendamento(Base):
    """Agendamento de atendimento presencial.

    Relacionamentos:
    - cliente: quem agendou (FK para clientes.id)
    - protocolo: protocolo associado (opcional, FK para protocolos.id)
    - atendimento: registro de atendimento gerado (opcional)
    """

    __tablename__ = "agendamentos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    protocolo_id: Mapped[int | None] = mapped_column(
        ForeignKey("protocolos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Dados do agendamento
    data_hora: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        index=True,
    )
    data_hora_fim: Mapped[datetime.datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )
    status: Mapped[StatusAgendamento] = mapped_column(
        String(20),
        nullable=False,
        default=StatusAgendamento.AGENDADO,
        index=True,
    )
    tipo: Mapped[TipoAtendimento] = mapped_column(
        String(20),
        nullable=False,
        default=TipoAtendimento.NORMAL,
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    local: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="balcao_1",
    )

    # Metadados LGPD
    cpf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    criado_em: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        default=func.now(),
    )
    atualizado_em: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    # Relacionamentos ORM
    cliente: Mapped[Cliente] = relationship(
        "Cliente",
        back_populates="agendamentos",
        lazy="joined",
    )
    protocolo: Mapped[Protocolo | None] = relationship(
        "Protocolo",
        back_populates="agendamentos",
        lazy="joined",
    )

    # Constraints de negócio
    __table_args__ = (
        CheckConstraint(
            "data_hora_fim IS NULL OR data_hora_fim > data_hora",
            name="check_data_hora_fim_gt_data_hora",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Agendamento id={self.id} cliente_id={self.cliente_id} "
            f"status={self.status} data_hora={self.data_hora.isoformat()}>"
        )

    @classmethod
    def criar(
        cls,
        *,
        cliente_id: int,
        cliente_cpf: str,
        data_hora: datetime.datetime,
        titulo: str,
        descricao: str | None = None,
        tipo: TipoAtendimento = TipoAtendimento.NORMAL,
        local: str = "balcao_1",
        protocolo_id: int | None = None,
    ) -> Agendamento:
        """Factory method com hash de CPF (LGPD).

        Args:
            cliente_id: ID do cliente (FK)
            cliente_cpf: CPF em texto puro (será hasheado)
            data_hora: Data/hora do agendamento
            titulo: Título descritivo
            descricao: Descrição opcional
            tipo: Tipo de atendimento
            local: Local físico do atendimento
            protocolo_id: ID do protocolo associado (opcional)

        Returns:
            Instância de Agendamento pronta para persistir
        """
        return cls(
            cliente_id=cliente_id,
            protocolo_id=protocolo_id,
            cpf_hash=hash_pii(cliente_cpf),
            data_hora=data_hora,
            titulo=titulo,
            descricao=descricao,
            tipo=tipo,
            local=local,
        )

    def confirmar(self) -> None:
        """Muda status para CONFIRMADO."""
        if self.status == StatusAgendamento.AGENDADO:
            self.status = StatusAgendamento.CONFIRMADO

    def cancelar(self) -> None:
        """Muda status para CANCELADO."""
        if self.status in (
            StatusAgendamento.AGENDADO,
            StatusAgendamento.CONFIRMADO,
        ):
            self.status = StatusAgendamento.CANCELADO

    def registrar_falta(self) -> None:
        """Muda status para FALTOU (no-show)."""
        if self.status == StatusAgendamento.AGENDADO:
            self.status = StatusAgendamento.FALTOU

    def iniciar_atendimento(self) -> None:
        """Muda status para EM_ATENDIMENTO."""
        if self.status == StatusAgendamento.CONFIRMADO:
            self.status = StatusAgendamento.EM_ATENDIMENTO

    def concluir(self) -> None:
        """Muda status para CONCLUIDO e registra hora de término."""
        if self.status == StatusAgendamento.EM_ATENDIMENTO:
            self.status = StatusAgendamento.CONCLUIDO
            self.data_hora_fim = datetime.datetime.now(datetime.timezone.utc)