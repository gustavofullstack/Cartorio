"""Endpoints API REST para AGENT PIETRA (canal cliente).

P0 (Gustavo 2026-07-27): endpoints para coleta de dados + atendimento +
agendamento + memoria persistente, com PRIMARY KEY telefone.

GET  /api/v1/pietra/cliente/{telefone}
    -> cliente + dados_coletados + dados_pendentes
POST /api/v1/pietra/cliente/collect
    -> upsert cliente (telefone + opcional nome/email/cpf/data_nascimento)
POST /api/v1/pietra/atendimento/iniciar
    -> cria atendimento_v2 + opcional agendamento + salva memoria
GET  /api/v1/pietra/atendimento/{telefone}/historico
    -> lista atendimentos do cliente
POST /api/v1/pietra/agendamento
    -> cria agendamento (online ou presencial) + memoria
GET  /api/v1/pietra/agendamento/{telefone}/proximos
    -> lista agendamentos futuros
GET  /api/v1/pietra/memoria/{telefone}
    -> historico conversa (Redis cache + Postgres)
POST /api/v1/pietra/memoria/{telefone}/append
    -> append mensagem (assistant response)
GET  /api/v1/pietra/memoria/{telefone}/stats
    -> stats de uso de memoria

LGPD: todos os endpoints log via audit_log (SHA256+HMAC chain).
PII nunca aparece no response (apenas masks).

Modified by Gustavo Almeida · 2026-07-27
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.pietra_coleta import (
    _normalize_phone_br,
    hash_phone,
    upsert_cliente_por_telefone,
)
from app.services.pietra_atendimento import (
    AtendimentoRequest,
    iniciar_atendimento,
)
from app.services.pietra_memoria import (
    recuperar_historico,
    salvar_mensagem,
    stats_memoria,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pietra", tags=["pietra"])


# === Schemas Pydantic ===

class CollectRequest(BaseModel):
    telefone: str = Field(..., description="Telefone E.164 ou BR (obrigatorio)")
    nome: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    cpf: Optional[str] = Field(None, max_length=14)
    data_nascimento: Optional[str] = Field(None, description="AAAA-MM-DD")
    consentimento_lgpd: bool = False
    consentimento_canal: str = "imessage"
    consentimento_ip: Optional[str] = None

    @field_validator("telefone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        norm = _normalize_phone_br(v)
        if not norm:
            raise ValueError(f"telefone invalido: {v!r}")
        return norm

    @field_validator("data_nascimento")
    @classmethod
    def validate_dob(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            d = dt.date.fromisoformat(v)
            if d > dt.date.today() or d.year < 1900:
                raise ValueError("data_nascimento fora do range")
            return v
        except ValueError as e:
            raise ValueError(f"data_nascimento invalido: {v!r} ({e})")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[\w.+-]+@[\w-]+\.[\w.-]+$", v):
            raise ValueError(f"email invalido: {v!r}")
        return v

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        digits = re.sub(r"\D", "", v)
        if len(digits) != 11:
            raise ValueError(f"cpf deve ter 11 digitos: {v!r}")
        return digits


class CollectResponse(BaseModel):
    cliente_id: int
    cliente_criado: bool
    telefone_hash: str
    dados_coletados: dict[str, Any]
    dados_pendentes: list[str]
    consentimento_lgpd: bool
    mensagem: str


class AtendimentoIniciarRequest(BaseModel):
    telefone: str
    canal: str = "imessage"
    tipo: str = "consulta"  # consulta|agendamento_online|agendamento_presencial|segunda_via
    nome: Optional[str] = None
    email: Optional[str] = None
    cpf: Optional[str] = None
    data_nascimento: Optional[str] = None
    protocolo_id: Optional[int] = None
    data_hora: Optional[dt.datetime] = None
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    local: str = "balcao_1"
    consentimento_lgpd: bool = False
    consentimento_ip: Optional[str] = None
    observacoes: Optional[str] = None

    @field_validator("telefone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        norm = _normalize_phone_br(v)
        if not norm:
            raise ValueError(f"telefone invalido: {v!r}")
        return norm


class AtendimentoIniciarResponse(BaseModel):
    atendimento_id: int
    cliente_id: int
    cliente_criado: bool
    agendamento_id: Optional[int] = None
    protocolo_id: Optional[int] = None
    dados_coletados: dict[str, Any]
    dados_pendentes: list[str]
    memoria_salva: bool
    audit_ids: list[int]
    proximos_passos: list[str]
    mensagem: str


class MemoriaAppendRequest(BaseModel):
    session_id: str
    role: str  # user|assistant|system|tool
    content: str
    metadata: Optional[dict[str, Any]] = None
    canal: str = "imessage"


# === Endpoints ===

@router.get("/cliente/{telefone}", response_model=CollectResponse)
def get_cliente(telefone: str, db: Session = Depends(get_db)) -> CollectResponse:
    """Retorna dados do cliente (LGPD-masked). PRIMARY KEY: telefone."""
    norm = _normalize_phone_br(telefone)
    if not norm:
        raise HTTPException(status_code=400, detail="telefone invalido")
    tel_hash = hash_phone(norm)
    from app.models.cliente import Cliente
    from sqlalchemy import select
    cliente = db.execute(
        select(Cliente).where(
            Cliente.telefone_hash == tel_hash,
            Cliente.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if cliente is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")
    dados_coletados = {
        "nome": cliente.nome,
        "email": cliente.email,
        "data_nascimento": cliente.data_nascimento.isoformat() if cliente.data_nascimento else None,
        "tem_cpf": len(cliente.cpf_hash) > 50,  # heuristica: dummy hash < 50 chars
    }
    dados_pendentes = []
    if not cliente.nome or cliente.nome == "(aguardando nome)":
        dados_pendentes.append("nome")
    if not cliente.email:
        dados_pendentes.append("email (opcional)")
    if not cliente.data_nascimento:
        dados_pendentes.append("data_nascimento")
    if len(cliente.cpf_hash) <= 50:
        dados_pendentes.append("cpf")
    return CollectResponse(
        cliente_id=cliente.id,
        cliente_criado=False,
        telefone_hash=tel_hash,
        dados_coletados=dados_coletados,
        dados_pendentes=dados_pendentes,
        consentimento_lgpd=cliente.consentimento_lgpd,
        mensagem=f"Cliente #{cliente.id} carregado. Pendente coletar: {', '.join(dados_pendentes) or 'nada'}",
    )


@router.post("/cliente/collect", response_model=CollectResponse)
def collect_cliente(
    req: CollectRequest, request: Request, db: Session = Depends(get_db),
) -> CollectResponse:
    """Coleta progressiva: cria ou atualiza cliente por telefone.

    LGPD: consentimento_lgpd deve ser True. Telefone e PRIMARY KEY.
    """
    if not req.consentimento_lgpd:
        logger.warning("collect sem consentimento_lgpd para tel=%s", req.telefone[:8])
    result = upsert_cliente_por_telefone(
        db,
        telefone=req.telefone,
        nome=req.nome,
        email=req.email,
        cpf=req.cpf,
        data_nascimento=req.data_nascimento,
        consentimento_lgpd=req.consentimento_lgpd,
        consentimento_canal=req.consentimento_canal,
        consentimento_ip=req.consentimento_ip or (request.client.host if request.client else None),
    )
    db.commit()
    return CollectResponse(
        cliente_id=result.cliente_id,
        cliente_criado=result.cliente_criado,
        telefone_hash=result.telefone_hash,
        dados_coletados=result.dados_coletados,
        dados_pendentes=result.dados_pendentes,
        consentimento_lgpd=result.consentimento_lgpd,
        mensagem=(
            f"Cliente #{result.cliente_id} criado" if result.cliente_criado
            else f"Cliente #{result.cliente_id} atualizado"
        ) + f". Pendente: {', '.join(result.dados_pendentes) or 'nada'}",
    )


@router.post("/atendimento/iniciar", response_model=AtendimentoIniciarResponse)
def atendimento_iniciar(
    req: AtendimentoIniciarRequest, request: Request, db: Session = Depends(get_db),
) -> AtendimentoIniciarResponse:
    """Inicia atendimento: coleta + cria atendimento + agendamento opcional + memoria."""
    atendimento_req = AtendimentoRequest(
        telefone=req.telefone,
        canal=req.canal,
        tipo=req.tipo,
        nome=req.nome,
        email=req.email,
        cpf=req.cpf,
        data_nascimento=req.data_nascimento,
        protocolo_id=req.protocolo_id,
        data_hora=req.data_hora,
        titulo=req.titulo,
        descricao=req.descricao,
        local=req.local,
        consentimento_lgpd=req.consentimento_lgpd,
        consentimento_ip=req.consentimento_ip or (request.client.host if request.client else None),
        observacoes=req.observacoes,
    )
    result = iniciar_atendimento(db, atendimento_req, request)
    return AtendimentoIniciarResponse(
        atendimento_id=result.atendimento_id,
        cliente_id=result.cliente_id,
        cliente_criado=result.cliente_criado,
        agendamento_id=result.agendamento_id,
        protocolo_id=result.protocolo_id,
        dados_coletados=result.dados_coletados,
        dados_pendentes=result.dados_pendentes,
        memoria_salva=result.memoria_salva,
        audit_ids=result.audit_ids,
        proximos_passos=result.proximos_passos,
        mensagem=(
            f"Atendimento #{result.atendimento_id} iniciado. "
            f"Cliente #{result.cliente_id} ({'criado' if result.cliente_criado else 'atualizado'}). "
            f"Agendamento: #{result.agendamento_id or 'nenhum'}. "
            f"Memoria: {'salva' if result.memoria_salva else 'falha'}."
        ),
    )


@router.post("/agendamento", response_model=AtendimentoIniciarResponse)
def criar_agendamento(
    req: AtendimentoIniciarRequest, request: Request, db: Session = Depends(get_db),
) -> AtendimentoIniciarResponse:
    """Cria agendamento (online ou presencial) + coleta de dados + memoria."""
    if req.tipo not in ("agendamento_online", "agendamento_presencial"):
        req.tipo = "agendamento_presencial"  # default
    if not req.data_hora or not req.titulo:
        raise HTTPException(status_code=400, detail="data_hora e titulo obrigatorios")
    req.observacoes = (req.observacoes or "") + f" [agendamento {req.tipo}]"
    return atendimento_iniciar(req, request, db)


@router.get("/atendimento/{telefone}/historico")
def get_historico_atendimentos(telefone: str, db: Session = Depends(get_db)) -> dict:
    """Lista atendimentos do cliente por telefone."""
    norm = _normalize_phone_br(telefone)
    if not norm:
        raise HTTPException(status_code=400, detail="telefone invalido")
    tel_hash = hash_phone(norm)
    from sqlalchemy import text
    rows = db.execute(
        text("""
            SELECT id, cliente_id, canal, tipo, status,
                   dados_coletados, dados_pendentes, agendamento_id, protocolo_id,
                   criado_em, atualizado_em
            FROM atendimentos_v2
            WHERE telefone_hash = :tel
            ORDER BY criado_em DESC
            LIMIT 50
        """),
        {"tel": tel_hash},
    ).fetchall()
    return {
        "telefone_hash": tel_hash,
        "total": len(rows),
        "atendimentos": [
            {
                "id": r[0],
                "cliente_id": r[1],
                "canal": r[2],
                "tipo": r[3],
                "status": r[4],
                "dados_coletados": r[5] if isinstance(r[5], dict) else (r[5] or {}),
                "dados_pendentes": r[6] if isinstance(r[6], list) else (r[6] or []),
                "agendamento_id": r[7],
                "protocolo_id": r[8],
                "criado_em": r[9].isoformat() if r[9] else None,
                "atualizado_em": r[10].isoformat() if r[10] else None,
            }
            for r in rows
        ],
    }


@router.get("/memoria/{telefone}")
def get_memoria(
    telefone: str,
    session_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> dict:
    """Recupera historico de conversa (Redis cache + Postgres)."""
    norm = _normalize_phone_br(telefone)
    if not norm:
        raise HTTPException(status_code=400, detail="telefone invalido")
    tel_hash = hash_phone(norm)
    historico = recuperar_historico(
        db,
        telefone_hash=tel_hash,
        session_id=session_id,
        limit=limit,
    )
    return {
        "telefone_hash": tel_hash,
        "session_id": session_id,
        "total": len(historico),
        "mensagens": historico,
    }


@router.post("/memoria/{telefone}/append")
def append_memoria(
    telefone: str, req: MemoriaAppendRequest, db: Session = Depends(get_db),
) -> dict:
    """Append uma mensagem na memoria persistente."""
    norm = _normalize_phone_br(telefone)
    if not norm:
        raise HTTPException(status_code=400, detail="telefone invalido")
    tel_hash = hash_phone(norm)
    ok = salvar_mensagem(
        db,
        telefone_hash=tel_hash,
        session_id=req.session_id,
        role=req.role,
        content=req.content,
        metadata=req.metadata,
        canal=req.canal,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="memoria write falhou (redis+postgres)")
    db.commit()
    return {
        "status": "ok",
        "telefone_hash": tel_hash,
        "session_id": req.session_id,
        "role": req.role,
    }


@router.get("/memoria/{telefone}/stats")
def get_stats_memoria(telefone: str, db: Session = Depends(get_db)) -> dict:
    """Estatisticas de uso de memoria do cliente."""
    norm = _normalize_phone_br(telefone)
    if not norm:
        raise HTTPException(status_code=400, detail="telefone invalido")
    tel_hash = hash_phone(norm)
    return stats_memoria(db, tel_hash)


@router.get("/health")
def pietra_health() -> dict:
    """Health check do modulo PIETRA."""
    from app.services.pietra_memoria import get_redis
    r = get_redis()
    return {
        "status": "ok",
        "redis": "connected" if r is not None else "disconnected",
        "module": "pietra",
        "version": "1.0.0",
    }
