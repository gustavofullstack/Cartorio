"""Regression tests for the API-key boundary on MCP Streamable HTTP."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mcp_server import mcp_app, settings

TEST_MCP_API_KEY = "test-mcp-api-key"
MCP_HEADERS = {
    "accept": "application/json, text/event-stream",
    "content-type": "application/json",
}
INITIALIZE_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "mcp-auth-test", "version": "1.0"},
    },
}


def _post_initialize(client: TestClient, authorization: str | None = None):
    headers = dict(MCP_HEADERS)
    if authorization:
        headers["authorization"] = authorization
    return client.post("/", json=INITIALIZE_REQUEST, headers=headers)


def test_mcp_http_rejects_request_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    with TestClient(mcp_app()) as client:
        response = _post_initialize(client)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_mcp_http_rejects_invalid_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    with TestClient(mcp_app()) as client:
        response = _post_initialize(client, "Bearer wrong-key")

    assert response.status_code == 401


def test_mcp_http_accepts_configured_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    with TestClient(mcp_app()) as client:
        response = _post_initialize(client, f"Bearer {TEST_MCP_API_KEY}")

    assert response.status_code == 200
    assert "cartorio-mcp-cabuloso" in response.text


def test_mcp_http_fails_closed_when_api_key_is_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", None)
    with TestClient(mcp_app()) as client:
        response = _post_initialize(client, "Bearer any-value")

    assert response.status_code == 503
