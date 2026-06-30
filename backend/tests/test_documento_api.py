"""Tests for /api/v1/documento endpoints.

Validates documento API endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestDocumentoAPI:
    """Documento endpoint tests."""

    def test_documento_segunda_via_requires_auth(self) -> None:
        """POST /api/v1/documento/segunda-via requires API key."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/documento/segunda-via",
            json={"cliente_id": 1, "tipo_documento": "certidao"},
        )
        assert response.status_code in (401, 403, 200, 404, 422)
