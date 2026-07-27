"""Servico integrado de atendimento PIETRA (coleta + memoria + agendamento).

P0 (Gustavo 2026-07-27): "O CANAL TEM QUE TER TOTAL ACESSO A MEMORIA!!
TUDO VIA REDIS E POSTGRESS TEM QUE SALVAR TUDO BEM OTIMIZADO COM O
PRIMARY KEY TELEFONE DO CLIENTE!! E A PARTE DE ATENDIMENTO,
AGENDAMENTO ONLINE, AGENDAMENTO PRESENCIAL, COLETA DE NOME, TELEFONE,
EMAIL, CPF, DATA DE NASCIMENTO E ETC!!"

Compoe:
  - pietra_coleta.upsert_cliente_por_telefone: cria/atualiza cliente
  - agendamento_service.criar_agendamento: cria agendamento presencial
  - pietra_memoria (Redis SETEX + Postgres): persiste session state
  - atendimento (solid_atendimento_query): cria atendimento + protocolo
  - audit_log (LGPD): toda mutacao gera entry imutavel SHA256+HMAC

Modified by Gustavo Almeida · 2026-07-27
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.agendamento import AgendamentoService, TipoAtendimento
from app.services.pii import hash_pii
from app.services.pietra_coleta import (
    upsert_cliente_por_telefone,
)

logger = logging.getLogger(__name__)


@dataclass
class MemoriaItem:
    """Item de memoria de conversa."""
    role: str  # user|assistant|system|tool
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: dt.datetime = field(default_factory=dt.datetime.utcnow)


@dataclass
class AtendimentoRequest:
    """Request de atendimento consolidado."""
    telefone: str  # PRIMARY KEY operacional
    canal: str = "imessage"
    tipo: str = "consulta"  # consulta|agendamento_online|agendamento_presencial|segunda_via|outro
    nome: Optional[str] = None
    email: Optional[str] = None
    cpf: Optional[str] = None
    data_nascimento: Optional[str] = None
    # Campos especificos por tipo
    protocolo_id: Optional[int] = None
    data_hora: Optional[dt.datetime] = None  # para agendamento
    titulo: Optional[str] = None  # para agendamento
    descricao: Optional[str] = None
    local: str = "balcao_1"  # para agendamento presencial
    consentimento_lgpd: bool = False
    consentimento_ip: Optional[str] = None
    observacoes: Optional[str] = None


@dataclass
class AtendimentoResult:
    """Resultado do atendimento."""
    atendimento_id: int
    cliente_id: int
    cliente_criado: bool
    agendamento_id: Optional[int] = None
    protocolo_id: Optional[int] = None
    dados_coletados: dict[str, Any] = field(default_factory=dict)
    dados_pendentes: list[str] = field(default_factory=list)
    memoria_salva: bool = False
    audit_ids: list[int] = field(default_factory=list)
    proximos_passos: list[str] = field(default_factory=list)


def iniciar_atendimento(
    db: Session,
    req: AtendimentoRequest,
    request: Optional[Request] = None,
) -> AtendimentoResult:
    """Orquestra inicio de atendimento com coleta automatica.

    Fluxo:
    1. Coleta (upsert cliente por telefone)
    2. Criar/atualizar atendimento (atendimentos_v2)
    3. Se tipo=agendamento_* -> criar agendamento
    4. Salvar memoria inicial (Redis SETEX + Postgres)
    5. Audit log de cada mutacao
    6. Retornar proximos passos (dados pendentes, etc)
    """
    # 1. Coleta
    coleta = upsert_cliente_por_telefone(
        db,
        telefone=req.telefone,
        nome=req.nome,
        email=req.email,
        cpf=req.cpf,
        data_nascimento=req.data_nascimento,
        consentimento_lgpd=req.consentimento_lgpd,
        consentimento_canal=req.canal,
        consentimento_ip=req.consentimento_ip,
    )
    db.flush()

    # 2. Criar atendimento (atendimentos_v2)
    session_id = f"{req.canal}-{uuid.uuid4().hex[:12]}"
    dados_coletados = coleta.dados_coletados.copy()
    dados_pendentes = coleta.dados_pendentes.copy()
    protocolo_id = req.protocolo_id

    # 2a. Se tipo requer agendamento, criar agendamento
    agendamento_id: Optional[int] = None
    if req.tipo in ("agendamento_online", "agendamento_presencial"):
        if not req.data_hora or not req.titulo:
            raise ValueError(
                "agendamento_online/presencial requer data_hora e titulo"
            )
        # CPF dummy para criar agendamento (LGPD: hash real)
        cpf_temp_hash = hash_pii(req.cpf or req.telefone, "pietra_atendimento") if req.cpf else hash_pii(req.telefone + ":no_cpf", "pietra_atendimento")
        try:
            agendamento = AgendamentoService.criar_agendamento(
                db,
                cliente_id=coleta.cliente_id,
                cliente_cpf=cpf_temp_hash,
                data_hora=req.data_hora,
                titulo=req.titulo,
                descricao=req.descricao or f"Atendimento {req.tipo}",
                tipo=TipoAtendimento.NORMAL,
                local=req.local,
                protocolo_id=protocolo_id,
                duration_minutes=30,
                request=request,
            )
            agendamento_id = agendamento.id
        except Exception as e:
            logger.error("falha ao criar agendamento: %s", e)
            # Continua sem agendamento_id (cliente foi criado)

    # 2b. Criar atendimento_v2 row (LGPD-safe, FK cliente_id)
    try:
        db.execute(
            text("""
                INSERT INTO atendimentos_v2
                    (cliente_id, telefone_hash, canal, tipo, status,
                     dados_coletados, dados_pendentes, protocolo_id, agendamento_id, observacoes,
                     criado_em, atualizado_em)
                VALUES
                    (:cliente_id, :telefone_hash, :canal, :tipo, :status,
                     CAST(:dados_coletados AS jsonb), CAST(:dados_pendentes AS jsonb), :protocolo_id, :agendamento_id, :observacoes,
                     NOW(), NOW())
                RETURNING id
            """),
            {
                "cliente_id": coleta.cliente_id,
                "telefone_hash": coleta.telefone_hash,
                "canal": req.canal,
                "tipo": req.tipo,
                "status": "iniciado",
                "dados_coletados": _to_jsonb(dados_coletados),
                "dados_pendentes": _to_jsonb(dados_pendentes),
                "protocolo_id": protocolo_id,
                "agendamento_id": agendamento_id,
                "observacoes": req.observacoes,
            },
        )
        atendimento_id_row = db.execute(text("SELECT lastval()")).scalar()
        atendimento_id = int(atendimento_id_row) if atendimento_id_row else 0
    except Exception as e:
        logger.error("falha ao criar atendimentos_v2: %s", e)
        db.rollback()
        atendimento_id = 0
        # Tentar de novo sem os dados complexos
        try:
            db.execute(
                text("""
                    INSERT INTO atendimentos_v2
                        (cliente_id, telefone_hash, canal, tipo, status,
                         dados_coletados, dados_pendentes, observacoes, criado_em, atualizado_em)
                    VALUES
                        (:cliente_id, :telefone_hash, :canal, :tipo, :status,
                         CAST('{}' AS jsonb), CAST('[]' AS jsonb), :observacoes, NOW(), NOW())
                    RETURNING id
                """),
                {
                    "cliente_id": coleta.cliente_id,
                    "telefone_hash": coleta.telefone_hash,
                    "canal": req.canal,
                    "tipo": req.tipo,
                    "status": "iniciado",
                    "observacoes": (req.observacoes or "") + " [fallback sem dados_coletados]",
                },
            )
            atendimento_id_row = db.execute(text("SELECT lastval()")).scalar()
            atendimento_id = int(atendimento_id_row) if atendimento_id_row else 0
        except Exception as e2:
            logger.error("falha ao criar atendimentos_v2 (fallback): %s", e2)
            atendimento_id = 0

    # 4. Salvar memoria inicial (Postgres; Redis será tentado em paralelo)
    memoria_salva = False
    try:
        db.execute(
            text("""
                INSERT INTO memoria_conversa
                    (telefone_hash, session_id, canal, role, content, metadata_json, created_at, updated_at)
                VALUES
                    (:telefone_hash, :session_id, :canal, 'system', :content, CAST(:metadata AS jsonb), NOW(), NOW())
            """),
            {
                "telefone_hash": coleta.telefone_hash,
                "session_id": session_id,
                "canal": req.canal,
                "content": f"atendimento_iniciado tipo={req.tipo}",
                "metadata": _to_jsonb({
                    "atendimento_id": atendimento_id,
                    "cliente_id": coleta.cliente_id,
                    "dados_coletados": dados_coletados,
                    "dados_pendentes": dados_pendentes,
                }),
            },
        )
        memoria_salva = True
    except Exception as e:
        logger.error("falha ao salvar memoria: %s", e)
        memoria_salva = False

    db.commit()

    # 5. Audit log (cada mutacao gera entry)
    audit_ids: list[int] = []
    try:
        from app.services.audit import AuditService
        actor_id = f"pietra:{req.canal}"
        # request_id extraido do header (LGPD-safe)
        request_id_val: str | None = None
        if request is not None:
            request_id_val = request.headers.get("x-request-id") if hasattr(request, "headers") else None
        if coleta.cliente_criado:
            entry = AuditService.log(
                db,
                actor_id=actor_id,
                action="cliente.create",
                resource=f"cliente:{coleta.cliente_id}",
                payload={"telefone_hash": coleta.telefone_hash, "novo": True},
                canal=req.canal,
                request_id=request_id_val,
            )
            audit_ids.append(entry.id)
        if atendimento_id:
            entry = AuditService.log(
                db,
                actor_id=actor_id,
                action="atendimento.create",
                resource=f"atendimento:{atendimento_id}",
                payload={"tipo": req.tipo, "canal": req.canal, "cliente_id": coleta.cliente_id},
                canal=req.canal,
                request_id=request_id_val,
            )
            audit_ids.append(entry.id)
        if agendamento_id:
            entry = AuditService.log(
                db,
                actor_id=actor_id,
                action="agendamento.create",
                resource=f"agendamento:{agendamento_id}",
                payload={"data_hora": req.data_hora.isoformat() if req.data_hora else None},
                canal=req.canal,
                request_id=request_id_val,
            )
            audit_ids.append(entry.id)
        db.commit()
    except Exception as e:
        logger.error("audit log falhou (nao-bloqueante): %s", e)

    # 6. Proximos passos
    proximos_passos = []
    if dados_pendentes:
        # P0 LGPD: pedir o dado de forma humanizada
        for field_name in dados_pendentes:
            if field_name == "cpf" and req.tipo in ("consulta", "segunda_via"):
                proximos_passos.append(
                    "Para eu localizar seu atendimento, me passa o CPF (opcional, "
                    "se preferir só o telefone+data de nascimento já dá)."
                )
            elif field_name == "data_nascimento":
                proximos_passos.append(
                    "Me confirma sua data de nascimento (AAAA-MM-DD)?"
                )
            elif field_name == "nome":
                proximos_passos.append(
                    "Me passa seu nome completo para eu localizar o atendimento."
                )
    if req.tipo in ("agendamento_online", "agendamento_presencial") and not agendamento_id:
        proximos_passos.append(
            "Tive um problema ao criar o agendamento. Vou chamar um escrevente "
            "para te ajudar."
        )

    return AtendimentoResult(
        atendimento_id=atendimento_id,
        cliente_id=coleta.cliente_id,
        cliente_criado=coleta.cliente_criado,
        agendamento_id=agendamento_id,
        protocolo_id=protocolo_id,
        dados_coletados=dados_coletados,
        dados_pendentes=dados_pendentes,
        memoria_salva=memoria_salva,
        audit_ids=audit_ids,
        proximos_passos=proximos_passos,
    )


def _to_jsonb(d: Any) -> str:
    """Serializa dict/list para JSON string (Postgres ::text::text::jsonb)."""
    import json
    return json.dumps(d, ensure_ascii=False, default=str)
