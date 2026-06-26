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


def upgrade() -> None:
    # A18: Add created_at + updated_at to agendamentos (TimestampMixin)
    op.add_column("agendamentos", sa.Column("created_at", sa.DateTime(), nullable=True))
    op.add_column("agendamentos", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # A18: Add created_at + updated_at to webhook_events (TimestampMixin)
    op.add_column("webhook_events", sa.Column("created_at", sa.DateTime(), nullable=True))
    op.add_column("webhook_events", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # A19: Add deleted_at (soft delete) to core models
    op.add_column("protocolos", sa.Column("deleted_at", sa.DateTime(), nullable=True, index=True))
    op.add_column("conversas", sa.Column("deleted_at", sa.DateTime(), nullable=True, index=True))
    op.add_column("documentos", sa.Column("deleted_at", sa.DateTime(), nullable=True, index=True))
    op.add_column("agendamentos", sa.Column("deleted_at", sa.DateTime(), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("agendamentos", "deleted_at")
    op.drop_column("documentos", "deleted_at")
    op.drop_column("conversas", "deleted_at")
    op.drop_column("protocolos", "deleted_at")
    op.drop_column("webhook_events", "updated_at")
    op.drop_column("webhook_events", "created_at")
    op.drop_column("agendamentos", "updated_at")
    op.drop_column("agendamentos", "created_at")
