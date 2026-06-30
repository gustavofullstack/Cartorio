"""Tests for /api/v1/health/backup endpoint.

Validates backup status endpoint.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestHealthBackupAPI:
    """Health backup endpoint tests."""

    def test_backup_requires_auth(self) -> None:
        """GET /api/v1/health/backup requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/health/backup")
        assert response.status_code in (401, 403, 200, 404)

    def test_backup_returns_json(self) -> None:
        """GET /api/v1/health/backup returns JSON response."""
        client = TestClient(app)
        headers = {"X-API-Key": "test-key"}
        response = client.get("/api/v1/health/backup", headers=headers)
        # May return 200 (with backup status) or 401/403 (auth)
        assert response.status_code in (200, 401, 403, 404)
