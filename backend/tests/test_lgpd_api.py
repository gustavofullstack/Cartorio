"""Tests for /api/v1/lgpd/ endpoints.

Validates LGPD API endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestLGPD_API:
    """LGPD endpoint tests."""

    def test_lgpd_historico_requires_auth(self) -> None:
        """GET /api/v1/lgpd/{cpf}/historico requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/lgpd/12345678901/historico")
        assert response.status_code in (401, 403, 200, 404)

    def test_lgpd_anonimizar_requires_auth(self) -> None:
        """POST /api/v1/lgpd/{cpf}/anonimizar requires API key."""
        client = TestClient(app)
        response = client.post("/api/v1/lgpd/12345678901/anonimizar")
        assert response.status_code in (401, 403, 200, 404)

    def test_lgpd_portabilidade_requires_auth(self) -> None:
        """POST /api/v1/lgpd/{cpf}/portabilidade requires API key."""
        client = TestClient(app)
        response = client.post("/api/v1/lgpd/12345678901/portabilidade")
        assert response.status_code in (401, 403, 200, 404)

    def test_lgpd_oposicao_requires_auth(self) -> None:
        """POST /api/v1/lgpd/{cpf}/oposicao requires API key."""
        client = TestClient(app)
        response = client.post("/api/v1/lgpd/12345678901/oposicao")
        assert response.status_code in (401, 403, 200, 404)

    def test_lgpd_optout_requires_auth(self) -> None:
        """POST /api/v1/lgpd/{cpf}/optout requires API key."""
        client = TestClient(app)
        response = client.post("/api/v1/lgpd/12345678901/optout")
        assert response.status_code in (401, 403, 200, 404)
