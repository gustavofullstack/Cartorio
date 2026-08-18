"""P0 #194 — poll LGPD nativa + roteamento apos consentimento.

Bateria curta e focada. Nao substitui a suite completa.

Cobre:
1. POLL YES persiste consentimento e nao reabre o gate
2. POLL NO nao concede consentimento
3. retry do YES e idempotente
4. fallback textual "sim"
5. usuario ja consentido nao recebe LGPD/poll de novo
6. poll ativa nao duplica nem naga a cada webhook
7. aviso inicial nao impede o pipeline
8. primeira pergunta pos-onboarding agenda o router
9. segunda pergunta tambem agenda o router
10. webhook duplicado nao bloqueia a proxima mensagem
11. exception no debounce libera o lock
12. prompt stale com consent=true nao reabre o gate
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks

import app.api.v1.telegram as tg


class _FakePipeline:
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
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.client = self

    async def set(
        self, key: str, value: str, *, ex: int | None = None, nx: bool = False
    ) -> str | None:
        if nx and key in self.store:
            return None
        self.store[key] = value
        return "OK"

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0

    def pipeline(self, transaction: bool = True) -> _FakePipeline:
        return _FakePipeline(self)


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


def _poll_answer_update(
    update_id: int,
    *,
    poll_id: str,
    option: int,
    user_id: int = 4242,
) -> dict:
    return {
        "update_id": update_id,
        "poll_answer": {
            "poll_id": poll_id,
            "option_ids": [option],
            "user": {"id": user_id},
        },
    }


@pytest.fixture(autouse=True)
def _clean_debounce_metadata() -> None:
    tg._DEBOUNCE_METADATA.clear()
    yield
    tg._DEBOUNCE_METADATA.clear()


async def _post(
    bus: _FakeBus,
    payload: dict,
    *,
    send: AsyncMock | None = None,
    poll: AsyncMock | None = None,
    agent: AsyncMock | None = None,
    background: BackgroundTasks | None = None,
) -> tuple[dict, AsyncMock, AsyncMock]:
    send = send or AsyncMock(return_value=True)
    poll = poll or AsyncMock(return_value=True)
    agent = agent or AsyncMock(return_value=("Resposta Pietra", None))
    bt = background or BackgroundTasks()
    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "_send_typing_fast", new=AsyncMock()),
        patch.object(tg, "_react", new=AsyncMock()),
        patch.object(tg, "_send_message", new=send),
        patch.object(tg, "_send_poll", new=poll),
        patch.object(tg, "_call_cartorio_agent", new=agent),
        patch.object(tg, "_client_profile_upsert", new=AsyncMock()),
        patch.object(tg, "_typing_loop", new=AsyncMock()),
        patch.object(tg, "DEBOUNCE_WINDOW", 0),
    ):
        resp = await tg.telegram_webhook(_make_request(payload), bt, None, MagicMock())
    return resp, send, poll


def _poll_texts(send: AsyncMock) -> list[str]:
    return [str(c.args[1]) for c in send.await_args_list if len(c.args) > 1]


def _consent_key(chat_id: int = 4242) -> str:
    return f"tg:lgpd:consent:{chat_id}"


@pytest.mark.asyncio
async def test_poll_yes_persists_consent_and_closes_gate() -> None:
    bus = _FakeBus()
    bus.store["tg:lgpd:poll:poll-001"] = "4242"
    resp, send, poll = await _post(bus, _poll_answer_update(1, poll_id="poll-001", option=0))
    assert resp["kind"] == "poll_answer"
    assert bus.store.get(_consent_key()) == "1"
    assert poll.await_count == 0
    assert any("confirmado" in t.lower() for t in _poll_texts(send))

    follow, send2, poll2 = await _post(
        bus, _private_text_update(2, "Quanto custa reconhecer firma?")
    )
    assert follow.get("kind") != "lgpd_gate"
    assert follow.get("scheduled") is True
    assert poll2.await_count == 0
    assert not any("lgpd" in t.lower() and "enquete" in t.lower() for t in _poll_texts(send2))


@pytest.mark.asyncio
async def test_poll_no_does_not_grant_consent() -> None:
    bus = _FakeBus()
    bus.store["tg:lgpd:poll:poll-002"] = "4242"
    resp, send, poll = await _post(bus, _poll_answer_update(3, poll_id="poll-002", option=1))
    assert resp["kind"] == "poll_answer"
    assert _consent_key() not in bus.store
    assert poll.await_count == 0
    assert any("nao" in t.lower() or "não" in t.lower() for t in _poll_texts(send))


@pytest.mark.asyncio
async def test_poll_yes_retry_is_idempotent() -> None:
    bus = _FakeBus()
    bus.store["tg:lgpd:poll:poll-003"] = "4242"
    first, send1, _ = await _post(bus, _poll_answer_update(4, poll_id="poll-003", option=0))
    assert first["kind"] == "poll_answer"
    assert bus.store.get(_consent_key()) == "1"
    retry, send2, poll2 = await _post(bus, _poll_answer_update(5, poll_id="poll-003", option=0))
    assert retry["kind"] == "poll_answer"
    assert retry.get("idempotent") is True
    assert bus.store.get(_consent_key()) == "1"
    assert poll2.await_count == 0
    assert send2.await_count == 0


@pytest.mark.asyncio
async def test_fallback_sim_grants_consent() -> None:
    bus = _FakeBus()
    resp, send, poll = await _post(bus, _private_text_update(6, " sim "))
    assert resp["kind"] == "lgpd_consent"
    assert bus.store.get(_consent_key()) == "1"
    assert any("confirmado" in t.lower() for t in _poll_texts(send))
    assert poll.await_count == 0


@pytest.mark.asyncio
async def test_already_consented_does_not_receive_lgpd_or_poll() -> None:
    bus = _FakeBus()
    bus.store[_consent_key()] = "1"
    resp, send, poll = await _post(bus, _private_text_update(7, "Oi"))
    assert resp.get("kind") != "lgpd_gate"
    assert resp.get("scheduled") is True
    assert poll.await_count == 0
    assert not any("enquete" in t.lower() or "autoriza" in t.lower() for t in _poll_texts(send))


@pytest.mark.asyncio
async def test_active_poll_does_not_duplicate_or_nag() -> None:
    bus = _FakeBus()
    first, send1, poll1 = await _post(bus, _private_text_update(8, "Oi"))
    assert first["kind"] in {"lgpd_gate", "lgpd_prompt"}
    assert poll1.await_count == 1
    question = poll1.await_args.args[1]
    assert "concorda com o tratamento" in question.lower()
    assert poll1.await_args.args[2] == ["Sim", "Nao"]

    second, send2, poll2 = await _post(
        bus, _private_text_update(9, "Quanto custa reconhecer firma?")
    )
    assert second["kind"] == "lgpd_gate"
    assert poll2.await_count == 0
    assert send2.await_count == 0


@pytest.mark.asyncio
async def test_initial_notice_does_not_kill_pipeline() -> None:
    bus = _FakeBus()
    await _post(bus, _private_text_update(10, "sim"))
    assert bus.store.get(_consent_key()) == "1"
    follow, _, poll = await _post(bus, _private_text_update(11, "Quanto custa reconhecer firma?"))
    assert follow.get("scheduled") is True
    assert follow.get("kind") != "lgpd_consent"
    assert poll.await_count == 0


@pytest.mark.asyncio
async def test_first_and_second_post_onboarding_questions_reach_router() -> None:
    bus = _FakeBus()
    bus.store[_consent_key()] = "1"
    first, _, _ = await _post(bus, _private_text_update(12, "Quanto custa reconhecer firma?"))
    assert first.get("scheduled") is True
    assert "tg:lock:4242" in bus.store
    assert "Quanto custa reconhecer firma?" in bus.store["tg:queue:4242"]

    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "DEBOUNCE_WINDOW", 0),
        patch.object(tg, "_typing_loop", new=AsyncMock()),
        patch.object(tg, "_client_profile_upsert", new=AsyncMock()),
        patch.object(
            tg, "_call_cartorio_agent", new=AsyncMock(return_value=("Firma custa X", None))
        ),
        patch.object(tg, "_send_message", new=AsyncMock(return_value=True)) as send,
        patch.object(tg, "_react", new=AsyncMock()),
    ):
        await tg._process_telegram_debounce(4242, "4242")
    assert send.await_count == 1
    assert "Firma custa X" in send.await_args.args[1]
    assert "tg:lock:4242" not in bus.store

    second, _, _ = await _post(bus, _private_text_update(13, "E autenticacao?"))
    assert second.get("scheduled") is True
    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "DEBOUNCE_WINDOW", 0),
        patch.object(tg, "_typing_loop", new=AsyncMock()),
        patch.object(tg, "_client_profile_upsert", new=AsyncMock()),
        patch.object(
            tg, "_call_cartorio_agent", new=AsyncMock(return_value=("Autenticacao custa Y", None))
        ),
        patch.object(tg, "_send_message", new=AsyncMock(return_value=True)) as send2,
        patch.object(tg, "_react", new=AsyncMock()),
    ):
        await tg._process_telegram_debounce(4242, "4242")
    assert send2.await_count == 1
    assert "Autenticacao custa Y" in send2.await_args.args[1]


@pytest.mark.asyncio
async def test_duplicate_webhook_does_not_block_next_message() -> None:
    bus = _FakeBus()
    bus.store[_consent_key()] = "1"
    first, _, _ = await _post(bus, _private_text_update(14, "Quanto custa reconhecer firma?"))
    assert first.get("scheduled") is True
    dup, _, _ = await _post(bus, _private_text_update(14, "Quanto custa reconhecer firma?"))
    assert dup["status"] == "duplicate"
    nxt, _, poll = await _post(bus, _private_text_update(15, "E autenticacao?"))
    assert nxt.get("status") == "ok"
    assert nxt.get("kind") != "lgpd_gate"
    assert poll.await_count == 0


@pytest.mark.asyncio
async def test_debounce_exception_releases_lock_and_next_message_is_processable() -> None:
    bus = _FakeBus()
    conv = "4242"
    bus.store[f"tg:queue:{conv}"] = json.dumps([{"text": "oi", "msg_id": 1}])
    bus.store[f"tg:lock:{conv}"] = "1"
    tg._DEBOUNCE_METADATA[conv] = {"user_id": 4242}
    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "DEBOUNCE_WINDOW", 0),
        patch.object(tg, "_typing_loop", new=AsyncMock()),
        patch.object(tg, "_client_profile_upsert", new=AsyncMock()),
        patch.object(tg, "_call_cartorio_agent", new=AsyncMock(side_effect=RuntimeError("boom"))),
        patch.object(tg, "_send_message", new=AsyncMock(return_value=True)),
    ):
        await tg._process_telegram_debounce(4242, conv)
    assert f"tg:lock:{conv}" not in bus.store

    bus.store[_consent_key()] = "1"
    follow, _, _ = await _post(bus, _private_text_update(16, "E autenticacao?"))
    assert follow.get("scheduled") is True


@pytest.mark.asyncio
async def test_stale_prompt_with_durable_consent_does_not_reopen_gate() -> None:
    bus = _FakeBus()
    bus.store[_consent_key()] = "1"
    bus.store["tg:lgpd:prompt:4242"] = "1"
    bus.store["tg:lgpd:active_poll:4242"] = "poll-old"
    resp, send, poll = await _post(bus, _private_text_update(17, "Quanto custa reconhecer firma?"))
    assert resp.get("kind") != "lgpd_gate"
    assert resp.get("scheduled") is True
    assert poll.await_count == 0
    assert send.await_count == 0
