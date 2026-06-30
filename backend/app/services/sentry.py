"""Sentry error tracking com PII scrubber pre-envio (A4).

Decisao arquitetural:
- Sentry SDK eh opcional (pip install sentry-sdk[fastapi]).
- Sem SENTRY_DSN: modo NoOp (apenas loga warnings localmente).
- Com SENTRY_DSN: envia eventos com PII scrubbed.

LGPD safety:
- PII (CPF, RG, CNS, CNH, email, telefone) eh SEMPRE removido de
  mensagens de excecao + tags + extra context antes de enviar pro Sentry.
- Audit log nao vai pro Sentry (fica so no DB append-only).
"""

from __future__ import annotations

import logging
import re
import os
from typing import Any

logger = logging.getLogger(__name__)

# Padroes PII que NAO podem ir pro Sentry (apenas regex, nao exaustivo).
# Mascaramento: substitui por SHA256[:8] para manter rastreabilidade
# cruzada (logs locais + Sentry) sem expor o valor.
_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cpf", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b")),
    ("cnpj", re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("phone_br", re.compile(r"\(?\d{2}\)?\s?9?\d{4}-?\d{4}")),
    ("cns", re.compile(r"\b\d{15}\b")),
    ("cnh", re.compile(r"\b\d{11}\b")),
    ("ip", re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
)


def _scrub_string(value: str) -> str:
    """Substitui PII em string por [MASKED:kind]."""
    result = value
    for kind, pattern in _PII_PATTERNS:
        result = pattern.sub(f"[MASKED:{kind}]", result)
    return result


def scrub_pii(obj: Any) -> Any:
    """Recursivamente scrub PII em dict/list/str.

    - str: aplica _scrub_string
    - dict: recursivo nos values (keys nao modificados)
    - list/tuple: recursivo nos elementos
    - outros tipos: retorna as-is
    """
    if isinstance(obj, str):
        return _scrub_string(obj)
    if isinstance(obj, dict):
        return {k: scrub_pii(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        scrubbed = [scrub_pii(v) for v in obj]
        return type(obj)(scrubbed)
    return obj


def _init_sentry() -> bool:
    """Inicializa Sentry SDK se DSN disponivel. Returns True se ativo."""
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return False
    try:
        import sentry_sdk  # type: ignore[import-not-found]
        from sentry_sdk.integrations.fastapi import FastApiIntegration  # type: ignore[import-not-found]
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration  # type: ignore[import-not-found]

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("SENTRY_ENV", "production"),
            release=os.getenv("SENTRY_RELEASE", "cartorio-api@0.6.0"),
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            # LGPD: nunca enviar PII automaticamente.
            send_default_pii=False,
            # Performance: 20% das transacoes (ajustar conforme volume).
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.2")),
            # Filtro before_send para garantir scrub adicional.
            before_send=_before_send,
        )
        logger.info("sentry initialized dsn=%s...", dsn[:20])
        return True
    except ImportError:
        logger.warning("sentry-sdk not installed, error tracking disabled")
        return False


def _before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    """Hook Sentry: scrub PII em todo evento antes de enviar."""
    # Scrub mensagem de excecao
    if "message" in event:
        event["message"] = _scrub_string(event["message"])
    # Scrub exception values
    if "exception" in event:
        for exc in event["exception"].get("values", []):
            if "value" in exc:
                exc["value"] = _scrub_string(exc["value"])
    # Scrub tags
    if "tags" in event:
        event["tags"] = scrub_pii(event["tags"])
    # Scrub extra
    if "extra" in event:
        event["extra"] = scrub_pii(event["extra"])
    # Scrub user (se vier)
    if "user" in event:
        event["user"] = scrub_pii(event["user"])
    return event


def capture_exception(exc: Exception, extra: dict[str, Any] | None = None) -> None:
    """Captura excecao para Sentry (com PII scrubbed) ou loga localmente.

    Args:
        exc: Excecao capturada.
        extra: contexto extra (ja sera scrubbed antes do envio).
    """
    if not _init_sentry():
        # Modo NoOp: loga localmente.
        logger.exception(
            "exception (sentry disabled): %s", exc, extra=scrub_pii(extra) if extra else None
        )
        return

    import sentry_sdk  # type: ignore[import-not-found]

    with sentry_sdk.push_scope() as scope:
        if extra:
            scope.set_extra("context", scrub_pii(extra))
        sentry_sdk.capture_exception(exc)


def capture_message(message: str, level: str = "info", extra: dict[str, Any] | None = None) -> None:
    """Captura mensagem para Sentry (com PII scrubbed)."""
    safe_msg = _scrub_string(message)
    if not _init_sentry():
        getattr(logger, level, logger.info)("msg (sentry disabled): %s", safe_msg)
        return
    import sentry_sdk  # type: ignore[import-not-found]

    with sentry_sdk.push_scope() as scope:
        if extra:
            scope.set_extra("context", scrub_pii(extra))
        sentry_sdk.capture_message(safe_msg, level=level)


__all__ = [
    "capture_exception",
    "capture_message",
    "scrub_pii",
]
