"""Regression tests for the API-key boundary on MCP Streamable HTTP."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.middleware.mcp_api_key import MCPApiKeyMiddleware
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
    payload = response_text.split("data: ", maxsplit=1)[1].split("\n", maxsplit=1)[0]
    tools = json.loads(payload)["result"]["tools"]
    return {tool["name"] for tool in tools}


def _initialize_public_session(client: TestClient) -> dict[str, str]:
    response = _post_initialize(client, f"Bearer {TEST_MCP_PUBLIC_API_KEY}")
    assert response.status_code == 200
    return _mcp_headers(f"Bearer {TEST_MCP_PUBLIC_API_KEY}", response.headers["mcp-session-id"])


def _initialize_internal_session(client: TestClient) -> dict[str, str]:
    response = _post_initialize(client, f"Bearer {TEST_MCP_API_KEY}")
    assert response.status_code == 200
    return _mcp_headers(f"Bearer {TEST_MCP_API_KEY}", response.headers["mcp-session-id"])


def _public_tool_call(headers: dict[str, str], tipo: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "cartorio_calcular_emolumento",
            "arguments": {"tipo": tipo},
        },
    }


def _invoke_public_middleware(
    headers: list[tuple[bytes, bytes]],
    messages: list[dict[str, Any]],
    *,
    maximum_body_bytes: int = 16,
    consume_replayed_body: bool = False,
) -> tuple[bool, list[dict[str, Any]], bytes]:
    pending_messages = list(messages)
    sent_messages: list[dict[str, Any]] = []
    public_app_called = False
    replayed_body = b""

    async def receive() -> dict[str, Any]:
        return pending_messages.pop(0)

    async def send(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    async def app(scope: dict[str, Any], receive_fn: Any, send_fn: Any) -> None:
        nonlocal public_app_called, replayed_body
        public_app_called = True
        if consume_replayed_body:
            replayed_body = (await receive_fn()).get("body", b"")

    middleware = MCPApiKeyMiddleware(
        app,
        api_key=TEST_MCP_API_KEY,
        public_api_key=TEST_MCP_PUBLIC_API_KEY,
        public_app=app,
        public_max_body_bytes=maximum_body_bytes,
    )
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    asyncio.run(middleware(scope, receive, send))

    return public_app_called, sent_messages, replayed_body


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
                "params": _public_tool_call(headers, "procuracao_geral")["params"],
            },
            headers=headers,
        )

    assert response.status_code == 200
    assert "cartorio_calcular_emolumento" not in response.text


def test_mcp_internal_profile_preserves_legacy_emolumento_alias(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    monkeypatch.setattr(settings, "mcp_public_api_key", TEST_MCP_PUBLIC_API_KEY)
    with TestClient(mcp_app()) as client:
        headers = _initialize_internal_session(client)
        response = client.post("/", json=_public_tool_call(headers, "procuracao"), headers=headers)

    assert response.status_code == 200


def test_mcp_public_profile_rejects_noncanonical_or_pii_tipo_without_echo(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    monkeypatch.setattr(settings, "mcp_public_api_key", TEST_MCP_PUBLIC_API_KEY)
    invalid_types = (
        "procuracao",
        "529.982.247-25",
        "+55 34 99999-1234",
        "cliente@example.com",
        "Ana São\u200bJosé",
    )
    with TestClient(mcp_app()) as client:
        headers = _initialize_public_session(client)
        for invalid_tipo in invalid_types:
            response = client.post(
                "/", json=_public_tool_call(headers, invalid_tipo), headers=headers
            )
            assert response.status_code == 200
            assert "INVALID_EMOLUMENTO_TYPE" in response.text
            assert invalid_tipo not in response.text


def test_mcp_public_profile_rejects_batch_notification_and_alternate_path(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    monkeypatch.setattr(settings, "mcp_public_api_key", TEST_MCP_PUBLIC_API_KEY)
    with TestClient(mcp_app()) as client:
        headers = _initialize_public_session(client)
        batch = client.post(
            "/", json=[_public_tool_call(headers, "procuracao_geral")], headers=headers
        )
        notification = client.post(
            "/",
            json={"jsonrpc": "2.0", "method": "notifications/tools/list_changed"},
            headers=headers,
        )
        alternate_path = client.post(
            "/alternative",
            json={
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "cartorio_consultar_protocolo", "arguments": {}},
            },
            headers=headers,
        )

    assert batch.status_code == 403
    assert notification.status_code == 403
    assert alternate_path.status_code == 403


def test_mcp_public_session_does_not_upgrade_to_internal_profile(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    monkeypatch.setattr(settings, "mcp_public_api_key", TEST_MCP_PUBLIC_API_KEY)
    with TestClient(mcp_app()) as client:
        public_headers = _initialize_public_session(client)
        internal_headers = _mcp_headers(
            f"Bearer {TEST_MCP_API_KEY}", public_headers["mcp-session-id"]
        )
        response = client.post(
            "/",
            json={"jsonrpc": "2.0", "id": 6, "method": "tools/list", "params": {}},
            headers=internal_headers,
        )

    assert response.status_code != 200
    assert "cartorio_consultar_protocolo" not in response.text


def test_mcp_public_profile_rejects_oversized_content_length_before_json_parse(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_api_key", TEST_MCP_API_KEY)
    monkeypatch.setattr(settings, "mcp_public_api_key", TEST_MCP_PUBLIC_API_KEY)
    monkeypatch.setattr(settings, "mcp_public_max_body_bytes", 1024)
    payload = {"jsonrpc": "2.0", "id": 7, "method": "tools/list", "params": {"padding": "x" * 2048}}
    with TestClient(mcp_app()) as client:
        response = client.post(
            "/", json=payload, headers=_mcp_headers(f"Bearer {TEST_MCP_PUBLIC_API_KEY}")
        )

    assert response.status_code == 413


def test_mcp_public_profile_rejects_chunked_oversized_body_without_content_length() -> None:
    public_app_called, sent_messages, _ = _invoke_public_middleware(
        [
            (b"authorization", f"Bearer {TEST_MCP_PUBLIC_API_KEY}".encode()),
            (b"transfer-encoding", b"chunked"),
        ],
        [
            {"type": "http.request", "body": b"{" * 9, "more_body": True},
            {"type": "http.request", "body": b"}" * 9, "more_body": False},
        ],
    )

    assert not public_app_called
    assert sent_messages[0]["status"] == 413


@pytest.mark.parametrize(
    "headers",
    [
        [
            (b"authorization", f"Bearer {TEST_MCP_PUBLIC_API_KEY}".encode()),
            (b"content-length", b"5"),
            (b"content-length", b"5"),
        ],
        [
            (b"content-length", b"5"),
            (b"authorization", f"Bearer {TEST_MCP_PUBLIC_API_KEY}".encode()),
            (b"content-length", b"5"),
        ],
    ],
)
def test_mcp_public_profile_rejects_duplicate_content_length_in_any_order(
    headers: list[tuple[bytes, bytes]],
) -> None:
    public_app_called, sent_messages, _ = _invoke_public_middleware(headers, [])

    assert not public_app_called
    assert sent_messages[0]["status"] == 400


@pytest.mark.parametrize("content_length", [b"-1", b"16 ", b"12\xb2"])
def test_mcp_public_profile_rejects_non_decimal_content_length(content_length: bytes) -> None:
    public_app_called, sent_messages, _ = _invoke_public_middleware(
        [
            (b"authorization", f"Bearer {TEST_MCP_PUBLIC_API_KEY}".encode()),
            (b"content-length", content_length),
        ],
        [],
    )

    assert not public_app_called
    assert sent_messages[0]["status"] == 400


def test_mcp_public_profile_rejects_transfer_encoding_with_content_length() -> None:
    public_app_called, sent_messages, _ = _invoke_public_middleware(
        [
            (b"authorization", f"Bearer {TEST_MCP_PUBLIC_API_KEY}".encode()),
            (b"transfer-encoding", b"chunked"),
            (b"content-length", b"10"),
        ],
        [],
    )

    assert not public_app_called
    assert sent_messages[0]["status"] == 400


@pytest.mark.parametrize("transfer_encoding", [b"gzip", b"chunked, gzip", b"identity"])
def test_mcp_public_profile_rejects_unsupported_transfer_encoding(transfer_encoding: bytes) -> None:
    public_app_called, sent_messages, _ = _invoke_public_middleware(
        [
            (b"authorization", f"Bearer {TEST_MCP_PUBLIC_API_KEY}".encode()),
            (b"transfer-encoding", transfer_encoding),
        ],
        [],
    )

    assert not public_app_called
    assert sent_messages[0]["status"] == 400


def test_mcp_public_profile_accepts_chunked_body_with_incremental_limit() -> None:
    body = b'{"jsonrpc":"2.0","method":"ping"}'
    public_app_called, sent_messages, replayed_body = _invoke_public_middleware(
        [
            (b"authorization", f"Bearer {TEST_MCP_PUBLIC_API_KEY}".encode()),
            (b"transfer-encoding", b"chunked"),
        ],
        [
            {"type": "http.request", "body": body[:12], "more_body": True},
            {"type": "http.request", "body": body[12:], "more_body": False},
        ],
        maximum_body_bytes=len(body),
        consume_replayed_body=True,
    )

    assert public_app_called
    assert not sent_messages
    assert replayed_body == body


def test_mcp_public_profile_does_not_require_content_length() -> None:
    body = b'{"jsonrpc":"2.0","method":"ping"}'
    public_app_called, sent_messages, replayed_body = _invoke_public_middleware(
        [(b"authorization", f"Bearer {TEST_MCP_PUBLIC_API_KEY}".encode())],
        [{"type": "http.request", "body": body, "more_body": False}],
        maximum_body_bytes=len(body),
        consume_replayed_body=True,
    )

    assert public_app_called
    assert not sent_messages
    assert replayed_body == body


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
