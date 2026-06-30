"""Testes do VersionHeaderMiddleware (A20)."""

from __future__ import annotations


import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.version_header import (
    API_NEXT_VERSION,
    API_RELEASED,
    API_VERSION,
    VersionHeaderMiddleware,
    install_version_endpoint,
)


@pytest.fixture
def app():
    app = FastAPI()
    app.add_middleware(VersionHeaderMiddleware)
    install_version_endpoint(app)

    @app.get("/test")
    async def test() -> dict:
        return {"ok": True}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestVersionHeader:
    """TDD strict - A20."""

    def test_constants_defined(self):
        """Constantes de versao estao definidas."""
        assert API_VERSION == "0.5.4"
        assert API_RELEASED == "2026-06-24"
        assert API_NEXT_VERSION is not None

    def test_response_has_version_header(self, client):
        """Response tem X-API-Version."""
        resp = client.get("/test")
        assert resp.headers.get("X-API-Version") == API_VERSION

    def test_response_has_released_header(self, client):
        """Response tem X-API-Released."""
        resp = client.get("/test")
        assert resp.headers.get("X-API-Released") == API_RELEASED

    def test_response_has_link_header(self, client):
        """Response tem Link para proxima versao (RFC 8594)."""
        resp = client.get("/test")
        link = resp.headers.get("Link", "")
        assert "successor-version" in link
        assert "docs" in link

    def test_version_endpoint_returns_metadata(self, client):
        """GET /version retorna metadata completa."""
        resp = client.get("/version")
        assert resp.status_code == 200

        data = resp.json()
        assert data["version"] == API_VERSION
        assert data["released"] == API_RELEASED
        assert data["next_version"] == API_NEXT_VERSION
        assert data["deprecated"] is False
        assert "docs" in data["links"]
        assert "openapi" in data["links"]

    def test_version_endpoint_also_has_headers(self, client):
        """/version tambem recebe headers de versionamento."""
        resp = client.get("/version")
        assert resp.headers.get("X-API-Version") == API_VERSION

    def test_404_also_has_version_headers(self, client):
        """Ate 404 recebe headers de versionamento."""
        resp = client.get("/not-found")
        assert resp.status_code == 404
        assert resp.headers.get("X-API-Version") == API_VERSION
