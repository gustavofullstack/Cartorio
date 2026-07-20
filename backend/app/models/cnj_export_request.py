"""Registro local do fluxo de aprovacao para exportacoes agregadas ao CNJ.

O registro contem somente identificadores operacionais de DPO e hashes do
artefato. Ele nunca armazena dados de titulares nem o arquivo exportado.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CNJExportRequest(Base):
    """Pedido de exportacao CNJ sujeito a aprovacao humana independente."""

    __tablename__ = "cnj_export_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    reference_period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="requested", index=True)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approval_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    report_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manifest_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Artefato agregado minimizado, recuperável após a geração. Nunca contém
    # linhas de titulares; é armazenado para evitar perda após um timeout HTTP.
    artifact_json: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = ["CNJExportRequest"]
