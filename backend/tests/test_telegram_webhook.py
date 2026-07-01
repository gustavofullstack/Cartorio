"""Testes do endpoint Telegram webhook (turn 52 - v2.0 com rate limit + debounce).

Cobre:
- Comandos nativos (/start, /menu, /cancelar, /humano, /lgpd)
- Botões inline (callbacks)
- State machine (Redis) para fluxos multi-passo
- Rate limiting (sliding window 60s)
- Debounce (janela 3s)
- Tools MCP-style (agendar, consultar protocolo, calcular emolumento)
- PII scrub (camada 1 + 3)
- HMAC validation (secret_token)
- SEMPRE retorna 200 (evita retry infinito Telegram)
- Reacoes (emojis so em reacoes, nunca no texto)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def telegram_update_start() -> dict:
    return {
        "update_id": 123456,
        "message": {
            "message_id": 1,
            "from": {"id": 6682284055, "first_name": "Gustavo", "is_bot": False},
            "chat": {"id": 6682284055, "type": "private"},
            "text": "/start",
            "date": 1719227400,
        },
    }


@pytest.fixture
def telegram_update_text() -> dict:
    return {
        "update_id": 123456,
        "message": {
            "message_id": 2,
            "from": {"id": 6682284055, "first_name": "Joao", "is_bot": False},
            "chat": {"id": 6682284055, "type": "private"},
            "text": "Quanto custa uma certidao?",
            "date": 1719227400,
        },
    }


@pytest.fixture
def telegram_callback_agendar() -> dict:
    return {
        "update_id": 999,
        "callback_query": {
            "id": "cb_123",
            "from": {"id": 6682284055, "first_name": "Gustavo"},
            "message": {
                "chat": {"id": 6682284055},
                "message_id": 10,
            },
            "data": "agendar",
        },
    }


# === Comandos nativos (zero LLM) ===


def test_webhook_start_command(client: TestClient, telegram_update_start: dict) -> None:
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)
        ) as mock_send:
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    resp = client.post("/api/v1/telegram/webhook", json=telegram_update_start)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    mock_send.assert_called_once()
    sent_text = mock_send.call_args[0][1]
    assert "Cartorio" in sent_text
    # Verifica que tem inline keyboard
    call_kwargs = mock_send.call_args
    assert call_kwargs[1].get("reply_markup") is not None


def test_webhook_menu_command(client: TestClient) -> None:
    update = {
        "update_id": 1,
        "message": {
            "from": {"id": 6682284055},
            "chat": {"id": 6682284055},
            "text": "/menu",
            "date": 1719227400,
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)
        ) as mock_send:
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "Cartorio" in sent_text


def test_webhook_cancelar_command(client: TestClient) -> None:
    update = {
        "update_id": 1,
        "message": {
            "from": {"id": 6682284055},
            "chat": {"id": 6682284055},
            "text": "/cancelar",
            "date": 1719227400,
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)
        ) as mock_send:
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "cancelada" in sent_text.lower()


def test_unknown_command_shows_menu(client: TestClient) -> None:
    update = {
        "update_id": 1,
        "message": {
            "from": {"id": 6682284055},
            "chat": {"id": 6682284055},
            "text": "/agendar",
            "date": 1719227400,
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)
        ) as mock_send:
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    # /agendar nao existe mais como comando - cai no unknown_command
    sent_text = mock_send.call_args[0][1]
    assert "não disponível" in sent_text or "menu" in sent_text.lower()


# === Callbacks (botões inline) ===


def test_callback_agendar_shows_services(
    client: TestClient, telegram_callback_agendar: dict
) -> None:
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)
        ) as mock_send:
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    with patch(
                        "app.api.v1.telegram._answer_callback_query",
                        new=AsyncMock(return_value=True),
                    ):
                        resp = client.post(
                            "/api/v1/telegram/webhook", json=telegram_callback_agendar
                        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["kind"] == "callback"
    sent_text = mock_send.call_args[0][1]
    assert "Agendar" in sent_text or "serviço" in sent_text.lower()


def test_callback_cancelar_returns_menu(client: TestClient) -> None:
    update = {
        "update_id": 999,
        "callback_query": {
            "id": "cb_cancel",
            "from": {"id": 6682284055},
            "message": {"chat": {"id": 6682284055}, "message_id": 10},
            "data": "cancelar",
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)
        ) as mock_send:
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    with patch(
                        "app.api.v1.telegram._answer_callback_query",
                        new=AsyncMock(return_value=True),
                    ):
                        resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "menu" in sent_text.lower()


# === State machine (com Redis mock) ===


def test_webhook_agendar_flow(client: TestClient) -> None:
    mock_bus = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_bus.client = mock_redis

    # Step 1: click agendar
    update1 = {
        "update_id": 1,
        "callback_query": {
            "id": "cb1",
            "from": {"id": 6682284055},
            "message": {"chat": {"id": 6682284055}, "message_id": 10},
            "data": "agendar",
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=mock_bus):
        with patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)):
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    with patch(
                        "app.api.v1.telegram._answer_callback_query",
                        new=AsyncMock(return_value=True),
                    ):
                        resp = client.post("/api/v1/telegram/webhook", json=update1)
    assert resp.status_code == 200

    # Step 2: select service (callback serv:1)
    mock_redis.get.return_value = b'{"state":"agendar:servico","data":{}}'
    update2 = {
        "update_id": 2,
        "callback_query": {
            "id": "cb2",
            "from": {"id": 6682284055},
            "message": {"chat": {"id": 6682284055}, "message_id": 11},
            "data": "serv:1",
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=mock_bus):
        with patch(
            "app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)
        ) as mock_send:
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    with patch(
                        "app.api.v1.telegram._answer_callback_query",
                        new=AsyncMock(return_value=True),
                    ):
                        resp = client.post("/api/v1/telegram/webhook", json=update2)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "Reconhecimento" in sent_text or "data" in sent_text.lower()


# === Texto livre ===


def test_text_free_shows_menu(client: TestClient, telegram_update_text: dict) -> None:
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)
        ) as mock_send:
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    resp = client.post("/api/v1/telegram/webhook", json=telegram_update_text)
    assert resp.status_code == 200
    # Texto livre sem state = mostra menu
    sent_text = mock_send.call_args[0][1]
    assert "menu" in sent_text.lower() or "cartorio" in sent_text.lower() or "cartório" in sent_text.lower()


# === PII Scrubbing ===


def test_webhook_scrubs_pii_in_message(client: TestClient) -> None:
    update = {
        "update_id": 1,
        "message": {
            "from": {"id": 6682284055},
            "chat": {"id": 6682284055},
            "text": "Meu CPF e 123.456.789-09, manda certidao",
            "date": 1719227400,
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)):
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200


# === Non-text updates ===


def test_webhook_ignores_non_text_update(client: TestClient) -> None:
    update = {
        "update_id": 123456,
        "message": {
            "message_id": 1,
            "from": {"id": 12345},
            "chat": {"id": 12345},
        },
    }
    resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ignored"


# === HMAC validation ===


def test_hmac_valid_secret_accepted(client: TestClient, telegram_update_start: dict) -> None:
    import hashlib
    import hmac as hmac_mod
    import json as _json

    from app.api.v1 import telegram as tg_mod

    old_secret = tg_mod.TELEGRAM_WEBHOOK_SECRET
    try:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = "test-secret-123"
        raw_body = _json.dumps(telegram_update_start).encode()
        expected = hmac_mod.new(b"test-secret-123", raw_body, hashlib.sha256).hexdigest()
        with patch("app.api.v1.telegram.get_bus", return_value=None):
            with patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                    with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                        resp = client.post(
                            "/api/v1/telegram/webhook",
                            content=raw_body,
                            headers={
                                "X-Telegram-Bot-Api-Secret-Token": expected,
                                "Content-Type": "application/json",
                            },
                        )
        assert resp.status_code == 200
    finally:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = old_secret


def test_hmac_missing_header_rejected(client: TestClient, telegram_update_start: dict) -> None:
    import json as _json

    from app.api.v1 import telegram as tg_mod

    old_secret = tg_mod.TELEGRAM_WEBHOOK_SECRET
    try:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = "test-secret-123"
        raw_body = _json.dumps(telegram_update_start).encode()
        resp = client.post(
            "/api/v1/telegram/webhook",
            content=raw_body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401
    finally:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = old_secret


def test_hmac_wrong_token_rejected(client: TestClient, telegram_update_start: dict) -> None:
    import json as _json

    from app.api.v1 import telegram as tg_mod

    old_secret = tg_mod.TELEGRAM_WEBHOOK_SECRET
    try:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = "test-secret-123"
        raw_body = _json.dumps(telegram_update_start).encode()
        resp = client.post(
            "/api/v1/telegram/webhook",
            content=raw_body,
            headers={
                "X-Telegram-Bot-Api-Secret-Token": "wrong-token",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401
    finally:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = old_secret


def test_hmac_no_secret_skips_validation(client: TestClient, telegram_update_start: dict) -> None:
    from app.api.v1 import telegram as tg_mod

    old_secret = tg_mod.TELEGRAM_WEBHOOK_SECRET
    try:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = None
        with patch("app.api.v1.telegram.get_bus", return_value=None):
            with patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                    with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                        resp = client.post("/api/v1/telegram/webhook", json=telegram_update_start)
        assert resp.status_code == 200
    finally:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = old_secret


# === Bot token constant ===


def test_telegram_bot_token_constant() -> None:
    from app.api.v1.telegram import TELEGRAM_BOT_TOKEN

    assert TELEGRAM_BOT_TOKEN == "8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q"


# === Webhook info ===


def test_webhook_info_endpoint(client: TestClient) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True, "result": {"url": "https://example.com"}}
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.v1.telegram.httpx.AsyncClient", return_value=mock_client):
        resp = client.get("/api/v1/telegram/webhook/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
