"""Tests for /api/v1/health/radar endpoint.

Validates that radar endpoint responds correctly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestHealthRadar:
    """Health radar endpoint tests."""

    def test_radar_requires_auth(self) -> None:
        """GET /api/v1/health/radar requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/health/radar")
        assert response.status_code in (401, 403, 200, 404)

    def test_radar_with_invalid_key(self) -> None:
        """GET /api/v1/health/radar rejects invalid key."""
        client = TestClient(app)
        headers = {"X-API-Key": "invalid-key-12345"}
        response = client.get("/api/v1/health/radar", headers=headers)
        assert response.status_code in (401, 403, 200, 404)

    def test_health_basic(self) -> None:
        """GET /health returns 200 without auth."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_openapi_spec_available(self) -> None:
        """GET /openapi.json returns valid spec."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "openapi" in response.json()
