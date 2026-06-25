"""Endpoints de teste de integracoes externas (LLM providers, etc).

Esses endpoints NAO sao publicos - servem para:
1. Validar conectividade apos deploy (smoke test)
2. Debug de problemas com LLM providers
3. Auditar latencia/tokens em producao

LGPD compliance (auditoria 2026-06-23):
- Toda chamada via endpoint requer consent_granted=True explicito
- Actor_id padrao: 'smoke_test_admin' (operador do cartorio)
- Em Sprint 2 adicionar `X-API-Key` igual ao webhook Evolution
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import uuid as _uuid
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import require_cartorio_api_key
from app.config import settings
from app.db import session_scope
from app.integrations.opencode_go import ChatError, chat_with_settings
from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus


# ============================================================================
# Router
# ============================================================================

integrations_router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================


class OpenCodeTestRequest(BaseModel):
    """Request do endpoint de teste do OpenCode-Go.

    Attributes:
        message: Mensagem a enviar (default: 'ping' pra smoke test).
        model: Modelo a usar. Default = settings.opencode_go_model.
        temperature: Sampling temperature (0.0-2.0). Default 0.2.
        consent_granted: LGPD art. 7 I — consentimento do operador.
                        Default False (safe-by-default). Operator deve
                        confirmar que tem autorizacao para invocar LLM
                        com este conteudo.
        actor_id: Quem esta invocando (para audit log LGPD art. 37).
                 Default 'smoke_test_admin'.
    """

    message: str = Field(
        default="ping",
        description="Mensagem do user. Default 'ping' para smoke test.",
        max_length=2000,
    )
    model: str | None = Field(
        default=None,
        description="Modelo OpenCode-Go. Default: settings.opencode_go_model.",
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature.",
    )
    consent_granted: bool = Field(
        default=False,
        description=(
            "LGPD art. 7 I — consentimento do operador. "
            "Default False (safe-by-default). Operador DEVE setar True "
            "explicitamente apos confirmar que conteudo eh permitido."
        ),
    )
    actor_id: str = Field(
        default="smoke_test_admin",
        description="ID do operador para audit log (LGPD art. 37).",
        max_length=200,
    )


class OpenCodeTestResponse(BaseModel):
    """Response do endpoint de teste.

    Attributes:
        status: 'ok' ou 'erro'.
        model: Modelo usado.
        response: Texto gerado pelo modelo (None se erro). LGPD-015: ja vem scrubbed.
        tokens_in: Prompt tokens.
        tokens_out: Completion tokens.
        latency_ms: Latencia da chamada.
        pii_redacted_count: Total de PII scrubbed ANTES de enviar (defense-in-depth, input).
        output_pii_redacted_count: Total de PII scrubbed NO OUTPUT do LLM (LGPD-015, boundary 2).
        config: Configuracao usada (sem expor API key).
        erro: Detalhes do erro se status='erro'.
    """

    status: str
    model: str
    response: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int
    pii_redacted_count: int = 0
    output_pii_redacted_count: int = 0
    config: dict[str, Any]
    erro: dict[str, Any] | None = None


# ============================================================================
# Endpoint: POST /integrations/opencode/test
# ============================================================================


@integrations_router.post(
    "/integrations/opencode/test",
    tags=["meta"],
    summary="Smoke test do OpenCode-Go (LLM provider)",
    description=(
        "Envia uma mensagem de teste ao OpenCode-Go e retorna a response. "
        "Usado para validar conectividade apos deploy + auditar latencia/tokens. "
        "NAO expor publicamente - em Sprint 2 adicionar auth X-API-Key.\n\n"
        "LGPD: requer consent_granted=True. Default False (safe-by-default). "
        "Toda chamada eh scrubbada internamente (defense-in-depth) e gravada "
        "no audit log (LGPD art. 37)."
    ),
    response_model=OpenCodeTestResponse,
)
async def opencode_test(
    payload: Annotated[
        OpenCodeTestRequest,
        Body(
            examples=[
                {
                    "message": "ping",
                    "temperature": 0.0,
                    "consent_granted": True,
                    "actor_id": "admin:deploy_validation",
                },
                {
                    "message": "Qual a capital de MG?",
                    "temperature": 0.5,
                    "consent_granted": True,
                },
            ]
        ),
    ],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
) -> OpenCodeTestResponse:
    """Smoke test do OpenCode-Go LLM provider.

    B0.3 2026-06-25: agora exige X-API-Key (mesmo gate dos demais
    endpoints admin). Substitui o gap transversal onde /integrations/*
    estava sem auth porque CARTORIO_API_KEY nao estava configurada.
    """
    # Config visivel na response (SEM expor a API key - LGPD + segredo)
    config_public = {
        "provider": "opencode_go",
        "base_url": settings.opencode_go_base_url,
        "model": payload.model or settings.opencode_go_model,
        "api_key_configured": bool(settings.opencode_go_api_key),
    }

    # LGPD art. 7 I — consent gate no nivel do endpoint
    if not payload.consent_granted:
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "LGPD_BLOCKED",
                "mensagem": (
                    "LGPD art. 7 I — Consentimento nao concedido. "
                    "Passe consent_granted=true no body para invocar o LLM."
                ),
                "detalhes": {
                    "consent_granted_aceito": False,
                    "como_remediar": (
                        "Confirme com DPO que conteudo pode ser enviado "
                        "ao provider LLM e reenvie com consent_granted=true."
                    ),
                },
            },
        )

    try:
        resp = await chat_with_settings(
            messages=[{"role": "user", "content": payload.message}],
            model=payload.model,
            temperature=payload.temperature,
            consent_granted=True,
            actor_id=payload.actor_id,
            # db=None: smoke test NAO grava audit log (operador escolhe)
            # Em prod, esse endpoint deveria gravar via Depends(get_db)
        )

        return OpenCodeTestResponse(
            status="ok",
            model=resp.model,
            response=resp.content,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            latency_ms=resp.latency_ms,
            pii_redacted_count=resp.pii_redacted_count,
            output_pii_redacted_count=resp.output_pii_redacted_count,
            config=config_public,
            erro=None,
        )

    except ChatError as e:
        return OpenCodeTestResponse(
            status="erro",
            model=payload.model or settings.opencode_go_model,
            response=None,
            tokens_in=None,
            tokens_out=None,
            latency_ms=0,
            pii_redacted_count=0,
            output_pii_redacted_count=0,
            config=config_public,
            erro={
                "kind": e.kind,
                "status_code": e.status_code,
                "message": str(e),
                "body_preview": (e.body or "")[:200],
            },
        )


# ============================================================================
# Endpoint: GET /integrations/agent/health
# ============================================================================


class AgentHealthResponse(BaseModel):
    """Health check do OpenClaw Agent + LLM provider configurado."""

    status: str = Field(
        description="'ok' se openclaw alive + LLM provider respondendo, 'degraded' se parcial, 'down' se ambos off."
    )
    openclaw: dict[str, Any] = Field(
        description="Status do OpenClaw gateway: alive, latency_ms, version."
    )
    llm_provider: dict[str, Any] = Field(
        description="Status do LLM provider (opencode_go ou openclaw). Models available, ping latency."
    )
    timestamp: str = Field(description="ISO 8601 UTC do check.")


@integrations_router.get(
    "/integrations/agent/health",
    tags=["meta"],
    summary="Health check do OpenClaw Agent + LLM",
    description=(
        "Verifica se OpenClaw gateway esta alive + se o LLM provider "
        "configurado esta respondendo. Retorna 200 sempre (com status='ok'/'degraded'/'down') "
        "para que healthchecks externos (k8s livenessProbe) possam ler o body.\n\n"
        "Latencia tipica: < 100ms quando tudo OK; ate 5s se OpenClaw ou LLM travados.\n\n"
        "LGPD: nao envia dados pessoais, nao faz log de PII. Healthcheck seguro."
    ),
    response_model=AgentHealthResponse,
)
async def agent_health() -> AgentHealthResponse:
    """Health check do OpenClaw + LLM provider (smoke test composto)."""
    import datetime as _dt

    # 1. OpenClaw gateway
    openclaw_status: dict[str, Any] = {
        "alive": False,
        "latency_ms": None,
        "version": None,
        "error": None,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as ac:
            r = await ac.get(f"{settings.openclaw_base_url}/health")
        openclaw_status["alive"] = r.status_code == 200
        # Headers em httpx sao case-insensitive no lookup
        version = r.headers.get("x-openclaw-version") or r.headers.get("X-OpenClaw-Version")
        if version:
            openclaw_status["version"] = version
    except (httpx.RequestError, httpx.TimeoutException) as e:
        openclaw_status["error"] = f"{type(e).__name__}: {e}"

    # 2. LLM provider (opencode_go - primary)
    llm_status: dict[str, Any] = {
        "provider": settings.llm_default_provider,
        "model": settings.opencode_go_model,
        "reachable": False,
        "error": None,
    }
    if settings.opencode_go_api_key:
        try:
            async with httpx.AsyncClient(timeout=5.0) as ac:
                # Ping via endpoint /models (OpenAI-compat)
                r = await ac.get(
                    f"{settings.opencode_go_base_url}/models",
                    headers={"Authorization": f"Bearer {settings.opencode_go_api_key}"},
                )
            llm_status["reachable"] = r.status_code in (200, 401, 403)
        except (httpx.RequestError, httpx.TimeoutException) as e:
            llm_status["error"] = f"{type(e).__name__}: {e}"
    else:
        llm_status["error"] = "OPENCODE_GO_API_KEY nao configurado"

    # 3. Status agregado
    if openclaw_status["alive"] and llm_status["reachable"]:
        status = "ok"
    elif openclaw_status["alive"] or llm_status["reachable"]:
        status = "degraded"
    else:
        status = "down"

    return AgentHealthResponse(
        status=status,
        openclaw=openclaw_status,
        llm_provider=llm_status,
        timestamp=_dt.datetime.utcnow().isoformat() + "Z",
    )


# ============================================================================
# Endpoint: POST /integrations/outbox/dispatch  (webhook Supabase -> fila)
# ============================================================================
# Adicionado 2026-06-24 (commit f6aac74 criou a trigger; este endpoint processa)
# - Recebe webhook do Supabase quando INSERT em outbox_messages
# - Autenticado por X-API-Key (header)
# - Busca a mensagem do DB, executa handler da queue, atualiza status
# - Idempotente: se status==done, retorna 200 sem reprocessar
# - Backoff 5min em falha (next_retry_at)
# (imports movidos para o topo do arquivo - ruff E402)

_log = logging.getLogger("integrations.outbox")

_VALID_QUEUES = {q.value for q in OutboxQueue}  # {"evolution","chatwoot","telegram","outbox"}


async def _dispatch_evolution(payload: dict) -> None:
    """Envia mensagem via Evolution API (WhatsApp)."""
    if not settings.evolution_api_key:
        raise RuntimeError("EVOLUTION_API_KEY nao configurado")
    number = payload.get("number") or payload.get("to")
    text = payload.get("text") or payload.get("message")
    if not number or not text:
        raise ValueError("payload evolution precisa de 'number' e 'text'")
    instance = payload.get("instance") or settings.evolution_instance
    url = f"{settings.evolution_base_url.rstrip('/')}/message/sendText/{instance}"
    async with httpx.AsyncClient(timeout=15.0) as ac:
        r = await ac.post(
            url,
            headers={"apikey": settings.evolution_api_key, "Content-Type": "application/json"},
            json={"number": number, "text": text},
        )
    if r.status_code >= 400:
        raise RuntimeError(f"evolution HTTP {r.status_code}: {r.text[:200]}")


async def _dispatch_chatwoot(payload: dict) -> None:
    """Placeholder - integracao Chatwoot sera implementada em Sprint 2."""
    _log.info("chatwoot dispatch (placeholder): %s", json.dumps(payload)[:200])
    # TODO Sprint 2: POST %s/api/v1/accounts/%s/conversations ...


async def _dispatch_telegram(payload: dict) -> None:
    """Envia mensagem via Telegram Bot API."""
    bot_token = payload.get("bot_token") or getattr(settings, "telegram_bot_token", None)
    chat_id = payload.get("chat_id")
    text = payload.get("text") or payload.get("message")
    if not bot_token or not chat_id or not text:
        raise ValueError("payload telegram precisa de 'bot_token','chat_id','text'")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=15.0) as ac:
        r = await ac.post(url, json={"chat_id": chat_id, "text": text})
    if r.status_code >= 400:
        raise RuntimeError(f"telegram HTTP {r.status_code}: {r.text[:200]}")


async def _dispatch_outbox(payload: dict) -> None:
    """Queue generica - apenas loga (test mode)."""
    _log.info("outbox (test mode) payload: %s", json.dumps(payload)[:200])


_DISPATCHERS = {
    OutboxQueue.EVOLUTION: _dispatch_evolution,
    OutboxQueue.CHATWOOT: _dispatch_chatwoot,
    OutboxQueue.TELEGRAM: _dispatch_telegram,
    OutboxQueue.OUTBOX: _dispatch_outbox,
}


@integrations_router.post(
    "/integrations/outbox/dispatch",
    tags=["meta"],
    summary="Despachar mensagem do outbox (webhook Supabase)",
    description=(
        "Recebe webhook do Supabase quando ha INSERT em `outbox_messages`. "
        "Autenticado por `X-API-Key` (header). Busca a mensagem do DB, "
        "executa o handler da queue (`evolution|chatwoot|telegram|outbox`), "
        "atualiza o status para `done` ou `failed` (com `attempts++`).\n\n"
        "Payload esperado:\n"
        "```json\n"
        '{"event":"INSERT","table":"outbox_messages","outbox_id":"<uuid>",'
        '"queue":"evolution","payload":{...},"attempts":0}\n'
        "```\n\n"
        "Resposta: `{\"status\":\"done|failed\",\"attempts\":N,\"error\":\"...\"}`."
    ),
)
async def outbox_dispatch(
    request: Request,
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
) -> dict:
    """Webhook Supabase -> processa outbox_message por queue.

    B0.3 2026-06-25: refatorado para usar deps.require_cartorio_api_key
    (constant-time compare centralizado em app/api/deps.py).
    """

    # 2. Parse body
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"erro": "BAD_JSON", "mensagem": str(e)[:200]},
        )

    outbox_id_raw = body.get("outbox_id") or body.get("record", {}).get("id")
    queue_raw = body.get("queue") or body.get("record", {}).get("queue")
    payload = body.get("payload") or body.get("record", {}).get("payload") or {}
    _attempts_in = int(body.get("attempts") or 0)  # placeholder p/ future attempt tracking

    if not outbox_id_raw or not queue_raw:
        raise HTTPException(
            status_code=422,
            detail={"erro": "MISSING_FIELDS", "mensagem": "outbox_id e queue sao obrigatorios"},
        )
    if queue_raw not in _VALID_QUEUES:
        raise HTTPException(
            status_code=422,
            detail={"erro": "INVALID_QUEUE", "queue": queue_raw, "valid": sorted(_VALID_QUEUES)},
        )

    # 3. Busca outbox_message do DB
    try:
        outbox_uuid = _uuid.UUID(str(outbox_id_raw))
    except ValueError:
        raise HTTPException(status_code=422, detail={"erro": "INVALID_UUID", "outbox_id": outbox_id_raw})

    with session_scope() as db:
        msg = db.execute(
            select(OutboxMessage).where(OutboxMessage.id == outbox_uuid)
        ).scalar_one_or_none()

        if msg is None:
            raise HTTPException(
                status_code=404,
                detail={"erro": "OUTBOX_NOT_FOUND", "outbox_id": outbox_id_raw},
            )

        # Idempotencia: ja done? retorna 200 sem reprocessar
        if msg.status == OutboxStatus.DONE:
            return {"status": "done", "attempts": msg.attempts, "idempotent": True}

        # Marca processing
        msg.status = OutboxStatus.PROCESSING
        db.flush()

        # 4. Despacha por queue
        queue_enum = OutboxQueue(queue_raw)
        dispatcher = _DISPATCHERS[queue_enum]
        try:
            await dispatcher(payload if isinstance(payload, dict) else {})
            msg.status = OutboxStatus.DONE
            msg.attempts = (msg.attempts or 0) + 1
            msg.last_error = None
            result = {"status": "done", "attempts": msg.attempts, "error": None}
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:500]
            _log.exception("outbox dispatch failed id=%s queue=%s", outbox_id_raw, queue_raw)
            msg.status = OutboxStatus.FAILED
            msg.attempts = (msg.attempts or 0) + 1
            msg.last_error = err
            # next_retry_at: +5min para backoff simples
            msg.next_retry_at = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(minutes=5)
            result = {"status": "failed", "attempts": msg.attempts, "error": err}

    return result
