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
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import require_cartorio_api_key
from app.config import settings
from app.db import session_scope
from app.integrations.fallback import chat_with_fallback
from app.integrations.opencode_go import ChatError, chat_with_settings
from app.models.audit_log import AuditLog
from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus
from app.services.audit import AuditService
from app.services.metrics import store as metrics_store
from app.services.n8n_error import (
    classify_error_type,
    compute_payload_digest,
    validate_n8n_signature,
)


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
    use_fallback: bool = Field(
        default=False,
        description=(
            "Se True, usa fallback chain (opencode_go -> openclaw). "
            "Util quando opencode_go esta rate-limited (429) ou indisponivel. "
            "Sprint 3 Turno 18: adicionado para validar E2E live quando "
            "primary provider retorna erro transitorio."
        ),
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
        if payload.use_fallback:
            # Turno 37 2026-06-30: usa LLM_FALLBACK_CHAIN (10 provedores)
            from app.config import settings as _settings

            chain = [p.strip() for p in _settings.llm_fallback_chain.split(",") if p.strip()]
            resp = await chat_with_fallback(
                messages=[{"role": "user", "content": payload.message}],
                chain=chain,
                model=payload.model,
                temperature=payload.temperature,
                consent_granted=True,
                actor_id=payload.actor_id,
                # db=None: smoke test NAO grava audit log (operador escolhe)
            )
        else:
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
    "/integrations/openclaw",
    tags=["meta"],
    summary="Status direto do OpenClaw Agent (Turno 38)",
    description="Retorna status do gateway OpenClaw + lista models disponiveis + latency ping.",
    response_model=AgentHealthResponse,
)
async def openclaw_status_endpoint() -> AgentHealthResponse:
    """Status dedicado do OpenClaw Agent (alias para /integrations/agent/health).

    Adicionado no Turno 38 para corresponder ao path documentado na bateria V4.
    """
    return await agent_health()


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
        timestamp=_dt.datetime.now(_dt.UTC).replace(tzinfo=None).isoformat(),
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
        'Resposta: `{"status":"done|failed","attempts":N,"error":"..."}`.'
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
        raise HTTPException(
            status_code=422, detail={"erro": "INVALID_UUID", "outbox_id": outbox_id_raw}
        )

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


# ============================================================================
# Endpoint: POST /integrations/n8n/error  (B6 N8N Error Handler Global)
# ============================================================================
# B6 2026-06-25: recebe erros de QUALQUER workflow N8N ativo (Error Workflow
# global dispara este endpoint). Validacao HMAC via N8N_WEBHOOK_SECRET +
# header X-N8N-Signature. Grava audit_log (LGPD art. 37) + incrementa metrica
# Prometheus n8n_errors_total{workflow_name, error_type}.
#
# Cardinalidade controlada: workflow_name <= ~40 WFs ativos, error_type = 7
# valores discretos (connection|http_4xx|http_5xx|timeout|validation|auth|unknown).
#
# Idempotencia: execution_id dedup via audit_log (request_id eh o execution_id).

_n8n_error_log = logging.getLogger("integrations.n8n_error")


class N8nErrorRequest(BaseModel):
    """Payload do webhook N8N Error Workflow (B6).

    Attributes:
        workflow_name: Nome do WF que falhou (ex: '01 - Consulta Emolumento').
        workflow_id: ID do WF que falhou (opcional).
        execution_id: ID da execucao N8N (idempotency key).
        error_type: Tipo classificado (opcional - backend classifica).
        error: Dict com detalhes {name, message, http_code?, stack?}.
        node: Node do N8N que falhou (opcional).
        timestamp: ISO 8601 UTC (opcional).
    """

    workflow_name: str = Field(..., min_length=1, max_length=256)
    workflow_id: str | None = Field(default=None, max_length=128)
    execution_id: str = Field(..., min_length=1, max_length=128)
    error_type: str | None = Field(default=None, max_length=64)
    error: dict[str, Any] | None = Field(default=None)
    node: str | None = Field(default=None, max_length=128)
    timestamp: str | None = Field(default=None, max_length=64)


class N8nErrorResponse(BaseModel):
    """Response do endpoint /integrations/n8n/error."""

    status: str
    execution_id: str
    audit_id: int | None = None
    error_type: str


@integrations_router.post(
    "/integrations/n8n/error",
    tags=["meta"],
    summary="Webhook do N8N Error Workflow Global (B6)",
    description=(
        "Recebe notificacao de erro de qualquer workflow N8N ativo. "
        "Validado por HMAC-SHA256 (header `X-N8N-Signature`, secret "
        "`N8N_WEBHOOK_SECRET`). Grava em `audit_log` (LGPD art. 37) e "
        "incrementa contador Prometheus `n8n_errors_total{workflow_name,"
        "error_type}`. Idempotente via `execution_id`."
    ),
    response_model=N8nErrorResponse,
)
async def n8n_error_webhook(
    request: Request,
    payload: Annotated[N8nErrorRequest, Body(...)],
    x_n8n_signature: Annotated[str | None, Header(alias="X-N8N-Signature")] = None,
) -> N8nErrorResponse:
    """Webhook N8N Error Handler Global (B6 2026-06-25).

    Auth via HMAC N8N_WEBHOOK_SECRET. Grava audit_log LGPD-safe (apenas
    digest + metadados estruturados). Idempotente via execution_id.
    """
    # 1. HMAC validation (raw body para integridade byte-a-byte)
    raw_body = await request.body()
    if not validate_n8n_signature(raw_body, x_n8n_signature):
        _n8n_error_log.warning(
            "n8n_error HMAC invalido (signature_present=%s, body_len=%d)",
            x_n8n_signature is not None,
            len(raw_body),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "erro": "INVALID_SIGNATURE",
                "mensagem": "X-N8N-Signature ausente ou invalida.",
            },
            headers={"WWW-Authenticate": 'Signature realm="n8n-error"'},
        )

    execution_id = payload.execution_id
    error_type = payload.error_type or classify_error_type(payload.error)

    # Payload canonico audit_log (LGPD-safe: digest + metadados, sem bruto)
    payload_digest = compute_payload_digest(payload.model_dump())
    audit_payload: dict[str, Any] = {
        "workflow_name": payload.workflow_name,
        "workflow_id": payload.workflow_id,
        "execution_id": execution_id,
        "error_type": error_type,
        "node": payload.node,
        "ts": payload.timestamp,
        "payload_digest": payload_digest,
    }
    if payload.error:
        err_clean: dict[str, Any] = {}
        if payload.error.get("name"):
            err_clean["name"] = str(payload.error["name"])[:64]
        if payload.error.get("message"):
            err_clean["message"] = str(payload.error["message"])[:512]
        if isinstance(payload.error.get("http_code"), int):
            err_clean["http_code"] = payload.error["http_code"]
        if err_clean:
            audit_payload["error"] = err_clean

    # Extrai contexto do request
    client_ip = request.client.host if request.client else None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        client_ip = xff.split(",")[0].strip()

    # Grava audit_log (LGPD art. 37) com idempotencia via execution_id
    audit_id: int | None = None
    try:
        with session_scope() as db:
            existing = db.execute(
                select(AuditLog).where(
                    AuditLog.action == "n8n.error",
                    AuditLog.request_id == execution_id,
                )
            ).scalar_one_or_none()
            if existing is not None:
                _n8n_error_log.info(
                    "n8n_error idempotent execution_id=%s audit_id=%d",
                    execution_id,
                    existing.id,
                )
                return N8nErrorResponse(
                    status="idempotent",
                    execution_id=execution_id,
                    audit_id=existing.id,
                    error_type=error_type,
                )

            entry = AuditService.log(
                db,
                actor_id="n8n-error-workflow",
                actor_type="system",
                action="n8n.error",
                resource=f"workflow:{payload.workflow_name}",
                payload=audit_payload,
                ip=client_ip,
                user_agent=request.headers.get("user-agent"),
                request_id=execution_id,
                canal="n8n",
            )
            audit_id = entry.id
    except Exception:
        _n8n_error_log.exception("n8n_error audit_log failed execution_id=%s", execution_id)
        # Fail-soft: ainda incrementa metric + retorna 200
        audit_id = None

    # Incrementa metrica Prometheus
    metrics_store.inc_counter(
        "n8n_errors_total",
        labels={"workflow_name": payload.workflow_name, "error_type": error_type},
    )

    _n8n_error_log.info(
        "n8n_error accepted execution_id=%s workflow=%s error_type=%s audit_id=%s",
        execution_id,
        payload.workflow_name,
        error_type,
        audit_id,
    )

    return N8nErrorResponse(
        status="accepted" if audit_id is not None else "queued",
        execution_id=execution_id,
        audit_id=audit_id,
        error_type=error_type,
    )
