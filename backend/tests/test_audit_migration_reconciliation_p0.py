"""Contratos P0 das migrations de reconciliacao da auditoria PostgreSQL."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

from sqlalchemy import create_engine


VERSIONS = Path(__file__).parents[1] / "alembic/versions"
PREREQUISITES_PATH = VERSIONS / "2026_08_11_0030p1-reconcile-audit-prerequisites.py"
SERIALIZATION_PATH = VERSIONS / "2026_08_11_0031-serialize-audit-chain-writers.py"
IDENTITY_PATH = VERSIONS / "2026_08_11_0032-add-channel-identity-binding.py"
REQUIRED_AUDIT_COLUMNS = {
    "id",
    "actor_id",
    "actor_type",
    "action",
    "resource",
    "payload",
    "request_id",
    "canal",
    "ip",
    "user_agent",
    "prev_hash",
    "hash",
    "hmac_signature",
    "hmac_kid",
    "timestamp",
}


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chain_includes_reconciliation_before_serialization() -> None:
    prerequisites = _load(PREREQUISITES_PATH, "audit_prerequisites_revision")
    serialization = _load(SERIALIZATION_PATH, "audit_serialization_revision")
    identity = _load(IDENTITY_PATH, "channel_identity_revision")

    assert (prerequisites.revision, prerequisites.down_revision) == ("0030p1", "0030")
    assert (serialization.revision, serialization.down_revision) == ("0031", "0030p1")
    assert (identity.revision, identity.down_revision) == ("0032", "0031")


def test_prerequisite_migration_is_fail_closed_and_does_not_touch_audit_rows() -> None:
    migration = _load(PREREQUISITES_PATH, "audit_prerequisites_contract")
    sql = migration.UPGRADE_SQL

    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in sql
    assert set(migration.REQUIRED_AUDIT_COLUMNS) == REQUIRED_AUDIT_COLUMNS
    for column in REQUIRED_AUDIT_COLUMNS:
        assert f"('{column}')" in sql
    assert "audit HMAC key is missing or invalid" in sql
    assert "audit HMAC kid is missing or invalid" in sql
    assert "audit_log required columns are missing" in sql
    assert "INSERT INTO audit_log" not in sql
    assert "UPDATE audit_log" not in sql
    assert "DELETE FROM audit_log" not in sql
    assert "ROW LEVEL SECURITY" not in sql
    assert "ALTER TABLE" not in sql


def test_postgres_fake_executes_exact_upgrade_and_safe_downgrade(monkeypatch) -> None:
    migration = _load(PREREQUISITES_PATH, "audit_prerequisites_postgres_fake")
    calls: list[str] = []
    bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(migration.op, "execute", lambda statement: calls.append(str(statement)))

    migration.upgrade()
    migration.downgrade()

    assert calls == [migration.UPGRADE_SQL, migration.DOWNGRADE_SQL]


def test_real_sqlite_dialect_is_a_safe_noop(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        migration = _load(PREREQUISITES_PATH, "audit_prerequisites_sqlite")
        monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
        monkeypatch.setattr(
            migration.op,
            "execute",
            lambda _statement: (_ for _ in ()).throw(AssertionError("unexpected SQL")),
        )

        migration.upgrade()
        migration.downgrade()
    engine.dispose()
