"""Cache Redis 24h para emolumento (A21).

Chave: emolumento:{tipo_documento}:{valor}
TTL: 86400s (24h)
LGPD: chave NAO expoe PII (tipo+valor sao publicos).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 86400  # 24h


def _get_redis_client() -> Any:
    try:
        import redis  # type: ignore[import-untyped]
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return redis.Redis.from_url(url, socket_connect_timeout=2)
    except ImportError:
        return None


def _cache_key(tipo_documento: str, valor: float) -> str:
    """Constroi chave de cache deterministica."""
    valor_int = int(valor * 100)  # centavos para evitar float precision
    return f"emolumento:{tipo_documento}:{valor_int}"


def get_cached(tipo_documento: str, valor: float) -> dict | None:
    """Busca valor em cache. Retorna dict ou None se miss/erro."""
    r = _get_redis_client()
    if r is None:
        return None
    try:
        raw = r.get(_cache_key(tipo_documento, valor))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning("emolumento_cache.get falhou: %s", e)
        return None


def set_cached(tipo_documento: str, valor: float, payload: dict) -> bool:
    """Salva valor no cache. Retorna True se ok, False se erro."""
    r = _get_redis_client()
    if r is None:
        return False
    try:
        r.setex(
            _cache_key(tipo_documento, valor),
            CACHE_TTL_SECONDS,
            json.dumps(payload, default=str),
        )
        return True
    except Exception as e:
        logger.warning("emolumento_cache.set falhou: %s", e)
        return False


def invalidate(tipo_documento: str | None = None) -> int:
    """Invalida cache. Se tipo_documento=None, invalida TUDO (prefix scan).

    Returns:
        numero de chaves removidas.
    """
    r = _get_redis_client()
    if r is None:
        return 0
    try:
        if tipo_documento is None:
            keys = list(r.scan_iter(match="emolumento:*", count=100))
            if keys:
                r.delete(*keys)
            return len(keys)
        else:
            keys = list(r.scan_iter(match=f"emolumento:{tipo_documento}:*", count=100))
            if keys:
                r.delete(*keys)
            return len(keys)
    except Exception as e:
        logger.warning("emolumento_cache.invalidate falhou: %s", e)
        return 0
