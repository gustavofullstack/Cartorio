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
    resp = client.get(
        "/api/v1/emolumento/calcular?tipo=escritura_compra_venda&folhas=3&urgencia=true"
    )
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
    """Webhook sem PII: bot responde sem alarme de handoff.

    Ambiente local pode ter OPENCODE_GO_API_KEY real no .env, entao mockamos
    o cliente HTTP para garantir resposta deterministica sem dependencia de rede.

    P0.1 - response shape deve incluir pii_blocked=False e
    needs_human_handoff=False explicitamente (LGPD compliance signal).
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Posso te ajudar com sua certidao."}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8},
    }

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        payload = {
            "message": {"text": "Ola, preciso de uma certidao"},
            "sender": "user123",
            "instance": "inst1",
        }
        resp = client.post("/api/v1/webhook/evolution", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        # Resposta do bot mockado (sem [HUMANO])
        assert "Posso te ajudar" in data["response"]
        assert "[HUMANO]" not in data["response"]
        # P0.1 LGPD response shape - sem PII = sem handoff
        assert data["pii_blocked"] is False
        assert data["needs_human_handoff"] is False
        assert data["handoff_reason"] is None


def test_webhook_evolution_com_pii(client):
    """P0.1 - Webhook COM PII: response deve marcar pii_blocked=True e
    needs_human_handoff=True com handoff_reason='PII detectada'.

    Garante que o signal de bloqueio eh explicito no response (LGPD
    compliance - cartorio-n8n e integradores precisam saber que PII
    foi detectada sem precisar inferir do texto).
    """
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
    # P0.1 LGPD response shape - com PII = handoff explicito
    assert data["pii_blocked"] is True
    assert data["needs_human_handoff"] is True
    assert data["handoff_reason"] == "PII detectada"


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


def test_atendimento_historico_redis_and_db(client):
    from unittest.mock import MagicMock, patch

    # Mock Redis client
    mock_redis = MagicMock()
    mock_redis.lrange.return_value = [
        '{"role": "user", "content": "Ola da fila do Redis", "timestamp": "2026-06-23T19:00:00Z"}',
        '{"role": "assistant", "content": "Olá do Bot!", "timestamp": "2026-06-23T19:00:05Z"}',
    ]

    with patch("redis.from_url", return_value=mock_redis):
        resp = client.get("/api/v1/atendimento/user123/historico")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "user123"
        assert data["total"] == 2
        assert data["messages"][0]["content"] == "Ola da fila do Redis"
        assert data["messages"][1]["content"] == "Olá do Bot!"


def test_atendimento_historico_db_fallback(client):
    from unittest.mock import MagicMock, patch
    from app.models.conversa import Conversa
    from app.db import session_scope

    # Mock Redis to return empty list (trigger fallback to DB)
    mock_redis = MagicMock()
    mock_redis.lrange.return_value = []

    # Save a dummy conversa in SQLite test DB
    with session_scope() as db:
        conversa = Conversa(
            canal="whatsapp",
            external_id="user_db",
            raw_message_hash="hash123",
            raw_message_scrubbed="Mensagem do DB",
            bot_response="Resposta do Bot DB",
        )
        db.add(conversa)

    with patch("redis.from_url", return_value=mock_redis):
        resp = client.get("/api/v1/atendimento/user_db/historico")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "user_db"
        assert data["total"] == 2
        assert data["messages"][0]["content"] == "Mensagem do DB"
        assert data["messages"][1]["content"] == "Resposta do Bot DB"

def test_custom_swagger_ui_html(client):
    """Testa se o Swagger UI customizado é retornado corretamente no /docs."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "Cartorio Backend API - Swagger UI" in response.text
    assert "Swagger UI" in response.text
