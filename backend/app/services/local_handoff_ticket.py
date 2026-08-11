"""Ticket local fail-closed para pedidos que exigem um escrevente.

Nao existe chamada a Chatwoot, N8N ou agenda neste modulo. O ticket so e
considerado criado quando a linha local e a entrada da cadeia de auditoria
foram persistidas na mesma sessao.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.db import session_scope
from app.models.atendimento import Atendimento
from app.services.audit import AuditService


@dataclass(frozen=True, slots=True)
class LocalHandoffTicket:
    """Identificacao nao sensivel do ticket confirmado no banco local."""

    atendimento_id: int
    status: str


def pseudonymize_external_id(
    channel: str,
    external_id: str,
    *,
    hmac_key: str | None = None,
) -> str:
    """Substitui o identificador bruto por HMAC com separacao de dominio."""

    from app.services.chat_pipeline import Channel, pseudonymize_conversation_id

    normalized_channel = channel.strip().lower()
    normalized_external_id = external_id.strip()
    if not normalized_channel or not normalized_external_id:
        raise ValueError("channel and external_id are required")
    key = hmac_key if hmac_key is not None else settings.pietra_conversation_hmac_key
    conversation_pseudonym = pseudonymize_conversation_id(
        Channel(normalized_channel),
        normalized_external_id,
        hmac_key=key,
    )
    return f"hmac:v1:{conversation_pseudonym}"


def create_local_handoff_ticket(
    *,
    channel: str,
    external_id: str,
    action: str,
    request_id: str | None = None,
) -> LocalHandoffTicket:
    """Persiste ticket e audit; qualquer falha invalida o resultado inteiro."""

    normalized_action = action.strip().lower()
    if normalized_action not in {"humano", "agendar"}:
        raise ValueError("unsupported local handoff action")

    pseudonymous_id = pseudonymize_external_id(channel, external_id)
    ticket_type = "agendamento" if normalized_action == "agendar" else "duvida"
    status = "aguardando_escrevente"

    with session_scope() as db:
        ticket = Atendimento(
            canal=channel,
            external_id=pseudonymous_id,
            tipo=ticket_type,
            contexto_scrubbed="Pedido registrado pelo fail-safe do canal.",
            status=status,
            handoff_para_humano=True,
        )
        db.add(ticket)
        db.flush()
        if ticket.id is None:
            raise RuntimeError("local handoff ticket did not receive an ID")

        audit_entry = AuditService.log(
            db,
            actor_id=f"pietra:{channel}",
            actor_type="bot",
            action="atendimento.create.local_failsafe",
            resource=f"atendimento:{ticket.id}",
            payload={
                "canal": channel,
                "tipo": ticket_type,
                "status": status,
                "external_id_pseudonymized": True,
                "chatwoot_dispatched": False,
                "n8n_dispatched": False,
            },
            request_id=request_id,
            canal=channel,
        )
        if audit_entry.id is None:
            raise RuntimeError("local handoff audit did not receive an ID")
        ticket_id = ticket.id

    return LocalHandoffTicket(atendimento_id=ticket_id, status=status)
