"""Regression tests for the API-key boundary on MCP Streamable HTTP."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mcp_server import mcp_app, settings

TEST_MCP_API_KEY = "test-mcp-api-key"
TEST_MCP_PUBLIC_API_KEY = "test-mcp-public-api-key"
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


def _mcp_headers(authorization: str, session_id: str | None = None) -> dict[str, str]:
    headers = {**MCP_HEADERS, "authorization": authorization}
    if session_id:
        headers["mcp-session-id"] = session_id
    return headers


def _tool_names(response_text: str) -> set[str]:
    import json

    payload = response_text.split("data: ", maxsplit=1)[1].split("\n", maxsplit=1)[0]
    tools = json.loads(payload)["result"]["tools"]
    return {tool["name"] for tool in tools}


def _initialize_public_session(client: TestClient) -> dict[str, str]:
    response = _post_initialize(client, f"Bearer {TEST_MCP_PUBLIC_API_KEY}")
    assert response.status_code == 200
    return _mcp_headers(f"Bearer {TEST_MCP_PUBLIC_API_KEY}", response.headers["mcp-session-id"])


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


def test_mcp_public_profile_lists_only_emolumento_tool(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    monkeypatch.setattr(settings, "mcp_public_api_key", TEST_MCP_PUBLIC_API_KEY)
    with TestClient(mcp_app()) as client:
        headers = _initialize_public_session(client)
        response = client.post(
            "/",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers=headers,
        )

    assert response.status_code == 200
    assert _tool_names(response.text) == {"cartorio_calcular_emolumento"}


def test_mcp_public_profile_rejects_non_allowlisted_tool_call(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    monkeypatch.setattr(settings, "mcp_public_api_key", TEST_MCP_PUBLIC_API_KEY)
    with TestClient(mcp_app()) as client:
        headers = _initialize_public_session(client)
        response = client.post(
            "/",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "cartorio_consultar_protocolo", "arguments": {}},
            },
            headers=headers,
        )

    assert response.status_code == 403


def test_mcp_public_profile_allows_only_emolumento_tool_call(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    monkeypatch.setattr(settings, "mcp_public_api_key", TEST_MCP_PUBLIC_API_KEY)
    with TestClient(mcp_app()) as client:
        headers = _initialize_public_session(client)
        response = client.post(
            "/",
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "cartorio_calcular_emolumento",
                    "arguments": {"tipo": "procuracao"},
                },
            },
            headers=headers,
        )

    assert response.status_code == 200
    assert "cartorio_calcular_emolumento" not in response.text


def test_mcp_public_profile_accepts_only_well_formed_bearer_credential(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    monkeypatch.setattr(settings, "mcp_public_api_key", TEST_MCP_PUBLIC_API_KEY)
    with TestClient(mcp_app()) as client:
        malformed = _post_initialize(client, f"Bearer  {TEST_MCP_PUBLIC_API_KEY}")
        wrong_scheme = _post_initialize(client, f"Basic {TEST_MCP_PUBLIC_API_KEY}")

    assert malformed.status_code == 401
    assert wrong_scheme.status_code == 401


def test_mcp_public_profile_rejects_reused_internal_credential(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    monkeypatch.setattr(settings, "mcp_public_api_key", TEST_MCP_API_KEY)
    with TestClient(mcp_app()) as client:
        response = _post_initialize(client, f"Bearer {TEST_MCP_API_KEY}")

    assert response.status_code == 401
