"""FakeIdempotencyStore - implementacao in-memory para testes.

A6: mesmo contrato que RedisIdempotencyStore, mas sem dependencia de Redis.
"""

from __future__ import annotations

import time
from typing import Any


class FakeIdempotencyStore:
    """In-memory store com TTL simulado. Thread-unsafe (testes rodam em event loop)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[dict[str, Any], float]] = {}

    def _is_expired(self, key: str) -> bool:
        if key not in self._store:
            return True
        _, expires_at = self._store[key]
        return time.time() > expires_at

    async def setnx(self, key: str, value: dict[str, Any], ttl_seconds: int) -> bool:
        if key in self._store and not self._is_expired(key):
            return False
        self._store[key] = (value, time.time() + ttl_seconds)
        return True

    async def get(self, key: str) -> dict[str, Any] | None:
        if self._is_expired(key):
            self._store.pop(key, None)
            return None
        value, _ = self._store[key]
        return value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


__all__ = ["FakeIdempotencyStore"]
