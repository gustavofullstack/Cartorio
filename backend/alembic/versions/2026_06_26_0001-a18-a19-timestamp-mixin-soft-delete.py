"""A18+A19: TimestampMixin agendamento/webhook + deleted_at soft delete

Revision ID: 0015
Revises: 2026_06_25_0014
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "0015"
down_revision = "2026_06_25_0014"
branch_labels = None
depends_on = None


def _add_column_if_not_exists(table_name: str, column_name: str, type_, **kwargs) -> None:
    bind = op.get_bind()
    import sqlalchemy as sa

    inspector = sa.inspect(bind)
    cols = inspector.get_columns(table_name)
    if not any(c["name"] == column_name for c in cols):
        op.add_column(table_name, sa.Column(column_name, type_, **kwargs))


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    import sqlalchemy as sa

    inspector = sa.inspect(bind)
    cols = inspector.get_columns(table_name)
    if any(c["name"] == column_name for c in cols):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    # A18: Add created_at + updated_at to agendamentos (TimestampMixin)
    _add_column_if_not_exists("agendamentos", "created_at", sa.DateTime(), nullable=True)
    _add_column_if_not_exists("agendamentos", "updated_at", sa.DateTime(), nullable=True)

    # A18: Add created_at + updated_at to webhook_events (TimestampMixin)
    _add_column_if_not_exists("webhook_events", "created_at", sa.DateTime(), nullable=True)
    _add_column_if_not_exists("webhook_events", "updated_at", sa.DateTime(), nullable=True)

    # A19: Add deleted_at (soft delete) to core models
    _add_column_if_not_exists("protocolos", "deleted_at", sa.DateTime(), nullable=True, index=True)
    _add_column_if_not_exists("conversas", "deleted_at", sa.DateTime(), nullable=True, index=True)
    _add_column_if_not_exists("documentos", "deleted_at", sa.DateTime(), nullable=True, index=True)
    _add_column_if_not_exists(
        "agendamentos", "deleted_at", sa.DateTime(), nullable=True, index=True
    )


def downgrade() -> None:
    _drop_column_if_exists("agendamentos", "deleted_at")
    _drop_column_if_exists("documentos", "deleted_at")
    _drop_column_if_exists("conversas", "deleted_at")
    _drop_column_if_exists("protocolos", "deleted_at")
    _drop_column_if_exists("webhook_events", "updated_at")
    _drop_column_if_exists("webhook_events", "created_at")
    _drop_column_if_exists("agendamentos", "updated_at")
    _drop_column_if_exists("agendamentos", "created_at")
