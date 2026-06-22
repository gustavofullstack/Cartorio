"""Testes de integracao da API - cobre main.py, db.py e router.py."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def client(test_engine, test_session_factory):
    """TestClient que substitui engine e sessao do app por SQLite in-memory."""
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_ready_endpoint(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"


def test_calcular_emolumento_valido(client):
    resp = client.get("/api/v1/emolumento/calcular?tipo=escritura_compra_venda&folhas=3&urgencia=true")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "tipo" in data


def test_calcular_emolumento_tipo_invalido(client):
    resp = client.get("/api/v1/emolumento/calcular?tipo=inexistente")
    assert resp.status_code == 200
    data = resp.json()
    assert "erro" in data


def test_webhook_evolution_sem_pii(client):
    payload = {
        "message": {"text": "Ola, preciso de uma certidao"},
        "sender": "user123",
        "instance": "inst1",
    }
    resp = client.post("/api/v1/webhook/evolution", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "atendente" in data["response"]


def test_webhook_evolution_com_pii(client):
    payload = {
        "message": {"text": "Meu CPF 123.456.789-09 esta correto?"},
        "sender": "user456",
        "instance": "inst2",
    }
    resp = client.post("/api/v1/webhook/evolution", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "transferir" in data["response"]
    assert "123.456.789-09" not in data["scrubbed"]


def test_webhook_evolution_payload_vazio(client):
    resp = client.post("/api/v1/webhook/evolution", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_audit_verify_endpoint(client):
    resp = client.post("/api/v1/audit/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert "chain_ok" in data
    assert "last_valid_position" in data


def test_db_get_db_yields_session(test_engine, test_session_factory):
    """Cobre get_db() dependency do db.py."""
    with patch("app.db.SessionLocal", test_session_factory):
        from app.db import get_db

        gen = get_db()
        session = next(gen)
        assert isinstance(session, Session)
        try:
            next(gen)
        except StopIteration:
            pass


def test_db_session_scope_commit(test_engine, test_session_factory):
    """Cobre session_scope() context manager - caminho feliz."""
    with patch("app.db.SessionLocal", test_session_factory):
        from app.db import session_scope

        with session_scope() as session:
            assert isinstance(session, Session)


def test_db_session_scope_rollback(test_engine, test_session_factory):
    """Cobre session_scope() context manager - caminho de erro com rollback."""
    with patch("app.db.SessionLocal", test_session_factory):
        from app.db import session_scope

        with pytest.raises(ValueError, match="boom"):
            with session_scope() as _session:
                raise ValueError("boom")
