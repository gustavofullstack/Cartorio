"""Fallback LLM providers.

Se o provider primario (Opencode-Go) falhar por rate-limit (429), timeout,
network or 5xx, tenta automaticamente o provider secundario (OpenClaw)
garantindo o mesmo nivel de PII protection e audit logging (LGPD art. 37).

Chain (turno 18 2026-06-29): opencode_go -> openclaw -> jules
- jules eh fallback terciario (Google Gemini 3.1 Pro via Jules async API)
- jules usa polling 25s (latencia alta) mas eh free e independente de
  OpenCode-Go / OpenClaw
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.integrations.opencode_go import ChatError, ChatErrorKind, ChatResponse

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def _call_provider(
    provider: str,
    messages: list[dict[str, str]],
    *,
    model: str | None,
    temperature: float,
    consent_granted: bool,
    actor_id: str,
    db: "Session | None",
    session_id: str | None,
    rate_limit_per_minute: int | None,
    request_id: str | None,
    client_ip: str | None,
) -> ChatResponse:
    """Dispatch helper: chama o provider certo."""
    from app.integrations.opencode_go import chat_with_settings as chat_opencode
    from app.integrations.openclaw import chat_with_settings as chat_openclaw
    from app.integrations.jules import chat_with_settings as chat_jules

    if provider == "opencode_go":
        return await chat_opencode(
            messages=messages,
            model=model,
            temperature=temperature,
            consent_granted=consent_granted,
            actor_id=actor_id,
            db=db,
            session_id=session_id,
            rate_limit_per_minute=rate_limit_per_minute,
            request_id=request_id,
            client_ip=client_ip,
        )
    if provider == "openclaw":
        return await chat_openclaw(
            messages=messages,
            temperature=temperature,
            consent_granted=consent_granted,
            actor_id=actor_id,
            db=db,
            session_id=session_id,
            rate_limit_per_minute=rate_limit_per_minute,
            request_id=request_id,
            client_ip=client_ip,
        )
    if provider == "jules":
        return await chat_jules(
            messages=messages,
            temperature=temperature,
            consent_granted=consent_granted,
            actor_id=actor_id,
            db=db,
            session_id=session_id,
            rate_limit_per_minute=rate_limit_per_minute,
            request_id=request_id,
            client_ip=client_ip,
        )
    raise ChatError(
        f"Provedor desconhecido: {provider}",
        kind=ChatErrorKind.CONFIG,
    )


async def chat_with_fallback(
    messages: list[dict[str, str]],
    *,
    primary_provider: str = "opencode_go",
    fallback_provider: str = "openclaw",
    tertiary_provider: str = "jules",
    model: str | None = None,
    temperature: float = 0.2,
    consent_granted: bool = False,
    actor_id: str = "anonymous",
    db: "Session | None" = None,
    session_id: str | None = None,
    rate_limit_per_minute: int | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
) -> ChatResponse:
    """Tenta providers em chain: primary -> fallback -> tertiary.

    Logica (turno 18 2026-06-29):
    1. primary_provider (opencode_go por padrao).
    2. Se falhar ChatError nao-LGPD/CONFIG: fallback_provider (openclaw por padrao).
    3. Se fallback tambem falhar: tertiary_provider (jules por padrao, polling 25s).
    4. Audit log de cada fallback disparado.

    Raises:
        ChatError: Se TODOS providers falharem (propaga erro do ultimo).
    """
    from app.services.audit import AuditService

    chain = [primary_provider, fallback_provider, tertiary_provider]
    chain = [p for p in chain if p]  # remove None

    last_exc: ChatError | None = None
    for idx, provider in enumerate(chain):
        if idx == 0:
            # Primary: chamada direta
            pass
        else:
            # Fallback/tertiary: loga o fallback
            assert last_exc is not None
            logger.warning(
                "Chain step %d provider (%s) failed with kind=%s, attempting next (%s). Error: %s",
                idx,
                chain[idx - 1],
                last_exc.kind,
                provider,
                last_exc,
            )

        try:
            resp = await _call_provider(
                provider,
                messages,
                model=model,
                temperature=temperature,
                consent_granted=consent_granted,
                actor_id=actor_id,
                db=db,
                session_id=session_id,
                rate_limit_per_minute=rate_limit_per_minute,
                request_id=request_id,
                client_ip=client_ip,
            )
            logger.info(
                "LLM call successful using provider index=%d name=%s",
                idx,
                provider,
            )

            # Audit log de fallback disparado (LGPD art. 37) — so se idx > 0
            if idx > 0 and db is not None and last_exc is not None:
                try:
                    AuditService.log(
                        db,
                        actor_id=actor_id,
                        actor_type="system",
                        action="llm.fallback_triggered",
                        resource=f"llm:{provider}",
                        payload={
                            "primary_provider": primary_provider,
                            "fallback_chain": chain[: idx + 1],
                            "previous_error_kind": last_exc.kind,
                            "previous_error_msg": str(last_exc),
                            "model_used": resp.model,
                            "chain_step": idx,
                        },
                        request_id=request_id,
                        ip=client_ip,
                        canal="api",
                    )
                except Exception:
                    pass

            return resp

        except ChatError as exc:
            # LGPD/CONFIG: baila sem tentar chain
            if exc.kind in (ChatErrorKind.LGPD_BLOCKED, ChatErrorKind.CONFIG):
                raise
            last_exc = exc
            continue
        except Exception as exc:
            # Erro inesperado (bug, NaN, etc) -> wrap em ChatError NETWORK
            logger.error(
                "Unexpected error during LLM provider=%s execution: %s",
                provider,
                exc,
            )
            last_exc = ChatError(
                f"Erro inesperado no provider {provider}: {exc}",
                kind=ChatErrorKind.NETWORK,
            )
            last_exc.__cause__ = exc
            continue

    # Se chegou aqui, TODOS falharam
    assert last_exc is not None
    logger.error(
        "All LLM providers failed. Chain=%s Last error: %s",
        chain,
        last_exc,
    )
    raise last_exc
