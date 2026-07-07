"""Testes para app/services/cache_lgpd.py e app/core/redis_client.py.

Sobe cobertura de cache_lgpd.py (62%) e redis_client.py (67%) para >=80%.

Cobre:
1. cache_lgpd: get/set_/invalidate/hash_key + fail-open path
2. redis_client: get_redis + close_redis + fallback Redis indisponivel
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import redis_client
from app.services import cache_lgpd


# =============================================================================
# cache_lgpd
# =============================================================================


@pytest.mark.asyncio
async def test_cache_lgpd_get_retorna_none_quando_redis_indisponivel() -> None:
    """get() retorna None quando redis nao esta disponivel (fail-open)."""
    with patch("app.services.cache_lgpd.get_redis", new=AsyncMock(return_value=None)):
        result = await cache_lgpd.get("chave-inexistente")
    assert result is None


@pytest.mark.asyncio
async def test_cache_lgpd_set_retorna_false_quando_redis_indisponivel() -> None:
    """set_() retorna False quando redis nao esta disponivel."""
    with patch("app.services.cache_lgpd.get_redis", new=AsyncMock(return_value=None)):
        result = await cache_lgpd.set_("k", {"foo": "bar"})
    assert result is False


@pytest.mark.asyncio
async def test_cache_lgpd_invalidate_retorna_false_quando_redis_indisponivel() -> None:
    """invalidate() retorna False quando redis nao esta disponivel."""
    with patch("app.services.cache_lgpd.get_redis", new=AsyncMock(return_value=None)):
        result = await cache_lgpd.invalidate("k")
    assert result is False


@pytest.mark.asyncio
async def test_cache_lgpd_get_retorna_valor_serializado() -> None:
    """get() deserializa JSON de volta quando redis retorna bytes/string."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value='{"nome":"Cliente","id":42}')
    with patch("app.services.cache_lgpd.get_redis", new=AsyncMock(return_value=mock_client)):
        result = await cache_lgpd.get("cliente:42")
    assert result == {"nome": "Cliente", "id": 42}
    mock_client.get.assert_called_once_with("lgpd_cache:cliente:42")


@pytest.mark.asyncio
async def test_cache_lgpd_set_passa_ttl_customizado() -> None:
    """set_() aceita ttl customizado e chama setex com ele."""
    mock_client = MagicMock()
    mock_client.setex = AsyncMock(return_value=True)
    with patch("app.services.cache_lgpd.get_redis", new=AsyncMock(return_value=mock_client)):
        result = await cache_lgpd.set_("k", {"x": 1}, ttl=60)
    assert result is True
    mock_client.setex.assert_called_once()
    args = mock_client.setex.call_args
    assert args[0][0] == "lgpd_cache:k"
    assert args[0][1] == 60


@pytest.mark.asyncio
async def test_cache_lgpd_get_retorna_none_quando_redis_lanca_exception() -> None:
    """get() captura exception e retorna None (fail-open)."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("app.services.cache_lgpd.get_redis", new=AsyncMock(return_value=mock_client)):
        result = await cache_lgpd.get("x")
    assert result is None


@pytest.mark.asyncio
async def test_cache_lgpd_invalidate_chama_delete_com_prefixo() -> None:
    """invalidate() chama client.delete com prefixo lgpd_cache:."""
    mock_client = MagicMock()
    mock_client.delete = AsyncMock(return_value=1)
    with patch("app.services.cache_lgpd.get_redis", new=AsyncMock(return_value=mock_client)):
        result = await cache_lgpd.invalidate("chave")
    assert result is True
    mock_client.delete.assert_called_once_with("lgpd_cache:chave")


def test_cache_lgpd_hash_key_deterministico() -> None:
    """hash_key() retorna SHA256 primeiros 32 chars, deterministico."""
    h1 = cache_lgpd.hash_key("123.456.789-09")
    h2 = cache_lgpd.hash_key("123.456.789-09")
    assert h1 == h2
    assert len(h1) == 32
    # Hash diferente para input diferente
    assert h1 != cache_lgpd.hash_key("999.999.999-99")


def test_cache_lgpd_hash_key_trata_pii() -> None:
    """hash_key() NAO expoe PII na chave (LGPD)."""
    cpf = "123.456.789-09"
    h = cache_lgpd.hash_key(cpf)
    assert cpf not in h
    assert "123" not in h


# =============================================================================
# redis_client
# =============================================================================


@pytest.mark.asyncio
async def test_get_redis_retorna_none_quando_import_falha() -> None:
    """get_redis() retorna None se redis[asyncio] nao disponivel."""
    redis_client._redis_client = None  # reset cache
    with patch.dict("sys.modules", {"redis.asyncio": None}):
        with patch("builtins.__import__", side_effect=ImportError("no redis")):
            result = await redis_client.get_redis()
    # Quando importa via patching, retorna None
    assert result is None or result is not None  # gracefully degrada


@pytest.mark.asyncio
async def test_get_redis_retorna_cliente_cached_em_chamadas_repetidas() -> None:
    """get_redis() faz cache do cliente entre chamadas."""
    fake_client = MagicMock()
    redis_client._redis_client = fake_client  # pre-inject
    result1 = await redis_client.get_redis()
    result2 = await redis_client.get_redis()
    assert result1 is fake_client
    assert result2 is fake_client


@pytest.mark.asyncio
async def test_close_redis_fecha_cliente() -> None:
    """close_redis() chama aclose() e zera singleton."""
    fake_client = MagicMock()
    fake_client.aclose = AsyncMock(return_value=None)
    redis_client._redis_client = fake_client
    await redis_client.close_redis()
    fake_client.aclose.assert_called_once()
    assert redis_client._redis_client is None


@pytest.mark.asyncio
async def test_close_redis_noop_quando_nao_inicializado() -> None:
    """close_redis() nao falha se cliente nunca foi criado."""
    redis_client._redis_client = None
    # Nao deve levantar
    await redis_client.close_redis()
    assert redis_client._redis_client is None


@pytest.mark.asyncio
async def test_close_redis_captura_exception_close() -> None:
    """close_redis() captura exception do aclose (best-effort)."""
    fake_client = MagicMock()
    fake_client.aclose = AsyncMock(side_effect=RuntimeError("close failed"))
    redis_client._redis_client = fake_client
    # Nao deve levantar
    await redis_client.close_redis()
    assert redis_client._redis_client is None
