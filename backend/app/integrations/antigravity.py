"""Antigravity-SDK integration (Turno 38 — 2026-06-30).

Antigravity é uma CLI/SDK de agente AI que usa OAuth2 Google para autenticar
e prover modelos Gemini (gemini-3.1-pro, gemini-2.5-pro, gemini-3-flash).
Implementado como fallback alternativo a Jules (que também usa Gemini por
trás mas via API REST async).

Specs:
- OAuth2 Google (gcloud auth login ou device flow)
- Models: gemini-3.1-pro (planning), gemini-2.5-pro (execution), gemini-3-flash (fast_scan)
- Plano default: AI_ULTRA (concurrency 4, max_reasoning_steps 30)
- Tool permission mode: ASK_BEFORE_EXECUTE

Armazenamento de token:
- Tenta OS keyring primeiro
- Fallback: ~/.config/antigravity/auth_token.json

LGPD compliance:
- Mesmos padroes dos outros provedores (PII scrub input + output)
- Audit log via AuditService.log
- Consent gate antes da chamada
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import httpx

from app.integrations.opencode_go import ChatError, ChatErrorKind, ChatResponse
from app.services.pii import scrub

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default turn 38 — 2026-06-30: alias canonico do model selection.
# Mantem compat com o que rest of chain espera.

ANTIGRAVITY_DEFAULT_MODEL = "gemini-3.1-pro"
ANTIGRAVITY_PLANNING_MODEL = "gemini-3.1-pro"
ANTIGRAVITY_EXECUTION_MODEL = "gemini-2.5-pro"
ANTIGRAVITY_FAST_SCAN_MODEL = "gemini-3-flash"

logger = logging.getLogger(__name__)

# Antigravity config paths
ANTIGRAVITY_TOKEN_PATH = Path.home() / ".config" / "antigravity" / "auth_token.json"
ANTIGRAVITY_API_URL = "https://antigravity.googleapis.com/v1"


@dataclass(frozen=True)
class AntigravityConfig:
    """Configuracao Antigravity (OAuth2 stored ou dev token)."""

    name: str = "antigravity"
    base_url: str = ANTIGRAVITY_API_URL
    default_model: str = "gemini-3.1-pro"
    available_models: tuple[str, ...] = (
        "gemini-3.1-pro",
        "gemini-2.5-pro",
        "gemini-3-flash",
    )
    planning_model: str = "gemini-3.1-pro"
    execution_model: str = "gemini-2.5-pro"
    fast_scan_model: str = "gemini-3-flash"
    timeout_seconds: float = 60.0


def _load_oauth_token() -> Optional[str]:
    """Carrega OAuth token do keyring ou arquivo fallback.

    Returns:
        Access token ou None se nao disponivel.
    """
    # 1. OS keyring (se disponivel)
    try:
        import keyring

        token = keyring.get_password("antigravity", "oauth_access_token")
        if token:
            return token
    except (ImportError, Exception):
        pass

    # 2. Fallback arquivo
    if ANTIGRAVITY_TOKEN_PATH.exists():
        try:
            with ANTIGRAVITY_TOKEN_PATH.open() as f:
                data = json.load(f)
                return data.get("access_token") or data.get("token")
        except Exception as e:
            logger.warning("Falha ao ler token Antigravity de %s: %s", ANTIGRAVITY_TOKEN_PATH, e)

    # 3. Env var dev (escape hatch para testes)
    return os.environ.get("ANTIGRAVITY_TOKEN")


def is_configured() -> bool:
    """Verifica se Antigravity tem credenciais OAuth configuradas."""
    return _load_oauth_token() is not None


async def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    use_planning_mode: bool = False,
    timeout_seconds: float | None = None,
    consent_granted: bool = False,
    actor_id: str = "anonymous",
    db: "Session | None" = None,
    session_id: str | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
) -> ChatResponse:
    """Chama Antigravity API com LGPD compliance.

    Args:
        messages: Lista OpenAI-compat ({role, content}).
        model: Modelo a usar (default gemini-3.1-pro).
        use_planning_mode: Se True, usa o planning_model (mais lento, melhor raciocinio).
        consent_granted: LGPD art. 7 I — bloqueia se False.

    Returns:
        ChatResponse com content + metadata.

    Raises:
        ChatError:
        - CONFIG se nao tem OAuth token
        - LGPD_BLOCKED se consent_granted=False
        - HTTP_4XX/5XX se Antigravity retornar erro
    """
    config = AntigravityConfig()

    # Validacao
    token = _load_oauth_token()
    if not token:
        raise ChatError(
            "Antigravity OAuth token nao configurado. "
            f"Verifique {ANTIGRAVITY_TOKEN_PATH} ou env ANTIGRAVITY_TOKEN.",
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

    # Model selection
    selected_model = (
        config.planning_model if use_planning_mode else (model or config.default_model)
    )
    if selected_model not in config.available_models:
        logger.warning(
            "Antigravity: model %s nao disponivel, fallback para %s",
            selected_model,
            config.default_model,
        )
        selected_model = config.default_model

    # PII scrubbing INTERNO (defense-in-depth)
    scrubbed_messages: list[dict[str, str]] = []
    total_redacted = 0
    for msg in messages:
        content = msg.get("content", "") or ""
        result = scrub(content)
        scrubbed_messages.append({"role": msg.get("role", "user"), "content": result.text})
        total_redacted += result.redaction_count

    # Request format: Antigravity espera formato Gemini-like
    payload = {
        "model": selected_model,
        "messages": scrubbed_messages,
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{config.base_url}/chat/completions"

    start = time.time()
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds or config.timeout_seconds
        ) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as e:
        raise ChatError(
            f"Timeout Antigravity ({timeout_seconds or config.timeout_seconds}s)",
            kind=ChatErrorKind.TIMEOUT,
        ) from e
    except httpx.HTTPError as e:
        raise ChatError(
            f"Erro de rede Antigravity: {e}",
            kind=ChatErrorKind.NETWORK,
        ) from e

    latency_ms = int((time.time() - start) * 1000)

    if response.status_code >= 400:
        body = response.text[:500] if response.text else ""
        kind = ChatErrorKind.HTTP_4XX if response.status_code < 500 else ChatErrorKind.HTTP_5XX

        # 401/403 → token invalido/expirado, deve ser tratado (re-autenticar)
        if response.status_code in (401, 403):
            logger.error(
                "Antigravity token expirado/invalido (status=%d). Re-autenticar via OAuth2.",
                response.status_code,
            )

        raise ChatError(
            f"Antigravity HTTP {response.status_code}: {body[:200]}",
            kind=kind,
            status_code=response.status_code,
            body=body,
        )

    # Parse response (OpenAI-compat format)
    try:
        data = response.json()
    except Exception as e:
        raise ChatError(
            f"Response Antigravity nao-JSON: {e}",
            kind=ChatErrorKind.PARSE,
        ) from e

    try:
        content = data["choices"][0]["message"]["content"]
        finish_reason = data["choices"][0].get("finish_reason")
    except (KeyError, IndexError, TypeError) as e:
        raise ChatError(
            f"Estrutura inesperada Antigravity: {e}",
            kind=ChatErrorKind.PARSE,
        ) from e

    usage = data.get("usage", {})
    tokens_in = usage.get("prompt_tokens")
    tokens_out = usage.get("completion_tokens")

    # Output scrub
    scrub_result = scrub(content)
    safe_content = scrub_result.text
    output_pii_redacted_count = scrub_result.redaction_count

    # Audit log LGPD-015 (Turno 38 — 2026-06-30: era theater of compliance,
    # docstring prometia e codigo nao entregava. Agora chama AuditService.log
    # com padrao canonico igual a jules.py::chat_with_settings).
    if db is not None:
        try:
            from app.services.audit import AuditService

            AuditService.log(
                db,
                actor_id=actor_id,
                actor_type="bot",
                action="llm.antigravity_called",
                resource=f"llm:antigravity:{selected_model}",
                payload={
                    "model": selected_model,
                    "use_planning_mode": use_planning_mode,
                    "input_pii_redacted": total_redacted,
                    "output_pii_redacted": output_pii_redacted_count,
                    "latency_ms": latency_ms,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "consent_granted": consent_granted,
                },
                request_id=request_id,
                ip=client_ip,
                canal="api",
            )
            if output_pii_redacted_count > 0:
                AuditService.log(
                    db,
                    actor_id=actor_id,
                    actor_type="bot",
                    action="llm.output_scrubbed",
                    resource=f"llm:antigravity:{selected_model}",
                    payload={
                        "redaction_count": output_pii_redacted_count,
                        "provider": "antigravity",
                    },
                    request_id=request_id,
                    ip=client_ip,
                    canal="api",
                )
        except Exception as exc:
            logger.warning("antigravity.audit_log_failed: %s", exc)

    return ChatResponse(
        content=safe_content,
        model=data.get("model", selected_model),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
        pii_redacted_count=total_redacted,
        output_pii_redacted_count=output_pii_redacted_count,
        raw=None,
    )


async def chat_with_settings(
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> ChatResponse:
    """Convenience wrapper."""
    return await chat(messages, **kwargs)
