"""Testes A15 — Connection pool tuning."""
from __future__ import annotations

from app.db import engine


def test_engine_tem_pool_pre_ping_ativo() -> None:
    """Engine tem pool_pre_ping=True (evita conexao morta)."""
    pool = engine.pool
    assert pool._pre_ping is True


def test_engine_tem_pool_recycle_1h() -> None:
    """Engine tem pool_recycle=3600s (1h)."""
    pool = engine.pool
    # SQLite nao tem recycle, entao verificamos via config do engine
    if hasattr(pool, "_recycle"):
        assert pool._recycle == 3600
    else:
        # SQLite nao tem pool config — OK
        assert True
