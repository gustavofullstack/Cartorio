"""Testes do SlidingWindowStore (A7 - rate limit).

Cobre:
- RedisSlidingWindowStore (zadd, zremrangebyscore, zcount, _get_client)
- sliding_window_check (allowed/blocked/fail-open)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.sliding_window import (
    RedisSlidingWindowStore,
    SlidingWindowResult,
    sliding_window_check,
)


@pytest.fixture
def mock_store() -> MagicMock:
    """SlidingWindowStore mock (interface Protocol)."""
    store = MagicMock()
    store.zadd = AsyncMock(return_value=1)
    store.zremrangebyscore = AsyncMock(return_value=1)
    store.zcount = AsyncMock(return_value=0)
    return store


class TestRedisSlidingWindowStore:
    """Testes do RedisSlidingWindowStore."""

    def test_init_default_url(self) -> None:
        """__init__ usa REDIS_URL do settings."""
        store = RedisSlidingWindowStore(redis_url="redis://test:6379/0")
        assert store._url == "redis://test:6379/0"

    @pytest.mark.asyncio
    async def test_get_client_creates_on_first_call(self) -> None:
        """_get_client cria Redis client na primeira chamada."""
        with patch("app.services.sliding_window.redis_async.from_url") as mock_from_url:
            mock_from_url.return_value = AsyncMock()
            store = RedisSlidingWindowStore(redis_url="redis://test:6379/0")
            client1 = await store._get_client()
            client2 = await store._get_client()
        assert client1 is client2  # mesmo objeto (cache)
        mock_from_url.assert_called_once_with("redis://test:6379/0", socket_timeout=2.0, socket_connect_timeout=2.0, decode_responses=True)

    @pytest.mark.asyncio
    async def test_zadd_calls_redis_zadd(self) -> None:
        """zadd delega para redis.zadd."""
        store = RedisSlidingWindowStore(redis_url="redis://test:6379/0")
        fake_client = AsyncMock()
        fake_client.zadd.return_value = 1
        with patch.object(store, "_get_client", return_value=fake_client):
            result = await store.zadd("key:1", 1000.0, "member1")
        assert result == 1
        fake_client.zadd.assert_called_once_with("key:1", {"member1": 1000.0})

    @pytest.mark.asyncio
    async def test_zremrangebyscore_calls_redis(self) -> None:
        """zremrangebyscore delega para redis.zremrangebyscore."""
        store = RedisSlidingWindowStore(redis_url="redis://test:6379/0")
        fake_client = AsyncMock()
        fake_client.zremrangebyscore.return_value = 3
        with patch.object(store, "_get_client", return_value=fake_client):
            result = await store.zremrangebyscore("key:1", 0.0, 1000.0)
        assert result == 3
        fake_client.zremrangebyscore.assert_called_once_with("key:1", 0.0, 1000.0)

    @pytest.mark.asyncio
    async def test_zcount_calls_redis(self) -> None:
        """zcount delega para redis.zcount."""
        store = RedisSlidingWindowStore(redis_url="redis://test:6379/0")
        fake_client = AsyncMock()
        fake_client.zcount.return_value = 5
        with patch.object(store, "_get_client", return_value=fake_client):
            result = await store.zcount("key:1", 0.0, 1000.0)
        assert result == 5
        fake_client.zcount.assert_called_once_with("key:1", 0.0, 1000.0)


class TestSlidingWindowCheck:
    """Testes da funcao sliding_window_check."""

    @pytest.mark.asyncio
    async def test_allowed_when_under_limit(self, mock_store: MagicMock) -> None:
        """Retorna allowed=True se count < limit."""
        mock_store.zcount.return_value = 0
        mock_store.zadd.return_value = 1
        result = await sliding_window_check(mock_store, key="ip:hash", limit=10, window_s=60, now=1000.0)
        assert result.allowed is True
        assert result.current == 1
        assert result.limit == 10
        assert result.retry_after == 0
        mock_store.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_blocked_when_at_limit(self, mock_store: MagicMock) -> None:
        """Retorna allowed=False se count >= limit."""
        mock_store.zcount.return_value = 10
        result = await sliding_window_check(mock_store, key="ip:hash", limit=10, window_s=60, now=1000.0)
        assert result.allowed is False
        assert result.current == 10
        assert result.limit == 10
        assert result.retry_after > 0

    @pytest.mark.asyncio
    async def test_blocked_when_over_limit(self, mock_store: MagicMock) -> None:
        """Retorna allowed=False se count > limit."""
        mock_store.zcount.return_value = 15
        result = await sliding_window_check(mock_store, key="ip:hash", limit=10, window_s=60, now=1000.0)
        assert result.allowed is False
        assert result.current == 15

    @pytest.mark.asyncio
    async def test_fail_open_on_store_error(self, mock_store: MagicMock) -> None:
        """Em erro de store (fail-open), retorna allowed=True."""
        mock_store.zremrangebyscore.side_effect = ConnectionError("Redis offline")
        result = await sliding_window_check(mock_store, key="ip:hash", limit=10, window_s=60, now=1000.0)
        assert result.allowed is True
        assert result.current == 0

    @pytest.mark.asyncio
    async def test_removes_expired_before_check(self, mock_store: MagicMock) -> None:
        """Remove entradas expiradas antes de contar."""
        mock_store.zcount.return_value = 3
        await sliding_window_check(mock_store, key="ip:hash", limit=10, window_s=60, now=1000.0)
        mock_store.zremrangebyscore.assert_called_once_with("ip:hash", min_score=0, max_score=940.0)

    @pytest.mark.asyncio
    async def test_uses_default_now_when_not_provided(self, mock_store: MagicMock) -> None:
        """Usa time.time() se now nao fornecido."""
        mock_store.zcount.return_value = 0
        mock_store.zadd.return_value = 1
        with patch("app.services.sliding_window.time.time", return_value=5000.0):
            result = await sliding_window_check(mock_store, key="ip:hash", limit=10, window_s=60)
        assert result.allowed is True
        mock_store.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_current_count_incremented_on_allowed(self, mock_store: MagicMock) -> None:
        """current retorna count+1 apos registrar."""
        mock_store.zcount.return_value = 4
        mock_store.zadd.return_value = 1
        result = await sliding_window_check(mock_store, key="ip:hash", limit=10, window_s=60, now=1000.0)
        assert result.current == 5  # count(4) + 1

    @pytest.mark.asyncio
    async def test_returns_sliding_window_result_type(self, mock_store: MagicMock) -> None:
        """Retorna instancia de SlidingWindowResult."""
        mock_store.zcount.return_value = 2
        result = await sliding_window_check(mock_store, key="ip:hash", limit=10, window_s=60, now=1000.0)
        assert isinstance(result, SlidingWindowResult)
        assert hasattr(result, "allowed")
        assert hasattr(result, "current")
        assert hasattr(result, "limit")
        assert hasattr(result, "retry_after")
