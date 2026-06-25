"""Testes A13 — Dead man's switch 3-level (briefing /root/cartorio-a13-dead-mans-switch).

Escopo: SHAPE 3-LEVEL (healthy/warning/critical) com response
`last_audit_ts` + `stale_seconds` + `status` + `threshold_minutes`.

NAO conflita com:
- tests/test_dead_mans_switch.py — service-level (A23)
- tests/test_dead_mans_switch_a13.py — endpoint publico /health/audit-freshness
- tests/test_dead_mans_switch_jobs.py — jobs level 4-level

Cobertura:
- 3-level classifier (healthy/warning/critical) + Prometheus metric
- cron 3-level wrapper (`run_dead_mans_switch_check_3lvl`)
- Telegram mock (assert message format + chat_id)
- Endpoint GET /admin/audit/health (X-API-Key)
- Endpoint POST /admin/audit/check-now (X-API-Key)
- Env vars `AUDIT_DEAD_MANS_SWITCH_MINUTES` + `AUDIT_ALERT_TELEGRAM_CHAT_ID`
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.jobs.cron_dead_mans_switch import (
    CronRunResult3Lvl,
    run_dead_mans_switch_check_3lvl,
)
from app.jobs.dead_mans_switch import (
    DEFAULT_THRESHOLD_MINUTES,
    AuditHealth3Lvl,
    HealthStatus3Lvl,
    check_audit_log_freshness_3lvl,
)
from app.models.audit_log import AuditLog
from app.services.audit import AuditService
from app.services.metrics import store as metrics_store


# ============================================================================
# Helpers — frozen datetime + audit insert + isolated client (canon pattern)
# ============================================================================


@contextmanager
def _frozen_now(now: datetime):
    """Patch `datetime.now` no modulo jobs/dead_mans_switch."""
    real_datetime = __import__("datetime").datetime

    class _FrozenDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            if tz is None:
                return now.replace(tzinfo=None)
            return now.astimezone(tz)

    with patch("app.jobs.dead_mans_switch.datetime", _FrozenDateTime):
        yield now


def _insert_audit_at(
    db: Session,
    when: datetime,
    *,
    action: str = "test.action",
) -> AuditLog:
    """Insere AuditLog com hash chain via AuditService, depois sobrescreve
    `timestamp` para o valor desejado (necessario para testes deterministicos).
    """
    audit = AuditService.log(
        db=db,
        actor_id="test",
        actor_type="user",
        action=action,
        resource="test_resource",
        payload={},
    )
    audit.timestamp = when
    db.commit()
    db.refresh(audit)
    return audit


def _make_isolated_client_with_entry_age(entry_age_minutes: int | None):
    """Factory canon (mesmo pattern do test_dead_mans_switch_jobs.py):
    cria TestClient + engine isolado + 1 entry de teste (opcional).

    Returns (TestClient, restore_fn).
    """
    import app.db
    import app.main as app_main_module

    from app.models.base import Base

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)

    original_engine = app.db.engine
    original_session_local = app.db.SessionLocal
    original_session_scope = app.db.session_scope
    original_main_engine = app_main_module.engine

    app.db.engine = test_engine
    app_main_module.engine = test_engine
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    app.db.SessionLocal = TestSessionLocal

    @contextmanager
    def test_session_scope():
        s = TestSessionLocal()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app.db.session_scope = test_session_scope

    if entry_age_minutes is not None:
        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        with TestSessionLocal() as s:
            audit = AuditService.log(
                db=s,
                actor_id="t",
                actor_type="user",
                action="t",
                resource="t",
                payload={},
            )
            audit.timestamp = now - timedelta(minutes=entry_age_minutes)
            s.commit()

    the_app = app_main_module.app
    client = TestClient(the_app)

    def restore():
        app.db.engine = original_engine
        app_main_module.engine = original_main_engine
        app.db.SessionLocal = original_session_local
        app.db.session_scope = original_session_scope
        Base.metadata.drop_all(test_engine)

    return client, restore


# ============================================================================
# Tests — 3-level classifier
# ============================================================================


def test_3lvl_healthy_when_last_entry_5min_old(db_session: Session) -> None:
    """Healthy: last entry <= threshold (60min default)."""
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    _insert_audit_at(db_session, now - timedelta(minutes=5))

    with _frozen_now(now):
        health = check_audit_log_freshness_3lvl(db_session)

    assert isinstance(health, AuditHealth3Lvl)
    assert health.status == HealthStatus3Lvl.HEALTHY
    assert health.stale_seconds == 5 * 60
    assert health.last_audit_ts is not None
    assert health.threshold_minutes == DEFAULT_THRESHOLD_MINUTES

    # Prometheus metric
    assert metrics_store.gauges.get("audit_dead_mans_status") == 0


def test_3lvl_warning_when_last_entry_75min_old(db_session: Session) -> None:
    """Warning: last entry > threshold e <= 2x threshold."""
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    _insert_audit_at(db_session, now - timedelta(minutes=75))

    with _frozen_now(now):
        health = check_audit_log_freshness_3lvl(db_session)

    assert health.status == HealthStatus3Lvl.WARNING
    assert health.stale_seconds == 75 * 60

    # Prometheus metric
    assert metrics_store.gauges.get("audit_dead_mans_status") == 1


def test_3lvl_critical_when_last_entry_3h_old(db_session: Session) -> None:
    """Critical: last entry > 2x threshold."""
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    _insert_audit_at(db_session, now - timedelta(hours=3))

    with _frozen_now(now):
        health = check_audit_log_freshness_3lvl(db_session)

    assert health.status == HealthStatus3Lvl.CRITICAL
    assert health.stale_seconds == 3 * 3600

    # Prometheus metric
    assert metrics_store.gauges.get("audit_dead_mans_status") == 2


def test_3lvl_critical_when_table_empty(db_session: Session) -> None:
    """Critical (mapeado de empty): cold start treated as critical (fail-safe)."""
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)

    with _frozen_now(now):
        health = check_audit_log_freshness_3lvl(db_session)

    assert health.status == HealthStatus3Lvl.CRITICAL
    assert health.last_audit_ts is None
    assert health.stale_seconds is None
    assert metrics_store.gauges.get("audit_dead_mans_status") == 2


def test_3lvl_threshold_custom_via_param(db_session: Session) -> None:
    """Threshold customizado via param (override do default)."""
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    _insert_audit_at(db_session, now - timedelta(minutes=10))

    with _frozen_now(now):
        # threshold=5: 10min > 5*2=10 -> critical (limite inclusive)
        health = check_audit_log_freshness_3lvl(db_session, threshold_minutes=5)

    # 10min > 2*5=10min, entao critical (boundary)
    assert health.status == HealthStatus3Lvl.CRITICAL
    assert health.threshold_minutes == 5


# ============================================================================
# Tests — cron 3-level wrapper + Telegram mock
# ============================================================================


def test_cron_3lvl_healthy_no_alert(db_session: Session) -> None:
    """Cron 3-level healthy: alerted=False, telegram_sent=False."""
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    _insert_audit_at(db_session, now - timedelta(minutes=5))

    with _frozen_now(now):
        result = run_dead_mans_switch_check_3lvl(db_session)

    assert isinstance(result, CronRunResult3Lvl)
    assert result.alerted is False
    assert result.telegram_sent is False
    assert result.health.status == HealthStatus3Lvl.HEALTHY


def test_cron_3lvl_critical_alerted_no_chat_id(
    db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """Cron 3-level critical sem chat_id: alerted=True, telegram_sent=False."""
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    _insert_audit_at(db_session, now - timedelta(hours=3))

    with patch.object(settings, "audit_alert_telegram_chat_id", None):
        with _frozen_now(now):
            with caplog.at_level(logging.ERROR, logger="app.jobs.cron_dead_mans_switch"):
                result = run_dead_mans_switch_check_3lvl(db_session)

    assert result.alerted is True
    assert result.telegram_sent is False  # sem chat_id = placeholder log only
    # Mensagem de placeholder DEVE ter sido logada com "no chat_id configured"
    assert any(
        "DEAD_MANS_SWITCH_TELEGRAM_PLACEHOLDER" in rec.message
        and "no chat_id configured" in rec.message
        for rec in caplog.records
    )


def test_cron_3lvl_warning_alerted_with_chat_id(
    db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """Cron 3-level warning COM chat_id: alerted=True, telegram_sent=True."""
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    _insert_audit_at(db_session, now - timedelta(minutes=75))

    chat_id = "-1001234567890"  # chat_id Telegram GRUPO PIETRA SQUAD fake
    with patch.object(settings, "audit_alert_telegram_chat_id", chat_id):
        with _frozen_now(now):
            with caplog.at_level(logging.ERROR, logger="app.jobs.cron_dead_mans_switch"):
                result = run_dead_mans_switch_check_3lvl(db_session)

    assert result.alerted is True
    assert result.telegram_sent is True
    # Mensagem DEVE conter chat_id + formato canonico
    matching = [
        rec for rec in caplog.records if "DEAD_MANS_SWITCH_TELEGRAM_PLACEHOLDER" in rec.message
    ]
    assert matching, "expected telegram placeholder log"
    msg = matching[0].message
    assert chat_id in msg
    assert "[DEAD MAN'S SWITCH] audit_log WARNING" in msg
    assert "Ultima entry:" in msg
    assert "Stale:" in msg
    assert "Threshold:" in msg


def test_cron_3lvl_default_threshold_uses_settings(
    db_session: Session,
) -> None:
    """Cron 3-level sem param: usa settings.audit_dead_mans_switch_minutes."""
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    _insert_audit_at(db_session, now - timedelta(minutes=5))

    with patch.object(settings, "audit_dead_mans_switch_minutes", 999):
        with _frozen_now(now):
            result = run_dead_mans_switch_check_3lvl(db_session)

    # 5min < 999min = healthy
    assert result.health.status == HealthStatus3Lvl.HEALTHY
    assert result.health.threshold_minutes == 999


# ============================================================================
# Tests — endpoints admin /admin/audit/health + /admin/audit/check-now
# ============================================================================


def _auth_headers() -> dict[str, str]:
    api_key = os.environ.get("CARTORIO_API_KEY", "a" * 64)
    return {"X-API-Key": api_key}


def test_endpoint_admin_audit_health_healthy() -> None:
    """GET /admin/audit/health: status=healthy."""
    client, restore = _make_isolated_client_with_entry_age(entry_age_minutes=5)
    try:
        resp = client.get("/api/v1/admin/audit/health", headers=_auth_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "healthy"
        # stale_seconds entre 290 e 310 (~5min, tolerancia pra tempo de exec)
        assert 290 <= body["stale_seconds"] <= 310
        assert body["threshold_minutes"] == settings.audit_dead_mans_switch_minutes
        assert body["last_audit_ts"] is not None
    finally:
        restore()


def test_endpoint_admin_audit_health_warning() -> None:
    """GET /admin/audit/health: status=warning (75min)."""
    client, restore = _make_isolated_client_with_entry_age(entry_age_minutes=75)
    try:
        resp = client.get("/api/v1/admin/audit/health", headers=_auth_headers())
        assert resp.status_code == 503, resp.text
        body = resp.json()
        assert body["status"] == "warning"
        assert 4490 <= body["stale_seconds"] <= 4510  # ~75min
    finally:
        restore()


def test_endpoint_admin_audit_health_critical() -> None:
    """GET /admin/audit/health: status=critical (3h)."""
    client, restore = _make_isolated_client_with_entry_age(entry_age_minutes=180)
    try:
        resp = client.get("/api/v1/admin/audit/health", headers=_auth_headers())
        assert resp.status_code == 503, resp.text
        body = resp.json()
        assert body["status"] == "critical"
        assert 10790 <= body["stale_seconds"] <= 10810  # ~3h
    finally:
        restore()


def test_endpoint_admin_audit_health_requires_api_key() -> None:
    """GET /admin/audit/health sem X-API-Key: 401."""
    client, restore = _make_isolated_client_with_entry_age(entry_age_minutes=5)
    try:
        resp = client.get("/api/v1/admin/audit/health")
        assert resp.status_code == 401
    finally:
        restore()


def test_endpoint_admin_audit_check_now_healthy() -> None:
    """POST /admin/audit/check-now: healthy -> alerted=False."""
    client, restore = _make_isolated_client_with_entry_age(entry_age_minutes=5)
    try:
        resp = client.post(
            "/api/v1/admin/audit/check-now",
            headers=_auth_headers(),
            json={},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["alerted"] is False
        assert body["telegram_sent"] is False
    finally:
        restore()


def test_endpoint_admin_audit_check_now_critical_alerts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """POST /admin/audit/check-now: critical -> alerted=True + telegram log."""
    client, restore = _make_isolated_client_with_entry_age(entry_age_minutes=180)

    chat_id = "-1009999999999"
    with patch.object(settings, "audit_alert_telegram_chat_id", chat_id):
        try:
            with caplog.at_level(logging.ERROR, logger="app.jobs.cron_dead_mans_switch"):
                resp = client.post(
                    "/api/v1/admin/audit/check-now",
                    headers=_auth_headers(),
                    json={},
                )
            assert resp.status_code == 503, resp.text
            body = resp.json()
            assert body["status"] == "critical"
            assert body["alerted"] is True
            assert body["telegram_sent"] is True
            # Telegram log
            matching = [
                rec
                for rec in caplog.records
                if "DEAD_MANS_SWITCH_TELEGRAM_PLACEHOLDER" in rec.message
            ]
            assert matching
            assert chat_id in matching[0].message
        finally:
            restore()


def test_endpoint_admin_audit_check_now_threshold_override() -> None:
    """POST /admin/audit/check-now com body threshold_minutes: override."""
    # Entry de 2min atras: healthy no threshold default (60min),
    # critical no threshold=1 (2min > 2*1=2min = boundary)
    client, restore = _make_isolated_client_with_entry_age(entry_age_minutes=2)
    try:
        resp = client.post(
            "/api/v1/admin/audit/check-now",
            headers=_auth_headers(),
            json={"threshold_minutes": 1},
        )
        assert resp.status_code == 503, resp.text
        body = resp.json()
        assert body["status"] == "critical"
        assert body["threshold_minutes"] == 1
    finally:
        restore()


def test_endpoint_admin_audit_check_now_requires_api_key() -> None:
    """POST /admin/audit/check-now sem X-API-Key: 401."""
    client, restore = _make_isolated_client_with_entry_age(entry_age_minutes=5)
    try:
        resp = client.post("/api/v1/admin/audit/check-now", json={})
        assert resp.status_code == 401
    finally:
        restore()


def test_endpoint_admin_audit_check_now_audits_own_trigger() -> None:
    """POST /admin/audit/check-now audita propria execucao (LGPD gap fix).

    LGPD reviewer flag (08:46 BRT): GET /admin/audit/health auditava propria
    leitura mas POST /admin/audit/check-now NAO. Gap coberto via
    AuditService.log(action='audit.check.triggered').
    """
    import app.db
    from app.models.audit_log import AuditLog
    from sqlalchemy import select

    client, restore = _make_isolated_client_with_entry_age(entry_age_minutes=5)
    try:
        before_count = len(app.db.SessionLocal().execute(select(AuditLog)).scalars().all())

        resp = client.post(
            "/api/v1/admin/audit/check-now",
            headers=_auth_headers(),
            json={},
        )
        assert resp.status_code == 200, resp.text

        after_count = len(app.db.SessionLocal().execute(select(AuditLog)).scalars().all())
        # 1 entry nova (audit.check.triggered) — alem da entry seed do test
        assert after_count - before_count == 1

        # Confirma action name correto
        latest = (
            app.db.SessionLocal()
            .execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(1))
            .scalars()
            .one()
        )
        assert latest.action == "audit.check.triggered"
        assert latest.actor_type == "system"
    finally:
        restore()
