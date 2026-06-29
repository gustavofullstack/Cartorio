"""Deprecation headers middleware (A24.5).

Adiciona headers `Deprecation` (RFC 8594) + `Sunset` (RFC 7231) + `Link`
apenas em rotas /api/v1/* para avisar clientes que serao removidas em 2027-12-31.

Coexiste com VersionHeaderMiddleware (A20) que adiciona X-API-Version global.
Este middleware foca em ROTAS v1 especificamente, indicando que v2 eh o destino.

Headers aplicados em /api/v1/*:
- Deprecation: true (RFC 8594 boolean)
- Sunset: Wed, 31 Dec 2027 00:00:00 GMT (RFC 7231)
- Link: </api/v2/<path>>; rel="successor-version" (RFC 8594)

Nao aplica em /api/v2/*, /health, /docs, /openapi.json, /version.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("cartorio.deprecation")

# Sunset canonico da API v1: 2027-12-31 (A24 SLA — 18 meses a partir de 2026-06-25)
V1_SUNSET_DT = datetime(2027, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
V1_SUNSET_RFC7231 = V1_SUNSET_DT.strftime("%a, %d %b %Y %H:%M:%S GMT")


def _build_v2_link(request_path: str) -> str:
    """Converte /api/v1/<rest> -> /api/v2/<rest>.

    Args:
        request_path: path atual (ex: /api/v1/clientes)

    Returns:
        path equivalente v2 (ex: /api/v2/clientes)
    """
    if request_path.startswith("/api/v1/"):
        return "/api/v2/" + request_path[len("/api/v1/") :]
    return "/api/v2/"


class DeprecationHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona headers de deprecation em rotas /api/v1/*."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Processa request primeiro (permite 401/404 originais serem enriquecidos)
        response = await call_next(request)

        # Aplica headers APENAS em rotas v1
        path = request.url.path
        if path.startswith("/api/v1/"):
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = V1_SUNSET_RFC7231

            v2_path = _build_v2_link(path)
            response.headers["Link"] = f'<{v2_path}>; rel="successor-version"'

            logger.debug(
                "v1 deprecation headers applied: path=%s sunset=%s successor=%s",
                path,
                V1_SUNSET_RFC7231,
                v2_path,
            )

        return response
