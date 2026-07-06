"""Redis client singleton para serviços assíncronos (app.core.redis_client).

Fornece `get_redis()` assíncrono para uso em services que precisam
de um client Redis async (ex: cache_lgpd.py). Utiliza redis-py >= 4.2
com suporte a asyncio nativo.

LGPD: este módulo não lida com PII — apenas gerencia conexão.
Secrets: URL via REDIS_URL env var (nunca hardcoded).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_redis_client: Any | None = None


async def get_redis() -> Any | None:
    """Retorna cliente Redis async singleton (lazy init).

    Retorna None se redis não está disponível (sem raise —
    serviços de cache devem degradar graciosamente).

    Returns:
        redis.asyncio.Redis instance ou None se indisponível.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis.asyncio as aioredis  # type: ignore[import-untyped]

        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = aioredis.Redis.from_url(
            url,
            socket_connect_timeout=2,
            decode_responses=True,
        )
        return _redis_client
    except ImportError:
        logger.warning("redis[asyncio] não instalado — cache LGPD desabilitado")
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis conexão falhou: %s — cache LGPD desabilitado", exc)
        return None


async def close_redis() -> None:
    """Fecha conexão Redis (chamar no shutdown do app)."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:  # noqa: BLE001
            pass
        _redis_client = None
