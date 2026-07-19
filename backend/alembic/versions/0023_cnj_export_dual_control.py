"""Cria pedidos CNJ com dupla aprovacao humana e hashes de manifesto.

Revision ID: 0024
Revises: 0023
"""

from alembic import op
import sqlalchemy as sa

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cnj_export_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("reference_period", sa.String(length=7), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approval_reason", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("report_sha256", sa.String(length=64), nullable=True),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cnj_export_requests_reference_period", "cnj_export_requests", ["reference_period"]
    )
    op.create_index("ix_cnj_export_requests_status", "cnj_export_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_cnj_export_requests_status", table_name="cnj_export_requests")
    op.drop_index("ix_cnj_export_requests_reference_period", table_name="cnj_export_requests")
    op.drop_table("cnj_export_requests")
