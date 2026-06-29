"""Sliding window rate limit (A7).

Algoritmo: sliding window log usando Redis ZSET.
- Cada request eh adicionada ao ZSET com score = timestamp (em ms).
- Antes de checar, remove entradas com score < (now - window).
- Conta entradas com score >= (now - window).
- Se count >= limit, bloqueia.

Vantagens vs fixed window:
- Sem boundary attack (cliente nao pode enviar 60 reqs no segundo 59 + 60 reqs
  no segundo 0 do proximo minuto pra ter 120 reqs em 1 segundo).
- Distribuicao mais uniforme.

LGPD: chave eh hash do IP/session_id, nao IP puro.
Fail-open: se Redis offline, permite request (log warning).
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Protocol

import redis.asyncio as redis_async

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SlidingWindowResult:
    """Resultado de uma checagem de sliding window."""

    allowed: bool
    current: int
    limit: int
    retry_after: int  # segundos ate a request mais antiga sair da janela


class SlidingWindowStore(Protocol):
    """Interface de storage para sliding window. Implementacoes: RedisSlidingWindowStore, FakeSlidingWindowStore."""

    async def zadd(self, key: str, score: float, member: str) -> int: ...
    async def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int: ...
    async def zcount(self, key: str, min_score: float, max_score: float) -> int: ...


class RedisSlidingWindowStore:
    """Implementacao Redis do SlidingWindowStore."""

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

    async def zadd(self, key: str, score: float, member: str) -> int:
        client = await self._get_client()
        result: int = await client.zadd(key, {member: score})  # type: ignore[assignment]
        return int(result)

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        client = await self._get_client()
        result: int = await client.zremrangebyscore(key, min_score, max_score)  # type: ignore[assignment]
        return int(result)

    async def zcount(self, key: str, min_score: float, max_score: float) -> int:
        client = await self._get_client()
        result: int = await client.zcount(key, min_score, max_score)  # type: ignore[assignment]
        return int(result)


async def sliding_window_check(
    store: SlidingWindowStore,
    *,
    key: str,
    limit: int,
    window_s: int,
    now: float | None = None,
) -> SlidingWindowResult:
    """Checa se request eh permitida no sliding window.

    Args:
        store: SlidingWindowStore (Redis ou fake).
        key: Chave identificadora (hash do IP/session).
        limit: Maximo de requests no window.
        window_s: Tamanho da janela em segundos.
        now: Timestamp atual (em segundos). Default = time.time().
              Util para testes deterministicos.

    Returns:
        SlidingWindowResult(allowed, current, limit, retry_after).
    """
    if now is None:
        now = time.time()
    window_start = now - window_s

    try:
        # 1. Remove entradas expiradas (fora da janela)
        await store.zremrangebyscore(key, min_score=0, max_score=window_start)
        # 2. Conta entradas na janela
        current = await store.zcount(key, min_score=window_start, max_score=now)
        # 3. Decidir
        if current >= limit:
            # Bloqueado: calcula retry_after
            # O retry_after eh ate a request mais antiga sair da janela
            # (i.e., ate `window_s` segundos apos a primeira request da janela).
            # Sem info do ZSET mais antigo, usamos window_s como upper bound.
            retry_after = window_s
            return SlidingWindowResult(
                allowed=False, current=current, limit=limit, retry_after=retry_after
            )
        # 4. Allowed: registra a request
        member = f"{now}:{uuid.uuid4().hex[:8]}"
        await store.zadd(key, score=now, member=member)
        return SlidingWindowResult(allowed=True, current=current + 1, limit=limit, retry_after=0)
    except Exception as e:  # noqa: BLE001
        # Fail-open: Redis offline, permite request
        logger.warning("sliding_window: store offline, fail-open: %s", e)
        return SlidingWindowResult(allowed=True, current=0, limit=limit, retry_after=0)


__all__ = [
    "RedisSlidingWindowStore",
    "SlidingWindowResult",
    "SlidingWindowStore",
    "sliding_window_check",
]
