"""Testes para endpoints de integracao (OpenCode-Go smoke test, etc)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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
    """Cliente de teste com DB in-memory e engine mockado."""
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


# ============================================================================
# OpenCode-Go smoke test endpoint
# ============================================================================


def test_opencode_test_endpoint_success(client):
    """Endpoint /integrations/opencode/test retorna 200 com status=ok."""
    # Mock settings com API key configurada
    with (
        patch("app.config.settings.opencode_go_api_key", "sk-test-1234"),
        patch("app.config.settings.opencode_go_base_url", "https://api.opencode.ai/v1"),
        patch("app.config.settings.opencode_go_model", "deepseek-v4-flash"),
    ):
        # Mock httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "pong"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_cls.return_value = mock_client

            resp = client.post(
                "/api/v1/integrations/opencode/test",
                json={"message": "ping"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["response"] == "pong"
    assert data["tokens_in"] == 1
    assert data["tokens_out"] == 1
    assert data["latency_ms"] >= 0
    assert data["config"]["provider"] == "opencode_go"
    assert data["config"]["api_key_configured"] is True
    # Garante que API key NAO esta no response
    assert "sk-test-1234" not in str(data)


def test_opencode_test_endpoint_missing_api_key(client):
    """Endpoint retorna 200 com status=erro (CONFIG) se API key ausente."""
    with patch("app.config.settings.opencode_go_api_key", ""):
        resp = client.post(
            "/api/v1/integrations/opencode/test",
            json={"message": "ping"},
        )

    assert resp.status_code == 200  # nao 500 - erro de config e resposta valida
    data = resp.json()
    assert data["status"] == "erro"
    assert data["erro"]["kind"] == "CONFIG_ERROR"
    assert data["config"]["api_key_configured"] is False


def test_opencode_test_endpoint_http_500(client):
    """Endpoint retorna status=erro quando OpenCode-Go retorna 5xx."""
    with (
        patch("app.config.settings.opencode_go_api_key", "sk-test"),
        patch("app.config.settings.opencode_go_base_url", "https://api.opencode.ai/v1"),
    ):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_cls.return_value = mock_client

            resp = client.post(
                "/api/v1/integrations/opencode/test",
                json={"message": "ping"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "erro"
    assert data["erro"]["kind"] == "HTTP_5XX"
    assert data["erro"]["status_code"] == 500


def test_opencode_test_endpoint_default_message(client):
    """Endpoint aceita request sem body (usa default 'ping')."""
    with (
        patch("app.config.settings.opencode_go_api_key", "sk-test"),
        patch("app.config.settings.opencode_go_base_url", "https://api.opencode.ai/v1"),
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "pong"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_cls.return_value = mock_client

            resp = client.post("/api/v1/integrations/opencode/test", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    # Default model e mensagem usados
    assert data["model"] == "deepseek-v4-flash"


def test_opencode_test_endpoint_validates_temperature(client):
    """Endpoint rejeita temperature fora de [0.0, 2.0] com 422."""
    with patch("app.config.settings.opencode_go_api_key", "sk-test"):
        resp = client.post(
            "/api/v1/integrations/opencode/test",
            json={"message": "ping", "temperature": 5.0},  # invalido (>2.0)
        )

    assert resp.status_code == 422  # Pydantic validation


def test_opencode_test_endpoint_appears_in_openapi(client):
    """Endpoint aparece no OpenAPI/Swagger."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/v1/integrations/opencode/test" in paths
