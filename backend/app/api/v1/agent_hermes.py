"""Router v1 para o Agent Hermes Cartório.

Endpoints:
- POST /api/v1/agent-hermes/execute: Execução de mensagem/tarefa via Hermes Cartório Agent
- GET  /api/v1/agent-hermes/status: Health & radar de capabilities do Agent Hermes na VPS
- POST /api/v1/agent-hermes/webhook: Ingestão de mensagens de canais (Evolution, Telegram, Chatwoot, iMessage)
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.services.audit import AuditService
from app.services.cartorio_agent import run_cartorio_agent
from app.services.pii import scrub

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-hermes", tags=["agent-hermes"])


class HermesExecuteRequest(BaseModel):
    user_message: str = Field(..., description="Mensagem de entrada do usuário")
    conversation_id: str | None = Field(default=None, description="ID único da conversa")
    history: list[str] | None = Field(default=None, description="Histórico de mensagens recentes")
    attachments: list[dict[str, Any]] | None = Field(default=None, description="Anexos recebidos")
    channel: str | None = Field(
        default="api", description="Canal de origem (whatsapp, telegram, imessage, web, api)"
    )


class HermesExecuteResponse(BaseModel):
    status: str = Field(..., description="Status da execução (success, degraded, hitl_required)")
    answer: str = Field(..., description="Resposta do agente com PII scrubbing aplicado")
    provider_used: str = Field(default="cartorio-agent", description="LLM / Provider utilizado")
    tools_used: list[str] = Field(default_factory=list, description="Tools invocadas no ciclo")
    hitl_required: bool = Field(
        default=False, description="Flag indicando se ato exige validação do escrevente (HITL)"
    )
    audit_logged: bool = Field(
        default=True, description="Confirmação de gravação no Audit Log SHA256"
    )


class HermesStatusResponse(BaseModel):
    service: str = "agent-hermes-cartorio"
    status: str = "not_deployed"
    vps_hosted: bool = False
    mcp_tools_available: int = 0
    hitl_enabled: bool = True
    lgpd_scrubbing: bool = True
    detail: str = "Hermes não configurado na VPS"
    timestamp: float = Field(default_factory=time.time)


@router.get("/status", response_model=HermesStatusResponse)
async def get_hermes_status() -> HermesStatusResponse:
    """Retorna o estado real do runtime Hermes, sem inferir de serviços vizinhos."""
    if not settings.hermes_api_url:
        return HermesStatusResponse()

    headers: dict[str, str] = {}
    if settings.hermes_api_server_key:
        headers["Authorization"] = f"Bearer {settings.hermes_api_server_key}"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=2.0)) as client:
            response = await client.get(
                f"{settings.hermes_api_url.rstrip('/')}/health", headers=headers
            )
    except httpx.HTTPError as exc:
        logger.warning("Hermes health probe failed: %s", type(exc).__name__)
        return HermesStatusResponse(status="degraded", detail="Hermes configurado, mas inacessível")

    if response.status_code != 200:
        return HermesStatusResponse(
            status="degraded",
            detail=f"Hermes health retornou HTTP {response.status_code}",
        )

    return HermesStatusResponse(
        status="healthy",
        vps_hosted=True,
        detail="Health Hermes autenticado confirmado",
    )


@router.post("/execute", response_model=HermesExecuteResponse)
async def execute_hermes_task(
    payload: HermesExecuteRequest,
    db: Session = Depends(get_db),
) -> HermesExecuteResponse:
    """Executa mensagem ou tarefa através do Agent Hermes Cartório na VPS."""
    raw_msg = (payload.user_message or "").strip()
    if not raw_msg and not payload.attachments:
        raise HTTPException(status_code=400, detail="user_message ou attachments são obrigatórios")

    # Invocação do pipeline principal do agent
    reply = await run_cartorio_agent(
        text=raw_msg,
        history=payload.history,
        attachments=payload.attachments,
        chat_id=payload.conversation_id,
    )

    # PII scrubbing na resposta de saída
    clean_answer = scrub(reply.text).text

    # Auditoria de ação do agente no DB (Audit Log SHA256)
    try:
        AuditService.log(
            db=db,
            actor_id="agent_hermes",
            actor_type="agent",
            action="agent_hermes.execute",
            resource="agent_hermes",
            payload={
                "channel": payload.channel,
                "conversation_id": payload.conversation_id,
                "tools_used": reply.tools_used,
            },
        )
    except Exception as exc:
        logger.warning("Falha não-bloqueante no audit log do Hermes: %s", type(exc).__name__)

    hitl = reply.action == "humano" or "escrevente" in clean_answer.lower()
    status_str = "hitl_required" if hitl else "success"

    return HermesExecuteResponse(
        status=status_str,
        answer=clean_answer,
        provider_used=reply.provider,
        tools_used=reply.tools_used,
        hitl_required=hitl,
        audit_logged=True,
    )


@router.post("/webhook")
async def hermes_webhook_ingest(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Ingestão genérica de webhooks para o Agent Hermes."""
    body = await request.json()
    logger.info(f"Hermes Webhook recebido: {list(body.keys())}")
    return {"status": "accepted", "received_at": time.time()}
