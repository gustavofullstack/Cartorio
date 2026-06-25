"""Service n8n_error - HMAC validation + helpers para erros do N8N.

B6 N8N Error Handler Global (Sprint 3):
- N8N Error Workflow dispara este endpoint ao detectar falha em qualquer WF
- Validamos HMAC-SHA256 do body via header `X-N8N-Signature` (mesmo padrao
  Evolution: hex puro OU `sha256=<hex>` estilo GitHub/Stripe)
- N8N_WEBHOOK_SECRET nao configurado = dev mode (aceita) - alinha com Evolution
- Idempotencia: execution_id eh deduplicado (uma exec falhou uma vez = 1 audit)

Pattern identical to `app/services/evolution_ingest.py::validate_evolution_signature`
para consistencia entre integracoes externas (LGPD art. 37 audit chain).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any, Optional

log = logging.getLogger(__name__)


def validate_n8n_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    """Valida HMAC-SHA256 do body do webhook N8N Error Handler.

    Retorna True se:
    - Signature corresponde ao HMAC-SHA256(raw_body, N8N_WEBHOOK_SECRET), ou
    - Secret NAO esta configurado (dev mode - loga warning).

    Retorna False se:
    - Secret configurado mas signature ausente, ou
    - Signature fornecida mas nao corresponde (timing-safe via hmac.compare_digest).

    Suporta formato `sha256=<hex>` (estilo GitHub/Stripe) alem do hex puro.
    """
    # Le env var dinamicamente (NAO usa settings cache) - permite teste monkeypatch
    secret = os.getenv("N8N_WEBHOOK_SECRET") or ""
    if not secret:
        log.warning("n8n error webhook: N8N_WEBHOOK_SECRET nao configurado, dev mode")
        return True
    if not signature:
        return False
    # Strip prefix "sha256=" se presente
    sig_hex = signature
    if sig_hex.startswith("sha256="):
        sig_hex = sig_hex[len("sha256=") :]
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_hex)


def classify_error_type(error: Optional[dict[str, Any]]) -> str:
    """Classifica tipo de erro para label da metrica Prometheus.

    Cards:
    - `connection`: erros tipo ECONNREFUSED, ETIMEDOUT, EHOSTUNREACH (network)
    - `http_4xx`: HTTP 4xx do upstream
    - `http_5xx`: HTTP 5xx do upstream
    - `timeout`: requests Timeout/ReadTimeout
    - `validation`: erros de schema/validation (pydantic, json decode)
    - `auth`: 401, 403, invalid HMAC
    - `unknown`: fallback

    Cardinalidade controlada: 7 valores discretos (sem payload, sem URL).

    Prioridade:
    1. http_code (campo explicito) — mais confiavel que mensagem parseada
    2. Mensagem/name do erro — fallback para casos sem http_code
    """
    if not error:
        return "unknown"

    message = (error.get("message") or "").lower()
    name = (error.get("name") or "").lower()

    # 1. HTTP status code (campo explicito) tem prioridade sobre mensagem
    http_code = error.get("http_code") or error.get("statusCode")
    if isinstance(http_code, int):
        if 500 <= http_code < 600:
            return "http_5xx"
        if 400 <= http_code < 500:
            if http_code in (401, 403):
                return "auth"
            return "http_4xx"

    # 2. Mensagem/name — usado quando nao ha http_code explicito
    #    Checar TANTO message quanto name (Node error codes vem em name)
    if "econnrefused" in message or "econnrefused" in name:
        return "connection"
    if "econnreset" in message or "econnreset" in name:
        return "connection"
    if "etimedout" in message or "timeout" in name or "read timed out" in message:
        return "timeout"
    if (
        "ehostunreach" in message
        or "ehostunreach" in name
        or "enetunreach" in message
        or "enetunreach" in name
        or "enotfound" in message
        or "enotfound" in name
    ):
        return "connection"

    # 3. Validation
    if "validation" in name or "pydantic" in name or "validationerror" in name:
        return "validation"
    if ("json" in name or "json" in message) and "decode" in message:
        return "validation"

    return "unknown"


def compute_payload_digest(payload: dict[str, Any]) -> str:
    """SHA-256 do payload normalizado (audit log field).

    LGPD-safe: digest eh unidirecional, sem PII persistido.
    Audit log armazena digest + metadados estruturados, NAO payload bruto.
    """
    import json

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
