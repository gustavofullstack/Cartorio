"""Schemas Pydantic de metrics.

Usado pelo endpoint GET /api/v1/metrics (JSON estruturado para N8N).

LGPD: este schema NAO expoe PII. Apenas contadores e gauges agregados.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MetricsResponse(BaseModel):
    """Response do GET /api/v1/metrics.

    Shape canonico (Sprint 4 STREAM 1 - 2026-06-24):
    - clientes_total: int - total de clientes ativos
    - protocolos_total: dict[status, int] - count por status (aberto, concluido, etc)
    - audit_chain_length: int - total entries no audit log (LGPD art. 37)
    - uptime_seconds: float - tempo de vida do processo
    - counters: dict - contadores in-process (http_requests_total, pii_blocked_total, etc)
    - gauges: dict - gauges in-process (dlq_depth, cartorio_uptime_seconds, etc)
    """

    clientes_total: int = Field(..., ge=0, description="Total de clientes ativos no DB.")
    protocolos_total: dict[str, int] = Field(
        ..., description="Count de protocolos agrupados por status."
    )
    audit_chain_length: int = Field(
        ..., ge=0, description="Total de entries no audit log (LGPD art. 37)."
    )
    uptime_seconds: float = Field(
        ..., ge=0.0, description="Tempo de vida do processo backend em segundos."
    )
    counters: dict[str, Any] = Field(
        default_factory=dict,
        description="Contadores in-process (http_requests_total, pii_blocked_total).",
    )
    gauges: dict[str, Any] = Field(
        default_factory=dict,
        description="Gauges in-process (dlq_depth, cartorio_uptime_seconds).",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "clientes_total": 42,
                "protocolos_total": {"aberto": 5, "concluido": 12},
                "audit_chain_length": 1847,
                "uptime_seconds": 3600.5,
                "counters": {
                    "cartorio_http_requests_total": {
                        "endpoint=/api/v1/protocolo/{numero}|method=GET|status=200": 142
                    }
                },
                "gauges": {"dlq_depth": {"queue=evolution": 0}},
            }
        }
    }
