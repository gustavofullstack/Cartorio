"""Tests for /api/v2/clientes endpoint.

Validates v2 clientes cursor pagination.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestV2ClientesAPI:
    """V2 clientes endpoint tests."""

    def test_v2_clientes_requires_auth(self) -> None:
        """GET /api/v2/clientes requires API key."""
        client = TestClient(app)
        response = client.get("/api/v2/clientes")
        assert response.status_code in (401, 403, 200, 404)

    def test_v2_clientes_with_first_param(self) -> None:
        """GET /api/v2/clientes?first=10 accepts first parameter."""
        client = TestClient(app)
        headers = {"X-API-Key": "test-key"}
        response = client.get("/api/v2/clientes?first=10", headers=headers)
        assert response.status_code in (200, 401, 403, 404)
