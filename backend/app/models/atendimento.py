"""Modelo Atendimento - registro de atendimento humano (via Chatwoot handoff).

Quando o bot faz handoff para humano (workflow #03), o atendimento e
registrado aqui com referencia ao Chatwoot conversation_id. Usado pelo
workflow #07 (Pesquisa Satisfacao 24h) para enviar follow-up.
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Atendimento(Base, TimestampMixin):
    __tablename__ = "atendimentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    protocolo_id: Mapped[int | None] = mapped_column(
        ForeignKey("protocolos.id"), nullable=True, index=True
    )
    cliente_id: Mapped[int | None] = mapped_column(
        ForeignKey("clientes.id"), nullable=True, index=True
    )

    # Origem do atendimento
    canal: Mapped[str] = mapped_column(String(32), index=True)
    # whatsapp, telegram, web, presencial
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    # numero do whatsapp, telegram chat_id, etc

    # Chatwoot (CRM)
    chatwoot_conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chatwoot_inbox_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chatwoot_agent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status e tipo
    status: Mapped[str] = mapped_column(String(32), default="aberto", index=True)
    # aberto, em_atendimento, aguardando_cliente, concluido, cancelado
    tipo: Mapped[str] = mapped_column(String(64))
    # consulta_emolumento, criar_protocolo, 2a_via, agendamento, duvida, reclamacao

    # Contexto (LGPD-safe)
    contexto_scrubbed: Mapped[str | None] = mapped_column(Text, nullable=True)
    # versao com PII removida do contexto da conversa

    # Pesquisa de satisfacao (workflow #07)
    pesquisa_enviada_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pesquisa_nota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pesquisa_comentario: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps de ciclo
    iniciado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    handoff_para_humano: Mapped[bool] = mapped_column(Boolean, default=False)
