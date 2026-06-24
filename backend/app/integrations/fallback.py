"""Fallback LLM providers - placeholder para LiteLLM (BLOCKER 6 auditoria 2026-06-23).

Se OpenCode-Go falhar (timeout, 5xx, network), o sistema DEVE ter fallback
para LiteLLM (OpenAI / Anthropic / OpenClaw) com MESMO nivel de PII protection.

STATUS (2026-06-23): Implementado (OpenClaw via gateway)

Por que OpenClaw:
1. Nao temos contrato LiteLLM ativo no cartorio (chatwoot usa LiteLLM,
   cartorio nao).
2. Decisao de produto: openclaw gateway configurado em settings.openclaw_*

LGPD: ambos providers tem:
- Scrubbing interno (defense-in-depth)
- Audit log via AuditService
- Consent gate
- Rate limit
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from app.integrations.opencode_go import ChatError, ChatErrorKind

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.integrations.opencode_go import ChatResponse


async def chat_with_fallback(
    messages: list[dict[str, str]],
    *,
    primary_provider: str = "opencode_go",
    fallback_provider: str = "openclaw",
    model: str | None = None,
    temperature: float = 0.2,
    consent_granted: bool = False,
    actor_id: str = "anonymous",
    db: "Session | None" = None,
    session_id: str | None = None,
    rate_limit_per_minute: int | None = None,
) -> "ChatResponse":
    """Tenta provider primario, fallback se falhar.

    Raises:
        ChatError: Se ambos providers falharem.
    """
    import app.integrations.opencode_go as opencode_go
    import app.integrations.openclaw as openclaw

    try:
        return await opencode_go.chat_with_settings(
            messages=messages,
            model=model,
            temperature=temperature,
            consent_granted=consent_granted,
            actor_id=actor_id,
            db=db,
            session_id=session_id,
            rate_limit_per_minute=rate_limit_per_minute,
        )
    except ChatError as e:
        if e.kind in (
            ChatErrorKind.TIMEOUT,
            ChatErrorKind.HTTP_5XX,
            ChatErrorKind.NETWORK,
            ChatErrorKind.RATE_LIMITED,
        ):
            # Tenta fallback
            try:
                return await openclaw.chat_with_settings(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    consent_granted=consent_granted,
                    actor_id=actor_id,
                    db=db,
                    session_id=session_id,
                    rate_limit_per_minute=rate_limit_per_minute,
                )
            except openclaw.ChatError as fallback_err:
                # Re-raise as the generic/expected ChatError from opencode_go
                raise ChatError(
                    message=f"Fallback also failed: {fallback_err.args[0] if fallback_err.args else str(fallback_err)}",
                    kind=fallback_err.kind,
                    status_code=fallback_err.status_code,
                    body=fallback_err.body
                ) from fallback_err
        raise
