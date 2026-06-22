"""Modelo Conversa - log de cada interacao do bot (multi-canal)."""

from datetime import datetime
from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Conversa(Base, TimestampMixin):
    __tablename__ = "conversas"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int | None] = mapped_column(
        ForeignKey("clientes.id"), nullable=True, index=True
    )

    canal: Mapped[str] = mapped_column(String(32), index=True)  # whatsapp, telegram, web, email
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    # phone number, chat_id, session_id

    # Conteudo - SEMPRE PII-scrubbed antes de persistir
    raw_message_hash: Mapped[str] = mapped_column(String(64))
    # Guardamos hash + conteudo scrubbed, nao o original
    raw_message_scrubbed: Mapped[str] = mapped_column(Text)

    intent_detected: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # consultar_protocolo, agendar, calcular_emolumento, falar_humano, saudacao, etc

    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    bot_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Handoff (bot nao pode errar -> passa pra humano quando incerto)
    handoff_to_human: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    handoff_at: Mapped[datetime | None] = mapped_column(nullable=True)
    handoff_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    handoff_agent: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # LLM usado
    llm_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    llm_tokens_in: Mapped[int | None] = mapped_column(nullable=True)
    llm_tokens_out: Mapped[int | None] = mapped_column(nullable=True)
    llm_latency_ms: Mapped[int | None] = mapped_column(nullable=True)


__all__ = ["Conversa", "Base"]
