"""Cache Redis com TTL 24h e invalidação automática (LGPD compliant)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.redis_client import get_redis


CACHE_TTL_SECONDS = 86400  # 24h


async def get(key: str) -> Any | None:
    """Recupera valor do cache."""
    try:
        client = await get_redis()
        if client is None:
            return None
        raw = await client.get(f"lgpd_cache:{key}")
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


async def set_(key: str, value: Any, ttl: int = CACHE_TTL_SECONDS) -> bool:
    """Armazena valor com TTL."""
    try:
        client = await get_redis()
        if client is None:
            return False
        await client.setex(f"lgpd_cache:{key}", ttl, json.dumps(value, default=str))
        return True
    except Exception:
        return False


async def invalidate(key: str) -> bool:
    """Invalida entrada do cache."""
    try:
        client = await get_redis()
        if client is None:
            return False
        await client.delete(f"lgpd_cache:{key}")
        return True
    except Exception:
        return False


def hash_key(value: str) -> str:
    """Hash determinístico para chave de cache (evitar PII na key)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
