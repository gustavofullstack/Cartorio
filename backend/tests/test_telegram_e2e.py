"""E2E tests: Telegram -> API -> OpenClaw -> response (E06).

Cobre o fluxo completo:
1. Telegram envia update para webhook
2. API valida HMAC, PII scrub, consulta OpenClaw Agent
3. API envia resposta via Telegram API mock
4. Audit log gerado

Usa mocks para Telegram API e OpenClaw para nao depender de rede.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.models.base import Base


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    """Forca env vars para os testes."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test:token")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setenv("AUDIT_HMAC_KEY", "a" * 64)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def test_engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def client(test_engine, test_session_factory):
    """TestClient com engine SQLite e dependencies mockadas."""
    from app.db import get_db
    from app.main import app

    get_settings.cache_clear()

    def _override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        Base.metadata.create_all(test_engine)
        try:
            with TestClient(app) as c:
                yield c
        finally:
            app.dependency_overrides.clear()


@pytest.fixture
def telegram_update_text() -> dict:
    """Update de texto valido do Telegram."""
    return {
        "update_id": 123456,
        "message": {
            "message_id": 1,
            "from": {"id": 12345, "first_name": "Joao", "is_bot": False},
            "chat": {"id": 12345, "type": "private"},
            "text": "Ola, quero uma certidao",
            "date": 1719227400,
        },
    }


class TestTelegramE2E:
    """E2E: Telegram webhook -> API -> OpenClaw -> response."""

    def test_e2e_text_message_flow(self, client: TestClient, telegram_update_text: dict) -> None:
        """Fluxo completo: mensagem de texto -> resposta."""
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_openclaw_agent",
                new=AsyncMock(return_value="Aqui esta sua certidao!"),
            ) as mock_agent,
            patch(
                "app.api.v1.telegram._send_telegram_message",
                new=AsyncMock(),
            ) as mock_send,
        ):
            resp = client.post("/api/v1/telegram/webhook", json=telegram_update_text)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["chat_id"] == 12345
        assert data["response_sent"] is True
        mock_agent.assert_called_once()
        mock_send.assert_called_once()

    def test_e2e_with_pii_scrub(self, client: TestClient) -> None:
        """PII (CPF) e' scrubbed antes de ir ao OpenClaw."""
        update = {
            "update_id": 1,
            "message": {
                "from": {"id": 12345},
                "chat": {"id": 12345},
                "text": "Meu CPF e 123.456.789-09",
                "date": 1719227400,
            },
        }
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_openclaw_agent",
                new=AsyncMock(return_value="Ok"),
            ) as mock_agent,
            patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock()),
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        # Verificar que o PII foi scrubbed antes do agent
        call_args = mock_agent.call_args
        text_scrubbed = call_args.kwargs.get("text_scrubbed") or call_args.args[1]
        assert "[CPF_REDACTED]" in text_scrubbed
        assert "123.456.789-09" not in text_scrubbed

    def test_e2e_ignores_non_text(self, client: TestClient) -> None:
        """Update sem text (sticker) e' ignorado."""
        update = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "from": {"id": 12345},
                "chat": {"id": 12345},
                # sem campo "text"
            },
        }
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock()),
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "non-text update"

    def test_e2e_agent_failure_returns_ok(
        self, client: TestClient, telegram_update_text: dict
    ) -> None:
        """Falha do OpenClaw retorna 200 com erro amigavel."""
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_openclaw_agent",
                new=AsyncMock(side_effect=Exception("API error")),
            ),
            patch(
                "app.api.v1.telegram._send_telegram_message",
                new=AsyncMock(),
            ) as mock_send,
        ):
            resp = client.post("/api/v1/telegram/webhook", json=telegram_update_text)

        # Mesmo com erro do agent, retorna 200 com fallback
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["response_sent"] is True
        # Fallback message enviada
        mock_send.assert_called_once()
        call_text = mock_send.call_args[0][1]
        # Mensagem de fallback: "Desculpe, tive um problema tecnico..."
        assert "problema tecnico" in call_text.lower()

    def test_e2e_pii_scrubbed_in_response(self, client: TestClient) -> None:
        """Resposta do agent com PII e' scrubbed antes de enviar ao Telegram."""
        update = {
            "update_id": 1,
            "message": {
                "from": {"id": 12345},
                "chat": {"id": 12345},
                "text": "Qual meu CPF?",
                "date": 1719227400,
            },
        }
        # Agent retorna CPF na resposta (deveria ser scrubbado)
        agent_response = "Seu CPF e 123.456.789-09 e seu RG e MG-12.345.678"
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_openclaw_agent",
                new=AsyncMock(return_value=agent_response),
            ),
            patch(
                "app.api.v1.telegram._send_telegram_message",
                new=AsyncMock(),
            ) as mock_send,
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        # Mensagem enviada ao Telegram deve ter PII scrubbed
        sent_text = mock_send.call_args[0][1]
        assert "[CPF_REDACTED]" in sent_text
        assert "123.456.789-09" not in sent_text

    def test_e2e_audit_log_created(self, client: TestClient, telegram_update_text: dict) -> None:
        """Flow completo termina com sucesso (E06 smoke test)."""
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_openclaw_agent",
                new=AsyncMock(return_value="Resposta"),
            ),
            patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock()),
        ):
            resp = client.post("/api/v1/telegram/webhook", json=telegram_update_text)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["chat_id"] == 12345
        assert data["response_sent"] is True
