"""Contract tests for the PII-safe Cartório agent smoke script."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import smoke_cartorio_agent as smoke  # noqa: E402


def test_cors_accepts_success_with_matching_origin(monkeypatch: object) -> None:
    def fake_options(*args: object, **kwargs: object) -> httpx.Response:
        return httpx.Response(204, headers={"access-control-allow-origin": "https://lobe.test"})

    monkeypatch.setattr(smoke.httpx, "options", fake_options)
    result = smoke.check_cors("https://agent.test", "https://lobe.test")
    assert result.status == "ok"
    assert "key" not in result.details.lower()


def test_cors_rejects_405_without_echoing_response_headers(monkeypatch: object) -> None:
    def fake_options(*args: object, **kwargs: object) -> httpx.Response:
        return httpx.Response(
            405,
            headers={"access-control-allow-origin": "https://unexpected.example"},
        )

    monkeypatch.setattr(smoke.httpx, "options", fake_options)
    result = smoke.check_cors("https://agent.test", "https://lobe.test")
    assert result.status == "error"
    assert "unexpected.example" not in result.details


def test_websocket_challenge_does_not_send_auth_or_chat(monkeypatch: object) -> None:
    sent: list[object] = []

    class FakeWebSocket:
        async def __aenter__(self) -> "FakeWebSocket":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def recv(self) -> str:
            return '{"type":"event","event":"connect.challenge","payload":{"nonce":"redacted"}}'

        async def send(self, value: object) -> None:
            sent.append(value)

    def fake_connect(*args: object, **kwargs: object) -> FakeWebSocket:
        assert kwargs["origin"] == "https://lobe.test"
        return FakeWebSocket()

    monkeypatch.setitem(sys.modules, "websockets", SimpleNamespace(connect=fake_connect))
    result = asyncio.run(smoke.check_websocket_challenge("https://agent.test", "https://lobe.test"))
    assert result.status == "ok"
    assert sent == []


def test_lobechat_uses_health_fallback_without_body_logging(monkeypatch: object) -> None:
    calls: list[str] = []

    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        calls.append(url)
        return httpx.Response(
            404 if url.endswith("/api/health") else 200, text="contains-sensitive-body"
        )

    monkeypatch.setattr(smoke.httpx, "get", fake_get)
    result = smoke.check_lobechat_proxy("test", "https://lobe.test", optional=False)
    assert result.status == "ok"
    assert result.details.endswith("(proxy fallback)")
    assert "sensitive" not in result.details
    assert calls == ["https://lobe.test/api/health", "https://lobe.test/health"]
