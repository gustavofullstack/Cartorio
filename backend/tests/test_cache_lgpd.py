"""Testes para cache LGPD-compliant (Redis TTL 24h)."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.cache_lgpd import hash_key, CACHE_TTL_SECONDS


def test_cache_ttl_24h():
    assert CACHE_TTL_SECONDS == 86400


def test_hash_key_deterministic():
    assert hash_key("user:123") == hash_key("user:123")
    assert hash_key("user:123") != hash_key("user:456")


def test_hash_key_length_32():
    h = hash_key("anything")
    assert len(h) == 32


@pytest.mark.asyncio
async def test_get_cache_miss():
    with patch("app.services.cache_lgpd.get_redis") as mock_redis:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_redis.return_value = mock_client

        from app.services.cache_lgpd import get

        result = await get("missing_key")
        assert result is None


@pytest.mark.asyncio
async def test_get_redis_down_returns_none():
    with patch("app.services.cache_lgpd.get_redis", return_value=None):
        from app.services.cache_lgpd import get

        result = await get("any_key")
        assert result is None


@pytest.mark.asyncio
async def test_set_cache_success():
    with patch("app.services.cache_lgpd.get_redis") as mock_redis:
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()
        mock_redis.return_value = mock_client

        from app.services.cache_lgpd import set_

        result = await set_("test_key", {"foo": "bar"}, ttl=60)
        assert result is True
        mock_client.setex.assert_called_once()
