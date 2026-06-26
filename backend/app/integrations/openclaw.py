"""Integracao com OpenClaw Gateway Agent AI (LLM provider secundario / fallback).

OpenClaw expoe API compativel com OpenAI Chat Completions em
`{base_url}/v1/chat/completions`.

Modelos:
    Sempre usa "openclaw" para rotear para o agente default (Pietra), que
    executa a cadeia de fallback interno (deepseek-v4-flash-free, etc.).

LGPD compliance:
1. PII scrubbing INTERNO em cada message (defense-in-depth).
2. Audit log via AuditService.log().
3. Consent gate.
4. Rate limit por sessao (Redis).
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import httpx

from app.services.pii import scrub

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Reutilizar classes de erro do opencode_go para consistencia
from app.integrations.opencode_go import ChatError, ChatErrorKind, ChatResponse, _hash_payload, _audit_log_sync, _scrub_messages, _check_rate_limit


async def chat(
    messages: list[dict[str, str]],
    *,
    model: str = "openclaw",
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.2,
    timeout_seconds: float = 30.0,
    consent_granted: bool = False,
    actor_id: str = "anonymous",
    db: "Session | None" = None,
    session_id: str | None = None,
    rate_limit_per_minute: int | None = None,
    redis_url: str | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
) -> ChatResponse:
    """Chama OpenClaw Gateway Chat Completions com LGPD compliance."""
    from app.config import settings

    target_base_url = base_url or settings.openclaw_base_url
    target_api_key = api_key or settings.openclaw_api_key or "@Techno832466"

    if not target_base_url or target_base_url.strip() == "":
        raise ChatError(
            "Base URL do OpenClaw nao configurada.",
            kind=ChatErrorKind.CONFIG,
        )

    if not messages:
        raise ChatError(
            "Lista de messages vazia.",
            kind=ChatErrorKind.CONFIG,
        )

    # ---- LGPD art. 7 I — Consent gate ----
    if not consent_granted:
        raise ChatError(
            "LGPD art. 7 I — Consentimento nao concedido.",
            kind=ChatErrorKind.LGPD_BLOCKED,
        )

    # ---- Rate limit ----
    if rate_limit_per_minute is not None and session_id and redis_url:
        await asyncio.to_thread(_check_rate_limit, session_id, rate_limit_per_minute, redis_url)

    # ---- PII scrubbing INTERNO ----
    scrubbed_messages, pii_redacted_count = _scrub_messages(messages)

    # ---- Monta request ----
    url = f"{target_base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {target_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": scrubbed_messages,
        "temperature": temperature,
    }

    # ---- Executa com medicao de latencia ----
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as e:
        raise ChatError(
            f"Timeout apos {timeout_seconds}s na chamada OpenClaw",
            kind=ChatErrorKind.TIMEOUT,
        ) from e
    except httpx.HTTPError as e:
        raise ChatError(
            f"Erro de rede ao chamar OpenClaw: {e}",
            kind=ChatErrorKind.NETWORK,
        ) from e

    latency_ms = int((time.time() - start_time) * 1000)

    # ---- Trata HTTP errors ----
    if response.status_code >= 400:
        body_text = response.text[:500] if response.text else ""
        kind = ChatErrorKind.HTTP_4XX if response.status_code < 500 else ChatErrorKind.HTTP_5XX
        raise ChatError(
            f"OpenClaw retornou {response.status_code}: {body_text[:200]}",
            kind=kind,
            status_code=response.status_code,
            body=body_text,
        )

    # ---- Parse response ----
    try:
        data = response.json()
    except Exception as e:
        raise ChatError(
            f"Response do OpenClaw nao e JSON valido: {e}",
            kind=ChatErrorKind.PARSE,
            status_code=response.status_code,
        ) from e

    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice.get("finish_reason")
    except (KeyError, IndexError, TypeError) as e:
        raise ChatError(
            f"Estrutura inesperada na response do OpenClaw: {e}",
            kind=ChatErrorKind.PARSE,
            status_code=response.status_code,
        ) from e

    usage = data.get("usage", {})
    tokens_in = usage.get("prompt_tokens")
    tokens_out = usage.get("completion_tokens")

    # ---- Output PII scrubbing ----
    scrub_result = scrub(content)
    output_pii_redacted_count = scrub_result.redaction_count
    safe_content = scrub_result.text

    # ---- Audit log LGPD art. 37 ----
    if db is not None:
        request_hash = _hash_payload(payload)
        response_hash = _hash_payload(
            {
                "model": data.get("model", model),
                "finish_reason": finish_reason,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "content_length": len(content),
            }
        )

        audit_payload = {
            "provider": "openclaw",
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "consent_granted": consent_granted,
            "pii_redacted_count": pii_redacted_count,
            "request_hash": request_hash,
            "response_hash": response_hash,
            "session_id": session_id,
            "messages_count": len(scrubbed_messages),
            "temperature": temperature,
        }

        try:
            await asyncio.to_thread(
                _audit_log_sync,
                db,
                actor_id=actor_id,
                action="openclaw.chat",
                resource="llm:openclaw",
                payload=audit_payload,
            )
        except Exception:
            pass

        if output_pii_redacted_count > 0:
            output_audit_payload = {
                "provider": "openclaw",
                "model": model,
                "redacted_count": output_pii_redacted_count,
                "output_length": len(safe_content),
                "session_id": session_id,
            }
            try:
                await asyncio.to_thread(
                    _audit_log_sync,
                    db,
                    actor_id=actor_id,
                    action="llm.output_scrubbed",
                    resource="llm:openclaw",
                    payload=output_audit_payload,
                    request_id=request_id,
                    client_ip=client_ip,
                )
            except Exception:
                pass

    return ChatResponse(
        content=safe_content,
        model=data.get("model", model),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
        pii_redacted_count=pii_redacted_count,
        output_pii_redacted_count=output_pii_redacted_count,
        raw=None,
    )


async def chat_with_settings(
    messages: list[dict[str, str]],
    *,
    model: str = "openclaw",
    temperature: float = 0.2,
    consent_granted: bool = False,
    actor_id: str = "anonymous",
    db: "Session | None" = None,
    session_id: str | None = None,
    rate_limit_per_minute: int | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
) -> ChatResponse:
    """Wrapper que le settings do app.config."""
    from app.config import settings

    return await chat(
        messages=messages,
        model=model,
        api_key=settings.openclaw_api_key,
        base_url=settings.openclaw_base_url,
        temperature=temperature,
        consent_granted=consent_granted,
        actor_id=actor_id,
        db=db,
        session_id=session_id,
        rate_limit_per_minute=rate_limit_per_minute,
        redis_url=settings.redis_url,
        request_id=request_id,
        client_ip=client_ip,
    )
