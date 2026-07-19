"""Enforce independent CNJ export approval at database level.

Revision ID: 0026
Revises: 0025
"""

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_cnj_export_independent_approval",
        "cnj_export_requests",
        "approved_by IS NULL OR approved_by <> requested_by",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_cnj_export_independent_approval", "cnj_export_requests", type_="check"
    )
