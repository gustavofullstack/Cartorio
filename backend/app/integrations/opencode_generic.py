"""Provider generico OpenAI-compat (OpenCode-Free, OpenRouter, Groq, Mistral, Google AI Studio).

Todos esses provedores compartilham o mesmo formato OpenAI Chat Completions:
- POST {base_url}/chat/completions
- Headers: Authorization: Bearer {api_key}
- Body: {model, messages, temperature}

Essa abstracao cobre os provedores free-tier que temos configurados no PROMPT.json.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import httpx

from app.services.pii import scrub

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Tipos reutilizados (mesmos de opencode_go)
from app.integrations.opencode_go import ChatError, ChatErrorKind, ChatResponse  # noqa: E402


@dataclass
class ProviderConfig:
    """Configuracao de um provider OpenAI-compat."""

    name: str  # ex: 'opencode_free_1'
    base_url: str
    api_key: Optional[str]
    model: str
    timeout_seconds: float = 30.0

    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)


async def chat(
    messages: list[dict[str, str]],
    *,
    config: ProviderConfig,
    temperature: float = 0.2,
    timeout_seconds: float | None = None,
    consent_granted: bool = False,
    actor_id: str = "anonymous",
    db: "Session | None" = None,
    session_id: str | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
) -> ChatResponse:
    """Chama um provider OpenAI-compat com LGPD compliance."""
    if not config.is_configured():
        raise ChatError(
            f"Provider {config.name} nao configurado (api_key/base_url/model vazio).",
            kind=ChatErrorKind.CONFIG,
        )

    if not consent_granted:
        raise ChatError(
            "LGPD art. 7 I — Consentimento nao concedido.",
            kind=ChatErrorKind.LGPD_BLOCKED,
        )

    if not messages:
        raise ChatError(
            "Lista de messages vazia.",
            kind=ChatErrorKind.CONFIG,
        )

    # ---- PII scrubbing INTERNO (defense-in-depth) ----
    scrubbed_messages: list[dict[str, str]] = []
    total_redacted = 0
    for msg in messages:
        content = msg.get("content", "") or ""
        result = scrub(content)
        scrubbed_messages.append({"role": msg.get("role", "user"), "content": result.text})
        total_redacted += result.redaction_count

    url = f"{config.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.model,
        "messages": scrubbed_messages,
        "temperature": temperature,
    }

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds or config.timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as e:
        raise ChatError(
            f"Timeout em {config.name}",
            kind=ChatErrorKind.TIMEOUT,
        ) from e
    except httpx.HTTPError as e:
        raise ChatError(
            f"Erro de rede em {config.name}: {e}",
            kind=ChatErrorKind.NETWORK,
        ) from e

    latency_ms = int((time.time() - start) * 1000)

    if response.status_code >= 400:
        body = response.text[:500] if response.text else ""
        kind = ChatErrorKind.HTTP_4XX if response.status_code < 500 else ChatErrorKind.HTTP_5XX
        raise ChatError(
            f"{config.name} retornou {response.status_code}: {body[:200]}",
            kind=kind,
            status_code=response.status_code,
            body=body,
        )

    try:
        data = response.json()
    except Exception as e:
        raise ChatError(
            f"Response de {config.name} nao e JSON: {e}",
            kind=ChatErrorKind.PARSE,
        ) from e

    try:
        content = data["choices"][0]["message"]["content"]
        finish_reason = data["choices"][0].get("finish_reason")
    except (KeyError, IndexError, TypeError) as e:
        raise ChatError(
            f"Estrutura inesperada de {config.name}: {e}",
            kind=ChatErrorKind.PARSE,
        ) from e

    usage = data.get("usage", {})
    tokens_in = usage.get("prompt_tokens")
    tokens_out = usage.get("completion_tokens")

    # Output scrub (LGPD-015 BOUNDARY 2)
    scrub_result = scrub(content)
    safe_content = scrub_result.text
    output_pii_redacted_count = scrub_result.redaction_count

    return ChatResponse(
        content=safe_content,
        model=data.get("model", config.model),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
        pii_redacted_count=total_redacted,
        output_pii_redacted_count=output_pii_redacted_count,
        raw=None,
    )


# Provider dispatch table (Turno 37 2026-06-30)
PROVIDER_DISPATCH = {
    "opencode_go": "_opencode_go_provider",
    "opencode_free_1": "opencode_free_1",
    "opencode_free_2": "opencode_free_2",
    "opencode_free_3": "opencode_free_3",
    "openrouter": "openrouter",
    "groq": "groq",
    "mistral": "mistral",
    "google_ai_studio": "google_ai_studio",
    "jules": "jules",
    "openclaw": "openclaw",
}


def get_config_for(provider_name: str) -> ProviderConfig | None:
    """Retorna a config do provider ou None se nao encontrado."""
    from app.config import settings

    if provider_name == "opencode_go":
        return ProviderConfig(
            name="opencode_go",
            base_url=settings.opencode_go_base_url,
            api_key=settings.opencode_go_api_key,
            model=settings.opencode_go_model,
        )
    if provider_name == "opencode_free_1":
        return ProviderConfig(
            name="opencode_free_1",
            base_url=settings.opencode_free_1_base_url,
            api_key=settings.opencode_free_1_api_key,
            model=settings.opencode_free_1_model,
        )
    if provider_name == "opencode_free_2":
        return ProviderConfig(
            name="opencode_free_2",
            base_url=settings.opencode_free_2_base_url,
            api_key=settings.opencode_free_2_api_key,
            model=settings.opencode_free_2_model,
        )
    if provider_name == "opencode_free_3":
        return ProviderConfig(
            name="opencode_free_3",
            base_url=settings.opencode_free_3_base_url,
            api_key=settings.opencode_free_3_api_key,
            model=settings.opencode_free_3_model,
        )
    if provider_name == "openrouter":
        return ProviderConfig(
            name="openrouter",
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
        )
    if provider_name == "groq":
        return ProviderConfig(
            name="groq",
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key,
            model=settings.groq_model,
        )
    if provider_name == "mistral":
        return ProviderConfig(
            name="mistral",
            base_url=settings.mistral_base_url,
            api_key=settings.mistral_api_key,
            model=settings.mistral_model,
        )
    if provider_name == "google_ai_studio":
        return ProviderConfig(
            name="google_ai_studio",
            base_url=settings.google_ai_studio_base_url,
            api_key=settings.google_ai_studio_api_key,
            model=settings.google_ai_studio_model,
        )
    return None
