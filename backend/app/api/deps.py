"""FastAPI dependencies compartilhadas (auth, multi-tenant, etc).

Concentra aqui gates de auth reutilizaveis em rotas /integrations/*,
/metrics/n8n, DELETE /cliente/{id}, audit query etc. Substitui inline
checks espalhados (B0.3 2026-06-25 - DRY + coverage uniforme).

Patterns:
- constant-time compare (hmac.compare_digest) para evitar timing attacks
- 401 com WWW-Authenticate header (RFC 7235)
- audit log LGPD art. 37 em TODA tentativa falha (NAO loga valor da chave,
  apenas fingerprint sha256[:8]) — fix LGPD review P0.2 2026-06-25
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.config import Settings, get_settings
from app.services.audit import AuditService

_log = logging.getLogger("auth.deps")


def _key_fingerprint(provided: str | None) -> str:
    """Hash SHA-256 8 chars da chave fornecida (NAO a chave em si).

    LGPD D5 — fingerprint serve pra correlacionar tentativas (mesma chave
    rejeitada N vezes) SEM expor a chave real. Usado apenas no audit log.
    """
    if not provided:
        return "missing"
    return hashlib.sha256(provided.encode("utf-8")).hexdigest()[:8]


def _audit_auth_failure(
    request: Request,
    *,
    reason: str,
    provided: str | None,
) -> None:
    """Grava entrada de audit log pra falha de auth (LGPD art. 37 + P0.2).

    Try/except interno: SE o DB estiver down, a falha de audit NAO pode
    mascarar a resposta 401/503 original. Logamos warning e seguimos.
    """
    try:
        from app.db import session_scope

        # client_ip do Request (X-Forwarded-For honored se vier do proxy Easypanel)
        client_ip = request.client.host if request.client else None
        xff = request.headers.get("x-forwarded-for")
        if xff:
            client_ip = xff.split(",")[0].strip()

        with session_scope() as db:
            AuditService.log(
                db,
                actor_id="anonymous",
                actor_type="unauthorized",
                action="auth.failed",
                resource=str(request.url.path),
                payload={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "key_fingerprint": _key_fingerprint(provided),
                    "reason": reason,
                    "user_agent": request.headers.get("user-agent"),
                },
                ip=client_ip,
                user_agent=request.headers.get("user-agent"),
                request_id=request.headers.get("x-request-id"),
                canal="api",
            )
    except Exception as e:  # noqa: BLE001 — audit log failure must NOT mask 401
        _log.warning("audit log failed for auth failure: %s", e)


def require_cartorio_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    settings: Settings = Depends(get_settings),
) -> str:
    """Valida header X-API-Key contra settings.cartorio_api_key.

    LGPD art. 37 — toda tentativa falha eh audit-logged (ver _audit_auth_failure).
    Sucesso retorna apenas a chave validada para o handler usar como identificador
    de actor (ex: 'n8n_workflow_25').

    Raises:
        HTTPException 503 — CARTORIO_API_KEY nao configurada (safety net).
        HTTPException 401 — header ausente ou invalido.

    Returns:
        str — valor da chave validada (igual ao settings.cartorio_api_key).
    """
    # Aceita tanto X-API-Key quanto x-api-key (HTTP headers sao case-insensitive
    # mas FastAPI Header alias eh case-sensitive por padrao no query). O
    # Annotated acima jah cobre o canonical; este fallback cobre clients
    # que mandam lowercase (ex: requests Python com .headers['x-api-key']).
    provided = x_api_key or request.headers.get("x-api-key")

    expected = settings.cartorio_api_key
    if not expected:
        # FAIL-FAST ja foi aplicado em config.py (pattern + min_length=64),
        # mas safety net se settings desserializar com None por bug.
        _audit_auth_failure(request, reason="config_missing", provided=provided)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "erro": "API_KEY_NOT_CONFIGURED",
                "mensagem": (
                    "Endpoint protegido por X-API-Key mas CARTORIO_API_KEY "
                    "nao esta configurada no servidor. Verifique .env."
                ),
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not provided:
        _audit_auth_failure(request, reason="missing", provided=None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "erro": "UNAUTHORIZED",
                "mensagem": "X-API-Key ausente.",
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not hmac.compare_digest(provided, expected):
        _audit_auth_failure(request, reason="invalid", provided=provided)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "erro": "UNAUTHORIZED",
                "mensagem": "X-API-Key invalida.",
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return provided