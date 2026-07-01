"""Fallback LLM chain completo - Turno 37 2026-06-30.

Chain completo (10 provedores):
1. opencode_free_3 (deepseek-v4-flash-free, 1M) - primario default
2. opencode_free_1 (nemotron-3-ultra-free, 1M)
3. opencode_free_2 (mimo-v2.5-free, 1M)
4. opencode_go (deepseek-v4-flash)
5. openrouter (multi-model aggregator)
6. groq (compound, 131K)
7. mistral (devstral-small, 256K)
8. google_ai_studio (gemini-3.5-flash, 1M)
9. openclaw (gpt-5.5 / claude-sonnet legacy)
10. jules (gemini-3.1-pro async polling 25s)

LGPD compliance em cada chain step:
- PII scrubbing INTERNO (defense-in-depth)
- Audit log via AuditService.log()
- Consent gate bloqueia LGPD_BLOCKED sem tentar fallback
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.integrations.opencode_go import ChatError, ChatErrorKind, ChatResponse

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# Provedores que usam o wrapper generico OpenAI-compat (opencode_generic)
_OPENAI_COMPAT_PROVIDERS = frozenset(
    {
        "opencode_free_1",
        "opencode_free_2",
        "opencode_free_3",
        "openrouter",
        "groq",
        "mistral",
        "google_ai_studio",
    }
)

# Aliases: nomes alternativos que roteiam para providers reais (2026-07-01 turn 46).
# Evita CONFIG_ERROR quando algum caller passa nome "amigavel" (ex: "minimax").
_PROVIDER_ALIASES: dict[str, str] = {
    "minimax": "opencode_go",       # VPS aponta OPENCODE_GO_BASE_URL=https://api.minimax.io/v1
    "minimax-m3": "opencode_go",    # compat: nome antigo (lowercase)
    "MiniMax-M3": "opencode_go",    # compat: case-preserved (provider real name on VPS)
    "antigravity": "openclaw",      # rota alternativa se agent vier com nome errado
}


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
    """Dispatch helper: chama o provider certo com seus proprios settings."""
    # Resolve aliases (2026-07-01 turn 46) - ex: "minimax" -> "opencode_go"
    # Necessario porque OPENCODE_GO_BASE_URL aponta para https://api.minimax.io/v1 na VPS
    # mas o provider name usado em algumas chamadas eh "minimax"
    provider = _PROVIDER_ALIASES.get(provider, provider)

    if provider == "opencode_go":
        from app.integrations.opencode_go import chat_with_settings as chat_opencode_go

        return await chat_opencode_go(
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

    if provider in _OPENAI_COMPAT_PROVIDERS:
        # Providers genericos OpenAI-compat
        from app.integrations.opencode_generic import chat as chat_generic
        from app.integrations.opencode_generic import get_config_for

        config = get_config_for(provider)
        if config is None:
            raise ChatError(
                f"Provider {provider} nao tem config definida",
                kind=ChatErrorKind.CONFIG,
            )
        # Override model se passado explicitamente
        if model:
            config.model = model
        return await chat_generic(
            messages=messages,
            config=config,
            temperature=temperature,
            consent_granted=consent_granted,
            actor_id=actor_id,
            db=db,
            session_id=session_id,
            request_id=request_id,
            client_ip=client_ip,
        )

    if provider == "openclaw":
        from app.integrations.openclaw import chat_with_settings as chat_openclaw

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
        from app.integrations.jules import chat_with_settings as chat_jules

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

    if provider == "antigravity":
        from app.integrations.antigravity import chat_with_settings as chat_antigravity

        return await chat_antigravity(
            messages=messages,
            temperature=temperature,
            consent_granted=consent_granted,
            actor_id=actor_id,
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
    primary_provider: str | None = None,
    fallback_provider: str | None = None,  # deprecated: use chain via settings
    tertiary_provider: str | None = None,  # deprecated
    model: str | None = None,
    temperature: float = 0.2,
    consent_granted: bool = False,
    actor_id: str = "anonymous",
    db: "Session | None" = None,
    session_id: str | None = None,
    rate_limit_per_minute: int | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
    chain: list[str] | None = None,
) -> ChatResponse:
    """Tenta providers em chain ate algum funcionar (Turno 37 chain completo).

    Args:
        chain: lista ordenada de provider names. Se None, usa settings.llm_fallback_chain.
        primary_provider/fallback_provider/tertiary_provider: legacy 3-provider chain.
            Se passados, monta chain a partir deles.

    Logica:
    1. Para cada provider na chain:
       - Se LGPD_BLOCKED ou CONFIG_ERROR: aborta chain inteiro (faz raise)
       - Caso contrario: loga fallback disparado, tenta proximo
    2. Se TODOS falharem (exceto LGPD/CONFIG): raise ultima exception

    Returns:
        ChatResponse do primeiro provider que deu certo.

    Raises:
        ChatError: LGPD_BLOCKED/CONFIG (aborta chain) ou erro do ultimo provider.
    """
    from app.config import settings
    from app.services.audit import AuditService

    # Determina chain
    if chain is None:
        if primary_provider or fallback_provider or tertiary_provider:
            # Legacy 3-provider compat
            chain = [
                p
                for p in [
                    primary_provider or settings.llm_default_provider,
                    fallback_provider,
                    tertiary_provider,
                ]
                if p
            ]
        else:
            # Nova chain completa do settings
            chain = [p.strip() for p in settings.llm_fallback_chain.split(",") if p.strip()]

    if not chain:
        raise ChatError(
            "Chain de provedores vazia. Configure LLM_FALLBACK_CHAIN no .env.",
            kind=ChatErrorKind.CONFIG,
        )

    # ---- LGPD art. 7 I — Consent gate (BEFORE chain) ----
    if not consent_granted:
        raise ChatError(
            "LGPD art. 7 I — Consentimento nao concedido. Chain abortada.",
            kind=ChatErrorKind.LGPD_BLOCKED,
        )

    last_exc: ChatError | None = None
    for idx, provider in enumerate(chain):
        if idx > 0 and last_exc is not None:
            logger.warning(
                "Chain step %d provider (%s) failed kind=%s, attempting next (%s). Error: %s",
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
                consent_granted=True,  # ja validado acima
                actor_id=actor_id,
                db=db,
                session_id=session_id,
                rate_limit_per_minute=rate_limit_per_minute,
                request_id=request_id,
                client_ip=client_ip,
            )
            logger.info(
                "LLM call successful idx=%d provider=%s model=%s latency_ms=%d",
                idx,
                provider,
                resp.model,
                resp.latency_ms,
            )

            # Audit log de qual provider foi usado (LGPD art. 37)
            if db is not None:
                try:
                    AuditService.log(
                        db,
                        actor_id=actor_id,
                        actor_type="system",
                        action="llm.call_success",
                        resource=f"llm:{provider}",
                        payload={
                            "provider": provider,
                            "model": resp.model,
                            "tokens_in": resp.tokens_in,
                            "tokens_out": resp.tokens_out,
                            "latency_ms": resp.latency_ms,
                            "chain_idx": idx,
                            "chain_total": len(chain),
                            "pii_redacted": resp.pii_redacted_count,
                            "output_pii_redacted": resp.output_pii_redacted_count,
                            "consent_granted": consent_granted,
                            "previous_failed_chain": chain[:idx] if idx > 0 else [],
                            "previous_error_kind": last_exc.kind if last_exc else None,
                        },
                        request_id=request_id,
                        ip=client_ip,
                        canal="api",
                    )
                except Exception as exc:
                    logger.warning("Falha no audit log de llm.call_success: %s", exc)

            return resp

        except ChatError as exc:
            # LGPD/CONFIG: baila sem tentar chain
            if exc.kind in (ChatErrorKind.LGPD_BLOCKED, ChatErrorKind.CONFIG):
                logger.error(
                    "Provider %s abort chain (kind=%s): %s",
                    provider,
                    exc.kind,
                    exc,
                )
                raise
            last_exc = exc
            continue
        except Exception as exc:
            logger.error(
                "Erro inesperado em provider=%s: %s",
                provider,
                exc,
            )
            last_exc = ChatError(
                f"Erro inesperado no provider {provider}: {exc}",
                kind=ChatErrorKind.NETWORK,
            )
            last_exc.__cause__ = exc  # type: ignore[attr-defined]
            continue

    # TODOS falharam
    assert last_exc is not None
    logger.error(
        "ALL %d LLM providers failed. Last error: %s",
        len(chain),
        last_exc,
    )

    # Audit log do chain total failure
    if db is not None:
        try:
            AuditService.log(
                db,
                actor_id=actor_id,
                actor_type="system",
                action="llm.chain_total_failure",
                resource="llm:chain",
                payload={
                    "chain": chain,
                    "last_error_kind": last_exc.kind,
                    "last_error_msg": str(last_exc),
                },
                request_id=request_id,
                ip=client_ip,
                canal="api",
            )
        except Exception:
            pass

    raise last_exc
