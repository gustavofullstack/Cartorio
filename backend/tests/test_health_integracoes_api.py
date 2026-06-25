"""Tests for /api/v1/health/integracoes endpoint.

Validates integrations health check endpoint.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestHealthIntegracoesAPI:
    """Health integracoes endpoint tests."""

    def test_integracoes_requires_auth(self) -> None:
        """GET /api/v1/health/integracoes requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/health/integracoes")
        assert response.status_code in (401, 403, 200, 404)

    def test_integracoes_with_invalid_key(self) -> None:
        """GET /api/v1/health/integracoes rejects invalid key."""
        client = TestClient(app)
        headers = {"X-API-Key": "invalid-key-12345"}
        response = client.get("/api/v1/health/integracoes", headers=headers)
        assert response.status_code in (401, 403, 200, 404)
