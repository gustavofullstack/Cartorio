"""G8.10.T1 — Dynamic processing host identifier on HTTP responses.

Covers:
- get_processing_host_id() prefers PROCESSING_HOST_ID env
- falls back to socket.gethostname()
- ProcessingHostMiddleware sets X-Cartorio-Processing-Host on responses
- header has no PII (infra id only)
- 404 responses also carry the header

Modified by Gustavo Almeida — Wave G8.10.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.processing_host import (
    PROCESSING_HOST_ENV,
    PROCESSING_HOST_HEADER,
    ProcessingHostMiddleware,
    get_processing_host_id,
)


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ProcessingHostMiddleware)

    @app.get("/test")
    async def test() -> dict:
        return {"ok": True}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestGetProcessingHostId:
    def test_prefers_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(PROCESSING_HOST_ENV, "cartorio-api-replica-3")
        assert get_processing_host_id() == "cartorio-api-replica-3"

    def test_strips_whitespace_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(PROCESSING_HOST_ENV, "  worker-a  ")
        assert get_processing_host_id() == "worker-a"

    def test_empty_env_falls_back_to_hostname(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(PROCESSING_HOST_ENV, "   ")
        with patch("socket.gethostname", return_value="macbook.local"):
            assert get_processing_host_id() == "macbook.local"

    def test_missing_env_uses_hostname(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(PROCESSING_HOST_ENV, raising=False)
        with patch("socket.gethostname", return_value="vps-cartorio-1"):
            assert get_processing_host_id() == "vps-cartorio-1"

    def test_empty_hostname_returns_unknown(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(PROCESSING_HOST_ENV, raising=False)
        with patch("socket.gethostname", return_value=""):
            assert get_processing_host_id() == "unknown"

    def test_value_is_not_pii_shaped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Header value must be host id only — not CPF/email/user data."""
        monkeypatch.setenv(PROCESSING_HOST_ENV, "api-01")
        value = get_processing_host_id()
        assert value == "api-01"
        assert "@" not in value
        for forbidden in ("cpf", "email", "password", "token", "secret"):
            assert forbidden not in value.lower()


class TestProcessingHostMiddleware:
    def test_response_has_processing_host_header(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(PROCESSING_HOST_ENV, "test-host-xyz")
        resp = client.get("/test")
        assert resp.status_code == 200
        assert resp.headers.get(PROCESSING_HOST_HEADER) == "test-host-xyz"

    def test_header_uses_hostname_when_env_unset(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(PROCESSING_HOST_ENV, raising=False)
        with patch("socket.gethostname", return_value="node-42"):
            resp = client.get("/test")
        assert resp.status_code == 200
        assert resp.headers.get(PROCESSING_HOST_HEADER) == "node-42"

    def test_404_also_has_header(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(PROCESSING_HOST_ENV, "ghost")
        resp = client.get("/not-found")
        assert resp.status_code == 404
        assert resp.headers.get(PROCESSING_HOST_HEADER) == "ghost"

    def test_header_name_constant(self) -> None:
        assert PROCESSING_HOST_HEADER == "X-Cartorio-Processing-Host"
        assert PROCESSING_HOST_ENV == "PROCESSING_HOST_ID"

    def test_body_unaffected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(PROCESSING_HOST_ENV, "ok-host")
        resp = client.get("/test")
        assert resp.json() == {"ok": True}
