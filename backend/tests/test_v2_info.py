"""Tests for /api/v2/info endpoint.

Validates API v2 metadata endpoint.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestV2Info:
    """API v2 info endpoint tests."""

    def test_v2_info_returns_200(self) -> None:
        """GET /api/v2/info returns 200."""
        client = TestClient(app)
        response = client.get("/api/v2/info")
        assert response.status_code == 200

    def test_v2_info_has_version(self) -> None:
        """GET /api/v2/info includes version."""
        client = TestClient(app)
        response = client.get("/api/v2/info")
        data = response.json()
        assert "version" in data
        assert "2.0.0" in data["version"]

    def test_v2_info_has_sunset_date(self) -> None:
        """GET /api/v2/info includes sunset_date."""
        client = TestClient(app)
        response = client.get("/api/v2/info")
        data = response.json()
        assert "sunset_date" in data
        assert data["sunset_date"] == "2027-12-31"

    def test_v2_info_has_breaking_changes(self) -> None:
        """GET /api/v2/info includes breaking_changes list."""
        client = TestClient(app)
        response = client.get("/api/v2/info")
        data = response.json()
        assert "breaking_changes_vs_v1" in data
        assert len(data["breaking_changes_vs_v1"]) > 0

    def test_v2_info_no_auth_required(self) -> None:
        """GET /api/v2/info works without authentication."""
        client = TestClient(app)
        response = client.get("/api/v2/info")
        assert response.status_code == 200
        # No 401/403
        assert response.status_code not in (401, 403)
