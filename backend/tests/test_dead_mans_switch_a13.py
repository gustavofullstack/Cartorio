"""Testes A13 — Dead man's switch audit log."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.services.dead_mans_switch import (
    check_audit_log_alive,
    last_audit_timestamp,
)


def _make_db_with_last(last_ts: datetime | None) -> MagicMock:
    db = MagicMock()
    db.execute.return_value.scalar.return_value = last_ts
    return db


def test_audit_vazio_retorna_cold_start() -> None:
    """Tabela audit vazia = cold_start."""
    db = _make_db_with_last(None)
    result = check_audit_log_alive(db)
    assert result["alive"] is False
    assert result["cold_start"] is True
    assert result["last_seen"] is None
    assert result["seconds_since_last"] is None


def test_audit_recente_retorna_alive() -> None:
    """Audit log < 1h = alive."""
    now = datetime.now(tz=timezone.utc)
    db = _make_db_with_last(now - timedelta(minutes=30))
    result = check_audit_log_alive(db)
    assert result["alive"] is True
    assert result["cold_start"] is False
    assert 1790 <= result["seconds_since_last"] <= 1810  # ~30min


def test_audit_velho_1h_retorna_dead() -> None:
    """Audit log > 1h = dead (alive=False)."""
    now = datetime.now(tz=timezone.utc)
    db = _make_db_with_last(now - timedelta(hours=2))
    result = check_audit_log_alive(db)
    assert result["alive"] is False
    assert result["seconds_since_last"] is not None
    assert result["seconds_since_last"] >= 7200  # >= 2h


def test_audit_naive_datetime_normalizado_para_utc() -> None:
    """Datetime naive (sem tzinfo) eh tratado como UTC."""
    now = datetime.now(tz=timezone.utc)
    naive_ts = (now - timedelta(minutes=15)).replace(tzinfo=None)
    db = _make_db_with_last(naive_ts)
    result = check_audit_log_alive(db)
    assert result["alive"] is True
    assert result["last_seen"].tzinfo is not None


def test_last_audit_timestamp_none_quando_vazio() -> None:
    """last_audit_timestamp retorna None quando tabela vazia."""
    db = _make_db_with_last(None)
    assert last_audit_timestamp(db) is None
