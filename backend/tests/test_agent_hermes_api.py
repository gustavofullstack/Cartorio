"""Testes unitários e de integração para o router do Agent Hermes (/api/v1/agent-hermes)."""

import pytest
import httpx
import respx
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_agent_hermes_status_endpoint():
    """Testa o endpoint GET /api/v1/agent-hermes/status."""
    response = client.get("/api/v1/agent-hermes/status")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "agent-hermes-cartorio"
    assert data["status"] == "not_deployed"
    assert data["vps_hosted"] is False
    assert data["mcp_tools_available"] == 0


def test_agent_hermes_status_probes_configured_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Só declara Hermes saudável após o health do serviço isolado responder."""
    monkeypatch.setattr(settings, "hermes_api_url", "http://hermes.test:8642")
    monkeypatch.setattr(settings, "hermes_api_server_key", "test-key")
    with respx.mock:
        route = respx.get("http://hermes.test:8642/health").mock(return_value=httpx.Response(200))
        response = client.get("/api/v1/agent-hermes/status")

    assert response.status_code == 200
    assert route.called
    assert response.json()["status"] == "healthy"
    assert response.json()["vps_hosted"] is True


@pytest.mark.asyncio
async def test_agent_hermes_execute_endpoint():
    """Testa a execução de mensagem via POST /api/v1/agent-hermes/execute."""
    payload = {
        "user_message": "Qual é o valor do reconhecimento de firma?",
        "conversation_id": "test_conv_123",
        "channel": "test",
    }
    response = client.post("/api/v1/agent-hermes/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("success", "degraded", "hitl_required")
    assert "answer" in data
    assert data["audit_logged"] is True


def test_agent_hermes_webhook_endpoint():
    """Testa a ingestão de webhook via POST /api/v1/agent-hermes/webhook."""
    response = client.post("/api/v1/agent-hermes/webhook", json={"event": "ping"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
