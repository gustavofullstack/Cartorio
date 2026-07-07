"""Distributed lock com Redis (redlock simplificado).

SQUAD A20 — garante exclusao mutua em operacoes criticas
(emitir protocolo, validar documento, etc).
"""

from __future__ import annotations

import asyncio
import secrets
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.core.redis_client import get_redis


LOCK_TTL_SECONDS = 30
LOCK_PREFIX = "cartorio:lock:"


def _gen_token() -> str:
    """Token unico por holder (evita liberar lock de outro)."""
    return secrets.token_urlsafe(16)


class LockAcquireError(Exception):
    """Nao conseguiu adquirir o lock apos retries."""


async def _acquire(key: str, token: str, ttl: int = LOCK_TTL_SECONDS, retries: int = 5) -> bool:
    """Tenta adquirir lock com NX (set if not exists)."""
    try:
        client = await get_redis()
        if client is None:
            return False
        for attempt in range(retries):
            ok = await client.set(f"{LOCK_PREFIX}{key}", token, nx=True, ex=ttl)
            if ok:
                return True
            await asyncio.sleep(0.1 * (attempt + 1))
        return False
    except Exception:
        return False


async def _release(key: str, token: str) -> bool:
    """Libera lock somente se token bater (atomic check-and-del via Lua)."""
    try:
        client = await get_redis()
        if client is None:
            return False
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        result = await client.eval(script, 1, f"{LOCK_PREFIX}{key}", token)
        return result == 1
    except Exception:
        return False


@asynccontextmanager
async def lock(key: str, ttl: int = LOCK_TTL_SECONDS) -> AsyncIterator[bool]:
    """Context manager para lock distribuido.

    Usage:
        async with lock("emitir_protocolo:123"):
            # secao critica
            ...
    """
    token = _gen_token()
    acquired = await _acquire(key, token, ttl)
    try:
        yield acquired
    finally:
        if acquired:
            await _release(key, token)


async def try_lock(key: str, ttl: int = LOCK_TTL_SECONDS) -> tuple[bool, str | None]:
    """Tenta adquirir lock sem context manager.

    Returns: (acquired, token) — se acquired, usar token para release.
    """
    token = _gen_token()
    acquired = await _acquire(key, token, ttl)
    return acquired, token if acquired else None


async def release_lock(key: str, token: str) -> bool:
    """Libera lock previamente adquirido."""
    return await _release(key, token)
