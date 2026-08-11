"""Vinculo pseudonimo entre cliente e identidade operacional de canal.

O identificador original (telefone, JID ou chat id) nunca e persistido. A
tabela existe para permitir retencao e eliminacao LGPD deterministicas dos
stores Redis que usam pseudonimos HMAC.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ClienteChannelIdentity(Base, TimestampMixin):
    """Binding pseudonimo-only de um cliente para um canal."""

    __tablename__ = "cliente_channel_identities"
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "conversation_pseudonym",
            name="uq_cliente_channel_identity_channel_pseudonym",
        ),
        CheckConstraint(
            "length(conversation_pseudonym) = 64",
            name="ck_cliente_channel_identity_pseudonym_length",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    conversation_pseudonym: Mapped[str] = mapped_column(String(64), nullable=False)
    hmac_kid: Mapped[str] = mapped_column(String(64), nullable=False)


__all__ = ["ClienteChannelIdentity"]
