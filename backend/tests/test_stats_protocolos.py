"""Testes do endpoint /stats/protocolos (A16 - materialized view)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import get_db
from app.main import app


@pytest.fixture
def client(db_session):
    """Cliente FastAPI com DB SQLite isolado.

    Adiciona coluna deleted_at (A17) na tabela protocolos antes de
    delegar para o fixture db_session do conftest (que ja tem o isolamento
    correto da engine global).
    """
    with db_session.bind.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE protocolos ADD COLUMN deleted_at TIMESTAMP NULL"))
            conn.commit()
        except Exception:  # coluna ja existe
            pass

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


class TestStatsProtocolos:
    """TDD strict - A16."""

    def test_endpoint_returns_200(self, client):
        """Endpoint retorna 200 OK."""
        resp = client.get("/api/v1/stats/protocolos")
        assert resp.status_code == 200

    def test_response_shape(self, client):
        """Response tem chaves: source, count_groups, total_protocolos, items."""
        resp = client.get("/api/v1/stats/protocolos")
        data = resp.json()

        assert "source" in data
        assert data["source"] == "sqlite_aggregate"
        assert "count_groups" in data
        assert "total_protocolos" in data
        assert "total_valor_centavos" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_empty_db_returns_zero(self, client):
        """DB vazio: count_groups=0, total_protocolos=0."""
        resp = client.get("/api/v1/stats/protocolos")
        data = resp.json()

        assert data["count_groups"] == 0
        assert data["total_protocolos"] == 0
        assert data["total_valor_centavos"] == 0
        assert data["items"] == []
