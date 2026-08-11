"""Reconcile PostgreSQL prerequisites required by the serialized audit writer.

Revision ID: 0030p1
Revises: 0030
Create Date: 2026-08-11

This migration is deliberately additive and fail-closed. It never changes
``audit_log`` rows, policies, RLS or existing columns. ``pgcrypto`` is retained
on downgrade because the extension may predate this Alembic baseline.
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0030p1"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REQUIRED_AUDIT_COLUMNS: tuple[str, ...] = (
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
)

UPGRADE_SQL = r"""
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $audit_prerequisites$
DECLARE
    v_missing_columns TEXT;
    v_key_length INTEGER;
    v_kid_length INTEGER;
BEGIN
    IF to_regclass('public.audit_log') IS NULL THEN
        RAISE EXCEPTION USING
            ERRCODE = '42P01',
            MESSAGE = 'audit_log required table is missing';
    END IF;

    SELECT string_agg(required.column_name, ', ' ORDER BY required.column_name)
    INTO v_missing_columns
    FROM (
        VALUES
            ('id'),
            ('actor_id'),
            ('actor_type'),
            ('action'),
            ('resource'),
            ('payload'),
            ('request_id'),
            ('canal'),
            ('ip'),
            ('user_agent'),
            ('prev_hash'),
            ('hash'),
            ('hmac_signature'),
            ('hmac_kid'),
            ('timestamp')
    ) AS required(column_name)
    LEFT JOIN information_schema.columns actual
      ON actual.table_schema = 'public'
     AND actual.table_name = 'audit_log'
     AND actual.column_name = required.column_name
    WHERE actual.column_name IS NULL;

    IF v_missing_columns IS NOT NULL THEN
        RAISE EXCEPTION USING
            ERRCODE = '42703',
            MESSAGE = 'audit_log required columns are missing',
            DETAIL = v_missing_columns;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto')
       OR to_regprocedure('public.digest(text,text)') IS NULL
       OR to_regprocedure('public.hmac(text,text,text)') IS NULL THEN
        RAISE EXCEPTION USING
            ERRCODE = '42883',
            MESSAGE = 'pgcrypto digest/hmac functions are unavailable';
    END IF;

    v_key_length := length(COALESCE(current_setting('app.audit_hmac_key', true), ''));
    v_kid_length := length(COALESCE(current_setting('app.audit_hmac_kid', true), ''));

    IF v_key_length < 32 THEN
        RAISE EXCEPTION USING
            ERRCODE = '22023',
            MESSAGE = 'audit HMAC key is missing or invalid';
    END IF;
    IF v_kid_length < 1 OR v_kid_length > 64 THEN
        RAISE EXCEPTION USING
            ERRCODE = '22023',
            MESSAGE = 'audit HMAC kid is missing or invalid';
    END IF;
END;
$audit_prerequisites$;
"""

DOWNGRADE_SQL = r"""
DO $audit_prerequisites$
BEGIN
    -- Intentionally retained: ownership of pgcrypto may predate this baseline.
    NULL;
END;
$audit_prerequisites$;
"""


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if _is_postgresql():
        op.execute(UPGRADE_SQL)


def downgrade() -> None:
    if _is_postgresql():
        op.execute(DOWNGRADE_SQL)
