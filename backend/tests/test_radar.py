"""Unit tests for the new health/radar, postman, and LLM webhook integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import httpx

from app.models.base import Base
from app.config import settings


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
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app
        with TestClient(app) as c:
            yield c


def test_postman_collection(client):
    resp = client.get("/api/v1/postman")
    assert resp.status_code == 200
    data = resp.json()
    assert data["info"]["name"] == "Cartorio API"
    # 6 endpoints: emolumento, consultar protocolo, criar protocolo,
    # webhook evolution, audit verify, health radar
    assert len(data["item"]) == 6
    assert data["variable"][0]["key"] == "base_url"
    # Garante que os 2 novos endpoints do protocolo estao na colecao
    item_names = {item["name"] for item in data["item"]}
    assert "Consultar Protocolo" in item_names
    assert "Criar Protocolo" in item_names


@patch("app.db.engine.connect")
@patch("redis.from_url")
@patch("httpx.AsyncClient.get")
def test_health_radar_all_green(mock_get, mock_redis_from_url, mock_db_connect, client):
    # Mock DB connection
    mock_conn = MagicMock()
    mock_db_connect.return_value.__enter__.return_value = mock_conn

    # Mock Redis ping
    mock_r = MagicMock()
    mock_r.ping.return_value = True
    mock_redis_from_url.return_value = mock_r

    # Mock HTTPX gets for n8n, openclaw, evolution API
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    resp = client.get("/api/v1/health/radar")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "green"
    assert data["services"]["database"] == "online"
    assert data["services"]["redis"] == "online"
    assert data["services"]["n8n"] == "online"
    assert data["services"]["openclaw"] == "online"
    assert data["services"]["evolution"] == "online"


@patch("app.db.engine.connect")
@patch("redis.from_url")
@patch("httpx.AsyncClient.get")
def test_health_radar_all_red(mock_get, mock_redis_from_url, mock_db_connect, client):
    # Mock DB connection failure
    mock_db_connect.side_effect = Exception("DB Down")

    # Mock Redis failure
    mock_redis_from_url.side_effect = Exception("Redis Down")

    # Mock HTTPX failures
    mock_get.side_effect = httpx.RequestError("Network error")

    resp = client.get("/api/v1/health/radar")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "red"
    assert data["services"]["database"] == "offline"
    assert data["services"]["redis"] == "offline"
    assert data["services"]["n8n"] == "offline"
    assert data["services"]["openclaw"] == "offline"
    assert data["services"]["evolution"] == "offline"


@patch("httpx.AsyncClient.post")
def test_webhook_evolution_llm_success(mock_post, client):
    # Mock successful LLM call
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "Olá, posso te ajudar com sua certidão."
            }
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 15
        }
    }
    mock_post.return_value = mock_response

    # Force enable key
    with (
        patch.object(settings, "opencode_go_api_key", "sk-test-api-key"),
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
        assert "certidão" in data["response"]


@patch("httpx.AsyncClient.post")
def test_webhook_evolution_llm_handoff(mock_post, client):
    # Mock LLM calling human redirection
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "Encaminhando para um atendente. [HUMANO]"
            }
        }]
    }
    mock_post.return_value = mock_response

    with (
        patch.object(settings, "opencode_go_api_key", "sk-test-api-key"),
    ):
        payload = {
            "message": {"text": "Quero falar com gerente"},
            "sender": "user123",
            "instance": "inst1",
        }
        resp = client.post("/api/v1/webhook/evolution", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "HUMANO" not in data["response"]


@patch("httpx.AsyncClient.post")
def test_webhook_evolution_llm_error_status(mock_post, client):
    # Mock LLM error status
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_post.return_value = mock_response

    with (
        patch.object(settings, "opencode_go_api_key", "sk-test-api-key"),
    ):
        payload = {
            "message": {"text": "Teste erro"},
            "sender": "user123",
            "instance": "inst1",
        }
        resp = client.post("/api/v1/webhook/evolution", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "problema de" in data["response"]


@patch("httpx.AsyncClient.post")
def test_webhook_evolution_llm_exception(mock_post, client):
    # Mock LLM connection failure
    mock_post.side_effect = httpx.ConnectError("Timeout")

    with (
        patch.object(settings, "opencode_go_api_key", "sk-test-api-key"),
    ):
        payload = {
            "message": {"text": "Teste exception"},
            "sender": "user123",
            "instance": "inst1",
        }
        resp = client.post("/api/v1/webhook/evolution", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "problema de" in data["response"]
