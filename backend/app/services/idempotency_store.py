"""IdempotencyStore - interface para cache de respostas de POST.

A6: cliente envia `Idempotency-Key: <uuid>` em POST. Backend faz SETNX
no Redis com TTL 24h. Se ja existe, retorna 200 com o resultado anterior
(nao duplica mutacao).

LGPD: cache armazena APENAS o response (sem PII). Chave eh hash de
(Idempotency-Key + endpoint + actor_id) para evitar colisao entre
clientes/usuarios diferentes.
"""
from __future__ import annotations

import json
from typing import Any, Protocol

import redis.asyncio as redis_async

from app.config import settings


class IdempotencyStore(Protocol):
    """Interface de storage de idempotency. Implementacoes: RedisIdempotencyStore, FakeIdempotencyStore."""

    async def setnx(self, key: str, value: dict[str, Any], ttl_seconds: int) -> bool:
        """SETNX com TTL. Retorna True se inseriu, False se ja existia."""
        ...

    async def get(self, key: str) -> dict[str, Any] | None:
        """Retorna valor cacheado ou None se nao existe/expirou."""
        ...

    async def delete(self, key: str) -> None:
        """Remove chave (ex.: response 5xx nao cacheia)."""
        ...


class RedisIdempotencyStore:
    """Implementacao Redis do IdempotencyStore.

    Algoritmo: SETNX com TTL 24h. Chave = `idempotency:<hash>`.
    """

    DEFAULT_TTL_SECONDS = 86400  # 24h

    def __init__(self, redis_url: str | None = None) -> None:
        self._url = redis_url or settings.redis_url
        self._client: redis_async.Redis | None = None

    async def _get_client(self) -> redis_async.Redis:
        if self._client is None:
            self._client = redis_async.from_url(
                self._url,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                decode_responses=True,
            )
        return self._client

    async def setnx(self, key: str, value: dict[str, Any], ttl_seconds: int) -> bool:
        client = await self._get_client()
        # SETNX (NX) + EX (TTL atomico)
        result = await client.set(key, json.dumps(value), nx=True, ex=ttl_seconds)
        return bool(result)

    async def get(self, key: str) -> dict[str, Any] | None:
        client = await self._get_client()
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def delete(self, key: str) -> None:
        client = await self._get_client()
        await client.delete(key)


__all__ = [
    "IdempotencyStore",
    "RedisIdempotencyStore",
]
