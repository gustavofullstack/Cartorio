"""Fallback LLM providers.

Se o provider primario (Opencode-Go) falhar por rate-limit (429), timeout,
network or 5xx, tenta automaticamente o provider secundario (OpenClaw)
garantindo o mesmo nivel de PII protection e audit logging (LGPD art. 37).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.integrations.opencode_go import ChatError, ChatErrorKind, ChatResponse

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


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
    request_id: str | None = None,
    client_ip: str | None = None,
) -> ChatResponse:
    """Tenta o provider primario, fallback se falhar.

    Lógica:
    1. Tenta primary_provider (opencode_go por padrao).
    2. Se falhar com ChatError (TIMEOUT, NETWORK, HTTP_5XX, RATE_LIMITED),
       tenta fallback_provider (openclaw por padrao).
    3. Registra no audit log qual provider final foi utilizado.

    Raises:
        ChatError: Se ambos providers falharem ou por erro de config/consent.
    """
    from app.integrations.opencode_go import chat_with_settings as chat_opencode
    from app.integrations.openclaw import chat_with_settings as chat_openclaw
    from app.services.audit import AuditService

    # 1. Tentar provedor primário
    try:
        if primary_provider == "opencode_go":
            resp = await chat_opencode(
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
            logger.info("LLM call successful using primary provider (opencode_go)")
            return resp
        elif primary_provider == "openclaw":
            resp = await chat_openclaw(
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
            logger.info("LLM call successful using primary provider (openclaw)")
            return resp
        else:
            raise ChatError(
                f"Provedor primario desconhecido: {primary_provider}",
                kind=ChatErrorKind.CONFIG,
            )

    except ChatError as primary_exc:
        # Se for erro de consentimento ou de config do caller, nao faz fallback
        if primary_exc.kind in (ChatErrorKind.LGPD_BLOCKED, ChatErrorKind.CONFIG):
            raise primary_exc

        logger.warning(
            "Primary LLM provider (%s) failed with kind=%s, attempting fallback to %s. Error: %s",
            primary_provider,
            primary_exc.kind,
            fallback_provider,
            primary_exc,
        )

        # 2. Tentar provedor secundário (fallback)
        try:
            if fallback_provider == "openclaw":
                resp = await chat_openclaw(
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
                logger.info("LLM call successful using fallback provider (openclaw)")

                # Audit log de fallback bem-sucedido (LGPD art. 37)
                if db is not None:
                    try:
                        AuditService.log(
                            db,
                            actor_id=actor_id,
                            actor_type="system",
                            action="llm.fallback_triggered",
                            resource=f"llm:{fallback_provider}",
                            payload={
                                "primary_provider": primary_provider,
                                "fallback_provider": fallback_provider,
                                "primary_error_kind": primary_exc.kind,
                                "primary_error_msg": str(primary_exc),
                                "model_used": resp.model,
                            },
                            request_id=request_id,
                            ip=client_ip,
                            canal="api",
                        )
                    except Exception:
                        pass

                return resp
            elif fallback_provider == "opencode_go":
                resp = await chat_opencode(
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
                logger.info("LLM call successful using fallback provider (opencode_go)")
                return resp
            else:
                raise ChatError(
                    f"Provedor fallback desconhecido: {fallback_provider}",
                    kind=ChatErrorKind.CONFIG,
                )

        except ChatError as fallback_exc:
            logger.error(
                "Fallback LLM provider (%s) also failed. Error: %s",
                fallback_provider,
                fallback_exc,
            )
            # Propaga o erro do fallback para indicar falha total
            raise fallback_exc
        except Exception as exc:
            logger.error(
                "Unexpected error during LLM fallback execution: %s",
                exc,
            )
            raise ChatError(
                f"Erro inesperado no fallback: {exc}",
                kind=ChatErrorKind.NETWORK,
            ) from exc
