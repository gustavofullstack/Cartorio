"""Enforce CNJ export state invariants in PostgreSQL.

Revision ID: 0025
Revises: 0024
"""

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_cnj_export_status",
        "cnj_export_requests",
        "status IN ('requested', 'approved', 'generated')",
    )
    op.create_check_constraint(
        "ck_cnj_export_reference_period",
        "cnj_export_requests",
        "reference_period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'",
    )
    op.create_check_constraint(
        "ck_cnj_export_state_fields",
        "cnj_export_requests",
        "(status = 'requested' AND approved_by IS NULL AND approved_at IS NULL "
        "AND approval_reason IS NULL AND generated_at IS NULL AND report_sha256 IS NULL "
        "AND manifest_sha256 IS NULL) OR "
        "(status = 'approved' AND approved_by IS NOT NULL AND approved_at IS NOT NULL "
        "AND approval_reason IS NOT NULL AND generated_at IS NULL AND report_sha256 IS NULL "
        "AND manifest_sha256 IS NULL) OR "
        "(status = 'generated' AND approved_by IS NOT NULL AND approved_at IS NOT NULL "
        "AND approval_reason IS NOT NULL AND generated_at IS NOT NULL AND report_sha256 IS NOT NULL "
        "AND manifest_sha256 IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_cnj_export_state_fields", "cnj_export_requests", type_="check")
    op.drop_constraint("ck_cnj_export_reference_period", "cnj_export_requests", type_="check")
    op.drop_constraint("ck_cnj_export_status", "cnj_export_requests", type_="check")
