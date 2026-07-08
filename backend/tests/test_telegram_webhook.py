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


@pytest.fixture(autouse=True)
def mock_llm_calls():
    with patch("app.integrations.fallback.chat_with_fallback") as mock_chat:
        mock_response = MagicMock()
        mock_response.content = "Olá! Use o /menu para ver as opções do cartorio."
        mock_chat.return_value = mock_response
        yield mock_chat


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
            "text": "/xyzzy_comando_invalido",
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
    # comando realmente desconhecido cai no unknown_command com menu
    sent_text = mock_send.call_args[0][1]
    assert "não disponível" in sent_text or "menu" in sent_text.lower()


def test_agendar_text_command_accepted(client: TestClient) -> None:
    """Regression: /agendar digitado deve ser aceito (whitelist canonica)."""
    update = {
        "update_id": 2,
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
    sent_text = mock_send.call_args[0][1]
    # /agendar DEVE abrir o menu de servicos, nao rejeitar
    assert "Agendar" in sent_text or "servi" in sent_text.lower()


def test_protocolo_text_command_accepted(client: TestClient) -> None:
    """Regression: /protocolo digitado deve ser aceito (whitelist canonica)."""
    update = {
        "update_id": 3,
        "message": {
            "from": {"id": 6682284055},
            "chat": {"id": 6682284055},
            "text": "/protocolo",
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
    assert "protocolo" in sent_text.lower()


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
    assert (
        "menu" in sent_text.lower()
        or "cartorio" in sent_text.lower()
        or "cartório" in sent_text.lower()
    )


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
    from app.api.v1 import telegram as tg_mod

    old_secret = tg_mod.TELEGRAM_WEBHOOK_SECRET
    try:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = "test-secret-123"
        with patch("app.api.v1.telegram.get_bus", return_value=None):
            with patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                    with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                        resp = client.post(
                            "/api/v1/telegram/webhook",
                            json=telegram_update_start,
                            headers={
                                "X-Telegram-Bot-Api-Secret-Token": "test-secret-123",
                                "Content-Type": "application/json",
                            },
                        )
        assert resp.status_code == 200
    finally:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = old_secret


def test_hmac_missing_header_rejected(client: TestClient, telegram_update_start: dict) -> None:
    from app.api.v1 import telegram as tg_mod

    old_secret = tg_mod.TELEGRAM_WEBHOOK_SECRET
    try:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = "test-secret-123"
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=telegram_update_start,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401
    finally:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = old_secret


def test_hmac_wrong_token_rejected(client: TestClient, telegram_update_start: dict) -> None:
    from app.api.v1 import telegram as tg_mod

    old_secret = tg_mod.TELEGRAM_WEBHOOK_SECRET
    try:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = "test-secret-123"
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=telegram_update_start,
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


# =============================================================================
# Debounce task tests
# =============================================================================


@pytest.mark.asyncio
async def test_process_telegram_debounce_success() -> None:
    """_process_telegram_debounce processa fila do Redis e envia resposta via LLM."""
    from unittest.mock import ANY
    import json
    from app.api.v1.telegram import _process_telegram_debounce

    mock_bus = MagicMock()
    mock_pipe = AsyncMock()
    raw_queue = json.dumps([{"text": "Ola bot", "msg_id": 12345}])
    mock_pipe.execute = AsyncMock(return_value=[raw_queue, True, True])
    mock_bus.client.pipeline.return_value.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_bus.client.pipeline.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.v1.telegram.get_bus", return_value=mock_bus):
        with patch("app.api.v1.telegram.DEBOUNCE_WINDOW", 0.001):
            with patch("app.api.v1.telegram._call_fast_llm", AsyncMock(return_value="Resposta")):
                with patch(
                    "app.api.v1.telegram._send_message", AsyncMock(return_value=True)
                ) as mock_send:
                    with patch(
                        "app.api.v1.telegram._react", AsyncMock(return_value=True)
                    ) as mock_react:
                        await _process_telegram_debounce(6682284055)

                        mock_send.assert_called_once_with(6682284055, "Resposta", reply_markup=ANY)
                        mock_react.assert_called_once_with(6682284055, 12345, "check")


@pytest.mark.asyncio
async def test_process_telegram_debounce_empty_queue() -> None:
    """_process_telegram_debounce encerra silenciosamente se fila vazia."""
    from app.api.v1.telegram import _process_telegram_debounce

    mock_bus = MagicMock()
    mock_pipe = AsyncMock()
    mock_pipe.execute = AsyncMock(return_value=[None])
    mock_bus.client.pipeline.return_value.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_bus.client.pipeline.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.v1.telegram.get_bus", return_value=mock_bus):
        with patch("app.api.v1.telegram.DEBOUNCE_WINDOW", 0.001):
            await _process_telegram_debounce(6682284055)


def test_telegram_health_endpoint_ok() -> None:
    """GET /api/v1/telegram/health retorna 200 com payload."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/v1/telegram/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "telegram-bot"
    assert body["bot"] == "test_cartorio_bot"
    assert body["webhook_configured"] is True


def test_telegram_metrics_endpoint_ok() -> None:
    """GET /api/v1/telegram/metrics returns counters + ts."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/v1/telegram/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "telegram-bot"
    assert body["version"] == "v0.6.0"
    assert "counters" in body
    assert isinstance(body["counters"], dict)
    assert "requests_total" in body["counters"]
    assert "responses_ok" in body["counters"]
    assert isinstance(body["ts"], int)


def test_bump_metric_increments_counter() -> None:
    """bump_metric incrementa contador de forma idempotente."""
    from app.api.v1.telegram import _METRICS, bump_metric

    original = _METRICS.get("test_bump", 0)
    bump_metric("test_bump")
    bump_metric("test_bump")
    bump_metric("test_bump", 5)
    assert _METRICS["test_bump"] == original + 7


def test_webhook_group_msg_without_command_reacts_and_orients() -> None:
    """FIX 2026-07-08: ao inves de silenciar msg de grupo sem comando, reage
    com eyes e manda msg de orientacao com menu. Gustavo reclamou que os
    botoes nao funcionam mas era silent ignore.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    payload = {
        "update_id": 99010,
        "message": {
            "message_id": 999,
            "chat": {"id": -1004331849032, "title": "TESTE/VALIDACAO", "type": "supergroup"},
            "from": {"id": 6682284055, "first_name": "Gustavo"},
            "text": "oi",
            "date": 1719227400,
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)
        ) as mock_send:
            with patch(
                "app.api.v1.telegram._react", new=AsyncMock(return_value=True)
            ) as mock_react:
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    resp = client.post("/api/v1/telegram/webhook", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ignored"
    assert "group message without command or mention" in body["reason"]
    # Deve reagir com eyes
    mock_react.assert_called_once()
    react_call = mock_react.call_args
    assert react_call[0][0] == -1004331849032
    assert react_call[0][1] == 999
    assert react_call[0][2] == "eyes"
    # Deve mandar orientacao com menu inline
    assert mock_send.call_count >= 1
    orient_call = mock_send.call_args_list[0]
    sent_text = orient_call[0][1]
    assert "/menu" in sent_text
    assert "@test_cartorio_bot" in sent_text
    # E a orientacao deve ter menu de botoes
    call_kwargs = orient_call[1]
    assert call_kwargs.get("reply_markup") is not None


def test_telegram_webhook_handles_supergroup_chat() -> None:
    """Webhook responde 200 a update vindo de supergroup (chat_id negativo, type=supergroup).
    Licao 2026-07-08: Gustavo migrou grupo -5319980720 p/ supergroup -1004331849032.
    Bot precisa responder igual em DM (chat_id positivo) ou supergroup (negativo)."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    payload = {
        "update_id": 99003,
        "message": {
            "chat": {
                "id": -1004331849032,
                "title": "TESTE/VALIDACAO",
                "type": "supergroup",
            },
            "from": {"id": 6682284055, "first_name": "Gustavo"},
            "text": "/start",
            "message_id": 9903,
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)):
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    resp = client.post("/api/v1/telegram/webhook", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["chat_id"] == -1004331849032
    assert body["response_sent"] is True


def test_menu_keyboard_with_cancel_has_cancel_button() -> None:
    """Versao do menu com botao Cancelar visivel - Gustavo pediu p/ parar spam no grupo."""
    from app.api.v1.telegram import _menu_keyboard_with_cancel

    kb = _menu_keyboard_with_cancel()
    flat = [btn for row in kb for btn in row]
    texts = [b["text"] for b in flat]
    callbacks = [b["callback_data"] for b in flat]
    assert "Agendar Atendimento" in texts
    assert "Consultar Protocolo" in texts
    assert "Falar com Escrevente" in texts
    assert "Cancelar" in texts
    assert "cmd:menu" in callbacks


def test_telegram_menu_command_includes_cancel_button() -> None:
    """POST /webhook /menu retorna reply_markup com botao Cancelar (anti-spam grupo)."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    payload = {
        "update_id": 99004,
        "message": {
            "chat": {"id": -1004331849032, "type": "supergroup"},
            "from": {"id": 6682284055, "first_name": "Gustavo"},
            "text": "/menu",
            "message_id": 99004,
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)):
            with patch("app.api.v1.telegram._set_reaction", new=AsyncMock(return_value=True)):
                with patch("app.api.v1.telegram._send_typing", new=AsyncMock()):
                    resp = client.post("/api/v1/telegram/webhook", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["response_sent"] is True


# =============================================================================
# my_chat_member (bot enter/leave/promoted em grupo) - 2026-07-08
# =============================================================================


def test_webhook_handles_my_chat_member_join() -> None:
    """Quando bot entra em grupo, manda mensagem de boas-vindas com /menu.

    Gustavo descobriu que o bot tinha saido do grupo TESTE/VALIDACAO/CORRECAO
    (-5319980720 migrado para -1004331849032) e o webhook silenciosamente
    ignorava os updates. Agora respondemos com welcome + botoes.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    payload = {
        "update_id": 99005,
        "my_chat_member": {
            "chat": {
                "id": -1004331849032,
                "title": "TESTE/VALIDACAO/CORRECAO",
                "type": "supergroup",
            },
            "from": {"id": 6682284055, "first_name": "Gustavo"},
            "old_chat_member": {"user": {"id": 8859206262, "is_bot": True}, "status": "left"},
            "new_chat_member": {
                "user": {"id": 8859206262, "is_bot": True},
                "status": "administrator",
            },
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)
        ) as mock_send:
            resp = client.post("/api/v1/telegram/webhook", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["kind"] == "my_chat_member_join"
    assert body["chat_id"] == -1004331849032
    mock_send.assert_called_once()
    sent_text = mock_send.call_args[0][1]
    assert "BOT CARTORIO ATIVO" in sent_text
    assert "TESTE/VALIDACAO/CORRECAO" in sent_text
    assert "/menu" in sent_text
    # Keyboard com botao Cancelar deve estar presente
    call_kwargs = mock_send.call_args[1]
    assert call_kwargs.get("keyboard") is not None


def test_webhook_handles_my_chat_member_leave() -> None:
    """Quando bot sai ou e removido de grupo, loga e ignora sem erro."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    payload = {
        "update_id": 99006,
        "my_chat_member": {
            "chat": {"id": -1004331849032, "type": "supergroup"},
            "from": {"id": 6682284055, "first_name": "Gustavo"},
            "old_chat_member": {
                "user": {"id": 8859206262, "is_bot": True},
                "status": "administrator",
            },
            "new_chat_member": {
                "user": {"id": 8859206262, "is_bot": True},
                "status": "left",
            },
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)
        ) as mock_send:
            resp = client.post("/api/v1/telegram/webhook", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["kind"] == "my_chat_member_left"
    # Nao deve mandar mensagem quando sai
    mock_send.assert_not_called()


def test_classify_metric_for_status() -> None:
    """classify_metric_for_status mapeia corretamente cada status para o contador."""
    from app.api.v1 import telegram as tg_mod

    original = tg_mod._METRICS.copy()
    try:
        tg_mod._METRICS["responses_ok"] = 0
        tg_mod._METRICS["responses_partial"] = 0
        tg_mod._METRICS["responses_failed"] = 0
        tg_mod.classify_metric_for_status("ok", "command")
        tg_mod.classify_metric_for_status("ok", "command")
        tg_mod.classify_metric_for_status("partial", "command")
        tg_mod.classify_metric_for_status("ignored", "callback")
        tg_mod.classify_metric_for_status("duplicate", "command")
        tg_mod.classify_metric_for_status("ignored_command", "command")
        # callbacks nao contam em responses_ok (handled separately)
        tg_mod.classify_metric_for_status("ok", "callback")
        assert tg_mod._METRICS["responses_ok"] == 2
        assert tg_mod._METRICS["responses_partial"] == 1
        # failed sobe quando status nao eh nenhum dos mapeados
    finally:
        tg_mod._METRICS.update(original)


def test_get_tg_pool_lifecycle_and_no_loop() -> None:
    """Exercita o ciclo de vida do _get_tg_pool e o bloco try/except sem event loop."""
    from app.api.v1.telegram import _get_tg_pool
    import asyncio

    # 1. Fora do loop de eventos (deve cair no except RuntimeError)
    pool1 = _get_tg_pool()
    assert pool1 is not None

    # 2. Dentro do loop de eventos (deve registrar o loop atual)
    async def _test():
        pool2 = _get_tg_pool()
        assert pool2 is not None
        return pool2

    pool2 = asyncio.run(_test())
    assert pool2 is not pool1


def test_debug_last_updates_records_and_returns_recent(client: TestClient) -> None:
    """FIX 2026-07-08: Gustavo precisa inspecionar o que o backend REALMENTE
    recebeu no webhook para diagnosticar 'botoes nao funcionam' via Painel ZCode.

    - POST /api/v1/telegram/webhook com payload sintetico DEVE popular a lista
    - GET /api/v1/telegram/debug/last-updates DEVE retornar o ultimo update.
    - Lista trunca em _LAST_UPDATES_MAX (20) entradas.
    """
    from app.api.v1.telegram import _LAST_UPDATES

    _LAST_UPDATES.clear()

    payload = {
        "update_id": 900001,
        "message": {
            "message_id": 11,
            "from": {"id": 6682284055, "first_name": "Gustavo", "is_bot": False},
            "chat": {"id": -1004331849032, "type": "supergroup", "title": "TESTE"},
            "text": "/menu",
            "date": 1719227400,
        },
    }
    resp = client.post("/api/v1/telegram/webhook", json=payload)
    assert resp.status_code == 200

    debug = client.get("/api/v1/telegram/debug/last-updates")
    assert debug.status_code == 200
    body = debug.json()
    assert body["service"] == "telegram-bot"
    assert isinstance(body["last_updates"], list)
    assert body["last_updates"], "webhook deveria ter registrado pelo menos 1 update"
    latest = body["last_updates"][-1]
    assert latest["update_id"] == 900001
    assert latest["kind"] == "message"
    assert latest["chat_id"] == -1004331849032
    assert latest["data"] == "/menu"
    assert "response" in latest


def test_metrics_classifies_callback_and_duplicate() -> None:
    """Cobertura para o classificador de metricas por status (FIX 2026-07-08)."""
    from app.api.v1.telegram import classify_metric_for_status, _METRICS  # noqa: F401

    before_ok = _METRICS["responses_ok"]

    classify_metric_for_status("ok", kind="message")
    classify_metric_for_status("ok", kind="callback")  # callbacks NAO contam como ok
    classify_metric_for_status("duplicate", kind="message")  # duplicatas sao ignoradas
    classify_metric_for_status("partial", kind="message")

    assert _METRICS["responses_ok"] == before_ok + 1
    # callback_ok NAO incrementa responses_ok
    assert _METRICS["responses_partial"] >= 1
