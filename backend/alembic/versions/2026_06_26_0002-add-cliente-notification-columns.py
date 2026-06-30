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


def upgrade() -> None:
    # A26: Notification fields — add columns that exist in model but not in DB
    op.add_column("clientes", sa.Column("telegram_chat_id", sa.String(64), nullable=True))
    op.add_column("clientes", sa.Column("whatsapp_number", sa.String(20), nullable=True))
    op.add_column(
        "clientes",
        sa.Column("email_notifications", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "clientes",
        sa.Column("sms_notifications", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column("clientes", sa.Column("preferred_contact_method", sa.String(32), nullable=True))

    # Indexes for notification lookups
    op.create_index("ix_clientes_telegram_chat_id", "clientes", ["telegram_chat_id"])
    op.create_index("ix_clientes_whatsapp_number", "clientes", ["whatsapp_number"])


def downgrade() -> None:
    op.drop_index("ix_clientes_whatsapp_number")
    op.drop_index("ix_clientes_telegram_chat_id")
    op.drop_column("clientes", "preferred_contact_method")
    op.drop_column("clientes", "sms_notifications")
    op.drop_column("clientes", "email_notifications")
    op.drop_column("clientes", "whatsapp_number")
    op.drop_column("clientes", "telegram_chat_id")
