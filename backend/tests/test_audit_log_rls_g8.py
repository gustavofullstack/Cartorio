"""PostgreSQL integration tests for G8.19.T3 audit_log RLS locks."""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError

_POSTGRES_URL = os.environ.get("AUDIT_RLS_TEST_DATABASE_URL", "")
_IS_POSTGRES = _POSTGRES_URL.startswith(("postgresql://", "postgresql+"))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _IS_POSTGRES,
        reason="postgres-only: defina AUDIT_RLS_TEST_DATABASE_URL para o banco de teste",
    ),
]


@pytest.fixture
def postgres_connection() -> Iterator[Connection]:
    engine = create_engine(_POSTGRES_URL, pool_pre_ping=True)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()
    engine.dispose()


def _assert_permission_denied(error: DBAPIError) -> None:
    sqlstate = getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)
    assert sqlstate == "42501"


def test_audit_log_select_succeeds(postgres_connection: Connection) -> None:
    postgres_connection.exec_driver_sql("SET LOCAL ROLE dpo")
    total = postgres_connection.execute(text("SELECT count(*) FROM public.audit_log")).scalar_one()
    assert isinstance(total, int)


def test_audit_log_insert_succeeds(postgres_connection: Connection) -> None:
    postgres_connection.exec_driver_sql("SET LOCAL ROLE service_role")
    audit_hash = secrets.token_hex(32)
    audit_id = postgres_connection.execute(
        text(
            """
            INSERT INTO public.audit_log (
                actor_id, actor_type, action, resource, payload,
                prev_hash, hash, hmac_signature, timestamp
            ) VALUES (
                :actor_id, 'system', 'audit.rls_test', 'audit_log', CAST(:payload AS JSON),
                NULL, :audit_hash, :hmac_signature, CURRENT_TIMESTAMP
            )
            RETURNING id
            """
        ),
        {
            "actor_id": "g8.19.t3.integration",
            "payload": "{}",
            "audit_hash": audit_hash,
            "hmac_signature": secrets.token_hex(64),
        },
    ).scalar_one()
    assert isinstance(audit_id, int)


def test_audit_log_update_blocked(postgres_connection: Connection) -> None:
    postgres_connection.exec_driver_sql("SET LOCAL ROLE service_role")
    with pytest.raises(DBAPIError) as exc_info:
        postgres_connection.execute(
            text("UPDATE public.audit_log SET actor_type = actor_type WHERE false")
        )
    _assert_permission_denied(exc_info.value)


def test_audit_log_delete_blocked(postgres_connection: Connection) -> None:
    postgres_connection.exec_driver_sql("SET LOCAL ROLE service_role")
    with pytest.raises(DBAPIError) as exc_info:
        postgres_connection.execute(text("DELETE FROM public.audit_log WHERE false"))
    _assert_permission_denied(exc_info.value)


def test_audit_log_rls_enabled(postgres_connection: Connection) -> None:
    is_enabled = postgres_connection.execute(
        text(
            """
            SELECT relrowsecurity
            FROM pg_class
            WHERE oid = 'public.audit_log'::regclass
            """
        )
    ).scalar_one()
    assert is_enabled is True


def test_audit_log_force_rls(postgres_connection: Connection) -> None:
    is_forced = postgres_connection.execute(
        text(
            """
            SELECT relforcerowsecurity
            FROM pg_class
            WHERE oid = 'public.audit_log'::regclass
            """
        )
    ).scalar_one()
    assert is_forced is True
