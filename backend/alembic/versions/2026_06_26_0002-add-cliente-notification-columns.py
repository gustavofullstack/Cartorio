"""A26: Add cliente notification columns (telegram_chat_id, whatsapp, etc.)

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-26

Adds notification/contact columns to clientes that exist in the
SQLAlchemy model but were never applied to the production DB.
Fixes: sqlalchemy.exc.ProgrammingError column telegram_chat_id does not exist.
"""

from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
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


def _create_index_if_not_exists(index_name: str, table_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    import sqlalchemy as sa

    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes(table_name)
    if not any(idx["name"] == index_name for idx in indexes):
        op.create_index(index_name, table_name, columns)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    bind = op.get_bind()
    import sqlalchemy as sa

    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes(table_name)
    if any(idx["name"] == index_name for idx in indexes):
        op.drop_index(index_name, table_name)


def upgrade() -> None:
    # A26: Notification fields — add columns that exist in model but not in DB
    _add_column_if_not_exists("clientes", "telegram_chat_id", sa.String(64), nullable=True)
    _add_column_if_not_exists("clientes", "whatsapp_number", sa.String(20), nullable=True)
    _add_column_if_not_exists(
        "clientes",
        "email_notifications",
        sa.Boolean(),
        nullable=False,
        server_default="true",
    )
    _add_column_if_not_exists(
        "clientes",
        "sms_notifications",
        sa.Boolean(),
        nullable=False,
        server_default="true",
    )
    _add_column_if_not_exists("clientes", "preferred_contact_method", sa.String(32), nullable=True)

    # Indexes for notification lookups
    _create_index_if_not_exists("ix_clientes_telegram_chat_id", "clientes", ["telegram_chat_id"])
    _create_index_if_not_exists("ix_clientes_whatsapp_number", "clientes", ["whatsapp_number"])


def downgrade() -> None:
    _drop_index_if_exists("ix_clientes_whatsapp_number", "clientes")
    _drop_index_if_exists("ix_clientes_telegram_chat_id", "clientes")
    _drop_column_if_exists("clientes", "preferred_contact_method")
    _drop_column_if_exists("clientes", "sms_notifications")
    _drop_column_if_exists("clientes", "email_notifications")
    _drop_column_if_exists("clientes", "whatsapp_number")
    _drop_column_if_exists("clientes", "telegram_chat_id")
