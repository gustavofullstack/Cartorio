"""Modelo Cliente - NUNCA armazenar CPF/telefone em texto puro, apenas hash."""

from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Cliente(Base, TimestampMixin):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Hash SHA256 do CPF (com salt por cliente). CPF puro NUNCA persiste.
    cpf_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    telefone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # LGPD
    consentimento_lgpd: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consentimento_em: Mapped[datetime | None] = mapped_column(nullable=True)
    consentimento_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    consentimento_canal: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Soft delete pra direito ao esquecimento
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    protocolos: Mapped[list["Protocolo"]] = relationship(back_populates="cliente")  # type: ignore[name-defined]


__all__ = ["Cliente", "Base"]
