"""add outbox_messages table (A2 DLQ + metric dlq_depth{queue})

Revision ID: 2026_06_24_0002
Revises: 2026_06_24_0001
Create Date: 2026-06-24 12:30:00.000000

LGPD-by-design:
- payload jsonb armazena APOS PII scrub (caller responsibility)
- queue enum limita cardinalidade do label dlq_depth{queue}
- last_error text NAO deve ter PII (caller responsibility)

Compat: PostgreSQL (JSONB nativo) + SQLite (JSON fallback via batch_alter_table).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026_06_24_0002"
down_revision: Union[str, None] = "2026_06_24_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria tabela outbox_messages + indices + enums."""
    # Detecta se a tabela ja' existe (idempotente para prod ja' aplicado)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "outbox_messages" in inspector.get_table_names():
        return

    # Cria enum types (Postgres)
    queue_enum = sa.Enum(
        "evolution", "chatwoot", "telegram", "outbox", name="outbox_queue_enum"
    )
    status_enum = sa.Enum(
        "pending", "processing", "done", "failed", name="outbox_status_enum"
    )

    # Em PG cria enums; em SQLite cria como VARCHAR
    queue_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)

    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "queue",
            queue_enum,
            nullable=False,
            index=True,
        ),
        sa.Column(
            "payload",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            index=True,
            server_default="pending",
        ),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column(
            "next_retry_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Indices adicionais para query de retry
    op.create_index(
        "ix_outbox_queue_status",
        "outbox_messages",
        ["queue", "status"],
    )
    op.create_index(
        "ix_outbox_next_retry_at",
        "outbox_messages",
        ["next_retry_at"],
    )


def downgrade() -> None:
    """Remove tabela outbox_messages + enums."""
    op.drop_index("ix_outbox_queue_status", table_name="outbox_messages")
    op.drop_table("outbox_messages")

    # Drop enums (PG only)
    sa.Enum(name="outbox_queue_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="outbox_status_enum").drop(op.get_bind(), checkfirst=True)
