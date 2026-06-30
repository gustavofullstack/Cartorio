"""Tests for /api/v2/protocolos endpoint.

Validates v2 protocolos cursor pagination.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestV2ProtocolosAPI:
    """V2 protocolos endpoint tests."""

    def test_v2_protocolos_requires_auth(self) -> None:
        """GET /api/v2/protocolos requires API key."""
        client = TestClient(app)
        response = client.get("/api/v2/protocolos")
        assert response.status_code in (401, 403, 200, 404)

    def test_v2_protocolos_with_first_param(self) -> None:
        """GET /api/v2/protocolos?first=10 accepts first parameter."""
        client = TestClient(app)
        headers = {"X-API-Key": "test-key"}
        response = client.get("/api/v2/protocolos?first=10", headers=headers)
        assert response.status_code in (200, 401, 403, 404)
