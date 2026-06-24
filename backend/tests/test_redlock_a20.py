"""Testes A20 — Redlock distributed lock (Redis SET NX EX)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.redlock import acquire_lock, is_locked, release_lock


def _make_redis_mock(set_returns: bool) -> MagicMock:
    r = MagicMock()
    r.set.return_value = set_returns
    r.eval.return_value = 1 if set_returns else 0
    r.exists.return_value = set_returns
    return r


def test_acquire_lock_retorna_token_quando_sucesso() -> None:
    """SET NX True = lock acquired, retorna token."""
    with patch("app.services.redlock._get_redis_client") as mock_get:
        mock_get.return_value = _make_redis_mock(set_returns=True)
        token = acquire_lock("test:lock1", ttl_seconds=30)
    assert token is not None
    assert len(token) == 32  # UUID4 hex


def test_acquire_lock_retorna_none_quando_ocupado() -> None:
    """SET NX False = ja locked por outro, retorna None."""
    with patch("app.services.redlock._get_redis_client") as mock_get:
        mock_get.return_value = _make_redis_mock(set_returns=False)
        token = acquire_lock("test:lock2", ttl_seconds=30)
    assert token is None


def test_acquire_lock_redis_indisponivel_fail_open() -> None:
    """Sem Redis = fail-open (retorna None, nao bloqueia)."""
    with patch("app.services.redlock._get_redis_client") as mock_get:
        mock_get.return_value = None
        token = acquire_lock("test:lock3", ttl_seconds=30)
    assert token is None  # fail-open


def test_release_lock_retorna_true_quando_token_confere() -> None:
    """release_lock retorna True se Lua script deleta."""
    with patch("app.services.redlock._get_redis_client") as mock_get:
        mock_get.return_value = _make_redis_mock(set_returns=True)
        result = release_lock("test:lock4", token="abc123")
    assert result is True


def test_release_lock_retorna_false_quando_token_nao_confere() -> None:
    """release_lock retorna False se token nao confere (race condition evitada)."""
    with patch("app.services.redlock._get_redis_client") as mock_get:
        mock_get.return_value = _make_redis_mock(set_returns=False)
        result = release_lock("test:lock5", token="wrong")
    assert result is False


def test_is_locked_true_quando_existe() -> None:
    """is_locked retorna True se chave existe no Redis."""
    with patch("app.services.redlock._get_redis_client") as mock_get:
        mock_get.return_value = _make_redis_mock(set_returns=True)
        assert is_locked("test:lock6") is True


def test_is_locked_false_quando_redis_indisponivel() -> None:
    """is_locked retorna False se Redis offline (fail-open)."""
    with patch("app.services.redlock._get_redis_client") as mock_get:
        mock_get.return_value = None
        assert is_locked("test:lock7") is False
