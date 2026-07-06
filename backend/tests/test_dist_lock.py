"""Testes para distributed lock (SQUAD A20 Redlock)."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.dist_lock import lock, try_lock


@pytest.mark.asyncio
async def test_lock_acquired():
    """Lock adquirido retorna True."""
    with patch("app.services.dist_lock.get_redis") as mock_redis:
        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)
        mock_client.eval = AsyncMock(return_value=1)
        mock_redis.return_value = mock_client

        async with lock("test_key") as acquired:
            assert acquired is True


@pytest.mark.asyncio
async def test_lock_released_after_context():
    """Lock é liberado ao sair do context manager."""
    with patch("app.services.dist_lock.get_redis") as mock_redis:
        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)
        mock_client.eval = AsyncMock(return_value=1)
        mock_redis.return_value = mock_client

        async with lock("test_key"):
            pass

        # eval deve ter sido chamado para release
        assert mock_client.eval.called


@pytest.mark.asyncio
async def test_lock_redis_down_returns_false():
    """Se Redis down, lock retorna False (fail-open)."""
    with patch("app.services.dist_lock.get_redis", return_value=None):
        async with lock("test_key") as acquired:
            assert acquired is False


@pytest.mark.asyncio
async def test_try_lock_success():
    """try_lock retorna (True, token) quando acquired."""
    with patch("app.services.dist_lock.get_redis") as mock_redis:
        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)
        mock_redis.return_value = mock_client

        acquired, token = await try_lock("test_key")
        assert acquired is True
        assert token is not None
        assert len(token) > 16  # secrets.token_urlsafe(16)


@pytest.mark.asyncio
async def test_try_lock_busy():
    """try_lock retorna (False, None) quando lock já taken."""
    with patch("app.services.dist_lock.get_redis") as mock_redis:
        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=False)  # NX fails
        mock_redis.return_value = mock_client

        acquired, token = await try_lock("test_key")
        assert acquired is False
        assert token is None
