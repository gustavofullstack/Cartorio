"""Import centralizado dos modelos."""

from app.models.atendimento import Atendimento
from app.models.audit_log import AuditLog
from app.models.base import Base, TimestampMixin
from app.models.cliente import Cliente
from app.models.conversa import Conversa
from app.models.documento import Documento
from app.models.protocolo import Protocolo

__all__ = [
    "Atendimento",
    "AuditLog",
    "Base",
    "Cliente",
    "Conversa",
    "Documento",
    "Protocolo",
    "TimestampMixin",
]
