"""Slow request logger middleware.

Registra em log estruturado qualquer request que leve >SLOW_THRESHOLD_MS.
Util para identificar gargalos antes que afetem SLA P95 < 200ms.

- Threshold default: 500ms (configuravel via SLOW_LOG_THRESHOLD_MS)
- Path skipped: /health/* /metrics (ruido)
- Audit log: nunca eh chamado aqui (slow log nao eh mutacao)
- Estrutura log: JSON com method, path, status, duration_ms, request_id
"""
from __future__ import annotations

import json
import logging
import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("cartorio.slow")

SLOW_THRESHOLD_MS_DEFAULT = 500

# Paths que NAO devem ser logados como slow (sao ruidosos/sem valor)
SKIP_PATHS: tuple[str, ...] = (
    "/health",
    "/health/",
    "/health/live",
    "/health/ready",
    "/health/radar",
    "/health/db",
    "/health/redis",
    "/health/llm",
    "/health/backup",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
)


class SlowLogMiddleware(BaseHTTPMiddleware):
    """Log estruturado para requests lentas.

    NAO bloqueia a response. Apenas emite log de WARNING/INFO.
    Threshold configuravel via app.state.settings.slow_log_threshold_ms.
    """

    def __init__(self, app, threshold_ms: int = SLOW_THRESHOLD_MS_DEFAULT) -> None:
        super().__init__(app)
        self.threshold_ms = threshold_ms

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip ruidosos
        if any(request.url.path.startswith(p) for p in SKIP_PATHS):
            return await call_next(request)

        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        if elapsed_ms >= self.threshold_ms:
            request_id = getattr(request.state, "request_id", None)
            log_payload = {
                "event": "slow_request",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed_ms, 2),
                "threshold_ms": self.threshold_ms,
                "request_id": request_id,
                "client_ip": getattr(request.state, "client_ip", None),
            }
            # WARNING para >=2x threshold, INFO para >=1x threshold
            level = logging.WARNING if elapsed_ms >= self.threshold_ms * 2 else logging.INFO
            logger.log(level, json.dumps(log_payload, default=str))

        return response
