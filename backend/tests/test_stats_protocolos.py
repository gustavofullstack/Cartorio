"""Testes do endpoint /stats/protocolos (A16 - materialized view)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models.base import Base


@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    # A17: adicionar coluna deleted_at
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE protocolos ADD COLUMN deleted_at TIMESTAMP NULL"))
        conn.commit()
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="module")
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="module")
def client(test_engine, test_session_factory):
    """Cliente FastAPI com DB SQLite isolado (module-scoped)."""
    def _override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

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
