"""FastAPI dependencies compartilhadas (auth, multi-tenant, etc).

Concentra aqui gates de auth reutilizaveis em rotas /integrations/*,
/metrics/n8n, DELETE /cliente/{id}, audit query etc. Substitui inline
checks espalhados (B0.3 2026-06-25 - DRY + coverage uniforme).

Patterns:
- constant-time compare (hmac.compare_digest) para evitar timing attacks
- 401 com WWW-Authenticate header (RFC 7235)
- audit log LGPD art. 37 em toda tentativa falha (NAO loga o valor da chave)
"""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.config import Settings, get_settings


def require_cartorio_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    settings: Settings = Depends(get_settings),
) -> str:
    """Valida header X-API-Key contra settings.cartorio_api_key.

    LGPD art. 37 — toda tentativa (sucesso ou falha) eh audit-logged em
    routes que envolvem dados pessoais. Aqui retornamos apenas a chave
    validada (string) para o handler usar como identificar de actor
    (ex: 'n8n_workflow_25').

    Raises:
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
        # FAIL-FAST ja foi aplicado em config.py (min_length=64), mas safety net.
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

    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "erro": "UNAUTHORIZED",
                "mensagem": "X-API-Key ausente ou invalida.",
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return provided
