"""Modelo Cliente - NUNCA armazenar CPF/telefone em texto puro, apenas hash."""

import enum
from datetime import datetime
from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MotivoEncerramento(str, enum.Enum):
    """LGPD art. 18 VI + D4 (retenção cartoraria).

    Define o motivo do encerramento do tratamento de dados do cliente.
    Usado em `cliente.motivo_encerramento` (soft delete / revogação).
    """

    REVOGACAO_CONSENTIMENTO = "revogacao_consentimento"  # LGPD art. 18 VI
    RETENCAO_5Y = "retencao_5y"  # Provimento CNJ 74/2018 (cliente COM protocolo)
    EXERCICIO_DIREITO_TITULAR = "exercicio_direito_titular"  # LGPD art. 18 (outros)
    OUTROS = "outros"


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

    # Soft delete (LGPD art. 18 VI + D4)
    # Soft quando cliente tem protocolo; hard quando nao tem (ver ADR-018).
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    motivo_encerramento: Mapped[MotivoEncerramento | None] = mapped_column(
        SAEnum(MotivoEncerramento, name="motivo_encerramento_enum"),
        nullable=True,
    )
    # Audit chain: ID da entry do audit log que documentou o encerramento.
    # NULL = nunca encerrado. Garante rastreabilidade da decisao.
    audit_encerramento_id: Mapped[int | None] = mapped_column(
        ForeignKey("audit_log.id", use_alter=True, ondelete="SET NULL"),
        nullable=True,
    )

    protocolos: Mapped[list["Protocolo"]] = relationship(back_populates="cliente")  # type: ignore[name-defined]


__all__ = ["Cliente", "Base", "MotivoEncerramento"]
