"""Fallback LLM providers - placeholder para LiteLLM (BLOCKER 6 auditoria 2026-06-23).

Se OpenCode-Go falhar (timeout, 5xx, network), o sistema DEVE ter fallback
para LiteLLM (OpenAI / Anthropic / OpenClaw) com MESMO nivel de PII protection.

STATUS (2026-06-23): PLACEHOLDER / TODO.

Por que placeholder:
1. Nao temos contrato LiteLLM ativo no cartorio (chatwoot usa LiteLLM,
   cartorio nao).
2. Decisao de produto: qual provider secundario? OpenClaw (ja configurado
   em settings.openclaw_*) ou LiteLLM direto?
3. DPA com provedor secundario precisa ser assinado antes de ir pra prod.

Quando implementar (sprint 2):
1. Criar `app/integrations/openclaw.py` espelhando opencode_go.py
   (mesma assinatura, mesmo scrub, mesmo audit)
2. Criar `chat_with_fallback(messages, *, primary=opencode_go, fallback=openclaw)`
3. Tentar primary primeiro, se ChatError(TIMEOUT|HTTP_5XX|NETWORK|RATE_LIMITED)
   tenta fallback com mesmos parametros
4. Audit log marca qual provider foi usado
5. Teste de integracao: forcar primary a falhar, verificar fallback executou

LGPD: ambos providers devem ter:
- Scrubbing interno (defense-in-depth)
- Audit log via AuditService
- Consent gate
- Rate limit
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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

    PLACEHOLDER: atualmente so delega ao opencode_go. Fallback sera
    adicionado em sprint 2 com provider openclaw.

    Raises:
        ChatError: Se ambos providers falharem.
    """
    from app.integrations.opencode_go import chat_with_settings

    # TODO sprint 2: implementar logica de fallback
    # Por enquanto, delega direto ao opencode_go
    return await chat_with_settings(
        messages=messages,
        model=model,
        temperature=temperature,
        consent_granted=consent_granted,
        actor_id=actor_id,
        db=db,
        session_id=session_id,
        rate_limit_per_minute=rate_limit_per_minute,
    )
