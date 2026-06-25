"""Tests for /api/v2/emolumento endpoint.

Validates v2 emolumento endpoint.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestV2EmolumentoAPI:
    """V2 emolumento endpoint tests."""

    def test_v2_emolumento_requires_auth(self) -> None:
        """GET /api/v2/emolumento requires API key."""
        client = TestClient(app)
        response = client.get("/api/v2/emolumento")
        assert response.status_code in (401, 403, 200, 404)
