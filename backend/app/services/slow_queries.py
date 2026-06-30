"""Slow queries storage service (A16).

Ar).

Armazena queries lentas em Redis (TTL 24h) para consulta via
endpoint `/admin/slow-queries`.

- Key Redis: `cartorio:slow_queries` (sorted set, score = timestamp)
- Max entries: 1000 (LRU eviction via ZREMRANGEBYRANK)
- TTL: 24h por entry (expire automatico)
- Nao loga PII (ja filtrado no middleware via SKIP_PATHS)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import redis.asyncio as redis_async

from app.config import settings

logger = logging.getLogger(__name__)

SLOW_QUERIES_KEY = "cartorio:slow_queries"
SLOW_QUERIES_MAX_ENTRIES = 1000
SLOW_QUERIES_TTL_SECONDS = 86400  # 24h


class SlowQueriesError(Exception):
    """Erro do servico de slow queries."""


class SlowQueriesStore:
    """Wrapper async do redis-py para armazenar queries lentas.

    Usage:
        store = SlowQueriesStore()
        await store.add_slow_query({
            "event": "slow_request",
            "method": "GET",
            "path": "/api/v1/protocolo/123",
            "status_code": 200,
            "duration_ms": 1250.5,
            "threshold_ms": 500,
            "request_id": "abc123",
            "client_ip": "192.168.1.1/24",
        })
        queries = await store.get_slow_queries(limit=50)
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._url = redis_url or settings.redis_url
        self._client: redis_async.Redis | None = None

    async def _get_client(self) -> redis_async.Redis:
        """Lazy connect. Falha rapida se redis_url nao setado."""
        if self._client is None:
            if not self._url:
                raise SlowQueriesError("redis_url nao configurado em settings")
            self._client = redis_async.from_url(
                self._url,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        """Fecha client (cleanup em lifespan shutdown)."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def add_slow_query(self, query_data: dict[str, Any]) -> bool:
        """Adiciona uma query lenta ao sorted set Redis.

        Args:
            query_data: Dict com os campos da query lenta.

        Returns:
            True se adicionado com sucesso.
        """
        try:
            client = await self._get_client()

            # Adiciona timestamp se nao existir
            if "timestamp" not in query_data:
                query_data["timestamp"] = time.time()

            # Serializa para JSON
            member = json.dumps(query_data, default=str, ensure_ascii=False)
            score = query_data["timestamp"]

            # ZADD no sorted set
            await client.zadd(SLOW_QUERIES_KEY, {member: score})

            # Define TTL na key (apenas se ainda nao tem)
            await client.expire(SLOW_QUERIES_KEY, SLOW_QUERIES_TTL_SECONDS)

            # LRU: remove entries mais antigas se passou do limite
            count = await client.zcard(SLOW_QUERIES_KEY)
            if count > SLOW_QUERIES_MAX_ENTRIES:
                # Remove os mais antigos (menor score)
                await client.zremrangebyrank(
                    SLOW_QUERIES_KEY, 0, count - SLOW_QUERIES_MAX_ENTRIES - 1
                )

            return True

        except Exception as e:
            logger.error("slow_queries.add falhou: %s", e)
            return False

    async def get_slow_queries(
        self,
        limit: int = 100,
        min_duration_ms: float | None = None,
        path_prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        """Recupera queries lentas mais recentes.

        Args:
            limit: Maximo de entradas a retornar (default 100).
            min_duration_ms: Filtrar por duracao minima em ms.
            path_prefix: Filtrar por prefixo do path.

        Returns:
            Lista de queries lentas (mais recentes primeiro).
        """
        try:
            client = await self._get_client()

            # ZREVRANGE para pegar os mais recentes (maior score primeiro)
            members = await client.zrevrange(SLOW_QUERIES_KEY, 0, limit - 1)

            results = []
            for member in members:
                try:
                    query = json.loads(member)  # type: ignore[arg-type]
                    # Filtros opcionais
                    if min_duration_ms is not None:
                        if query.get("duration_ms", 0) < min_duration_ms:
                            continue
                    if path_prefix is not None:
                        if not query.get("path", "").startswith(path_prefix):
                            continue
                    results.append(query)
                except (json.JSONDecodeError, TypeError):
                    continue

            return results

        except Exception as e:
            logger.error("slow_queries.get falhou: %s", e)
            return []

    async def get_slow_queries_count(self) -> int:
        """Retorna total de queries lentas armazenadas."""
        try:
            client = await self._get_client()
            return await client.zcard(SLOW_QUERIES_KEY)
        except Exception:
            return 0

    async def clear(self) -> bool:
        """Limpa todas as queries lentas (admin only)."""
        try:
            client = await self._get_client()
            await client.delete(SLOW_QUERIES_KEY)
            return True
        except Exception as e:
            logger.error("slow_queries.clear falhou: %s", e)
            return False


# Singleton lazy
_store: SlowQueriesStore | None = None


def get_slow_queries_store() -> SlowQueriesStore:
    """Singleton do SlowQueriesStore. Use como Depends em endpoints."""
    global _store
    if _store is None:
        _store = SlowQueriesStore()
    return _store


__all__ = [
    "SLOW_QUERIES_KEY",
    "SLOW_QUERIES_MAX_ENTRIES",
    "SLOW_QUERIES_TTL_SECONDS",
    "SlowQueriesError",
    "SlowQueriesStore",
    "get_slow_queries_store",
]
