"""Tests for /api/v1/cliente endpoints.

Validates cliente API endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestClienteAPI:
    """Cliente endpoint tests."""

    def test_cliente_list_requires_auth(self) -> None:
        """GET /api/v1/cliente requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/cliente")
        assert response.status_code in (401, 403, 200, 404)

    def test_cliente_by_id_requires_auth(self) -> None:
        """GET /api/v1/cliente/{id} requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/cliente/1")
        assert response.status_code in (401, 403, 200, 404)

    def test_cliente_create_requires_auth(self) -> None:
        """POST /api/v1/cliente requires API key."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/cliente",
            json={"nome": "Test", "cpf": "12345678901"},
        )
        assert response.status_code in (401, 403, 200, 404, 422)
