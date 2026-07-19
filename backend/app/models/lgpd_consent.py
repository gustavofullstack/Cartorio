"""SQLAlchemy model para LGPD Consent Log (G6.C.T9).

Audit trail de consentimento (LGPD art. 37 - registro de operacoes).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LGPDConsentLog(Base):
    """Audit log de consentimento LGPD do titular."""

    __tablename__ = "lgpd_consent_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    analytics: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    marketing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[str] = mapped_column(String(8), nullable=False, default="v3")
    ip_hash: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    user_agent: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_lgpd_consent_timestamp_version", "timestamp", "version"),
        Index("ix_lgpd_consent_accepted_timestamp", "accepted", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<LGPDConsentLog id={self.id} accepted={self.accepted} version={self.version}>"
