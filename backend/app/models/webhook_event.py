"""Modelo WebhookEvent - idempotencia de webhooks externos.

Tabela de deduplicacao. Quando Evolution API ou Chatwoot enviam um evento,
gravamos (source, event_id) aqui antes de processar. Replay (mesmo source+event_id)
retorna 200 sem reprocessar.

LGPD: gravamos apenas o hash SHA256 do payload, nao o payload inteiro
(que pode conter PII do cliente, transcricao de conversa, etc).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("source", "event_id", name="uq_webhook_events_source_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    # "evolution" | "chatwoot"
    event_id: Mapped[str] = mapped_column(String(256), index=True)
    # message_id (evolution) ou event id (chatwoot)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    payload_hash: Mapped[str] = mapped_column(String(64))
    # SHA256 hex do payload original (auditoria, LGPD-safe)
