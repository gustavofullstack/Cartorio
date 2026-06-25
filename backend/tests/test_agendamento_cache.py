"""Testes A26 — agendamento_cache: Redis cache layer para agendamentos.

Cobertura:
- _get_redis_client com/sem Redis, erro de import
- get/set agendamentos pendentes (hit, miss, erro, sem Redis)
- get/set agendamentos próximos (hit, miss, erro, sem Redis)
- get/set cliente cache (hit, miss, erro, sem Redis)
- invalidate_agendamento_cache (com e sem chaves)
- invalidate_cliente_cache (existe e não existe)
- Constantes do módulo
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.agendamento_cache import (
    CACHE_KEY_PREFIX,
    CACHE_TTL_SECONDS,
    CACHE_VERSION,
    _cache_key_cliente,
    _cache_key_pendentes,
    _cache_key_proximos,
    _get_redis_client,
    get_agendamentos_pendentes_cached,
    get_agendamentos_proximos_cached,
    get_cliente_cached,
    invalidate_agendamento_cache,
    invalidate_cliente_cache,
    set_agendamentos_pendentes_cached,
    set_agendamentos_proximos_cached,
    set_cliente_cached,
)


# ─── Constantes ────────────────────────────────────────────────────────

def test_constants():
    """Constantes do módulo têm valores esperados."""
    assert CACHE_TTL_SECONDS == 60
    assert CACHE_VERSION == "v1"
    assert CACHE_KEY_PREFIX == "agendamento:v1"


def test_cache_key_pendentes():
    """Chave de cache para pendentes segue padrão."""
    assert _cache_key_pendentes() == "agendamento:v1:pendentes"


def test_cache_key_proximos():
    """Chave de cache para próximos segue padrão."""
    assert _cache_key_proximos() == "agendamento:v1:proximos"


def test_cache_key_cliente_inclui_hash():
    """Chave de cache para cliente inclui hash do ID."""
    key = _cache_key_cliente(42)
    assert key.startswith("agendamento:v1:cliente:")
    assert "42" not in key  # ID é hasheado, não em texto plano (LGPD)


# ─── _get_redis_client ─────────────────────────────────────────────────

def test_get_redis_client_sucesso():
    """_get_redis_client retorna cliente Redis quando disponível."""
    import builtins
    import app.services.agendamento_cache as cache_mod

    mock_redis = MagicMock()
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "redis":
            mock_mod = MagicMock()
            mock_mod.Redis.from_url.return_value = mock_redis
            return mock_mod
        return original_import(name, *args, **kwargs)

    with (
        patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}),
        patch("builtins.__import__", side_effect=mock_import),
    ):
        client = cache_mod._get_redis_client()
        assert client is mock_redis


def test_get_redis_client_import_error():
    """_get_redis_client retorna None se redis não instalado."""
    import app.services.agendamento_cache as cache_mod
    with patch("builtins.__import__", side_effect=ImportError("no redis")):
        client = cache_mod._get_redis_client()
        assert client is None


def test_get_redis_client_sem_env():
    """_get_redis_client usa fallback localhost sem REDIS_URL."""
    mock_redis = MagicMock()
    import builtins
    import app.services.agendamento_cache as cache_mod
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "redis":
            mock_mod = MagicMock()
            mock_mod.Redis.from_url.return_value = mock_redis
            return mock_mod
        return original_import(name, *args, **kwargs)

    with (
        patch("builtins.__import__", side_effect=mock_import),
        patch.dict("os.environ", {}, clear=True),
    ):
        client = cache_mod._get_redis_client()
        assert client is mock_redis


# ─── get/set pendentes ─────────────────────────────────────────────────

def test_get_pendentes_hit():
    """get_agendamentos_pendentes_cached retorna dados no hit."""
    mock_redis = MagicMock()
    data = [{"id": 1, "status": "pendente"}]
    mock_redis.get.return_value = json.dumps(data)

    with (
        patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis),
        patch("app.services.agendamento_metrics.metrics_store") as mock_metrics,
    ):
        result = get_agendamentos_pendentes_cached()

    assert result == data
    mock_redis.get.assert_called_once_with("agendamento:v1:pendentes")
    assert mock_metrics.inc_counter.called


def test_get_pendentes_miss():
    """get_agendamentos_pendentes_cached retorna None no miss."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with (
        patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis),
        patch("app.services.agendamento_metrics.metrics_store") as mock_metrics,
    ):
        result = get_agendamentos_pendentes_cached()

    assert result is None


def test_get_pendentes_sem_redis():
    """get_agendamentos_pendentes_cached retorna None sem Redis."""
    with (
        patch("app.services.agendamento_cache._get_redis_client", return_value=None),
        patch("app.services.agendamento_metrics.metrics_store") as mock_metrics,
    ):
        result = get_agendamentos_pendentes_cached()

    assert result is None
    mock_metrics.inc_counter.assert_called_once()


def test_get_pendentes_erro():
    """get_agendamentos_pendentes_cached retorna None em erro."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = ConnectionError("redis down")

    with (
        patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis),
        patch("app.services.agendamento_metrics.metrics_store") as mock_metrics,
    ):
        result = get_agendamentos_pendentes_cached()

    assert result is None


def test_set_pendentes_sucesso():
    """set_agendamentos_pendentes_cached salva com TTL."""
    mock_redis = MagicMock()

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        result = set_agendamentos_pendentes_cached([{"id": 1}])

    assert result is True
    mock_redis.set.assert_called_once()
    assert mock_redis.set.call_args[1]["ex"] == CACHE_TTL_SECONDS


def test_set_pendentes_sem_redis():
    """set_agendamentos_pendentes_cached retorna False sem Redis."""
    with patch("app.services.agendamento_cache._get_redis_client", return_value=None):
        result = set_agendamentos_pendentes_cached([{"id": 1}])

    assert result is False


def test_set_pendentes_erro():
    """set_agendamentos_pendentes_cached retorna False em erro."""
    mock_redis = MagicMock()
    mock_redis.set.side_effect = ConnectionError("redis down")

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        result = set_agendamentos_pendentes_cached([{"id": 1}])

    assert result is False


# ─── get/set próximos ─────────────────────────────────────────────────

def test_get_proximos_hit():
    """get_agendamentos_proximos_cached retorna dados no hit."""
    mock_redis = MagicMock()
    data = [{"id": 2, "status": "confirmado"}]
    mock_redis.get.return_value = json.dumps(data)

    with (
        patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis),
        patch("app.services.agendamento_metrics.metrics_store"),
    ):
        result = get_agendamentos_proximos_cached()

    assert result == data


def test_get_proximos_miss():
    """get_agendamentos_proximos_cached retorna None no miss."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with (
        patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis),
        patch("app.services.agendamento_metrics.metrics_store"),
    ):
        result = get_agendamentos_proximos_cached()

    assert result is None


def test_get_proximos_sem_redis():
    """get_agendamentos_proximos_cached retorna None sem Redis."""
    with patch("app.services.agendamento_cache._get_redis_client", return_value=None):
        result = get_agendamentos_proximos_cached()

    assert result is None


def test_get_proximos_erro():
    """get_agendamentos_proximos_cached retorna None em erro Redis."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = ConnectionError("redis down")

    with (
        patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis),
        patch("app.services.agendamento_metrics.metrics_store"),
    ):
        result = get_agendamentos_proximos_cached()

    assert result is None


def test_set_proximos_sucesso():
    """set_agendamentos_proximos_cached salva com TTL."""
    mock_redis = MagicMock()

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        result = set_agendamentos_proximos_cached([{"id": 2}])

    assert result is True
    mock_redis.set.assert_called_once()


def test_set_proximos_sem_redis():
    """set_agendamentos_proximos_cached retorna False sem Redis."""
    with patch("app.services.agendamento_cache._get_redis_client", return_value=None):
        result = set_agendamentos_proximos_cached([{"id": 2}])

    assert result is False


def test_set_proximos_erro():
    """set_agendamentos_proximos_cached retorna False em erro Redis."""
    mock_redis = MagicMock()
    mock_redis.set.side_effect = ConnectionError("redis down")

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        result = set_agendamentos_proximos_cached([{"id": 2}])

    assert result is False


# ─── get/set cliente ───────────────────────────────────────────────────

def test_get_cliente_hit():
    """get_cliente_cached retorna dados no hit."""
    mock_redis = MagicMock()
    data = {"id": 42, "nome": "João"}
    mock_redis.get.return_value = json.dumps(data)

    with (
        patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis),
        patch("app.services.agendamento_metrics.metrics_store"),
    ):
        result = get_cliente_cached(42)

    assert result == data


def test_get_cliente_miss():
    """get_cliente_cached retorna None no miss."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with (
        patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis),
        patch("app.services.agendamento_metrics.metrics_store"),
    ):
        result = get_cliente_cached(42)

    assert result is None


def test_get_cliente_sem_redis():
    """get_cliente_cached retorna None sem Redis."""
    with patch("app.services.agendamento_cache._get_redis_client", return_value=None):
        result = get_cliente_cached(42)

    assert result is None


def test_get_cliente_erro():
    """get_cliente_cached retorna None em erro Redis."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = ConnectionError("redis down")

    with (
        patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis),
        patch("app.services.agendamento_metrics.metrics_store"),
    ):
        result = get_cliente_cached(42)

    assert result is None


def test_set_cliente_sucesso():
    """set_cliente_cached salva com TTL 5x maior."""
    mock_redis = MagicMock()

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        result = set_cliente_cached(42, {"id": 42, "nome": "João"})

    assert result is True
    mock_redis.set.assert_called_once()
    assert mock_redis.set.call_args[1]["ex"] == CACHE_TTL_SECONDS * 5


def test_set_cliente_sem_redis():
    """set_cliente_cached retorna False sem Redis."""
    with patch("app.services.agendamento_cache._get_redis_client", return_value=None):
        result = set_cliente_cached(42, {"id": 42})

    assert result is False


def test_set_cliente_erro():
    """set_cliente_cached retorna False em erro Redis."""
    mock_redis = MagicMock()
    mock_redis.set.side_effect = ConnectionError("redis down")

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        result = set_cliente_cached(42, {"id": 42})

    assert result is False


# ─── invalidate ────────────────────────────────────────────────────────

def test_invalidate_agendamento_cache_com_chaves():
    """invalidate_agendamento_cache remove chaves e retorna contagem."""
    mock_redis = MagicMock()
    mock_redis.scan_iter.return_value = ["key1", "key2", "key3"]

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        count = invalidate_agendamento_cache()

    assert count == 3
    mock_redis.delete.assert_called_once_with("key1", "key2", "key3")


def test_invalidate_agendamento_cache_sem_chaves():
    """invalidate_agendamento_cache retorna 0 se não há chaves."""
    mock_redis = MagicMock()
    mock_redis.scan_iter.return_value = []

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        count = invalidate_agendamento_cache()

    assert count == 0
    mock_redis.delete.assert_not_called()


def test_invalidate_agendamento_cache_sem_redis():
    """invalidate_agendamento_cache retorna 0 sem Redis."""
    with patch("app.services.agendamento_cache._get_redis_client", return_value=None):
        count = invalidate_agendamento_cache()

    assert count == 0


def test_invalidate_cliente_cache_existe():
    """invalidate_cliente_cache deleta chave se existe."""
    mock_redis = MagicMock()
    mock_redis.exists.return_value = 1

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        count = invalidate_cliente_cache(42)

    assert count == 1
    mock_redis.delete.assert_called_once()


def test_invalidate_cliente_cache_nao_existe():
    """invalidate_cliente_cache retorna 0 se chave não existe."""
    mock_redis = MagicMock()
    mock_redis.exists.return_value = 0

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        count = invalidate_cliente_cache(42)

    assert count == 0
    mock_redis.delete.assert_not_called()


def test_invalidate_cliente_cache_sem_redis():
    """invalidate_cliente_cache retorna 0 sem Redis."""
    with patch("app.services.agendamento_cache._get_redis_client", return_value=None):
        count = invalidate_cliente_cache(42)

    assert count == 0


def test_invalidate_cliente_cache_erro():
    """invalidate_cliente_cache retorna 0 em erro Redis."""
    mock_redis = MagicMock()
    mock_redis.exists.side_effect = ConnectionError("redis down")

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        count = invalidate_cliente_cache(42)

    assert count == 0


def test_invalidate_agendamento_cache_erro():
    """invalidate_agendamento_cache retorna 0 em erro Redis."""
    mock_redis = MagicMock()
    mock_redis.scan_iter.side_effect = ConnectionError("redis down")

    with patch("app.services.agendamento_cache._get_redis_client", return_value=mock_redis):
        count = invalidate_agendamento_cache()

    assert count == 0
