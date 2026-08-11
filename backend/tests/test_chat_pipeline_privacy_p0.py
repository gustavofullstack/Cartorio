"""Regressoes P0 para privacidade do historico compartilhado do bot."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chat_pipeline import (
    Channel,
    OutboundMessage,
    check_idempotency,
    check_rate_limit,
    enqueue_message,
    fetch_queue,
    hash_content,
    process_message,
    process_debounced,
    pseudonymize_conversation_id,
)
from app.services.chat_pipeline import InboundMessage


TEST_HMAC_KEY = "test-chat-pipeline-hmac-key-at-least-32-chars"
RAW_CONVERSATION_ID = "private-conversation-token"
RAW_UPDATE_ID = "private-update-token"


def test_pseudonymize_conversation_id_is_stable_and_domain_separated() -> None:
    whatsapp_id = pseudonymize_conversation_id(
        Channel.WHATSAPP,
        RAW_CONVERSATION_ID,
        hmac_key=TEST_HMAC_KEY,
    )
    repeated = pseudonymize_conversation_id(
        Channel.WHATSAPP,
        RAW_CONVERSATION_ID,
        hmac_key=TEST_HMAC_KEY,
    )
    telegram_id = pseudonymize_conversation_id(
        Channel.TELEGRAM,
        RAW_CONVERSATION_ID,
        hmac_key=TEST_HMAC_KEY,
    )

    assert whatsapp_id == repeated
    assert whatsapp_id != telegram_id
    assert len(whatsapp_id) == 64
    assert RAW_CONVERSATION_ID not in whatsapp_id


def test_pseudonymize_conversation_id_fails_closed_without_configured_key(monkeypatch) -> None:
    from app.services import chat_pipeline

    monkeypatch.setattr(chat_pipeline.settings, "pietra_conversation_hmac_key", "")
    with pytest.raises(RuntimeError, match="conversation HMAC key is not configured"):
        pseudonymize_conversation_id(
            Channel.WHATSAPP,
            RAW_CONVERSATION_ID,
        )


def test_pseudonymize_conversation_id_rejects_short_key() -> None:
    with pytest.raises(RuntimeError, match="conversation HMAC key is not configured"):
        pseudonymize_conversation_id(
            Channel.WHATSAPP,
            RAW_CONVERSATION_ID,
            hmac_key="short-key",
        )


@pytest.mark.asyncio
async def test_queue_and_rate_limit_keys_never_contain_raw_sender(monkeypatch) -> None:
    from app.services import chat_pipeline

    monkeypatch.setattr(chat_pipeline.settings, "pietra_conversation_hmac_key", TEST_HMAC_KEY)
    bus = MagicMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[1, 1, True])
    bus.client.pipeline.return_value = pipe
    bus.client.set = AsyncMock(return_value=True)
    message = InboundMessage(
        channel=Channel.WHATSAPP,
        sender_id=RAW_CONVERSATION_ID,
        text="mensagem sem dados pessoais",
    )

    with patch("app.services.chat_pipeline.get_bus", return_value=bus):
        assert await enqueue_message(message) is True
        pipe.execute.return_value = [[b'{"text":"mensagem sem dados pessoais"}'], 1]
        queued_messages = await fetch_queue(Channel.WHATSAPP, RAW_CONVERSATION_ID)
        assert await check_rate_limit(RAW_CONVERSATION_ID, Channel.WHATSAPP) is True
        assert (
            await check_idempotency(
                "private-update-token",
                Channel.WHATSAPP,
                RAW_CONVERSATION_ID,
            )
            is False
        )

    queue_key = pipe.rpush.call_args.args[0]
    fetch_key = pipe.lrange.call_args.args[0]
    rate_limit_key = bus.client.set.await_args_list[0].args[0]
    idempotency_key = bus.client.set.await_args_list[1].args[0]
    assert queued_messages == [{"text": "mensagem sem dados pessoais"}]
    assert fetch_key == queue_key
    assert RAW_CONVERSATION_ID not in queue_key
    assert RAW_CONVERSATION_ID not in rate_limit_key
    assert RAW_CONVERSATION_ID not in idempotency_key
    assert "private-update-token" not in idempotency_key
    assert pseudonymize_conversation_id(Channel.WHATSAPP, RAW_CONVERSATION_ID) in queue_key
    assert pseudonymize_conversation_id(Channel.WHATSAPP, RAW_CONVERSATION_ID) in rate_limit_key
    assert pseudonymize_conversation_id(Channel.WHATSAPP, RAW_CONVERSATION_ID) in idempotency_key


@pytest.mark.asyncio
async def test_mute_lookup_uses_conversation_pseudonym(monkeypatch) -> None:
    from app.services import chat_pipeline

    monkeypatch.setattr(chat_pipeline.settings, "pietra_conversation_hmac_key", TEST_HMAC_KEY)
    bus = MagicMock()
    adapter = MagicMock()
    muted = MagicMock(return_value=False)
    message = InboundMessage(
        channel=Channel.WHATSAPP,
        sender_id=RAW_CONVERSATION_ID,
        text="mensagem sem dados pessoais",
    )

    with (
        patch("app.services.chat_pipeline.get_bus", return_value=bus),
        patch("app.services.chat_pipeline.check_idempotency", new=AsyncMock(return_value=False)),
        patch("app.services.chat_pipeline.enqueue_message", new=AsyncMock(return_value=False)),
        patch("app.services.bot_mute.is_bot_muted", muted),
        patch("app.services.chat_pipeline.audit_log", new=AsyncMock()),
    ):
        await process_message(message, adapter)

    mute_conversation_id = muted.call_args.args[2]
    assert RAW_CONVERSATION_ID not in mute_conversation_id
    assert mute_conversation_id == pseudonymize_conversation_id(
        Channel.WHATSAPP,
        RAW_CONVERSATION_ID,
    )


@pytest.mark.asyncio
async def test_structured_log_hashes_update_id() -> None:
    adapter = MagicMock()
    emitted = MagicMock()
    message = InboundMessage(
        channel=Channel.WHATSAPP,
        sender_id=RAW_CONVERSATION_ID,
        update_id=RAW_UPDATE_ID,
        text="mensagem sem dados pessoais",
    )

    with (
        patch("app.services.chat_pipeline.check_idempotency", new=AsyncMock(return_value=True)),
        patch("app.services.chat_pipeline.audit_log", new=AsyncMock()),
        patch("app.services.chat_pipeline._emit", emitted),
    ):
        await process_message(message, adapter)

    log_fields = emitted.call_args.kwargs
    assert "update_id" not in log_fields
    assert log_fields["update_hash"] == hash_content(RAW_UPDATE_ID)
    assert RAW_UPDATE_ID not in str(log_fields)


@pytest.mark.asyncio
async def test_history_persists_only_final_guarded_response(monkeypatch) -> None:
    from app.services import chat_pipeline

    monkeypatch.setattr(chat_pipeline.settings, "pietra_conversation_hmac_key", TEST_HMAC_KEY)
    bus = MagicMock()
    adapter = MagicMock()
    adapter.send = AsyncMock(return_value=True)
    adapter.react = AsyncMock(return_value=True)
    raw_model_response = (
        "Sou o Hermes. Contato privado: private.person@example.com. "
        "Model provider is rate-limiting. O atendimento segue normalmente."
    )
    history_get = AsyncMock(return_value=[])
    history_append = AsyncMock(return_value=[])
    run_agent = AsyncMock(return_value=SimpleNamespace(text=raw_model_response, extra_messages=[]))

    with (
        patch(
            "app.services.chat_pipeline.fetch_queue",
            new=AsyncMock(
                return_value=[{"text": "mensagem sem dados pessoais", "msg_id": "message-1"}]
            ),
        ),
        patch("app.services.chat_pipeline.check_rate_limit", new=AsyncMock(return_value=True)),
        patch("app.services.chat_pipeline.typing_loop", new=AsyncMock(return_value=None)),
        patch("app.services.chat_pipeline.get_bus", return_value=bus),
        patch("app.services.dialog_history.hist_get", history_get),
        patch("app.services.dialog_history.hist_append", history_append),
        patch(
            "app.services.cartorio_agent.run_cartorio_agent",
            new=run_agent,
        ),
        patch("app.api.v1.telegram.format_bot_text", side_effect=lambda text: text),
        patch("app.api.v1.telegram.strip_emojis", side_effect=lambda text: text),
        patch("app.services.chat_pipeline.audit_log", new=AsyncMock()),
    ):
        await process_debounced(Channel.WHATSAPP, RAW_CONVERSATION_ID, adapter)

    expected_history_id = (
        f"{Channel.WHATSAPP.value}:"
        f"{pseudonymize_conversation_id(Channel.WHATSAPP, RAW_CONVERSATION_ID)}"
    )
    assert history_get.await_args.args[1] == expected_history_id
    assert all(call.args[1] == expected_history_id for call in history_append.await_args_list)
    assert run_agent.await_args.kwargs["chat_id"] == pseudonymize_conversation_id(
        Channel.WHATSAPP,
        RAW_CONVERSATION_ID,
    )
    assert run_agent.await_args.kwargs["chat_id"] != RAW_CONVERSATION_ID

    assistant_call = next(
        call for call in history_append.await_args_list if call.args[2] == "assistant"
    )
    persisted_response = assistant_call.args[3]
    sent_message = adapter.send.await_args.args[0]
    assert isinstance(sent_message, OutboundMessage)
    assert persisted_response == sent_message.text
    assert "private.person@example.com" not in persisted_response
    assert "Hermes" not in persisted_response
    assert "rate-limiting" not in persisted_response
