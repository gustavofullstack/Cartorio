"""Testes A21 — Cache Redis 24h emolumento + invalidation."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.emolumento_cache import (
    CACHE_TTL_SECONDS,
    get_cached,
    invalidate,
    set_cached,
)


def test_cache_ttl_24h() -> None:
    """TTL canonico = 86400s (24h)."""
    assert CACHE_TTL_SECONDS == 86400


def test_get_cached_hit() -> None:
    """get_cached retorna dict se hit."""
    with patch("app.services.emolumento_cache._get_redis_client") as mock_get:
        r = MagicMock()
        r.get.return_value = '{"valor_base": 100.0, "valor_total": 108.0}'
        mock_get.return_value = r
        result = get_cached("escritura", 100000.0)
    assert result == {"valor_base": 100.0, "valor_total": 108.0}


def test_get_cached_miss_retorna_none() -> None:
    """get_cached retorna None se chave nao existe."""
    with patch("app.services.emolumento_cache._get_redis_client") as mock_get:
        r = MagicMock()
        r.get.return_value = None
        mock_get.return_value = r
        result = get_cached("certidao", 50.0)
    assert result is None


def test_get_cached_redis_offline_retorna_none() -> None:
    """get_cached retorna None se Redis indisponivel (fail-open)."""
    with patch("app.services.emolumento_cache._get_redis_client") as mock_get:
        mock_get.return_value = None
        assert get_cached("escritura", 100000.0) is None


def test_set_cached_sucesso() -> None:
    """set_cached retorna True se salvou."""
    with patch("app.services.emolumento_cache._get_redis_client") as mock_get:
        r = MagicMock()
        r.setex.return_value = True
        mock_get.return_value = r
        result = set_cached("escritura", 100000.0, {"valor_total": 108.0})
    assert result is True
    r.setex.assert_called_once()
    args = r.setex.call_args
    assert args[0][1] == 86400  # TTL


def test_invalidate_tudo() -> None:
    """invalidate(None) remove todas as chaves emolumento:*."""
    with patch("app.services.emolumento_cache._get_redis_client") as mock_get:
        r = MagicMock()
        r.scan_iter.return_value = [b"emolumento:a:1", b"emolumento:b:2"]
        mock_get.return_value = r
        result = invalidate(None)
    assert result == 2
    r.delete.assert_called_once()


def test_invalidate_por_tipo() -> None:
    """invalidate(tipo) remove apenas chaves daquele tipo."""
    with patch("app.services.emolumento_cache._get_redis_client") as mock_get:
        r = MagicMock()
        r.scan_iter.return_value = [b"emolumento:escritura:1", b"emolumento:escritura:2"]
        mock_get.return_value = r
        result = invalidate("escritura")
    assert result == 2
