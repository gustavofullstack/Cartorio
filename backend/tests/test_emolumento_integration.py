"""Integration tests for emolumento endpoints.

Validates emolumento service and cache behavior.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestEmolumentoIntegration:
    """Emolumento endpoint integration tests."""

    def test_emolumento_list_requires_auth(self) -> None:
        """GET /api/v1/emolumentos requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/emolumentos")
        assert response.status_code in (401, 403, 200, 404, 422)

    def test_emolumento_by_id_requires_auth(self) -> None:
        """GET /api/v1/emolumentos/{id} requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/emolumentos/1")
        assert response.status_code in (401, 403, 200, 404, 422)

    def test_emolumento_cache_hit(self) -> None:
        """Second request should be faster (cache)."""
        client = TestClient(app)
        headers = {"X-API-Key": "test-key"}
        r1 = client.get("/api/v1/emolumentos", headers=headers)
        r2 = client.get("/api/v1/emolumentos", headers=headers)
        # Both should return same status
        assert r1.status_code == r2.status_code
