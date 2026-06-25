"""Schemas Pydantic do modulo API (Pydantic v2).

Concentra os contratos de entrada/saida HTTP. Nunca retornar modelos
SQLAlchemy direto no endpoint - sempre mapear pra schema.
"""

# Re-exporta schemas para imports limpos (ex: from app.schemas import AgendamentoCreateRequest)
from app.schemas.agendamento import (
    AgendamentoBase,
    AgendamentoCreateRequest,
    AgendamentoResponse,
)
from app.schemas.audit import (
    AuditLogCreate,
    AuditLogCreatedResponse,
    AuditLogFilter,
    AuditLogListResponse,
    AuditLogResponse,
)
from app.schemas.metrics import MetricsResponse, N8nMetricsIngest, N8nMetricsIngestResponse
from app.schemas.protocolo import (
    CanalOrigem,
    ClienteResumo,
    EtapaHistorico,
    HistoricoEtapa,
    LGPDBlockedResponse,
    ProtocoloApiCreateRequest,
    ProtocoloApiCreateResponse,
    ProtocoloCreateRequest,
    ProtocoloCreateResponse,
    ProtocoloNotFoundResponse,
    ProtocoloResponse,
    StatusProtocolo,
)
