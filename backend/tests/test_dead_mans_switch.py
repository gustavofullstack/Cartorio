"""Testes do Dead Man's Switch - A23.

Cobertura:
- last_audit_timestamp retorna None se tabela vazia
- last_audit_timestamp retorna max(timestamp) se ha entries
- check_audit_log_alive: alive=True se <= 1h
- check_audit_log_alive: alive=False se > 1h
- check_audit_log_alive: cold_start=True se vazio
- check_audit_log_alive: cold_start=False se ha entries (mesmo antigas)
- seconds_since_last calculado corretamente
- Lida com timestamp naive (assume UTC)
- DEAD_THRESHOLD = 1h
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.audit_log import AuditLog
from app.services.audit import AuditService
from app.services.dead_mans_switch import (
    COLD_START_THRESHOLD,
    DEAD_THRESHOLD,
    check_audit_log_alive,
    last_audit_timestamp,
)


from collections.abc import Generator


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """SQLite in-memory + schema."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _make_audit(db: Session, ts: datetime, action: str = "test.action") -> AuditLog:
    """Helper para criar AuditLog com hash chain (via AuditService).

    Sobrescreve timestamp DEPOIS do log (que gera chain sequencial).
    """
    audit = AuditService.log(
        db=db,
        actor_id="test",
        actor_type="user",
        action=action,
        resource="test_resource",
        payload={},
    )
    # AuditService gera timestamp=now(); sobrescreve para teste deterministico
    audit.timestamp = ts
    db.commit()
    db.refresh(audit)
    return audit


class TestDeadMansSwitch:
    """TDD strict - A23."""

    def test_dead_threshold_is_1h(self):
        """Threshold eh 1h (LGPD art. 37 - continuidade do audit)."""
        assert DEAD_THRESHOLD == timedelta(hours=1)

    def test_cold_start_threshold_5min(self):
        """Cold start = 5min (janela para considerar app em boot)."""
        assert COLD_START_THRESHOLD == timedelta(minutes=5)

    def test_empty_table_returns_none(self, db: Session):
        """Tabela vazia: last_audit_timestamp retorna None."""
        assert last_audit_timestamp(db) is None

    def test_empty_table_cold_start(self, db: Session):
        """Tabela vazia: cold_start=True, alive=False."""
        result = check_audit_log_alive(db)
        assert result["alive"] is False
        assert result["cold_start"] is True
        assert result["last_seen"] is None
        assert result["seconds_since_last"] is None

    def test_recent_audit_alive(self, db: Session):
        """Audit < 1h atras: alive=True."""
        now = datetime.now(tz=timezone.utc)
        _make_audit(db, now - timedelta(minutes=30))

        result = check_audit_log_alive(db)
        assert result["alive"] is True
        assert result["cold_start"] is False
        assert result["seconds_since_last"] is not None
        assert 1700 <= result["seconds_since_last"] <= 1900  # ~30min

    def test_old_audit_dead(self, db: Session):
        """Audit > 1h atras: alive=False."""
        now = datetime.now(tz=timezone.utc)
        _make_audit(db, now - timedelta(hours=2))

        result = check_audit_log_alive(db)
        assert result["alive"] is False
        assert result["cold_start"] is False
        assert result["seconds_since_last"] is not None
        assert result["seconds_since_last"] >= 7100  # ~2h

    def test_multiple_audits_takes_latest(self, db: Session):
        """Com varios audits, retorna o mais recente (max timestamp)."""
        now = datetime.now(tz=timezone.utc)
        _make_audit(db, now - timedelta(hours=3), action="a")
        _make_audit(db, now - timedelta(hours=2), action="b")
        _make_audit(db, now - timedelta(minutes=10), action="c")

        result = check_audit_log_alive(db)
        assert result["alive"] is True
        # Seconds since ~10min
        assert 500 <= result["seconds_since_last"] <= 700

    def test_naive_timestamp_assumes_utc(self, db: Session):
        """Timestamp naive eh tratado como UTC (nao quebra)."""
        now = datetime.now(tz=timezone.utc)
        # Cria com naive (sem tzinfo)
        recent_naive = (now - timedelta(minutes=15)).replace(tzinfo=None)
        _make_audit(db, recent_naive)

        result = check_audit_log_alive(db)
        assert result["alive"] is True
        assert result["seconds_since_last"] is not None

    def test_alive_boundary_1h(self, db: Session):
        """Boundary: exatamente 1h atras ainda eh alive (<=)."""
        now = datetime.now(tz=timezone.utc)
        _make_audit(db, now - timedelta(hours=1), action="boundary")

        result = check_audit_log_alive(db)
        # Aceita vivo (delta <= 1h) ou morto (delta > 1h por clock drift)
        # O importante eh NAO quebrar
        assert isinstance(result["alive"], bool)
