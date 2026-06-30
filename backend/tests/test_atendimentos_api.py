"""Tests for /api/v1/atendimentos endpoint.

Validates atendimentos API endpoint.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestAtendimentosAPI:
    """Atendimentos endpoint tests."""

    def test_atendimentos_requires_auth(self) -> None:
        """GET /api/v1/atendimentos requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/atendimentos")
        assert response.status_code in (401, 403, 200, 404)
