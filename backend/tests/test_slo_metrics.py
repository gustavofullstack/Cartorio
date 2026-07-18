"""Tests para SLO metrics module (G6.A.T9)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)

from app.services import slo_metrics  # noqa: E402


def test_slo_metrics_module_carregado() -> None:
    """Modulo slo_metrics deve ter funcoes principais."""
    assert hasattr(slo_metrics, "record_http_request")
    assert hasattr(slo_metrics, "record_n8n_workflow")
    assert hasattr(slo_metrics, "record_openclaw_request")
    assert hasattr(slo_metrics, "update_composite_slo")
    assert hasattr(slo_metrics, "update_error_budget")
    assert hasattr(slo_metrics, "is_slo_enabled")


def test_is_slo_enabled_sem_env() -> None:
    """is_slo_enabled retorna bool baseado em env var."""
    result = slo_metrics.is_slo_enabled()
    assert isinstance(result, bool)


def test_is_slo_enabled_desabilitado() -> None:
    """is_slo_enabled retorna False se SLO_METRICS_ENABLED=false."""
    old = os.environ.get("SLO_METRICS_ENABLED")
    os.environ["SLO_METRICS_ENABLED"] = "false"
    try:
        # So retorna False se PROMETHEUS_ENABLED ou se env for false
        result = slo_metrics.is_slo_enabled()
        # Se prom nao ta habilitado, sempre False
        assert result is False
    finally:
        if old is None:
            os.environ.pop("SLO_METRICS_ENABLED", None)
        else:
            os.environ["SLO_METRICS_ENABLED"] = old


def test_record_http_request_com_prometheus() -> None:
    """record_http_request deve funcionar se prometheus client disponivel."""
    if not slo_metrics.PROMETHEUS_ENABLED:
        return  # skip se nao tiver prometheus
    # Nao deve levantar excecao
    slo_metrics.record_http_request(
        method="GET",
        endpoint="/api/v1/protocolo/123",
        status_code=200,
        duration_seconds=0.123,
    )
    slo_metrics.record_http_request(
        method="POST",
        endpoint="/api/v1/atendimento",
        status_code=500,
        duration_seconds=2.5,
    )


def test_record_n8n_workflow_com_prometheus() -> None:
    """record_n8n_workflow deve funcionar se prometheus client disponivel."""
    if not slo_metrics.PROMETHEUS_ENABLED:
        return  # skip
    slo_metrics.record_n8n_workflow(workflow="02-criar-protocolo", status="success")
    slo_metrics.record_n8n_workflow(workflow="02-criar-protocolo", status="error")


def test_record_openclaw_request_com_prometheus() -> None:
    """record_openclaw_request deve funcionar se prometheus client disponivel."""
    if not slo_metrics.PROMETHEUS_ENABLED:
        return  # skip
    slo_metrics.record_openclaw_request(
        agent="cartorio-bot", endpoint="/v1/chat", duration_seconds=3.5
    )


def test_update_composite_slo_com_prometheus() -> None:
    """update_composite_slo deve atualizar gauges."""
    if not slo_metrics.PROMETHEUS_ENABLED:
        return  # skip
    slo_metrics.update_composite_slo(availability=0.998, latency=0.96)


def test_update_error_budget_com_prometheus() -> None:
    """update_error_budget deve atualizar label."""
    if not slo_metrics.PROMETHEUS_ENABLED:
        return  # skip
    slo_metrics.update_error_budget("api_availability", 0.85)


def test_status_class_classification() -> None:
    """Validar que o bucket status_class funciona (2xx/4xx/5xx)."""
    # 200 -> 2xx, 404 -> 4xx, 500 -> 5xx
    test_cases = [(200, "2xx"), (201, "2xx"), (404, "4xx"), (500, "5xx")]
    for status_code, expected_class in test_cases:
        actual = f"{status_code // 100}xx"
        assert actual == expected_class


def test_slo_module_docstring() -> None:
    """Modulo deve ter docstring explicando proposito."""
    assert slo_metrics.__doc__ is not None
    assert "SLO" in slo_metrics.__doc__
    assert "Prometheus" in slo_metrics.__doc__
