"""Testes do IdempotencyStore (A6 - cache de POST com Idempotency-Key).

Cobre:
- RedisIdempotencyStore: setnx, get, delete, _get_client
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.idempotency_store import RedisIdempotencyStore


class TestRedisIdempotencyStore:
    """Testes do RedisIdempotencyStore."""

    def test_init_default_ttl(self) -> None:
        """DEFAULT_TTL_SECONDS = 86400 (24h)."""
        assert RedisIdempotencyStore.DEFAULT_TTL_SECONDS == 86400

    def test_init_custom_redis_url(self) -> None:
        """__init__ aceita redis_url customizada."""
        store = RedisIdempotencyStore(redis_url="redis://custom:6379/1")
        assert store._url == "redis://custom:6379/1"
        assert store._client is None

    @pytest.mark.asyncio
    async def test_get_client_creates_on_first_call(self) -> None:
        """_get_client cria Redis client na primeira chamada e reusa."""
        with patch("app.services.idempotency_store.redis_async.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client

            store = RedisIdempotencyStore(redis_url="redis://test:6379/0")
            client1 = await store._get_client()
            client2 = await store._get_client()

        assert client1 is client2  # cache: mesmo objeto
        mock_from_url.assert_called_once_with(
            "redis://test:6379/0",
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
            decode_responses=True,
        )

    @pytest.mark.asyncio
    async def test_setnx_returns_true_on_insert(self) -> None:
        """setnx retorna True quando chave nao existe (SETNX sucesso)."""
        store = RedisIdempotencyStore(redis_url="redis://test:6379/0")
        fake_client = AsyncMock()
        fake_client.set.return_value = True  # NX + EX sucesso
        with patch.object(store, "_get_client", return_value=fake_client):
            result = await store.setnx("key:abc", {"status": "ok"}, ttl_seconds=3600)

        assert result is True
        fake_client.set.assert_called_once()
        call_kwargs = fake_client.set.call_args.kwargs
        assert call_kwargs["nx"] is True
        assert call_kwargs["ex"] == 3600

    @pytest.mark.asyncio
    async def test_setnx_returns_false_on_conflict(self) -> None:
        """setnx retorna False quando chave ja existe."""
        store = RedisIdempotencyStore(redis_url="redis://test:6379/0")
        fake_client = AsyncMock()
        fake_client.set.return_value = None  # SETNX falhou (None = ja existe)
        with patch.object(store, "_get_client", return_value=fake_client):
            result = await store.setnx("key:abc", {"status": "ok"}, ttl_seconds=3600)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_returns_dict_when_exists(self) -> None:
        """get retorna dict quando chave existe."""
        store = RedisIdempotencyStore(redis_url="redis://test:6379/0")
        fake_client = AsyncMock()
        fake_client.get.return_value = '{"status": "ok", "code": 200}'
        with patch.object(store, "_get_client", return_value=fake_client):
            result = await store.get("key:abc")

        assert result == {"status": "ok", "code": 200}
        fake_client.get.assert_called_once_with("key:abc")

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self) -> None:
        """get retorna None quando chave nao existe."""
        store = RedisIdempotencyStore(redis_url="redis://test:6379/0")
        fake_client = AsyncMock()
        fake_client.get.return_value = None
        with patch.object(store, "_get_client", return_value=fake_client):
            result = await store.get("key:missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_parses_json_correctly(self) -> None:
        """get faz parse do JSON armazenado."""
        store = RedisIdempotencyStore(redis_url="redis://test:6379/0")
        fake_client = AsyncMock()
        fake_client.get.return_value = '{"nested": {"a": 1, "b": [1, 2, 3]}}'
        with patch.object(store, "_get_client", return_value=fake_client):
            result = await store.get("key:nested")
        assert result == {"nested": {"a": 1, "b": [1, 2, 3]}}

    @pytest.mark.asyncio
    async def test_delete_calls_redis_delete(self) -> None:
        """delete delega para redis.delete."""
        store = RedisIdempotencyStore(redis_url="redis://test:6379/0")
        fake_client = AsyncMock()
        with patch.object(store, "_get_client", return_value=fake_client):
            await store.delete("key:abc")
        fake_client.delete.assert_called_once_with("key:abc")

    @pytest.mark.asyncio
    async def test_full_flow_setnx_get_delete(self) -> None:
        """Fluxo completo: setnx -> get -> delete."""
        store = RedisIdempotencyStore(redis_url="redis://test:6379/0")
        fake_client = AsyncMock()

        # Simula redis state
        stored: dict[str, str] = {}

        async def fake_set(key: str, value: str, **kwargs: object) -> bool | None:
            nx = kwargs.get("nx", False)
            if nx and key in stored:
                return None
            stored[key] = value
            return True

        fake_client.set = AsyncMock(side_effect=fake_set)  # type: ignore[method-assign]
        fake_client.get = AsyncMock(side_effect=lambda k: stored.get(k))  # type: ignore[method-assign]
        fake_client.delete = AsyncMock(side_effect=lambda k: stored.pop(k, None))  # type: ignore[method-assign]

        with patch.object(store, "_get_client", return_value=fake_client):
            # 1. setnx
            inserted = await store.setnx("key:flow", {"data": "value1"}, ttl_seconds=300)
            assert inserted is True

            # 2. get exists
            val = await store.get("key:flow")
            assert val == {"data": "value1"}

            # 3. setnx again (should fail)
            reinserted = await store.setnx("key:flow", {"data": "value2"}, ttl_seconds=300)
            assert reinserted is False

            # 4. delete
            await store.delete("key:flow")

            # 5. get after delete
            val_after = await store.get("key:flow")
            assert val_after is None
