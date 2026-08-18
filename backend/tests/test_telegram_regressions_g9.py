"""Testes de regressao G9 (2026-07-20) — fixes do diagnostico E1 (webhook Telegram).

Cada teste FALHA sem o fix correspondente em app/api/v1/telegram.py / app/main.py:

(a) A3/A4: webhook retorna 200 mesmo com Redis quebrado — get_bus levantando
    ConnectionError (fallback sincrono degraded) e falha no enqueue/lock
    (200 {"status": "degraded"}, nunca 5xx).
(b) A3: JSON invalido vira 200 degraded (nunca 5xx — Telegram faz retry infinito).
(c) A5: dois usuarios no mesmo grupo dentro da janela de debounce -> AMBOS
    processados (metadata chaveada por conv chat:user, nao por chat_id).
(d) A1/A2: sync_telegram_webhook NAO chama setWebhook sem TELEGRAM_WEBHOOK_SECRET;
    com secret configurado, envia secret_token e URL via env TELEGRAM_WEBHOOK_URL.
(e) A6: excecao no debounce envia mensagem de erro amigavel (best-effort) e
    fila vazia inesperada loga warning (antes: silencio total).

Modified by Gustavo Almeida
"""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks

import app.api.v1.telegram as tg


# =============================================================================
# Fakes
# =============================================================================


class _FakePipeline:
    """Pipeline minimo usado pelo debounce (get/delete/delete/execute)."""

    def __init__(self, bus: _FakeBus) -> None:
        self._bus = bus
        self._ops: list[tuple[str, str]] = []

    async def __aenter__(self) -> _FakePipeline:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def get(self, key: str) -> None:
        self._ops.append(("get", key))

    async def delete(self, key: str) -> None:
        self._ops.append(("del", key))

    async def execute(self) -> list:
        out: list = []
        for op, key in self._ops:
            if op == "get":
                out.append(self._bus.store.get(key))
            else:
                out.append(1 if self._bus.store.pop(key, None) is not None else 0)
        return out


class _FakeBus:
    """Bus em memoria com a API minima usada pelo webhook/debounce."""

    def __init__(self, *, broken_get: bool = False) -> None:
        self.store: dict[str, str] = {}
        self.client = self
        self._broken_get = broken_get

    async def set(
        self, key: str, value: str, *, ex: int | None = None, nx: bool = False
    ) -> str | None:
        if nx and key in self.store:
            return None
        self.store[key] = value
        return "OK"

    async def get(self, key: str) -> str | None:
        if self._broken_get:
            raise ConnectionError("redis fora (simulado)")
        return self.store.get(key)

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0

    def pipeline(self, transaction: bool = True) -> _FakePipeline:
        return _FakePipeline(self)


# =============================================================================
# Helpers
# =============================================================================


def _make_request(payload: dict) -> MagicMock:
    req = MagicMock()
    req.json = AsyncMock(return_value=payload)
    return req


def _private_text_update(update_id: int, text: str, chat_id: int = 4242) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "from": {"id": chat_id, "first_name": "Maria"},
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
            "date": 1721308800,
        },
    }


def _group_text_update(update_id: int, user_id: int, text: str, chat_id: int = -100999) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "from": {"id": user_id, "first_name": f"User{user_id}"},
            "chat": {"id": chat_id, "type": "supergroup", "title": "Grupo Teste"},
            "text": text,
            "date": 1721308800,
        },
    }


@pytest.fixture(autouse=True)
def _clean_debounce_metadata():
    tg._DEBOUNCE_METADATA.clear()
    yield
    tg._DEBOUNCE_METADATA.clear()


# =============================================================================
# (a) A3/A4: webhook NUNCA retorna 5xx — Redis quebrado
# =============================================================================


@pytest.mark.asyncio
async def test_webhook_returns_200_when_redis_down() -> None:
    """get_bus levantando ConnectionError NUNCA derruba o webhook (sem fix: 500)."""
    update = _private_text_update(9001, "quanto custa uma procuracao?")
    with (
        patch.object(tg, "get_bus", side_effect=ConnectionError("redis down")),
        patch.object(tg, "_send_typing_fast", new=AsyncMock()),
        patch.object(tg, "_react", new=AsyncMock()),
        patch.object(tg, "_call_cartorio_agent", new=AsyncMock(return_value=("Resposta", None))),
        patch.object(tg, "_send_message", new=AsyncMock(return_value=True)) as send,
    ):
        resp = await tg.telegram_webhook(
            _make_request(update), BackgroundTasks(), None, MagicMock()
        )
    assert resp["status"] == "ok"
    assert resp["degraded"] is True
    send.assert_awaited_once()


@pytest.mark.asyncio
async def test_webhook_returns_200_degraded_when_enqueue_fails() -> None:
    """Falha no enqueue/lock (Redis morrendo no meio) -> 200 degraded (sem fix: 500)."""
    bus = _FakeBus()
    bus.store["tg:lgpd:consent:4242"] = "1"
    update = _private_text_update(9002, "preciso de uma certidao de nascimento")
    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "_send_typing_fast", new=AsyncMock()),
        patch.object(tg, "_react", new=AsyncMock()),
        patch.object(
            tg, "_enqueue_message", new=AsyncMock(side_effect=ConnectionError("redis down"))
        ),
    ):
        resp = await tg.telegram_webhook(
            _make_request(update), BackgroundTasks(), None, MagicMock()
        )
    assert resp["status"] == "degraded"
    assert resp["reason"] == "enqueue_failed"


# =============================================================================
# (b) A3: JSON invalido vira 200 degraded
# =============================================================================


@pytest.mark.asyncio
async def test_webhook_invalid_json_returns_200_degraded() -> None:
    """Body que nao e JSON NUNCA vira 5xx (sem fix: re-raise -> 500)."""
    req = MagicMock()
    req.json = AsyncMock(side_effect=json.JSONDecodeError("Expecting value", "doc", 0))
    resp = await tg.telegram_webhook(req, BackgroundTasks(), None, MagicMock())
    assert resp["status"] == "degraded"
    assert resp["reason"] == "invalid_json"


# =============================================================================
# (c) A5: dois usuarios no mesmo grupo na janela de debounce -> ambos processados
# =============================================================================


@pytest.mark.asyncio
async def test_two_users_same_group_both_processed() -> None:
    """Metadata por conv: 2 usuarios no mesmo grupo recebem resposta (sem fix: so 1)."""
    bus = _FakeBus()
    chat_id = -100999
    conv1, conv2 = f"{chat_id}:111", f"{chat_id}:222"
    bus.store[f"tg:lgpd:consent:{conv1}"] = "1"
    bus.store[f"tg:lgpd:consent:{conv2}"] = "1"
    upd1 = _group_text_update(9101, 111, "@test_cartorio_bot quero agendar", chat_id)
    upd2 = _group_text_update(9102, 222, "@test_cartorio_bot consultar protocolo", chat_id)
    bt = BackgroundTasks()
    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "_send_typing_fast", new=AsyncMock()),
        patch.object(tg, "_react", new=AsyncMock()),
        patch.object(tg, "_client_profile_upsert", new=AsyncMock()),
        patch.object(tg, "_typing_loop", new=AsyncMock()),
        patch.object(tg, "DEBOUNCE_WINDOW", 0),
        patch.object(tg, "_call_cartorio_agent", new=AsyncMock(return_value=("Resposta", None))),
        patch.object(tg, "_send_message", new=AsyncMock(return_value=True)) as send,
    ):
        r1 = await tg.telegram_webhook(_make_request(upd1), bt, None, MagicMock())
        r2 = await tg.telegram_webhook(_make_request(upd2), bt, None, MagicMock())
        assert r1["scheduled"] is True
        assert r2["scheduled"] is True
        # A5: uma entrada de metadata POR CONVERSA (sem fix: 1 entrada por chat_id)
        assert set(tg._DEBOUNCE_METADATA.keys()) == {conv1, conv2}
        assert len(bt.tasks) == 2
        # Roda os debounces (em prod roda via background_tasks pos-response)
        for task in bt.tasks:
            await task()
        # A5: os DOIS usuarios foram processados (sem fix: apenas 1)
        assert send.await_count == 2
        assert f"tg:queue:{conv1}" not in bus.store
        assert f"tg:queue:{conv2}" not in bus.store
        assert tg._DEBOUNCE_METADATA == {}


# =============================================================================
# (d) A1/A2: sync_telegram_webhook nunca registra webhook sem secret
# =============================================================================


@pytest.mark.asyncio
async def test_sync_webhook_aborts_without_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem TELEGRAM_WEBHOOK_SECRET, setWebhook NUNCA e chamado (sem fix: vai sem secret)."""
    monkeypatch.setattr(tg, "TELEGRAM_BOT_TOKEN", "123:test-token")
    monkeypatch.setattr(tg, "TELEGRAM_WEBHOOK_SECRET", None)
    pool = MagicMock()
    pool.post = AsyncMock()
    monkeypatch.setattr(tg, "_get_tg_pool", lambda: pool)

    result = await tg.sync_telegram_webhook()

    assert result["ok"] is False
    assert "secret" in result["reason"].lower()
    pool.post.assert_not_called()


@pytest.mark.asyncio
async def test_sync_webhook_sends_secret_and_env_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Com secret, payload leva secret_token e URL vem de TELEGRAM_WEBHOOK_URL (sem hardcode)."""
    monkeypatch.setattr(tg, "TELEGRAM_BOT_TOKEN", "123:test-token")
    monkeypatch.setattr(tg, "TELEGRAM_WEBHOOK_SECRET", "segredo-de-teste")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_URL", "https://example.test/hook")
    pool = MagicMock()
    pool.post = AsyncMock(return_value=MagicMock(json=lambda: {"ok": True, "description": "ok"}))
    monkeypatch.setattr(tg, "_get_tg_pool", lambda: pool)

    result = await tg.sync_telegram_webhook()

    assert result["ok"] is True
    payload = pool.post.call_args.kwargs["json"]
    assert payload["secret_token"] == "segredo-de-teste"
    assert payload["url"] == "https://example.test/hook"
    assert "poll_answer" in payload["allowed_updates"]


# =============================================================================
# (e) A6: debounce nunca falha em silencio
# =============================================================================


@pytest.mark.asyncio
async def test_debounce_exception_sends_friendly_error() -> None:
    """Excecao no debounce envia msg de erro amigavel best-effort (sem fix: silencio)."""
    bus = _FakeBus()
    chat_id = 777
    conv = str(chat_id)
    bus.store[f"tg:queue:{conv}"] = json.dumps([{"text": "oi", "msg_id": 5}])
    tg._DEBOUNCE_METADATA[conv] = {"user_id": 777}
    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "DEBOUNCE_WINDOW", 0),
        patch.object(tg, "_typing_loop", new=AsyncMock()),
        patch.object(tg, "_client_profile_upsert", new=AsyncMock()),
        patch.object(tg, "_call_cartorio_agent", new=AsyncMock(side_effect=RuntimeError("boom"))),
        patch.object(tg, "_send_message", new=AsyncMock(return_value=True)) as send,
    ):
        await tg._process_telegram_debounce(chat_id, conv)
    send.assert_awaited_once()
    assert "instabilidade" in send.call_args.args[1].lower()


@pytest.mark.asyncio
async def test_debounce_empty_queue_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Fila vazia inesperada loga warning (sem fix: retorno silencioso)."""
    bus = _FakeBus()
    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "DEBOUNCE_WINDOW", 0),
        patch.object(tg, "_typing_loop", new=AsyncMock()),
        caplog.at_level(logging.WARNING, logger="app.api.v1.telegram"),
    ):
        await tg._process_telegram_debounce(888, "888")
    assert any("fila vazia" in rec.message for rec in caplog.records)
