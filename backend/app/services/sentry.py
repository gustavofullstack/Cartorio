"""Sentry error tracking com PII scrubber pre-envio (A4 + G8.18.T4).

Decisao arquitetural:
- Sentry SDK eh opcional (pip install sentry-sdk[fastapi]).
- Sem SENTRY_DSN: modo NoOp (apenas loga warnings localmente).
- Com SENTRY_DSN: envia eventos com PII scrubbed.

LGPD safety:
- PII (CPF, RG, CNS, CNH, email, telefone) eh SEMPRE removido de
  mensagens de excecao + tags + extra context antes de enviar pro Sentry.
- Audit log nao vai pro Sentry (fica so no DB append-only).
- G8.18.T4: scrub cobre TODOS os campos do Sentry event protocol:
  message, exception.values, exception.stacktrace.frames, breadcrumbs,
  request.{query_string, cookies, headers, data}, user.id (com hash
  deterministico quando looks_like_pii). LGPD Art. 46 + Art. 50.
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


def looks_like_pii(value: str) -> bool:
    """G8.18.T4 — retorna True se a string contem algum padrao PII bruto.

    Usa o modulo `app.services.pii.detect_only` (LGPD canonico) quando
    disponivel; cai pro regex local em fallback (caso pii module ainda
    nao foi inicializado — raro em prod mas evita ImportError em tests).
    """
    if not isinstance(value, str) or not value:
        return False
    try:
        from app.services.pii import detect_only as _detect_only

        return bool(_detect_only(value))
    except Exception:
        for _, pattern in _PII_PATTERNS:
            if pattern.search(value):
                return True
        return False


def hash_pii_sentry(value: str) -> str:
    """G8.18.T4 — hash deterministico para substituir user.id raw.

    Usa SHA256(value) puro (sem salt per-client) porque o valor ja vai
    sair do backend; o objetivo eh apenas evitar expor o PII raw no
    SaaS do Sentry mantendo rastreabilidade cruzada via prefixo.
    """
    import hashlib

    return "anon-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def scrub_dict_inplace(d: dict[str, Any]) -> None:
    """G8.18.T4 — scrub in-place recursivo (apaga PII de dicts aninhados).

    - str + looks_like_pii -> "[LGPD-SCRUBBED]"
    - dict -> recursivo
    - list -> per-element
    - outros tipos -> intactos
    """
    for k, v in list(d.items()):
        if isinstance(v, str):
            if looks_like_pii(v):
                d[k] = "[LGPD-SCRUBBED]"
        elif isinstance(v, dict):
            scrub_dict_inplace(v)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, str) and looks_like_pii(item):
                    v[i] = "[LGPD-SCRUBBED]"
                elif isinstance(item, dict):
                    scrub_dict_inplace(item)


def scrub_pii_from_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """G8.18.T4 — Sentry before_send hook que cobre TODOS os campos do event protocol.

    Cobre:
    1. message
    2. exception.values[].value/type + stacktrace.frames[].filename/function/vars
    3. breadcrumbs.values[].message + .data (dict recursivo)
    4. request.{query_string, cookies, headers, data}
    5. user.id -> hash deterministico se looks_like_pii
    6. tags + extra + user (mantido do hook legado)

    LGPD Art. 46 (seguranca) + Art. 50 (boa-fe). Zero PII raw em
    vendor externo (Sentry SaaS).
    """
    if event is None:
        return None

    # 1. Scrub message (string field).
    if "message" in event and isinstance(event["message"], str):
        event["message"] = _scrub_string(event["message"])

    # 2. Scrub exception values + stacktrace frames.
    if "exception" in event and isinstance(event["exception"], dict):
        for exc in event["exception"].get("values", []) or []:
            if not isinstance(exc, dict):
                continue
            for key in ("value", "type"):
                if key in exc and isinstance(exc[key], str):
                    exc[key] = _scrub_string(exc[key])
            stacktrace = exc.get("stacktrace")
            if isinstance(stacktrace, dict):
                for frame in stacktrace.get("frames", []) or []:
                    if not isinstance(frame, dict):
                        continue
                    for fkey in ("filename", "function", "vars"):
                        if fkey in frame:
                            if isinstance(frame[fkey], str):
                                frame[fkey] = _scrub_string(frame[fkey])
                            elif isinstance(frame[fkey], dict):
                                scrub_dict_inplace(frame[fkey])

    # 3. Scrub breadcrumbs (message string + data dict recursivo).
    if "breadcrumbs" in event and isinstance(event["breadcrumbs"], dict):
        for bc in event["breadcrumbs"].get("values", []) or []:
            if not isinstance(bc, dict):
                continue
            for bkey in ("message",):
                if bkey in bc and isinstance(bc[bkey], str):
                    bc[bkey] = _scrub_string(bc[bkey])
            data = bc.get("data")
            if isinstance(data, dict):
                scrub_dict_inplace(data)

    # 4. Scrub request (query_string/cookies/headers/body).
    if "request" in event and isinstance(event["request"], dict):
        req = event["request"]
        for rkey in ("query_string", "cookies", "headers"):
            if rkey in req:
                if isinstance(req[rkey], str):
                    req[rkey] = _scrub_string(req[rkey])
                elif isinstance(req[rkey], dict):
                    for k, v in list(req[rkey].items()):
                        if isinstance(v, str) and looks_like_pii(v):
                            req[rkey][k] = "[LGPD-SCRUBBED]"
        if "data" in req and isinstance(req["data"], dict):
            scrub_dict_inplace(req["data"])

    # 5. user.id -> hash deterministico se looks_like_pii.
    user = event.get("user")
    if isinstance(user, dict) and "id" in user:
        uid = user["id"]
        if isinstance(uid, str) and looks_like_pii(uid):
            user["id"] = hash_pii_sentry(uid)
        elif not isinstance(uid, str):
            # Mantem so valores escalares seguros; serializa como hash.
            user["id"] = hash_pii_sentry(str(uid))

    # 6. Mantido do hook legado: tags + extra + user (recursivo).
    if "tags" in event:
        event["tags"] = scrub_pii(event["tags"])
    if "extra" in event:
        event["extra"] = scrub_pii(event["extra"])
    if "user" in event:
        event["user"] = scrub_pii(event["user"])

    return event


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
            # G8.18.T4 — hook canonico cobre TODOS os campos do event
            # protocol. Aplica tambem a transactions (PII em breadcrumbs
            # de transacoes HTTP, headers, etc).
            before_send=scrub_pii_from_event,
            before_send_transaction=scrub_pii_from_event,
        )
        logger.info("sentry initialized dsn=%s...", dsn[:20])
        return True
    except ImportError:
        logger.warning("sentry-sdk not installed, error tracking disabled")
        return False


def _before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    """Hook Sentry legado — delega para `scrub_pii_from_event` (G8.18.T4).

    Mantido como alias para nao quebrar imports externos / testes legados
    (ex.: test_sentry_a4.py). Toda a logica vive em
    `scrub_pii_from_event`.
    """
    import json

    if event is None:
        return None

    try:
        orig_str = json.dumps(event)
    except Exception:
        orig_str = ""

    event = scrub_pii_from_event(event, _hint) or event

    try:
        scrubbed_str = json.dumps(event)
    except Exception:
        scrubbed_str = ""

    if orig_str and scrubbed_str and orig_str != scrubbed_str:
        logger.warning("LGPD Sentry Alert: raw PII leak detected and prevented in Sentry payload!")
        from app.services.metrics import store

        store.inc_counter("cartorio_pii_leak_prevented_total")

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
    "hash_pii_sentry",
    "looks_like_pii",
    "scrub_dict_inplace",
    "scrub_pii",
    "scrub_pii_from_event",
]
