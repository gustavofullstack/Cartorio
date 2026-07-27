"""Testes unitários e de integração para o router do Agent Hermes (/api/v1/agent-hermes)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_agent_hermes_status_endpoint():
    """Testa o endpoint GET /api/v1/agent-hermes/status."""
    response = client.get("/api/v1/agent-hermes/status")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "agent-hermes-cartorio"
    assert data["status"] == "healthy"
    assert data["vps_hosted"] is True
    assert data["mcp_tools_available"] == 18


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
