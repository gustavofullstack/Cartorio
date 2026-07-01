"""Testes do endpoint Telegram webhook (turn 47 - state machine).

Cobre:
- Comandos nativos (/start, /menu, /agendar, /protocolo, /emolumento, /lgpd)
- State machine (Redis) para fluxos multi-passo
- Tools MCP-style (agendar, consultar protocolo, calcular emolumento)
- LLM rapido para intent nao-mapeado
- PII scrub (camada 1 + 3)
- HMAC validation (secret_token)
- SEMPRE retorna 200 (evita retry infinito Telegram)
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def telegram_update_start() -> dict:
    """Update com /start."""
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
    """Update de texto livre."""
    return {
        "update_id": 123456,
        "message": {
            "message_id": 1,
            "from": {"id": 6682284055, "first_name": "Joao", "is_bot": False},
            "chat": {"id": 6682284055, "type": "private"},
            "text": "Quanto custa uma certidao?",
            "date": 1719227400,
        },
    }


# ── Comandos nativos (zero LLM) ────────────────────────────────────


def test_webhook_start_command(client: TestClient, telegram_update_start: dict) -> None:
    """Comando /start retorna saudacao sem chamar LLM."""
    with patch("app.api.v1.telegram.get_bus", return_value=None):  # Redis offline
        with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)) as mock_send:
            resp = client.post("/api/v1/telegram/webhook", json=telegram_update_start)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["response_sent"] is True
    mock_send.assert_called_once()
    sent_text = mock_send.call_args[0][1]
    assert "Cartório 2º Ofício" in sent_text
    assert "/agendar" in sent_text


def test_webhook_menu_command(client: TestClient) -> None:
    """Comando /menu retorna menu principal sem chamar LLM."""
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
        with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)) as mock_send:
            resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "Escolha uma opção" in sent_text
    assert "/agendar" in sent_text


def test_webhook_agendar_command(client: TestClient) -> None:
    """Comando /agendar entra no state AGENDAR_SERVICO e retorna menu agendamento."""
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
        with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)) as mock_send:
            resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "Reconhecimento de firma" in sent_text or "Qual serviço" in sent_text
    assert "1." in sent_text


def test_webhook_protocolo_command(client: TestClient) -> None:
    """Comando /protocolo entra no state PROTOCOLO."""
    update = {
        "update_id": 1,
        "message": {
            "from": {"id": 6682284055},
            "chat": {"id": 6682284055},
            "text": "/protocolo",
            "date": 1719227400,
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)) as mock_send:
            resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "Informe o número do protocolo" in sent_text


def test_webhook_emolumento_command(client: TestClient) -> None:
    """Comando /emolumento entra no state EMOLUMENTO_TIPO."""
    update = {
        "update_id": 1,
        "message": {
            "from": {"id": 6682284055},
            "chat": {"id": 6682284055},
            "text": "/emolumento",
            "date": 1719227400,
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)) as mock_send:
            resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "Emolumentos" in sent_text
    assert "1." in sent_text


def test_webhook_lgpd_command(client: TestClient) -> None:
    """Comando /lgpd entra no state LGPD."""
    update = {
        "update_id": 1,
        "message": {
            "from": {"id": 6682284055},
            "chat": {"id": 6682284055},
            "text": "/lgpd",
            "date": 1719227400,
        },
    }
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)) as mock_send:
            resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "LGPD" in sent_text
    assert "Acesso" in sent_text


def test_webhook_cancelar_command(client: TestClient) -> None:
    """Comando /cancelar limpa estado e volta ao menu."""
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
        with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)) as mock_send:
            resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "cancelada" in sent_text.lower()


# ── State machine ──────────────────────────────────────────────────


def test_webhook_agendar_flow(client: TestClient) -> None:
    """Fluxo completo de agendamento via state machine (com Redis mockado)."""
    # Mock Redis bus para persistir estado entre chamadas
    mock_bus = AsyncMock()
    # Simula Redis client com setex, get, delete
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # state inicial: IDLE
    mock_bus.client = mock_redis

    step_texts = ["/agendar", "1", "15/07/2026", "14:30"]
    for i, step_text in enumerate(step_texts):
        # A cada step, atualiza o retorno do get conforme o estado esperado
        if i == 0:
            mock_redis.get.return_value = None  # IDLE
        elif i == 1:
            mock_redis.get.return_value = b'{"state":"agendar:servico","data":{}}'
        elif i == 2:
            mock_redis.get.return_value = b'{"state":"agendar:data","data":{"servico":"reconhecimento_firma","servico_nome":"Reconhecimento de Firma","valor":"R$ 8,50"}}'
        elif i == 3:
            mock_redis.get.return_value = b'{"state":"agendar:hora","data":{"servico":"reconhecimento_firma","servico_nome":"Reconhecimento de Firma","valor":"R$ 8,50","data":"2026-07-15"}}'

        update = {
            "update_id": 1,
            "message": {
                "from": {"id": 6682284055},
                "chat": {"id": 6682284055},
                "text": step_text,
                "date": 1719227400,
            },
        }
        with patch("app.api.v1.telegram.get_bus", return_value=mock_bus):
            with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)) as mock_send:
                with patch("app.api.v1.telegram._tool_agendar", new=AsyncMock(
                    return_value={"numero": "2026-000123"}
                )):
                    resp = client.post("/api/v1/telegram/webhook", json=update)
        assert resp.status_code == 200
        if step_text == "14:30":  # final step - agendamento confirmado
            sent_text = mock_send.call_args[0][1]
            assert "Protocolo" in sent_text or "confirmado" in sent_text
        elif step_text == "/agendar":
            sent_text = mock_send.call_args[0][1]
            assert "Reconhecimento" in sent_text or "Qual serviço" in sent_text


# ── LLM rapido (texto livre, sem comando nem state) ────────────────


def test_webhook_uses_fast_llm_for_free_text(
    client: TestClient, telegram_update_text: dict
) -> None:
    """Texto livre (sem comando, sem state) usa LLM rapido."""
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._call_fast_llm", new=AsyncMock(
                return_value="Emolumentos variam conforme o servico. Use /emolumento para consultar."
            )
        ) as mock_llm:
            with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)):
                resp = client.post("/api/v1/telegram/webhook", json=telegram_update_text)
    assert resp.status_code == 200
    mock_llm.assert_called_once()


def test_webhook_llm_fallback_when_llm_fails(
    client: TestClient, telegram_update_text: dict
) -> None:
    """Se LLM falha, retorna fallback message."""
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._call_fast_llm", new=AsyncMock(return_value="")
        ):
            with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)) as mock_send:
                resp = client.post("/api/v1/telegram/webhook", json=telegram_update_text)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "/menu" in sent_text or "escrevente" in sent_text


# ── PII Scrubbing ──────────────────────────────────────────────────


def test_webhook_scrubs_pii_in_message(client: TestClient) -> None:
    """Mensagem com CPF e' scrubbed antes do LLM."""
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
        with patch(
            "app.api.v1.telegram._call_fast_llm", new=AsyncMock(return_value="Ok")
        ) as mock_llm:
            with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)):
                resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    call_args = mock_llm.call_args
    text_sent = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")
    assert "[CPF_REDACTED]" in text_sent or "123.456.789-09" not in text_sent


def test_webhook_scrubs_pii_in_response(client: TestClient) -> None:
    """Resposta com PII e' scrubbed antes de enviar ao Telegram."""
    update = {
        "update_id": 1,
        "message": {
            "from": {"id": 6682284055},
            "chat": {"id": 6682284055},
            "text": "Qual meu CPF?",
            "date": 1719227400,
        },
    }
    pii_response = "Seu CPF e 111.222.333-44, Joao da Silva"
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        with patch(
            "app.api.v1.telegram._call_fast_llm", new=AsyncMock(return_value=pii_response)
        ):
            with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)) as mock_send:
                resp = client.post("/api/v1/telegram/webhook", json=update)
    assert resp.status_code == 200
    sent_text = mock_send.call_args[0][1]
    assert "111.222.333-44" not in sent_text


# ── Non-text updates ───────────────────────────────────────────────


def test_webhook_ignores_non_text_update(client: TestClient) -> None:
    """Update sem text/chat_id (ex: sticker) e' ignorado."""
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
    assert data["reason"] == "non-text update"


# ── HMAC validation ────────────────────────────────────────────────


def test_hmac_valid_secret_accepted(client: TestClient, telegram_update_start: dict) -> None:
    """HMAC valido e aceito quando secret configurado."""
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
            with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)):
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
    """Sem header HMAC quando secret configurado retorna 401."""
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
    """HMAC invalido retorna 401."""
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
    """Sem secret configurado, HMAC e ignorado (dev mode)."""
    from app.api.v1 import telegram as tg_mod

    old_secret = tg_mod.TELEGRAM_WEBHOOK_SECRET
    try:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = None
        with patch("app.api.v1.telegram.get_bus", return_value=None):
            with patch("app.api.v1.telegram._send_telegram_message", new=AsyncMock(return_value=True)):
                resp = client.post("/api/v1/telegram/webhook", json=telegram_update_start)
        assert resp.status_code == 200
    finally:
        tg_mod.TELEGRAM_WEBHOOK_SECRET = old_secret


# ── Telegram send ──────────────────────────────────────────────────


def test_send_telegram_message_success() -> None:
    """_send_telegram_message envia msg com sucesso."""
    import asyncio
    from unittest.mock import MagicMock, patch

    from app.api.v1.telegram import _send_telegram_message

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.v1.telegram.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(_send_telegram_message(12345, "Ola!"))
    assert result is True


def test_send_telegram_message_api_error_returns_false() -> None:
    """_send_telegram_message retorna False quando API retorna erro (sem exception)."""
    import asyncio
    from unittest.mock import MagicMock, patch

    from app.api.v1.telegram import _send_telegram_message

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.v1.telegram.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(_send_telegram_message(12345, "Ola!"))
    assert result is False


# ── Webhook info endpoint ──────────────────────────────────────────


def test_webhook_info_endpoint(client: TestClient) -> None:
    """GET /webhook/info retorna info do webhook."""
    from unittest.mock import MagicMock, patch

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


# ── Bot token constant ─────────────────────────────────────────────


def test_telegram_bot_token_constant() -> None:
    """Token do bot esta hardcoded (NAO rotacionar)."""
    from app.api.v1.telegram import TELEGRAM_BOT_TOKEN

    assert TELEGRAM_BOT_TOKEN == "8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q"
