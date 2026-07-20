"""Persist the minimized CNJ artifact for safe re-download.

Revision ID: 0027
Revises: 0026
"""

from alembic import op
import sqlalchemy as sa


revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cnj_export_requests", sa.Column("artifact_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("cnj_export_requests", "artifact_json")
