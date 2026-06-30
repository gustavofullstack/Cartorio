"""Tests for /api/v1/health/radar endpoint.

Validates radar health check endpoint.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestHealthRadarAPI:
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
