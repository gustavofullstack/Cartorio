"""Modelo Documento - arquivos anexados a um protocolo."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.protocolo import Protocolo


class Documento(Base, TimestampMixin):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    protocolo_id: Mapped[int] = mapped_column(ForeignKey("protocolos.id"), index=True)

    tipo: Mapped[str] = mapped_column(String(64), index=True)
    # rg, cpf, comprovante_residencia, certidao_casamento, escritura_anterior, etc
    storage_path: Mapped[str] = mapped_column(String(512))
    storage_provider: Mapped[str] = mapped_column(String(32), default="supabase")
    tamanho_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Integridade: SHA256 do arquivo (imutavel, recalculado on download)
    hash_sha256: Mapped[str] = mapped_column(String(64), index=True)

    # Quem fez upload
    uploaded_by: Mapped[str] = mapped_column(String(128))
    uploaded_by_tipo: Mapped[str] = mapped_column(String(32), default="cliente")
    # cliente, escrevente, sistema

    # Validacao humana (documentos juridicos exigem revisao)
    validado_por: Mapped[str | None] = mapped_column(String(128), nullable=True)
    validado_em: Mapped[datetime | None] = mapped_column(nullable=True)
    validacao_notas: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Soft delete (A19)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)

    protocolo: Mapped["Protocolo"] = relationship(back_populates="documentos")  # type: ignore[name-defined]


__all__ = ["Documento", "Base"]
