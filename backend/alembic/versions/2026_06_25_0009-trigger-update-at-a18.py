"""A18: trigger set_updated_at em todas as tabelas (LGPD audit trail)

Revision ID: 2026_06_25_0009
Revises: 2026_06_25_0008
Create Date: 2026-06-25 08:00:00.000000

SQUAD A A18 - automatic updated_at trigger global

Aplica BEFORE UPDATE trigger que seta NEW.updated_at = NOW() em
TODAS as tabelas que tem coluna updated_at. Garante audit trail
exato (LGPD art. 37 - rastreabilidade de alteracoes).

Idempotente: DROP TRIGGER IF EXISTS antes de CREATE TRIGGER.
Downgrade: drop function + drop todas triggers.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "2026_06_25_0009"
down_revision: Union[str, None] = "2026_06_25_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tabelas com updated_at (10 tabelas core)
TABLES_WITH_UPDATED_AT = (
    "clientes",
    "protocolos",
    "atendimentos",
    "documentos",
    "conversas",
    "emolumentos",
    "outbox_messages",
    "webhook_events",
    "lgpd_consents",
    "lgpd_audit_anpd",
)


def upgrade() -> None:
    # Funcao generica (1x)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$
        LANGUAGE plpgsql
        """
    )

    # 1 trigger por tabela (BEFORE UPDATE)
    for table in TABLES_WITH_UPDATED_AT:
        op.execute(f"DROP TRIGGER IF EXISTS trg_set_updated_at_{table} ON {table}")
        op.execute(
            f"""
            CREATE TRIGGER trg_set_updated_at_{table}
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at()
            """
        )


def downgrade() -> None:
    for table in TABLES_WITH_UPDATED_AT:
        op.execute(f"DROP TRIGGER IF EXISTS trg_set_updated_at_{table} ON {table}")
    op.execute("DROP FUNCTION IF EXISTS fn_set_updated_at()")
