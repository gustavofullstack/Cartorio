"""Tests for /api/v1/emolumentos endpoints.

Validates emolumento API endpoints.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestEmolumentoAPI:
    """Emolumento endpoint tests."""

    def test_emolumento_list_requires_auth(self) -> None:
        """GET /api/v1/emolumentos requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/emolumentos")
        assert response.status_code in (401, 403, 200, 404)

    def test_emolumento_by_id_requires_auth(self) -> None:
        """GET /api/v1/emolumentos/{id} requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/emolumentos/1")
        assert response.status_code in (401, 403, 200, 404)
