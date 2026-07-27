"""Catalogo versionado de emolumentos (Fase 1 — ciclo de vida do dado).

Spec: docs/DADOS_PRECOS_E_PAINEL_AGENT_AI.md. Cada captura da fonte oficial
(ex.: PDF da Portaria CGJ/TJMG) gera uma FonteCaptura versionada; uma versao
anterior NUNCA e sobrescrita — ao promover uma nova, a anterior vira SUPERSEDED.

Estados (maquina de ciclo de vida):
    CAPTURED -> EXTRACTED -> HUMAN_REVIEWED -> PUBLISHED -> SUPERSEDED
    (qualquer estado pode ir para REJECTED por decisao humana)

O agente so le itens PUBLISHED cuja vigencia contenha a data da consulta;
ausencia ou expiracao implicam HITL, nunca preco inventado.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin


class EstadoEmolumento:
    """Estados do ciclo de vida do dado de emolumentos (string, LGPD-safe)."""

    CAPTURED = "CAPTURED"
    EXTRACTED = "EXTRACTED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class FonteCaptura(Base, TimestampMixin):
    """Versao capturada da fonte oficial de emolumentos (append-only)."""

    __tablename__ = "fonte_capturas"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    capturado_em: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EstadoEmolumento.CAPTURED, index=True
    )
    revisado_por: Mapped[str | None] = mapped_column(String(128), nullable=True)
    revisado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    itens: Mapped[list[EmolumentoItem]] = relationship(
        back_populates="captura", cascade="all, delete-orphan"
    )


class EmolumentoItem(Base, TimestampMixin):
    """Item de emolumento extraido de uma captura (versionado por captura_id)."""

    __tablename__ = "emolumento_itens"
    __table_args__ = (
        UniqueConstraint(
            "captura_id", "tipo_ato", "item_portaria", name="uq_emolumento_item_versao"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    captura_id: Mapped[int] = mapped_column(
        ForeignKey("fonte_capturas.id"), nullable=False, index=True
    )
    tipo_ato: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    item_portaria: Mapped[str] = mapped_column(String(80), nullable=False)
    ato: Mapped[str] = mapped_column(Text, nullable=False)
    emolumentos: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tfj: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    valor_final: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # Dados extras nao normalizados (ex.: faixa {"de": ..., "ate": ...}).
    componentes: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    escopo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EstadoEmolumento.EXTRACTED, index=True
    )
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)

    captura: Mapped[FonteCaptura] = relationship(back_populates="itens")


__all__ = ["EmolumentoItem", "EstadoEmolumento", "FonteCaptura"]
