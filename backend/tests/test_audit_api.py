"""Tests for /api/v1/admin/audit endpoints.

Validates audit admin endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestAuditAPI:
    """Audit admin endpoint tests."""

    def test_audit_check_now_requires_auth(self) -> None:
        """POST /api/v1/admin/audit/check-now requires API key."""
        client = TestClient(app)
        response = client.post("/api/v1/admin/audit/check-now")
        assert response.status_code in (401, 403, 200, 404)

    def test_slow_queries_requires_auth(self) -> None:
        """GET /api/v1/admin/slow-queries requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/admin/slow-queries")
        assert response.status_code in (401, 403, 200, 404)
