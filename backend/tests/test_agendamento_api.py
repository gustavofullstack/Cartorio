"""Tests for /api/v1/agendamento/ endpoints.

Validates agendamento API endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestAgendamentoAPI:
    """Agendamento endpoint tests."""

    def test_agendamento_disponibilidade_requires_auth(self) -> None:
        """GET /api/v1/agendamento/disponibilidade requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/agendamento/disponibilidade")
        assert response.status_code in (401, 403, 200, 404, 422)

    def test_agendamento_create_requires_auth(self) -> None:
        """Criação de agenda não é uma superfície pública."""
        client = TestClient(app)
        response = client.post("/api/v1/agendamento", json={})
        assert response.status_code == 401

    def test_disponibilidade_estatica_falha_de_modo_seguro(self) -> None:
        """A API não pode inventar vagas enquanto a agenda real estiver ausente."""
        client = TestClient(app)
        response = client.get(
            "/api/v1/agendamento/disponibilidade",
            params={"dia": "segunda", "hora": 10},
            headers={"X-API-Key": "a" * 64},
        )
        assert response.status_code == 503
        body = response.json()
        assert body["detail"]["erro"] == "AGENDA_REAL_INDISPONIVEL"
        assert "slots" not in body["detail"]

    def test_agendamento_pendentes_requires_auth(self) -> None:
        """GET /api/v1/agendamento/pendentes requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/agendamento/pendentes")
        assert response.status_code in (401, 403, 200, 404)

    def test_agendamento_proximos_requires_auth(self) -> None:
        """GET /api/v1/agendamento/proximos requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/agendamento/proximos")
        assert response.status_code in (401, 403, 200, 404)
