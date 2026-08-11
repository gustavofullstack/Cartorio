"""Add pseudonym-only channel identity binding for LGPD erasure.

Revision ID: 0032
Revises: 0031
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_channel_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("conversation_pseudonym", sa.String(length=64), nullable=False),
        sa.Column("hmac_kid", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "length(conversation_pseudonym) = 64",
            name="ck_cliente_channel_identity_pseudonym_length",
        ),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "channel",
            "conversation_pseudonym",
            name="uq_cliente_channel_identity_channel_pseudonym",
        ),
    )
    op.create_index(
        "ix_cliente_channel_identities_cliente_id",
        "cliente_channel_identities",
        ["cliente_id"],
        unique=False,
    )
    op.create_index(
        "ix_cliente_channel_identities_channel",
        "cliente_channel_identities",
        ["channel"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cliente_channel_identities_channel",
        table_name="cliente_channel_identities",
    )
    op.drop_index(
        "ix_cliente_channel_identities_cliente_id",
        table_name="cliente_channel_identities",
    )
    op.drop_table("cliente_channel_identities")
