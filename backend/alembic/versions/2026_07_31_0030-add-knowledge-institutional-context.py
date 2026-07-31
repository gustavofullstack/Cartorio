"""Add the fail-closed ConhecimentoInstitucional bounded context.

Revision ID: 0030
Revises: 0029
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _state_check() -> str:
    return (
        "state IN ('INGESTED', 'EXTRACTED', 'CLASSIFIED', 'PENDING_HUMAN_VALIDATION', "
        "'APPROVED', 'PUBLISHED', 'SUPERSEDED', 'REJECTED', 'REVOKED')"
    )


def upgrade() -> None:
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_kind", sa.String(length=20), nullable=False),
        sa.Column("canonical_uri", sa.String(length=512), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "length(content_sha256) = 64", name="ck_knowledge_sources_sha256_length"
        ),
        sa.CheckConstraint(
            "source_kind IN ('OFFICIAL', 'INTERNAL', 'NORMATIVE')", name="ck_knowledge_sources_kind"
        ),
        sa.CheckConstraint(_state_check(), name="ck_knowledge_sources_state"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_sources_content_sha256", "knowledge_sources", ["content_sha256"], unique=True
    )
    op.create_index("ix_knowledge_sources_state", "knowledge_sources", ["state"], unique=False)

    op.create_table(
        "knowledge_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("version_number > 0", name="ck_knowledge_versions_number_positive"),
        sa.CheckConstraint(
            "length(content_sha256) = 64", name="ck_knowledge_versions_sha256_length"
        ),
        sa.CheckConstraint(_state_check(), name="ck_knowledge_versions_state"),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id", "version_number", name="uq_knowledge_versions_source_number"
        ),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_knowledge_versions_source_id", "knowledge_versions", ["source_id"], unique=False
    )
    op.create_index("ix_knowledge_versions_state", "knowledge_versions", ["state"], unique=False)

    op.create_table(
        "knowledge_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("unit_kind", sa.String(length=40), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("sequence_number > 0", name="ck_knowledge_units_sequence_positive"),
        sa.CheckConstraint("length(content_sha256) = 64", name="ck_knowledge_units_sha256_length"),
        sa.CheckConstraint(_state_check(), name="ck_knowledge_units_state"),
        sa.ForeignKeyConstraint(["version_id"], ["knowledge_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "version_id", "sequence_number", name="uq_knowledge_units_version_sequence"
        ),
    )
    op.create_index(
        "ix_knowledge_units_version_id", "knowledge_units", ["version_id"], unique=False
    )
    op.create_index("ix_knowledge_units_state", "knowledge_units", ["state"], unique=False)

    op.create_table(
        "knowledge_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("fact_key", sa.String(length=160), nullable=False),
        sa.Column("normalized_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(_state_check(), name="ck_knowledge_facts_state"),
        sa.ForeignKeyConstraint(["unit_id"], ["knowledge_units.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("unit_id", "fact_key", name="uq_knowledge_facts_unit_key"),
    )
    op.create_index("ix_knowledge_facts_unit_id", "knowledge_facts", ["unit_id"], unique=False)
    op.create_index("ix_knowledge_facts_state", "knowledge_facts", ["state"], unique=False)

    op.create_table(
        "knowledge_calculation_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("rule_key", sa.String(length=160), nullable=False),
        sa.Column("expression", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("requires_human_validation", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(_state_check(), name="ck_knowledge_calculation_rules_state"),
        sa.ForeignKeyConstraint(["version_id"], ["knowledge_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "version_id", "rule_key", name="uq_knowledge_calculation_rules_version_key"
        ),
    )
    op.create_index(
        "ix_knowledge_calculation_rules_version_id",
        "knowledge_calculation_rules",
        ["version_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_calculation_rules_state",
        "knowledge_calculation_rules",
        ["state"],
        unique=False,
    )

    op.create_table(
        "knowledge_document_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(_state_check(), name="ck_knowledge_document_types_state"),
        sa.ForeignKeyConstraint(["version_id"], ["knowledge_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "code", name="uq_knowledge_document_types_version_code"),
    )
    op.create_index(
        "ix_knowledge_document_types_version_id",
        "knowledge_document_types",
        ["version_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_document_types_state", "knowledge_document_types", ["state"], unique=False
    )

    op.create_table(
        "knowledge_classification_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("document_type_id", sa.Integer(), nullable=True),
        sa.Column("classifier_name", sa.String(length=120), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_knowledge_classification_confidence"
        ),
        sa.CheckConstraint(_state_check(), name="ck_knowledge_classification_state"),
        sa.ForeignKeyConstraint(["document_type_id"], ["knowledge_document_types.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["knowledge_units.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_knowledge_classification_results_idempotency"
        ),
    )
    op.create_index(
        "ix_knowledge_classification_results_unit_id",
        "knowledge_classification_results",
        ["unit_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_classification_results_document_type_id",
        "knowledge_classification_results",
        ["document_type_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_classification_results_state",
        "knowledge_classification_results",
        ["state"],
        unique=False,
    )

    op.create_table(
        "knowledge_validation_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("target_kind", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reviewer_id", sa.String(length=128), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "target_kind IN ('VERSION', 'UNIT', 'FACT', 'CALCULATION_RULE', 'DOCUMENT_TYPE', 'CLASSIFICATION_RESULT')",
            name="ck_knowledge_validation_target_kind",
        ),
        sa.CheckConstraint("target_id > 0", name="ck_knowledge_validation_target_positive"),
        sa.CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')", name="ck_knowledge_validation_decision"
        ),
        sa.ForeignKeyConstraint(["version_id"], ["knowledge_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_knowledge_validation_decisions_idempotency"
        ),
    )
    op.create_index(
        "ix_knowledge_validation_decisions_version_id",
        "knowledge_validation_decisions",
        ["version_id"],
        unique=False,
    )

    op.create_table(
        "knowledge_publications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("published_by", sa.String(length=128), nullable=False),
        sa.Column("publication_reference", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "state IN ('PUBLISHED', 'SUPERSEDED', 'REVOKED')",
            name="ck_knowledge_publications_state",
        ),
        sa.ForeignKeyConstraint(["version_id"], ["knowledge_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publication_reference"),
        sa.UniqueConstraint("version_id", name="uq_knowledge_publications_version"),
    )
    op.create_index(
        "ix_knowledge_publications_version_id",
        "knowledge_publications",
        ["version_id"],
        unique=False,
    )


def downgrade() -> None:
    for table_name in (
        "knowledge_publications",
        "knowledge_validation_decisions",
        "knowledge_classification_results",
        "knowledge_document_types",
        "knowledge_calculation_rules",
        "knowledge_facts",
        "knowledge_units",
        "knowledge_versions",
        "knowledge_sources",
    ):
        op.drop_table(table_name)
