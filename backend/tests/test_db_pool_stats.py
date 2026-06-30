"""Testes de get_pool_stats() - A22.

Cobertura:
- SQLite retorna stats zerados com nota
- Postgres retorna pool_size, max_overflow, checked_out, overflow, total_capacity
- utilization_pct eh float entre 0 e 100
- capacidade maxima = pool_size + max_overflow
"""

from __future__ import annotations

from unittest.mock import patch


from app.db import get_pool_stats


class FakePool:
    """Pool fake para testes."""

    def __init__(self, size: int, max_overflow: int, checkedout: int, overflow: int) -> None:
        self._size = size
        self._max_overflow = max_overflow
        self._checkedout = checkedout
        self._overflow = overflow

    def size(self) -> int:
        return self._size

    def checkedout(self) -> int:
        return self._checkedout

    def overflow(self) -> int:
        return self._overflow


class TestGetPoolStats:
    """TDD strict - A22 connection pool observability."""

    def test_sqlite_returns_zeroed_stats(self):
        """SQLite retorna stats zerados com nota."""
        with patch("app.db._is_sqlite", True):
            stats = get_pool_stats()

        assert stats["backend"] == "sqlite"
        assert stats["pool_size"] == 0
        assert stats["max_overflow"] == 0
        assert stats["checked_out"] == 0
        assert stats["overflow"] == 0
        assert stats["total_capacity"] == 0
        assert stats["utilization_pct"] == 0.0
        assert "note" in stats
        assert "SQLite" in stats["note"]

    def test_postgres_returns_full_stats(self):
        """Postgres retorna todas as chaves com valores reais."""
        fake_pool = FakePool(size=20, max_overflow=10, checkedout=5, overflow=0)

        with (
            patch("app.db._is_sqlite", False),
            patch("app.db.engine") as fake_engine,
        ):
            fake_engine.pool = fake_pool
            stats = get_pool_stats()

        assert stats["backend"] == "postgresql"
        assert stats["pool_size"] == 20
        assert stats["max_overflow"] == 10
        assert stats["checked_out"] == 5
        assert stats["overflow"] == 0
        assert stats["total_capacity"] == 30
        assert stats["utilization_pct"] == round((5 / 30) * 100, 2)

    def test_utilization_with_overflow(self):
        """Quando em pico, overflow > 0 e utilization_pct considera overflow."""
        # pool_size=20, mas checkedout=25 (5 em overflow)
        fake_pool = FakePool(size=20, max_overflow=10, checkedout=25, overflow=5)

        with (
            patch("app.db._is_sqlite", False),
            patch("app.db.engine") as fake_engine,
        ):
            fake_engine.pool = fake_pool
            stats = get_pool_stats()

        assert stats["checked_out"] == 25
        assert stats["overflow"] == 5
        assert stats["utilization_pct"] == round((25 / 30) * 100, 2)

    def test_utilization_100_percent(self):
        """100% utilization quando checked_out == total_capacity."""
        fake_pool = FakePool(size=20, max_overflow=10, checkedout=30, overflow=10)

        with (
            patch("app.db._is_sqlite", False),
            patch("app.db.engine") as fake_engine,
        ):
            fake_engine.pool = fake_pool
            stats = get_pool_stats()

        assert stats["utilization_pct"] == 100.0

    def test_utilization_zero_when_idle(self):
        """0% utilization quando nenhuma conexao em uso."""
        fake_pool = FakePool(size=20, max_overflow=10, checkedout=0, overflow=0)

        with (
            patch("app.db._is_sqlite", False),
            patch("app.db.engine") as fake_engine,
        ):
            fake_engine.pool = fake_pool
            stats = get_pool_stats()

        assert stats["utilization_pct"] == 0.0

    def test_utilization_is_float(self):
        """utilization_pct eh float (nao int)."""
        fake_pool = FakePool(size=20, max_overflow=10, checkedout=7, overflow=0)

        with (
            patch("app.db._is_sqlite", False),
            patch("app.db.engine") as fake_engine,
        ):
            fake_engine.pool = fake_pool
            stats = get_pool_stats()

        assert isinstance(stats["utilization_pct"], float)
