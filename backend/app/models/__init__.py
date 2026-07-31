"""Import centralizado dos modelos."""

from app.models.agendamento import Agendamento, StatusAgendamento, TipoAtendimento
from app.models.atendimento import Atendimento
from app.models.audit_log import AuditLog
from app.models.base import Base, TimestampMixin
from app.models.cliente import Cliente, MotivoEncerramento
from app.models.cnj_export_request import CNJExportRequest
from app.models.conhecimento_institucional import (
    DecisaoValidacao,
    DecisaoValidacaoConhecimento,
    EstadoConhecimento,
    FatoConhecimento,
    FonteConhecimento,
    PublicacaoConhecimento,
    RegraCalculoConhecimento,
    ResultadoClassificacaoConhecimento,
    TipoDocumentoConhecimento,
    UnidadeConhecimento,
    VersaoConhecimento,
)
from app.models.conversa import Conversa
from app.models.documento import Documento
from app.models.emolumento_catalogo import EmolumentoItem, EstadoEmolumento, FonteCaptura
from app.models.outbox_message import OutboxMessage
from app.models.protocolo import Protocolo
from app.models.webhook_event import WebhookEvent

__all__ = [
    "Agendamento",
    "Atendimento",
    "AuditLog",
    "Base",
    "Cliente",
    "CNJExportRequest",
    "Conversa",
    "DecisaoValidacao",
    "DecisaoValidacaoConhecimento",
    "Documento",
    "EmolumentoItem",
    "EstadoConhecimento",
    "EstadoEmolumento",
    "FatoConhecimento",
    "FonteCaptura",
    "FonteConhecimento",
    "MotivoEncerramento",
    "OutboxMessage",
    "Protocolo",
    "PublicacaoConhecimento",
    "RegraCalculoConhecimento",
    "ResultadoClassificacaoConhecimento",
    "StatusAgendamento",
    "TimestampMixin",
    "TipoAtendimento",
    "TipoDocumentoConhecimento",
    "UnidadeConhecimento",
    "VersaoConhecimento",
    "WebhookEvent",
]
