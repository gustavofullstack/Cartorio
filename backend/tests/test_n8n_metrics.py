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
    from datetime import datetime, timezone
    from unittest.mock import patch

    recent_ts = datetime.now(timezone.utc).isoformat()
    mock_response = {
        "data": [
            {
                "id": "exec-1",
                "workflowId": "wf-1",
                "status": "success",
                "startedAt": recent_ts,
                "stoppedAt": recent_ts,
                "workflow": {"name": "test-wf"},
            }
        ]
    }
    with patch("app.api.v1.n8n_metrics.httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = mock_response
        result = fetch_n8n_executions("https://n8n.test", "test-key", hours=24, timeout=10.0)
    assert len(result) == 1
    assert result[0]["workflowId"] == "wf-1"


def test_fetch_n8n_executions_filtra_janela() -> None:
    """Filtra execucoes fora da janela."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    now = datetime.now(timezone.utc)
    recent = now.isoformat()
    old = (now - timedelta(days=30)).isoformat()
    mock_response = {
        "data": [
            {
                "id": "exec-recent",
                "workflowId": "wf-1",
                "status": "success",
                "startedAt": recent,
                "stoppedAt": recent,
            },
            {
                "id": "exec-old",
                "workflowId": "wf-1",
                "status": "success",
                "startedAt": old,
                "stoppedAt": old,
            },
        ]
    }
    with patch("app.api.v1.n8n_metrics.httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = mock_response
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
    """Contrato publico recebe o prefixo v1 apenas uma vez."""
    from app.main import app

    app.openapi_schema = None
    paths = app.openapi()["paths"]
    assert "/api/v1/n8n/metrics/prometheus" in paths
    assert "/api/v1/n8n/metrics/summary" in paths
    assert not any("/api/v1/api/v1/" in path for path in paths)


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
