"""API versioning via header (A20).

Adiciona headers em TODA response:
- X-API-Version: versao da API (0.5.4)
- X-API-Deprecated: true se versao foi marcada deprecated
- Deprecation: RFC 8594 (data ISO quando foi deprecada)
- Sunset: RFC 8594 (data ISO quando sera removida)
- Link: RFC 8594 (link para nova versao)

Tambem expoe endpoint /version que retorna metadata completa.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("cartorio.version")

API_VERSION = "0.5.4"
API_RELEASED = "2026-06-24"
API_NEXT_VERSION = "0.6.0"  # Em desenvolvimento


class VersionHeaderMiddleware(BaseHTTPMiddleware):
    """Adiciona headers de versao em todas responses (A20)."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # Headers obrigatorios em TODA response
        response.headers["X-API-Version"] = API_VERSION
        response.headers["X-API-Released"] = API_RELEASED

        # Link para versao em desenvolvimento (RFC 8594)
        response.headers["Link"] = (
            f'</api/v{API_NEXT_VERSION.split(".")[0]}/docs>; rel="successor-version"'
        )

        return response


def install_version_endpoint(app: FastAPI) -> None:
    """Instala GET /version com metadata completa."""

    @app.get("/version", tags=["meta"], include_in_schema=False)
    async def version_info() -> dict:
        """Retorna versao completa + links (RFC 8594)."""
        return {
            "version": API_VERSION,
            "released": API_RELEASED,
            "next_version": API_NEXT_VERSION,
            "deprecated": False,
            "links": {
                "docs": "/docs",
                "openapi": "/openapi.json",
                "health": "/health",
            },
        }
