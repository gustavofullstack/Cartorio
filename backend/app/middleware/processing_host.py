"""G8.10.T1 — Dynamic processing host identifier on HTTP responses.

Adds ``X-Cartorio-Processing-Host`` to every response so proxies (Traefik),
operators, and multi-replica debugging can see which backend instance handled
the request.

Identifier source (no PII):
1. Env ``PROCESSING_HOST_ID`` when set (explicit override for containers)
2. Otherwise ``socket.gethostname()``

Never put user data, tokens, IPs of clients, or document ids in this header.
"""

from __future__ import annotations

import os
import socket
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

PROCESSING_HOST_HEADER = "X-Cartorio-Processing-Host"
PROCESSING_HOST_ENV = "PROCESSING_HOST_ID"


def get_processing_host_id() -> str:
    """Return the processing host identifier (env override or hostname).

    Values are infrastructure identifiers only — never PII.
    Empty/whitespace env is ignored and falls back to hostname.
    """
    override = os.environ.get(PROCESSING_HOST_ENV, "").strip()
    if override:
        return override
    try:
        host = socket.gethostname().strip()
    except OSError:  # pragma: no cover - extremely rare
        host = ""
    return host or "unknown"


class ProcessingHostMiddleware(BaseHTTPMiddleware):
    """Attach ``X-Cartorio-Processing-Host`` to all HTTP responses (G8.10.T1)."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers[PROCESSING_HOST_HEADER] = get_processing_host_id()
        return response


__all__ = [
    "PROCESSING_HOST_ENV",
    "PROCESSING_HOST_HEADER",
    "ProcessingHostMiddleware",
    "get_processing_host_id",
]
