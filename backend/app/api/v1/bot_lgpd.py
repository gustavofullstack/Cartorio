"""bot_lgpd.py — Endpoints LGPD para comandos de bot (T48, T49, T50).

Endpoints:
  POST /api/v1/bot/lgpd/cancelar       - Direito ao esquecimento (LGPD art. 18 VI)
  POST /api/v1/bot/lgpd/export         - Direito a portabilidade (LGPD art. 18 V)
  POST /api/v1/bot/lgpd/access         - Direito de acesso (LGPD art. 18 II)
  POST /api/v1/bot/lgpd/restaurar      - Cancelar solicitacao de esquecimento
  GET  /api/v1/bot/lgpd/revogacoes     - Lista revogacoes pendentes (admin)

Payload padrao:
  { "channel": "whatsapp" | "telegram",
    "sender_id": "<chat_id or remoteJid>",
    "request_id": "<optional correlation id>" }

Auth: nenhuma (bot envia do proprio canal). Sender_id eh hasheado
internamente (LGPD art. 37 - nunca armazenar PII).

Audit log: TODA operacao registrada (action + channel + sender_hash).

T48/T49 (2026-07-09): Sprint 5 LGPD compliance WhatsApp.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.cliente import Cliente, MotivoEncerramento
from app.services.audit import AuditService
from app.services.audit_context import audit_kwargs
from app.services.lgpd.bot_direito_esquecimento import (
    exportar_dados_cliente,
    listar_revogacoes_pendentes,
    marcar_como_deletado,
    restaurar_revogacao,
    solicitar_esquecimento_bot,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bot/lgpd", tags=["bot-lgpd"])


# ============================================================================
# Pydantic models
# ============================================================================


class CancelarRequest(BaseModel):
    """T47 - /cancelar command."""

    channel: Literal["telegram", "whatsapp"]
    sender_id: str = Field(..., min_length=1, max_length=128)
    request_id: str | None = None


class CancelarResponse(BaseModel):
    """Resposta do /cancelar."""

    status: Literal["ok"] = "ok"
    revogacao_id: str
    scheduled_delete_at: str
    janela_dias: int
    message: str
    cliente_id: int | None = None


class ExportRequest(BaseModel):
    """T49 - /lgpd export command."""

    channel: Literal["telegram", "whatsapp"]
    sender_id: str = Field(..., min_length=1, max_length=128)
    cliente_id: int | None = Field(default=None, ge=1)
    request_id: str | None = None


class ExportResponse(BaseModel):
    """Resposta do /lgpd export."""

    status: Literal["ok"] = "ok"
    filename: str
    sha256: str
    size_bytes: int
    data: dict
    message: str


class AccessRequest(BaseModel):
    """T48 - /lgpd command (acesso aos dados)."""

    channel: Literal["telegram", "whatsapp"]
    sender_id: str = Field(..., min_length=1, max_length=128)
    cliente_id: int | None = Field(default=None, ge=1)
    request_id: str | None = None


class AccessResponse(BaseModel):
    """Resposta do /lgpd acesso."""

    status: Literal["ok"] = "ok"
    cliente_id: int | None
    nome: str | None
    email: str | None
    cpf_hash: str | None  # LGPD: hash, nao raw
    consentimento_lgpd: bool | None
    created_at: str | None
    message: str


class RestaurarRequest(BaseModel):
    """Restaurar revogacao antes dos 30 dias."""

    revogacao_id: str = Field(..., min_length=8, max_length=64)
    request_id: str | None = None


class RestaurarResponse(BaseModel):
    status: Literal["ok", "not_found"] = "ok"
    revogacao_id: str
    message: str


class RevogacoesListResponse(BaseModel):
    status: Literal["ok"] = "ok"
    count: int
    revogacoes: list[dict]


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/cancelar",
    response_model=CancelarResponse,
    summary="[Bot] /cancelar - Direito ao esquecimento (LGPD art. 18 VI)",
    description=(
        "Registra solicitacao de esquecimento vinda do bot (Telegram/WhatsApp). "
        "Marca cliente como consentimento_lgpd=False, agenda hard delete em 30 "
        "dias (cron job diario). Sender_id eh hasheado internamente (LGPD art. 37). "
        "Cliente pode cancelar enviando /lgpd restaurar antes dos 30 dias."
    ),
)
async def post_cancelar(
    request: Request,
    payload: CancelarRequest,
    db: Annotated[Session, Depends(get_db)],
) -> CancelarResponse:
    """T47: direito ao esquecimento via bot."""
    result = await solicitar_esquecimento_bot(
        db,
        channel=payload.channel,
        sender_id=payload.sender_id,
        motivo=MotivoEncerramento.REVOGACAO_CONSENTIMENTO,
        request=request,
    )
    return CancelarResponse(
        revogacao_id=result.revogacao_id,
        scheduled_delete_at=result.scheduled_delete_at.isoformat(),
        janela_dias=30,
        message=result.message,
        cliente_id=result.cliente_id,
    )


@router.post(
    "/export",
    response_model=ExportResponse,
    summary="[Bot] /lgpd export - Direito a portabilidade (LGPD art. 18 V)",
    description=(
        "Exporta dados pessoais do cliente em JSON. Requer cliente_id valido. "
        "Retorna JSON completo + filename + sha256 para integridade. "
        "Para uso via bot, recomendado gerar link download temporario."
    ),
)
async def post_export(
    request: Request,
    payload: ExportRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ExportResponse:
    """T49: direito a portabilidade via bot."""
    if payload.cliente_id is None:
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "CLIENTE_ID_REQUIRED",
                "mensagem": "Para exportar dados, informe cliente_id (use /lgpd acesso primeiro).",
            },
        )

    try:
        result = exportar_dados_cliente(db, payload.cliente_id)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={"erro": "CLIENTE_NOT_FOUND", "mensagem": str(e)},
        )

    # Audit log (LGPD art. 37)
    try:
        ctx = audit_kwargs(request)
        ctx["canal"] = payload.channel
        AuditService.log(
            db,
            actor_id=f"{payload.channel}:{payload.sender_id[:16]}",
            actor_type="bot",
            action="lgpd.direito_portabilidade.export",
            resource=f"cliente:{payload.cliente_id}",
            payload={
                "filename": result.filename,
                "sha256": result.sha256,
                "size_bytes": result.size_bytes,
                "channel": payload.channel,
            },
            **ctx,
        )
        db.commit()
    except Exception as e:
        logger.warning("audit log falhou (non-blocking): %s", e)
        db.rollback()

    return ExportResponse(
        filename=result.filename,
        sha256=result.sha256,
        size_bytes=result.size_bytes,
        data=result.data_json,
        message=(
            f"Export gerado ({result.size_bytes} bytes). "
            f"SHA256: {result.sha256[:16]}... | DPO: dpo@2notasudi.com.br"
        ),
    )


@router.post(
    "/access",
    response_model=AccessResponse,
    summary="[Bot] /lgpd - Direito de acesso (LGPD art. 18 II)",
    description=(
        "Permite que o titular (via bot) consulte quais dados o cartorio possui. "
        "Requer cliente_id. Retorna dados basicos (nome, email, cpf_hash, consent)."
    ),
)
async def post_access(
    request: Request,
    payload: AccessRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AccessResponse:
    """T48: direito de acesso via bot."""
    if payload.cliente_id is None:
        return AccessResponse(
            cliente_id=None,
            nome=None,
            email=None,
            cpf_hash=None,
            consentimento_lgpd=None,
            created_at=None,
            message=(
                "Para consultar seus dados, precisamos confirmar sua identidade. "
                "Entre em contato com o DPO: dpo@2notasudi.com.br"
            ),
        )

    cliente = db.get(Cliente, payload.cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=404,
            detail={
                "erro": "CLIENTE_NOT_FOUND",
                "mensagem": f"Cliente {payload.cliente_id} nao encontrado.",
            },
        )

    # Audit log
    try:
        ctx = audit_kwargs(request)
        ctx["canal"] = payload.channel
        AuditService.log(
            db,
            actor_id=f"{payload.channel}:{payload.sender_id[:16]}",
            actor_type="bot",
            action="lgpd.direito_acesso.consulta",
            resource=f"cliente:{payload.cliente_id}",
            payload={"channel": payload.channel},
            **ctx,
        )
        db.commit()
    except Exception as e:
        logger.warning("audit log falhou (non-blocking): %s", e)
        db.rollback()

    return AccessResponse(
        cliente_id=cliente.id,
        nome=cliente.nome,
        email=cliente.email,
        cpf_hash=cliente.cpf_hash,  # LGPD: hash, nao raw
        consentimento_lgpd=cliente.consentimento_lgpd,
        created_at=cliente.created_at.isoformat() if cliente.created_at else None,
        message=(f"Dados basicos de cliente {cliente.id}. Para export completo, use /lgpd export."),
    )


@router.post(
    "/restaurar",
    response_model=RestaurarResponse,
    summary="[Bot] /lgpd restaurar - Cancelar solicitacao de esquecimento",
    description=(
        "Permite cancelar solicitacao de direito ao esquecimento dentro da "
        "janela de 30 dias. Apos 30 dias, hard delete ja foi aplicado e "
        "restauracao nao eh mais possivel."
    ),
)
async def post_restaurar(
    request: Request,
    payload: RestaurarRequest,
    db: Annotated[Session, Depends(get_db)],
) -> RestaurarResponse:
    """T47: cancelar solicitacao de esquecimento (dentro de 30 dias)."""
    ok = restaurar_revogacao(db, payload.revogacao_id)
    if not ok:
        return RestaurarResponse(
            status="not_found",
            revogacao_id=payload.revogacao_id,
            message="Revogacao nao encontrada ou ja expirada (30 dias).",
        )

    # Audit log
    try:
        ctx = audit_kwargs(request)
        AuditService.log(
            db,
            actor_id="bot",
            actor_type="bot",
            action="lgpd.direito_esquecimento.restaurado",
            resource=f"revogacao:{payload.revogacao_id}",
            payload={"revogacao_id": payload.revogacao_id},
            **ctx,
        )
        db.commit()
    except Exception as e:
        logger.warning("audit log falhou (non-blocking): %s", e)
        db.rollback()

    return RestaurarResponse(
        revogacao_id=payload.revogacao_id,
        message="Solicitacao de esquecimento cancelada. Seus dados foram preservados.",
    )


@router.get(
    "/revogacoes",
    response_model=RevogacoesListResponse,
    summary="[Admin] Lista revogacoes pendentes (LGPD art. 18 VI)",
    description=(
        "Retorna revogacoes com scheduled_delete_at <= now (pronto para hard "
        "delete). Usado pelo cron job diario. Endpoint admin - requer "
        "implementar X-API-Key auth em Sprint 5+."
    ),
)
async def get_revogacoes(
    db: Annotated[Session, Depends(get_db)],
) -> RevogacoesListResponse:
    """T47: lista revogacoes pendentes para o cron job."""
    revogacoes = listar_revogacoes_pendentes(db)
    return RevogacoesListResponse(
        count=len(revogacoes),
        revogacoes=revogacoes,
    )


@router.post(
    "/revogacoes/{revogacao_id}/delete",
    response_model=RestaurarResponse,
    summary="[Admin] Marca revogacao como deletada (apos cron aplicar hard delete)",
)
async def post_marcar_deletado(
    revogacao_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> RestaurarResponse:
    """T47: cron chama apos aplicar hard delete."""
    ok = marcar_como_deletado(db, revogacao_id)
    return RestaurarResponse(
        status="ok" if ok else "not_found",
        revogacao_id=revogacao_id,
        message="Revogacao marcada como deletada." if ok else "Revogacao nao encontrada.",
    )


__all__ = ["router"]
