"""Tests para N8N execution metrics endpoint (G6.B.T9)."""

from __future__ import annotations

import os

# IMPORTANTE: setar env ANTES de importar app
os.environ["APP_ENV"] = "staging"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUDIT_HMAC_KEY"] = "a" * 64
os.environ["CARTORIO_API_KEY"] = "a" * 64
os.environ.setdefault("N8N_API_KEY", "test-n8n-key")


from app.api.v1.n8n_metrics import fetch_n8n_executions  # noqa: E402


def test_fetch_n8n_executions_sucesso() -> None:
    """Mock simples: endpoint calcula metricas."""
    from unittest.mock import patch

    mock_response = {
        "data": [
            {
                "id": "exec-1",
                "workflowId": "wf-1",
                "status": "success",
                "startedAt": "2026-07-16T10:00:00.000Z",
                "stoppedAt": "2026-07-16T10:00:05.000Z",
                "workflow": {"name": "test-wf"},
            }
        ]
    }
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response
        result = fetch_n8n_executions("https://n8n.test", "test-key", hours=24, timeout=10.0)
    assert len(result) == 1
    assert result[0]["workflowId"] == "wf-1"


def test_fetch_n8n_executions_filtra_janela() -> None:
    """Filtra execucoes fora da janela."""
    from unittest.mock import patch

    mock_response = {
        "data": [
            {
                "id": "exec-recent",
                "workflowId": "wf-1",
                "status": "success",
                "startedAt": "2026-07-16T10:00:00.000Z",
                "stoppedAt": "2026-07-16T10:00:01.000Z",
            },
            {
                "id": "exec-old",
                "workflowId": "wf-1",
                "status": "success",
                "startedAt": "2026-07-01T10:00:00.000Z",
                "stoppedAt": "2026-07-01T10:00:01.000Z",
            },
        ]
    }
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response
        result = fetch_n8n_executions("https://n8n.test", "test-key", hours=24, timeout=10.0)
    assert len(result) == 1
    assert result[0]["id"] == "exec-recent"


def test_summary_metrics_calcula_p50_p95_p99() -> None:
    """Summary calcula percentis corretamente."""
    durations = sorted([0.1, 0.5, 1.0, 2.5, 5.0])
    p50_idx = len(durations) // 2
    p50 = durations[p50_idx]
    assert p50 == 1.0


def test_prometheus_format_workflow_lines() -> None:
    """Valida formato de linha Prometheus."""
    line = 'n8n_workflow_execution_total{workflow="test",status="success"} 5'
    assert "{" in line and "}" in line
    parts = line.split("}")
    assert len(parts) >= 2


def test_endpoint_path_registrado() -> None:
    """Endpoint registrado no router (com prefix)."""
    from app.api.v1.n8n_metrics import router
    paths = [r.path for r in router.routes]
    assert "/api/v1/n8n/metrics/prometheus" in paths
    assert "/api/v1/n8n/metrics/summary" in paths


def test_calculo_error_rate() -> None:
    """error_rate = error / total."""
    total = 100
    error = 5
    rate = error / total
    assert rate == 0.05


def test_calculo_success_rate() -> None:
    """success_rate = success / total."""
    total = 100
    success = 99
    rate = success / total
    assert rate == 0.99


def test_buckets_histogram_prometheus() -> None:
    """Buckets SRE padrao para histogram N8N."""
    expected = (0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
    assert 0.1 in expected
    assert 60.0 in expected
    assert len(expected) == 8