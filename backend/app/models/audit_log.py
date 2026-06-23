"""Modelo AuditLog - append-only com hash chain (tamper-evident).

Cada entrada referencia o hash SHA256 da entrada anterior. Qualquer alteracao
retroativa invalida toda a cadeia a partir do ponto modificado - deteccao
garantida sem dependencia de storage externo.
"""

from datetime import datetime
from sqlalchemy import JSON, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Quem
    actor_id: Mapped[str] = mapped_column(String(128), index=True)
    actor_type: Mapped[str] = mapped_column(String(32), default="user")
    # user, system, bot, escrevente, tabeliao

    # O que
    action: Mapped[str] = mapped_column(String(64), index=True)
    # protocolo.create, protocolo.update, cliente.delete, conversa.handoff, etc
    resource: Mapped[str] = mapped_column(String(128), index=True)
    # "protocolo:12345", "cliente:67890", "documento:abc"

    # Payload completo (estado antes/depois quando aplicavel)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    # Contexto
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    canal: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    # whatsapp, telegram, web, balcao, email, n8n, cron, system

    # Hash chain - imutavel, append-only
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hmac_signature: Mapped[str] = mapped_column(String(128))

    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_audit_resource_action", "resource", "action"),
        Index("ix_audit_actor_action", "actor_id", "action"),
    )


__all__ = ["AuditLog", "Base"]
