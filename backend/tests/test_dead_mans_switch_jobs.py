"""Testes A13 — Dead man's switch job + cron entrypoint + endpoints.

Escopo (nao conflita com tests/test_dead_mans_switch.py que cobre o service
de baixo nivel /health/audit (A23 SQUAD A)):

- jobs.dead_mans_switch.check_audit_log_freshness: classifica em 4 niveis
  (healthy / stale / critical / empty) com Pydantic AuditHealth tipado
- jobs.cron_dead_mans_switch.run_dead_mans_switch_check: entrypoint de cron
- GET /api/v1/health/audit-freshness: endpoint publico (200 healthy / 503 stale)
- POST /api/v1/admin/audit/dead-mans-switch/check: endpoint admin (X-API-Key)

Cenarios (6 obrigatorios + boundary + cron + endpoints):
- test_audit_fresh_5min_ok           (healthy)
- test_audit_fresh_45min_ok          (healthy, abaixo do threshold 60min)
- test_audit_stale_75min_alert       (stale, 1x < age < 2x threshold)
- test_audit_stale_2h_critical       (critical, age >= 2x threshold)
- test_audit_empty_table_empty       (empty, tabela vazia)
- test_cron_entrypoint_alerted_when_stale  (cron dispara alerta via placeholder)
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.jobs.cron_dead_mans_switch import run_dead_mans_switch_check
from app.jobs.dead_mans_switch import (
    DEFAULT_THRESHOLD_MINUTES,
    AuditHealth,
    HealthStatus,
    check_audit_log_freshness,
)
from app.models.audit_log import AuditLog
from app.services.audit import AuditService


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
        payload={"ts": when.isoformat()},
    )
    audit.timestamp = when
    db.commit()
    db.refresh(audit)
    return audit


def _now() -> datetime:
    """Now em UTC naive (audit_log.timestamp eh naive UTC)."""
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


# ============================================================================
# TestFreshness — 5 cenarios do brief + extras
# ============================================================================


class TestFreshness:
    """5 cenarios do brief + 1 boundary extra."""

    def test_audit_fresh_5min_ok(self, db_session: Session) -> None:
        """Ultima entry ha 5min -> healthy (abaixo threshold 60min)."""
        now = _now()
        _insert_audit_at(db_session, now - timedelta(minutes=5))

        health = check_audit_log_freshness(db_session)

        assert isinstance(health, AuditHealth)
        assert health.status == HealthStatus.HEALTHY
        assert health.alert is None
        assert health.threshold_minutes == DEFAULT_THRESHOLD_MINUTES
        assert health.last_entry_age_minutes is not None
        assert 4 <= health.last_entry_age_minutes <= 6  # type: ignore[operator]

    def test_audit_fresh_45min_ok(self, db_session: Session) -> None:
        """Ultima entry ha 45min -> healthy (ainda abaixo do threshold 60min)."""
        now = _now()
        _insert_audit_at(db_session, now - timedelta(minutes=45))

        health = check_audit_log_freshness(db_session)

        assert health.status == HealthStatus.HEALTHY
        assert health.alert is None
        assert 44 <= health.last_entry_age_minutes <= 46  # type: ignore[operator]

    def test_audit_stale_75min_alert(self, db_session: Session) -> None:
        """Ultima entry ha 75min -> stale (acima do threshold 60min, abaixo de 2x)."""
        now = _now()
        _insert_audit_at(db_session, now - timedelta(minutes=75))

        health = check_audit_log_freshness(db_session)

        assert health.status == HealthStatus.STALE
        assert health.alert is not None
        assert "STALE" in health.alert
        assert 74 <= health.last_entry_age_minutes <= 76  # type: ignore[operator]

    def test_audit_stale_2h_critical(self, db_session: Session) -> None:
        """Ultima entry ha 2h -> critical (>= 2x threshold)."""
        now = _now()
        _insert_audit_at(db_session, now - timedelta(hours=2))

        health = check_audit_log_freshness(db_session)

        assert health.status == HealthStatus.CRITICAL
        assert health.alert is not None
        assert "CRITICAL" in health.alert
        assert 119 <= health.last_entry_age_minutes <= 121  # type: ignore[operator]

    def test_audit_empty_table_empty(self, db_session: Session) -> None:
        """Tabela vazia -> empty (cold start / app sem gravar nada)."""
        assert db_session.query(AuditLog).count() == 0  # sanity

        health = check_audit_log_freshness(db_session)

        assert health.status == HealthStatus.EMPTY
        assert health.alert is not None
        assert "VAZIA" in health.alert.upper()
        assert health.last_entry_at is None
        assert health.last_entry_age_minutes is None

    def test_custom_threshold_minutes(self, db_session: Session) -> None:
        """Threshold customizavel: 30min, entry ha 45min -> stale."""
        now = _now()
        _insert_audit_at(db_session, now - timedelta(minutes=45))

        health = check_audit_log_freshness(db_session, threshold_minutes=30)

        assert health.status == HealthStatus.STALE
        assert health.threshold_minutes == 30

    def test_invalid_threshold_raises(self, db_session: Session) -> None:
        """threshold_minutes < 1 -> ValueError (validacao no boundary)."""
        with pytest.raises(ValueError, match="threshold_minutes deve ser >= 1"):
            check_audit_log_freshness(db_session, threshold_minutes=0)


# ============================================================================
# TestCronEntrypoint — wrapper cron
# ============================================================================


class TestCronEntrypoint:
    """Cobre o wrapper cron (run_dead_mans_switch_check)."""

    def test_cron_healthy_no_alert(self, db_session: Session) -> None:
        """healthy: alerted=False, retorna CronRunResult com health.healthy."""
        now = _now()
        _insert_audit_at(db_session, now - timedelta(minutes=10))

        result = run_dead_mans_switch_check(db_session)

        assert result.health.status == HealthStatus.HEALTHY
        assert result.alerted is False

    def test_cron_entrypoint_alerted_when_stale(self, db_session: Session) -> None:
        """stale: alerted=True, log placeholder disparado."""
        now = _now()
        _insert_audit_at(db_session, now - timedelta(minutes=75))

        result = run_dead_mans_switch_check(db_session)

        assert result.health.status == HealthStatus.STALE
        assert result.alerted is True

    def test_cron_entrypoint_alerted_when_critical(self, db_session: Session) -> None:
        """critical: alerted=True (max severity)."""
        now = _now()
        _insert_audit_at(db_session, now - timedelta(hours=3))

        result = run_dead_mans_switch_check(db_session)

        assert result.health.status == HealthStatus.CRITICAL
        assert result.alerted is True

    def test_cron_entrypoint_alerted_when_empty(self, db_session: Session) -> None:
        """empty (cold start): alerted=True."""
        assert db_session.query(AuditLog).count() == 0

        result = run_dead_mans_switch_check(db_session)

        assert result.health.status == HealthStatus.EMPTY
        assert result.alerted is True


# ============================================================================
# TestEndpoints — 2 endpoints novos (health/audit-freshness + admin)
# ============================================================================
#
# Pattern canonico: StaticPool + check_same_thread=False, patch app.db.engine
# + app.main.engine + app.db.SessionLocal + app.db.session_scope. Sem isso,
# o TestClient quebra com "SQLite objects created in a thread can only be
# used in that same thread" (FastAPI roda handler em worker thread).
# (Ver test_cliente_get_endpoint.py para o pattern original.)


def _make_isolated_client_with_entry(entry_age_minutes: int | None):
    """Factory: cria TestClient + engine isolado + 1 entry de teste (opcional).

    Returns (TestClient, SessionLocal_factory) para o caller inserir dados.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.models.base import Base
    import app.db
    import app.main as app_main_module

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

    # Insere entry se idade fornecida
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


class TestHealthAuditFreshnessEndpoint:
    """Cobre GET /api/v1/health/audit-freshness."""

    def test_200_when_healthy(self) -> None:
        """200 + status=healthy quando audit log fresco."""
        client, restore = _make_isolated_client_with_entry(entry_age_minutes=10)
        try:
            resp = client.get("/api/v1/health/audit-freshness")
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["status"] == "healthy"
            assert body["threshold_minutes"] == DEFAULT_THRESHOLD_MINUTES
            assert body["alert"] is None
        finally:
            restore()

    def test_503_when_critical(self) -> None:
        """503 + status=critical quando audit log muito stale (>2x threshold)."""
        client, restore = _make_isolated_client_with_entry(entry_age_minutes=120)
        try:
            resp = client.get("/api/v1/health/audit-freshness")
            assert resp.status_code == 503, resp.text
            body = resp.json()
            assert body["status"] == "critical"
            assert body["alert"] is not None
            assert "CRITICAL" in body["alert"]
        finally:
            restore()

    def test_503_when_empty(self) -> None:
        """503 + status=empty quando tabela vazia (cold start)."""
        client, restore = _make_isolated_client_with_entry(entry_age_minutes=None)
        try:
            resp = client.get("/api/v1/health/audit-freshness")
            assert resp.status_code == 503, resp.text
            body = resp.json()
            assert body["status"] == "empty"
            assert body["alert"] is not None
            assert body["last_entry_at"] is None
        finally:
            restore()


class TestAdminDeadMansSwitchEndpoint:
    """Cobre POST /api/v1/admin/audit/dead-mans-switch/check."""

    def test_401_without_api_key(self) -> None:
        """Sem X-API-Key -> 401 (gate B0.3.SEC)."""
        client, restore = _make_isolated_client_with_entry(entry_age_minutes=10)
        try:
            resp = client.post("/api/v1/admin/audit/dead-mans-switch/check")
            assert resp.status_code == 401, resp.text
        finally:
            restore()

    def test_200_when_healthy(self) -> None:
        """Com auth + fresco -> 200 + status=healthy."""
        from tests.conftest import TEST_CARTORIO_API_KEY

        client, restore = _make_isolated_client_with_entry(entry_age_minutes=5)
        try:
            resp = client.post(
                "/api/v1/admin/audit/dead-mans-switch/check",
                headers={"X-API-Key": TEST_CARTORIO_API_KEY},
            )
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["status"] == "healthy"
            assert body["alert"] is None
            assert body["alerted"] is False
        finally:
            restore()

    def test_503_when_stale(self) -> None:
        """Com auth + stale -> 503 + status=stale."""
        from tests.conftest import TEST_CARTORIO_API_KEY

        client, restore = _make_isolated_client_with_entry(entry_age_minutes=75)
        try:
            resp = client.post(
                "/api/v1/admin/audit/dead-mans-switch/check",
                headers={"X-API-Key": TEST_CARTORIO_API_KEY},
            )
            assert resp.status_code == 503, resp.text
            body = resp.json()
            assert body["status"] == "stale"
            assert body["alert"] is not None
            assert body["alerted"] is True
        finally:
            restore()
