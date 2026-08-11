"""Contrato P0: todos os writers da audit chain usam o mesmo lock."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from app.services.audit import AuditService


class FakeSession:
    def __init__(self, dialect_name: str) -> None:
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect_name))
        self.calls: list[tuple[str, dict[str, int]]] = []

    def get_bind(self):
        return self.bind

    def execute(self, statement, params):
        self.calls.append((str(statement), params))


def test_postgres_writer_acquires_transaction_advisory_lock() -> None:
    db = FakeSession("postgresql")

    AuditService._acquire_chain_lock(db)  # type: ignore[arg-type]

    assert db.calls == [
        (
            "SELECT pg_advisory_xact_lock(:lock_id)",
            {"lock_id": AuditService.AUDIT_CHAIN_ADVISORY_LOCK_ID},
        )
    ]


def test_non_postgres_unit_database_does_not_issue_pg_lock() -> None:
    db = FakeSession("sqlite")

    AuditService._acquire_chain_lock(db)  # type: ignore[arg-type]

    assert db.calls == []


def test_trigger_and_python_share_lock_before_reading_chain_tail() -> None:
    migration_path = (
        Path(__file__).parents[1]
        / "alembic/versions/2026_08_11_0031-serialize-audit-chain-writers.py"
    )
    spec = importlib.util.spec_from_file_location("audit_lock_migration", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    migration = module.UPGRADE_SQL
    lock_call = f"pg_advisory_xact_lock({AuditService.AUDIT_CHAIN_ADVISORY_LOCK_ID})"

    assert lock_call in migration
    assert migration.index(lock_call) < migration.index("SELECT al.hash INTO v_prev_hash")
