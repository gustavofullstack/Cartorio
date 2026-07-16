"""SLO metrics module (G6.A.T9).

Metricas Prometheus especificas para SLO (Service Level Objectives):
- http_request_duration_seconds (histogram, usado pelo SLO API Latency)
- http_requests_total (counter, usado pelo SLO API Availability)
- n8n_workflow_execution_status (counter, usado pelo SLO N8N Success)
- openclaw_request_duration_seconds (histogram, usado pelo SLO OpenClaw Response)

Buckets seguem convencao Google SRE para latencia HTTP.

Refs:
- infra/prometheus/slo_rules.yml (12 SLO rules)
- https://sre.google/workbook/implementing-slos/

Modified by Gustavo Almeida + cartorio-sre — G6 wave 19.
"""
from __future__ import annotations

import os
from typing import Literal

# Lazy import: prometheus_client pode nao estar em dev
try:
    from prometheus_client import Counter, Gauge, Histogram  # type: ignore[import-not-found]

    PROMETHEUS_ENABLED = True
except ImportError:
    PROMETHEUS_ENABLED = False
    # Stubs no-op para dev sem prometheus
    Counter = Gauge = Histogram = None  # type: ignore[assignment]

# ============================================================================
# SLO API Availability + Latency
# ============================================================================

if PROMETHEUS_ENABLED:
    http_requests_total = Counter(
        "http_requests_total",
        "Total HTTP requests received by API",
        labelnames=["method", "endpoint", "status_class"],
    )

    # Buckets Google SRE: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10
    http_request_duration_seconds = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        labelnames=["method", "endpoint"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    # ============================================================================
    # SLO N8N Workflow Success
    # ============================================================================

    n8n_workflow_execution_status = Counter(
        "n8n_workflow_execution_status",
        "N8N workflow execution by status (success/error)",
        labelnames=["workflow", "status"],
    )

    # ============================================================================
    # SLO OpenClaw Agent Response
    # ============================================================================

    openclaw_request_duration_seconds = Histogram(
        "openclaw_request_duration_seconds",
        "OpenClaw agent response duration in seconds",
        labelnames=["agent", "endpoint"],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    )

    # ============================================================================
    # Composite (compilado por N8N WFs que scrape-iam e enviam pro Prom)
    # ============================================================================

    slo_composite_availability = Gauge(
        "slo_composite_cartorio_availability_30d",
        "Composite SLO availability (API + N8N) 30d ratio",
    )

    slo_composite_latency = Gauge(
        "slo_composite_cartorio_latency_30d",
        "Composite SLO latency (API + OpenClaw) 30d ratio",
    )

    # ============================================================================
    # Budget burn (error budget remaining)
    # ============================================================================

    slo_error_budget_remaining = Gauge(
        "slo_error_budget_remaining_30d",
        "Error budget remaining per SLO (0-1, 1=100% budget intact)",
        labelnames=["slo_name"],
    )


def record_http_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Registra 1 HTTP request nos metrics SLO.

    Args:
        method: GET/POST/PUT/DELETE
        endpoint: rota (ex: /api/v1/protocolo)
        status_code: HTTP status code (200, 404, 500, ...)
        duration_seconds: latencia em segundos
    """
    if not PROMETHEUS_ENABLED:
        return
    status_class = f"{status_code // 100}xx"
    http_requests_total.labels(method=method, endpoint=endpoint, status_class=status_class).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration_seconds)


def record_n8n_workflow(workflow: str, status: Literal["success", "error"]) -> None:
    """Registra 1 execucao de N8N workflow."""
    if not PROMETHEUS_ENABLED:
        return
    n8n_workflow_execution_status.labels(workflow=workflow, status=status).inc()


def record_openclaw_request(agent: str, endpoint: str, duration_seconds: float) -> None:
    """Registra 1 request OpenClaw agent."""
    if not PROMETHEUS_ENABLED:
        return
    openclaw_request_duration_seconds.labels(agent=agent, endpoint=endpoint).observe(duration_seconds)


def update_composite_slo(availability: float, latency: float) -> None:
    """Atualiza gauges composite SLO (calculado por job externo)."""
    if not PROMETHEUS_ENABLED:
        return
    slo_composite_availability.set(availability)
    slo_composite_latency.set(latency)


def update_error_budget(slo_name: str, budget_remaining: float) -> None:
    """Atualiza error budget remaining (0-1)."""
    if not PROMETHEUS_ENABLED:
        return
    slo_error_budget_remaining.labels(slo_name=slo_name).set(budget_remaining)


def is_slo_enabled() -> bool:
    """Retorna se SLO metrics estao habilitados (env var + lib disponivel)."""
    return PROMETHEUS_ENABLED and os.environ.get("SLO_METRICS_ENABLED", "true").lower() != "false"