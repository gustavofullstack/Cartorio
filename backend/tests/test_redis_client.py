"""Testes para app/core/redis_client.py - get_redis + close_redis (cobertura).

Cobre:
1. get_redis retorna singleton (segunda call = mesma instancia)
2. get_redis lazy init quando _redis_client=None
3. get_redis retorna None se aioredis.Redis.from_url falha (Exception)
4. get_redis retorna None se ImportError
5. get_redis usa REDIS_URL env var com fallback
6. get_redis usa fallback 'redis://localhost:6379/0' se REDIS_URL nao setado
7. close_redis quando _redis_client=None (no-op)
8. close_redis fecha client quando existe
9. close_redis captura exception ao fechar
10. close_redis reseta _redis_client para None
11. close_redis chamado multiplas vezes eh safe

Sobe cobertura redis_client.py 78% -> >=95%.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core import redis_client
from app.core.redis_client import close_redis, get_redis


@pytest.fixture(autouse=True)
def _reset_redis_singleton():
    """Reseta _redis_client antes e depois de cada test."""
    redis_client._redis_client = None
    yield
    redis_client._redis_client = None


# =============================================================================
# get_redis - lazy init + singleton
# =============================================================================


@pytest.mark.asyncio
async def test_get_redis_lazy_init_retorna_cliente() -> None:
    """get_redis cria client Redis quando _redis_client=None."""
    mock_client = MagicMock()

    with patch.dict("os.environ", {}, clear=False):
        with patch("redis.asyncio.Redis.from_url", return_value=mock_client) as mock_from_url:
            with patch("app.core.redis_client.os.getenv", return_value="redis://custom:1234/0"):
                result = await get_redis()

    assert result is mock_client
    assert mock_from_url.called


@pytest.mark.asyncio
async def test_get_redis_singleton_reutiliza_instancia() -> None:
    """get_redis retorna mesma instancia em chamadas subsequentes."""
    mock_client = MagicMock()
    redis_client._redis_client = mock_client  # Pre-popula

    result = await get_redis()

    assert result is mock_client
    assert result is redis_client._redis_client


@pytest.mark.asyncio
async def test_get_redis_nao_chama_from_url_se_singleton_existe() -> None:
    """get_redis nao chama from_url se singleton ja existe."""
    mock_client = MagicMock()
    redis_client._redis_client = mock_client

    with patch("redis.asyncio.Redis.from_url") as mock_from_url:
        await get_redis()

    # from_url NAO deve ser chamado
    assert not mock_from_url.called


# =============================================================================
# get_redis - error handling
# =============================================================================


@pytest.mark.asyncio
async def test_get_redis_retorna_none_se_from_url_falha() -> None:
    """get_redis retorna None se from_url levanta Exception generica."""
    with patch("redis.asyncio.Redis.from_url", side_effect=Exception("connection refused")):
        result = await get_redis()

    assert result is None
    assert redis_client._redis_client is None


@pytest.mark.asyncio
async def test_get_redis_retorna_none_se_import_error() -> None:
    """get_redis retorna None se redis[asyncio] nao instalado."""
    # Forca ImportError no import do redis.asyncio
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "redis.asyncio":
            raise ImportError("No module named 'redis.asyncio'")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        result = await get_redis()

    assert result is None


# =============================================================================
# get_redis - env var
# =============================================================================


@pytest.mark.asyncio
async def test_get_redis_usa_redis_url_env_var() -> None:
    """get_redis usa REDIS_URL env var quando setado."""
    mock_client = MagicMock()
    captured_kwargs = {}

    def fake_from_url(url, **kwargs):
        captured_kwargs["url"] = url
        captured_kwargs["kwargs"] = kwargs
        return mock_client

    with patch.dict("os.environ", {"REDIS_URL": "redis://prod-server:6379/5"}, clear=False):
        with patch("redis.asyncio.Redis.from_url", side_effect=fake_from_url):
            result = await get_redis()

    assert result is mock_client
    assert "prod-server" in captured_kwargs["url"]
    assert captured_kwargs["kwargs"]["socket_connect_timeout"] == 2
    assert captured_kwargs["kwargs"]["decode_responses"] is True


@pytest.mark.asyncio
async def test_get_redis_usa_fallback_localhost_quando_redis_url_nao_setado() -> None:
    """get_redis usa redis://localhost:6379/0 como fallback."""
    mock_client = MagicMock()
    captured_kwargs = {}

    def fake_from_url(url, **kwargs):
        captured_kwargs["url"] = url
        return mock_client

    # Remove REDIS_URL do env
    env = {k: v for k, v in __import__("os").environ.items() if k != "REDIS_URL"}
    with patch.dict("os.environ", env, clear=True):
        with patch("redis.asyncio.Redis.from_url", side_effect=fake_from_url):
            result = await get_redis()

    assert result is mock_client
    assert captured_kwargs["url"] == "redis://localhost:6379/0"


# =============================================================================
# close_redis
# =============================================================================


@pytest.mark.asyncio
async def test_close_redis_no_op_quando_client_none() -> None:
    """close_redis nao faz nada se _redis_client=None."""
    redis_client._redis_client = None

    # Nao deve raise
    await close_redis()

    assert redis_client._redis_client is None


@pytest.mark.asyncio
async def test_close_redis_fecha_client_quando_existe() -> None:
    """close_redis chama aclose() no client."""
    mock_client = MagicMock()
    mock_client.aclose = MagicMock()  # Async? sync?

    # aclose e coroutine (async)
    import asyncio
    mock_client.aclose = lambda: asyncio.sleep(0)  # Coroutine

    redis_client._redis_client = mock_client

    await close_redis()

    assert redis_client._redis_client is None


@pytest.mark.asyncio
async def test_close_redis_reseta_client_para_none() -> None:
    """close_redis sempre reseta _redis_client=None no final."""
    import asyncio
    mock_client = MagicMock()
    mock_client.aclose = lambda: asyncio.sleep(0)
    redis_client._redis_client = mock_client

    await close_redis()

    assert redis_client._redis_client is None


@pytest.mark.asyncio
async def test_close_redis_captura_exception_ao_fechar() -> None:
    """close_redis captura exception do aclose() e ainda reseta _redis_client."""
    mock_client = MagicMock()
    mock_client.aclose = MagicMock(side_effect=Exception("close failed"))
    redis_client._redis_client = mock_client

    # Nao deve raise
    await close_redis()

    # _redis_client deve ser resetado mesmo com exception
    assert redis_client._redis_client is None


@pytest.mark.asyncio
async def test_close_redis_multiplas_vezes_eh_safe() -> None:
    """close_redis chamado multiplas vezes nao quebra."""
    import asyncio
    mock_client = MagicMock()
    mock_client.aclose = lambda: asyncio.sleep(0)
    redis_client._redis_client = mock_client

    await close_redis()
    await close_redis()  # Segunda chamada eh no-op (ja eh None)
    await close_redis()

    assert redis_client._redis_client is None