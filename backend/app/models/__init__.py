"""Import centralizado dos modelos."""

from app.models.agendamento import Agendamento, StatusAgendamento, TipoAtendimento
from app.models.atendimento import Atendimento
from app.models.audit_log import AuditLog
from app.models.base import Base, TimestampMixin
from app.models.cliente import Cliente, MotivoEncerramento
from app.models.conversa import Conversa
from app.models.documento import Documento
from app.models.outbox_message import OutboxMessage
from app.models.protocolo import Protocolo
from app.models.webhook_event import WebhookEvent

__all__ = [
    "Agendamento",
    "Atendimento",
    "AuditLog",
    "Base",
    "Cliente",
    "Conversa",
    "Documento",
    "MotivoEncerramento",
    "OutboxMessage",
    "Protocolo",
    "StatusAgendamento",
    "TimestampMixin",
    "TipoAtendimento",
    "WebhookEvent",
]
