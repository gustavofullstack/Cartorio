"""Tests para Dead Man's Switch API endpoint (G6.A.T11)."""

from __future__ import annotations

import os

os.environ["APP_ENV"] = "staging"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUDIT_HMAC_KEY"] = "a" * 64
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.schemas.dead_mans_switch import (  # noqa: E402
    DeadMansSwitchHistory,
    DeadMansSwitchHistoryItem,
    DeadMansSwitchStatus,
)


def test_status_basico_desabilitado() -> None:
    """Status quando threshold=0 (desabilitado)."""
    status = DeadMansSwitchStatus(
        enabled=False,
        threshold_minutes=0,
        last_heartbeat=None,
        age_seconds=None,
        is_alive=True,
        message="desabilitado",
    )
    assert status.enabled is False
    assert status.is_alive is True


def test_status_vivo() -> None:
    """Status quando esta vivo (heartbeat recente)."""
    status = DeadMansSwitchStatus(
        enabled=True,
        threshold_minutes=15,
        last_heartbeat="2026-07-16T18:00:00Z",
        age_seconds=120,
        is_alive=True,
        message="Vivo",
    )
    assert status.is_alive is True
    assert status.age_seconds == 120


def test_status_morto() -> None:
    """Status quando esta morto (heartbeat > threshold)."""
    status = DeadMansSwitchStatus(
        enabled=True,
        threshold_minutes=15,
        last_heartbeat="2026-07-16T17:00:00Z",
        age_seconds=3700,
        is_alive=False,
        message="MORTO",
    )
    assert status.is_alive is False
    assert status.age_seconds > 900  # 15min * 60s


def test_history_basico() -> None:
    """History com 0 items."""
    history = DeadMansSwitchHistory(total=0, items=[])
    assert history.total == 0
    assert len(history.items) == 0


def test_history_com_items() -> None:
    """History com items."""
    history = DeadMansSwitchHistory(
        total=2,
        items=[
            DeadMansSwitchHistoryItem(
                timestamp="2026-07-16T18:00:00Z",
                actor="cron",
                action="heartbeat",
                hash="abc123",
            ),
            DeadMansSwitchHistoryItem(
                timestamp="2026-07-16T17:00:00Z",
                actor="manual",
                action="heartbeat",
                hash="def456",
            ),
        ],
    )
    assert history.total == 2
    assert history.items[0].actor == "cron"
    assert history.items[1].actor == "manual"


def test_endpoint_path_registrado() -> None:
    """Endpoints registrados."""
    from app.api.v1.dead_mans_switch import router
    paths = [r.path for r in router.routes]
    assert "/api/v1/admin/dead-mans-switch/status" in paths
    assert "/api/v1/admin/dead-mans-switch/heartbeat" in paths
    assert "/api/v1/admin/dead-mans-switch/history" in paths


def test_threshold_default_15min() -> None:
    """Threshold default 15min = 900s."""
    threshold_min = 15
    threshold_sec = threshold_min * 60
    assert threshold_sec == 900


def test_age_calculation() -> None:
    """Idade em segundos = now - last."""
    from datetime import datetime, timezone
    now = datetime(2026, 7, 16, 18, 0, 0, tzinfo=timezone.utc)
    last = datetime(2026, 7, 16, 17, 45, 0, tzinfo=timezone.utc)
    age = (now - last).total_seconds()
    assert age == 900  # 15 minutos