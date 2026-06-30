"""Tests for OpenAPI spec endpoints.

Validates OpenAPI specification availability.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestOpenAPI:
    """OpenAPI endpoint tests."""

    def test_openapi_json_returns_200(self) -> None:
        """GET /openapi.json returns 200."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_json_has_version(self) -> None:
        """GET /openapi.json includes OpenAPI version."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        data = response.json()
        assert "openapi" in data
        assert "3." in data["openapi"]

    def test_openapi_json_has_paths(self) -> None:
        """GET /openapi.json includes paths."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        data = response.json()
        assert "paths" in data
        assert len(data["paths"]) > 0

    def test_docs_ui_returns_200(self) -> None:
        """GET /docs returns Swagger UI."""
        client = TestClient(app)
        response = client.get("/docs")
        assert response.status_code == 200
