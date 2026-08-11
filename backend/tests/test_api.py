"""Testes de integracao da API - cobre main.py, db.py e router.py."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def test_engine():
    """Engine SQLite in-memory para os testes desta suite."""
    import app.db as appdb

    return appdb.engine


@pytest.fixture
def test_session_factory(test_engine):
    import app.db as appdb

    return appdb.SessionLocal


@pytest.fixture
def client(test_engine, test_session_factory):
    """TestClient que usa o engine SQLite ja configurado pelo conftest autouse."""
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

    with (
        patch("app.config.settings.opencode_go_api_key", "sk-test-mock"),
        patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)),
    ):
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
    resp = client.post("/api/v1/audit/verify", headers={"X-API-Key": "a" * 64})
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
    """Historico legado nunca aceita identificador externo nem sem API key."""
    resp = client.get("/api/v1/atendimento/user123/historico")
    assert resp.status_code == 401


def test_atendimento_historico_db_fallback(client):
    """Mesmo autenticado, path raw falha fechado sem tentar resolver por PII."""
    from tests.conftest import TEST_CARTORIO_API_KEY

    unique_external_id = "user_db_fallback_isolated_xyz"
    resp = client.get(
        f"/api/v1/atendimento/{unique_external_id}/historico",
        headers={"X-API-Key": TEST_CARTORIO_API_KEY},
    )
    assert resp.status_code == 404
