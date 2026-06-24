"""OutboxMessage - Dead Letter Queue (DLQ) para integracoes externas.

Usado para armazenar mensagens que NAO puderam ser entregues (ex: WhatsApp
Evolution offline, Chatwoot rate limit, Telegram bot bloqueado). Worker
background (cron) reprocessa periodicamente.

Tabela: outbox_messages
- queue: enum (evolution|chatwoot|telegram|outbox) - cardinalidade limitada (LGPD)
- payload: jsonb - SEMPRE scrubbed antes de armazenar (LGPD-by-design)
- status: enum (pending|processing|done|failed)
- attempts: int - contador de retries
- last_error: text - ultimo erro de processamento
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.models.base import Base


class OutboxQueue(str, enum.Enum):
    """Queue enum (LGPD-safe cardinality)."""

    EVOLUTION = "evolution"
    CHATWOOT = "chatwoot"
    TELEGRAM = "telegram"
    OUTBOX = "outbox"  # generico


class OutboxStatus(str, enum.Enum):
    """Status do processamento."""

    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class OutboxMessage(Base):
    """Mensagem enfileirada para processamento assincrono."""

    __tablename__ = "outbox_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    queue: Mapped[OutboxQueue] = mapped_column(
        SAEnum(OutboxQueue, name="outbox_queue_enum"),
        nullable=False,
        index=True,
    )
    # payload SEMPRE scrubbed (LGPD). JSON type (SQLite+PG compat).
    # Em PG, JSONB eh preferido; SQLAlchemy mapeia JSON -> JSONB se dialect.
    payload: Mapped[dict] = mapped_column(
        # JSON type do SQLAlchemy eh portable: vira JSONB no PG (dialect-aware)
        # e TEXT serializado no SQLite. Alembic nao precisa de batch.
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
    )
    status: Mapped[OutboxStatus] = mapped_column(
        SAEnum(OutboxStatus, name="outbox_status_enum"),
        default=OutboxStatus.PENDING,
        nullable=False,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


__all__ = ["OutboxMessage", "OutboxQueue", "OutboxStatus"]
