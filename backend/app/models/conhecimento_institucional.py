"""Persistência append-only do bounded context ConhecimentoInstitucional.

Este módulo guarda metadados normalizados e rastreáveis sobre conhecimento
institucional. Ele não lê nem armazena corpus bruto e não publica conteúdo por
conta própria: disponibilidade depende de validação humana e publicação.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin


class EstadoConhecimento:
    """Estados permitidos; somente ``PUBLISHED`` é consumível automaticamente."""

    INGESTED = "INGESTED"
    EXTRACTED = "EXTRACTED"
    CLASSIFIED = "CLASSIFIED"
    PENDING_HUMAN_VALIDATION = "PENDING_HUMAN_VALIDATION"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"


class DecisaoValidacao:
    """Resultados possíveis de uma decisão humana, sem aprovação implícita."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


ESTADOS_CONHECIMENTO_SQL = (
    "'INGESTED', 'EXTRACTED', 'CLASSIFIED', 'PENDING_HUMAN_VALIDATION', "
    "'APPROVED', 'PUBLISHED', 'SUPERSEDED', 'REJECTED', 'REVOKED'"
)


class FonteConhecimento(Base, TimestampMixin):
    """Identidade imutável de uma fonte, deduplicada pelo hash de conteúdo."""

    __tablename__ = "knowledge_sources"
    __table_args__ = (
        CheckConstraint("length(content_sha256) = 64", name="ck_knowledge_sources_sha256_length"),
        CheckConstraint(
            "source_kind IN ('OFFICIAL', 'INTERNAL', 'NORMATIVE')",
            name="ck_knowledge_sources_kind",
        ),
        CheckConstraint(
            f"state IN ({ESTADOS_CONHECIMENTO_SQL})", name="ck_knowledge_sources_state"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    canonical_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EstadoConhecimento.INGESTED, index=True
    )


class VersaoConhecimento(Base, TimestampMixin):
    """Versão imutável de uma fonte; a numeração é única dentro da fonte."""

    __tablename__ = "knowledge_versions"
    __table_args__ = (
        UniqueConstraint("source_id", "version_number", name="uq_knowledge_versions_source_number"),
        CheckConstraint("version_number > 0", name="ck_knowledge_versions_number_positive"),
        CheckConstraint("length(content_sha256) = 64", name="ck_knowledge_versions_sha256_length"),
        CheckConstraint(
            f"state IN ({ESTADOS_CONHECIMENTO_SQL})", name="ck_knowledge_versions_state"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_sources.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EstadoConhecimento.INGESTED, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


class UnidadeConhecimento(Base, TimestampMixin):
    """Unidade estruturada de uma versão; não contém o documento bruto."""

    __tablename__ = "knowledge_units"
    __table_args__ = (
        UniqueConstraint(
            "version_id", "sequence_number", name="uq_knowledge_units_version_sequence"
        ),
        CheckConstraint("sequence_number > 0", name="ck_knowledge_units_sequence_positive"),
        CheckConstraint("length(content_sha256) = 64", name="ck_knowledge_units_sha256_length"),
        CheckConstraint(f"state IN ({ESTADOS_CONHECIMENTO_SQL})", name="ck_knowledge_units_state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_versions.id"), nullable=False, index=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EstadoConhecimento.EXTRACTED, index=True
    )


class FatoConhecimento(Base, TimestampMixin):
    """Fato normalizado extraído de uma unidade, sujeito a validação humana."""

    __tablename__ = "knowledge_facts"
    __table_args__ = (
        UniqueConstraint("unit_id", "fact_key", name="uq_knowledge_facts_unit_key"),
        CheckConstraint(f"state IN ({ESTADOS_CONHECIMENTO_SQL})", name="ck_knowledge_facts_state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_units.id"), nullable=False, index=True
    )
    fact_key: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_value: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EstadoConhecimento.EXTRACTED, index=True
    )


class RegraCalculoConhecimento(Base, TimestampMixin):
    """Regra declarativa versionada; a execução aceita somente gramática fechada."""

    __tablename__ = "knowledge_calculation_rules"
    __table_args__ = (
        UniqueConstraint(
            "version_id", "rule_key", name="uq_knowledge_calculation_rules_version_key"
        ),
        CheckConstraint(
            f"state IN ({ESTADOS_CONHECIMENTO_SQL})", name="ck_knowledge_calculation_rules_state"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_versions.id"), nullable=False, index=True
    )
    rule_key: Mapped[str] = mapped_column(String(160), nullable=False)
    expression: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EstadoConhecimento.PENDING_HUMAN_VALIDATION, index=True
    )
    requires_human_validation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TipoDocumentoConhecimento(Base, TimestampMixin):
    """Tipo de documento classificável, definido dentro da versão da fonte."""

    __tablename__ = "knowledge_document_types"
    __table_args__ = (
        UniqueConstraint("version_id", "code", name="uq_knowledge_document_types_version_code"),
        CheckConstraint(
            f"state IN ({ESTADOS_CONHECIMENTO_SQL})", name="ck_knowledge_document_types_state"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_versions.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EstadoConhecimento.CLASSIFIED, index=True
    )


class ResultadoClassificacaoConhecimento(Base, TimestampMixin):
    """Resultado idempotente de classificação, nunca aceito como decisão humana."""

    __tablename__ = "knowledge_classification_results"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_knowledge_classification_results_idempotency"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_knowledge_classification_confidence"
        ),
        CheckConstraint(
            f"state IN ({ESTADOS_CONHECIMENTO_SQL})", name="ck_knowledge_classification_state"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_units.id"), nullable=False, index=True
    )
    document_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_document_types.id"), nullable=True, index=True
    )
    classifier_name: Mapped[str] = mapped_column(String(120), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EstadoConhecimento.PENDING_HUMAN_VALIDATION, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)


class DecisaoValidacaoConhecimento(Base, TimestampMixin):
    """Decisão humana rastreável sobre um artefato do contexto."""

    __tablename__ = "knowledge_validation_decisions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_knowledge_validation_decisions_idempotency"),
        CheckConstraint(
            "target_kind IN ('VERSION', 'UNIT', 'FACT', 'CALCULATION_RULE', "
            "'DOCUMENT_TYPE', 'CLASSIFICATION_RESULT')",
            name="ck_knowledge_validation_target_kind",
        ),
        CheckConstraint("target_id > 0", name="ck_knowledge_validation_target_positive"),
        CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')", name="ck_knowledge_validation_decision"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_versions.id"), nullable=False, index=True
    )
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)


class PublicacaoConhecimento(Base, TimestampMixin):
    """Registro de publicação; revogação e supersede preservam o histórico."""

    __tablename__ = "knowledge_publications"
    __table_args__ = (
        UniqueConstraint("version_id", name="uq_knowledge_publications_version"),
        CheckConstraint(
            "state IN ('PUBLISHED', 'SUPERSEDED', 'REVOKED')",
            name="ck_knowledge_publications_state",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_versions.id"), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, default=EstadoConhecimento.PUBLISHED
    )
    published_by: Mapped[str] = mapped_column(String(128), nullable=False)
    publication_reference: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)


__all__ = [
    "DecisaoValidacao",
    "DecisaoValidacaoConhecimento",
    "EstadoConhecimento",
    "FatoConhecimento",
    "FonteConhecimento",
    "PublicacaoConhecimento",
    "RegraCalculoConhecimento",
    "ResultadoClassificacaoConhecimento",
    "TipoDocumentoConhecimento",
    "UnidadeConhecimento",
    "VersaoConhecimento",
]
