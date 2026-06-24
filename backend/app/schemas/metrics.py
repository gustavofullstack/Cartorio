"""Schemas Pydantic de metrics.

Usado pelos endpoints:
- GET /api/v1/metrics (JSON estruturado para N8N)
- POST /api/v1/metrics/n8n (B0.1 - ingestao de metrics do N8N workflow #25)

LGPD: este schema NAO expoe PII. Apenas contadores e gauges agregados.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ConfigDict


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


class N8nMetricsIngest(BaseModel):
    """Payload aceito pelo POST /api/v1/metrics/n8n.

    Workflow N8N #25 (metrics-collector) faz GET /api/v1/metrics/prometheus
    a cada 1min e POSTa o body (JSON.stringify do $json) aqui. Para evitar
    quebrar o workflow ja em producao, o schema aceita formato FLEXIVEL:

    - shape canonico (dict com chaves `counters`/`gauges`/`uptime_seconds`):
      cada counter vira inc_counter no MetricsStore com label `source=n8n`
      para distinguir de metrics internas. Gauges idem.
    - shape Prometheus raw (string text/plain): parseado linha-a-linha.
    - qualquer outro shape: aceito, mas logado como `n8n_metrics_received`
      com `payload_kind=unknown` para investigacao posterior.

    LGPD: nao expoe PII. Soh agregados (uptime, memory counters, etc).

    Referencia: Sprint 3 B0.1 (PLAN_GIGANTE_2026-06-24.md) - corrige erro
    recorrente workflow 25 (1 erro/min - 404 Not Found).
    """

    # Campos canonicos (todos opcionais - payload flexivel)
    counters: dict[str, dict[str, int]] | None = Field(
        default=None,
        description="Contadores N8N no formato {metric_name: {labels_key: int}}.",
    )
    gauges: dict[str, Any] | None = Field(
        default=None,
        description="Gauges N8N (suporta escalar E dict com labels).",
    )
    uptime_seconds: float | None = Field(
        default=None,
        ge=0.0,
        description="Uptime do processo N8N em segundos.",
    )
    workflows_active: int | None = Field(
        default=None,
        ge=0,
        description="Numero de workflows ativos reportados pelo N8N.",
    )
    memory_rss_mb: float | None = Field(
        default=None,
        ge=0.0,
        description="Memoria RSS do processo N8N em MB.",
    )
    timestamp: str | None = Field(
        default=None,
        description="ISO 8601 timestamp do momento da coleta (N8N side).",
    )

    # Fallback: payload cru (string Prometheus ou JSON.stringify de algo)
    raw: str | dict[str, Any] | None = Field(
        default=None,
        description="Payload cru aceito quando shape canonico nao bate.",
    )

    model_config = ConfigDict(extra="allow")  # aceita campos extras sem erro


class N8nMetricsIngestResponse(BaseModel):
    """Response do POST /api/v1/metrics/n8n.

    Confirma recebimento + reporta o que foi processado (counts, gauges,
    payload_kind) para o workflow #25 ter visibilidade do que aconteceu.
    """

    received: bool = Field(default=True, description="True se aceito (sempre 200).")
    payload_kind: str = Field(
        ...,
        description="Shape detectado: 'canonical' | 'prometheus_raw' | 'unknown'.",
    )
    counters_ingested: int = Field(
        default=0,
        ge=0,
        description="Numero de counters efetivamente registrados no MetricsStore.",
    )
    gauges_ingested: int = Field(
        default=0,
        ge=0,
        description="Numero de gauges efetivamente registrados no MetricsStore.",
    )
    metrics_size_bytes: int = Field(
        default=0,
        ge=0,
        description="Tamanho do payload recebido em bytes (auditoria).",
    )
    audit_action: str = Field(
        default="metrics.n8n_received",
        description="Action registrada no audit_log (LGPD art. 37).",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "received": True,
                "payload_kind": "canonical",
                "counters_ingested": 3,
                "gauges_ingested": 2,
                "metrics_size_bytes": 412,
                "audit_action": "metrics.n8n_received",
            }
        }
    }
