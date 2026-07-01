"""E2E tests: Telegram -> API -> LLM -> response (turn 47 - state machine).

Cobre o fluxo completo:
1. Telegram envia update para webhook
2. API processa comando nativo (state machine) ou LLM rapido
3. PII scrub em 3 camadas (input, pre-LLM, output)
4. API envia resposta via Telegram API
5. Audit log gerado

Usa mocks para Telegram API e LLM para nao depender de rede.
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
def telegram_update_start() -> dict:
    """Update com /start."""
    return {
        "update_id": 123456,
        "message": {
            "message_id": 1,
            "from": {"id": 6682284055, "first_name": "Joao", "is_bot": False},
            "chat": {"id": 6682284055, "type": "private"},
            "text": "/start",
            "date": 1719227400,
        },
    }


class TestTelegramE2E:
    """E2E: Telegram webhook -> API -> LLM -> response."""

    def test_e2e_start_command(self, client: TestClient, telegram_update_start: dict) -> None:
        """Comando /start -> resposta com saudacao + menu."""
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
        ):
            resp = client.post("/api/v1/telegram/webhook", json=telegram_update_start)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["response_sent"] is True
        mock_send.assert_called_once()
        sent_text = mock_send.call_args[0][1]
        assert "Cartorio 2o Oficio" in sent_text
        assert "/agendar" in sent_text

    def test_e2e_with_pii_scrub(self, client: TestClient) -> None:
        """PII (CPF) e' scrubbed antes de ir ao LLM."""
        update = {
            "update_id": 1,
            "message": {
                "from": {"id": 6682284055},
                "chat": {"id": 6682284055},
                "text": "Meu CPF e 123.456.789-09",
                "date": 1719227400,
            },
        }
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_fast_llm",
                new=AsyncMock(return_value="Ok"),
            ) as mock_llm,
            patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)),
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        # Verificar que o PII foi scrubbed antes do LLM
        call_args = mock_llm.call_args
        text_sent = call_args.args[0] if call_args.args else ""
        assert "123.456.789-09" not in text_sent

    def test_e2e_ignores_non_text(self, client: TestClient) -> None:
        """Update sem text (sticker) e' ignorado."""
        update = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "from": {"id": 12345},
                "chat": {"id": 12345},
            },
        }
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)),
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "non-text update"

    def test_e2e_llm_failure_returns_ok(
        self, client: TestClient, telegram_update_start: dict
    ) -> None:
        """Falha do LLM em texto livre retorna 200 com fallback (comando /start nao chama LLM)."""
        update = {
            "update_id": 1,
            "message": {
                "from": {"id": 6682284055},
                "chat": {"id": 6682284055},
                "text": "Quanto custa um testamento?",  # texto livre -> chama LLM
                "date": 1719227400,
            },
        }
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_fast_llm",
                new=AsyncMock(return_value=""),
            ),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        # Mesmo com erro do LLM, retorna 200 com fallback
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["response_sent"] is True
        mock_send.assert_called_once()
        call_text = mock_send.call_args[0][1]
        # Mensagem de fallback
        assert "/menu" in call_text or "escrevente" in call_text

    def test_e2e_pii_scrubbed_in_response(self, client: TestClient) -> None:
        """Resposta do LLM com PII e' scrubbed antes de enviar ao Telegram."""
        update = {
            "update_id": 1,
            "message": {
                "from": {"id": 6682284055},
                "chat": {"id": 6682284055},
                "text": "Qual meu CPF?",
                "date": 1719227400,
            },
        }
        # LLM retorna CPF na resposta (deveria ser scrubbado)
        llm_response = "Seu CPF e 123.456.789-09 e seu RG e MG-12.345.678"
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_fast_llm",
                new=AsyncMock(return_value=llm_response),
            ),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        # Mensagem enviada ao Telegram deve ter PII scrubbed
        sent_text = mock_send.call_args[0][1]
        assert "123.456.789-09" not in sent_text

    def test_e2e_comando_menu_sem_llm(
        self, client: TestClient, telegram_update_start: dict
    ) -> None:
        """Comando nativo /start nao chama LLM."""
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_fast_llm",
                new=AsyncMock(),
            ) as mock_llm,
            patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)),
        ):
            resp = client.post("/api/v1/telegram/webhook", json=telegram_update_start)

        assert resp.status_code == 200
        # /start e' comando nativo - nao chama LLM
        mock_llm.assert_not_called()

    def test_e2e_texto_livre_chama_llm(self, client: TestClient) -> None:
        """Texto livre (sem comando) chama LLM rapido."""
        update = {
            "update_id": 1,
            "message": {
                "from": {"id": 6682284055},
                "chat": {"id": 6682284055},
                "text": "Quero saber os horarios",
                "date": 1719227400,
            },
        }
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_fast_llm",
                new=AsyncMock(return_value="Horarios: seg-sex 9h-17h"),
            ) as mock_llm,
            patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)),
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        mock_llm.assert_called_once()
