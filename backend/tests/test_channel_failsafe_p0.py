"""Regressoes P0 para capacidades indisponiveis no canal WhatsApp."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.channel_failsafe import action_failsafe, unsupported_whatsapp_media
from app.services.chat_pipeline import (
    Channel,
    InboundMessage,
    process_debounced,
    process_message,
)
from app.services.local_handoff_ticket import (
    LocalHandoffTicket,
    create_local_handoff_ticket,
    pseudonymize_external_id,
)


TEST_HMAC_KEY = "local-handoff-test-key-with-at-least-32-characters"


@pytest.mark.parametrize(
    ("action", "reason", "required_text"),
    (
        ("humano", "human_handoff_unavailable", "não consegue transferir"),
        ("agendar", "scheduling_confirmation_unavailable", "não confirma agendamentos"),
    ),
)
def test_unavailable_actions_have_honest_institutional_fallback(
    action: str,
    reason: str,
    required_text: str,
) -> None:
    fallback = action_failsafe(action)

    assert fallback is not None
    assert fallback.reason == reason
    assert required_text in fallback.text
    assert "escrevente" in fallback.text
    assert "Chatwoot" not in fallback.text
    assert "N8N" not in fallback.text


@pytest.mark.parametrize(
    "message_type",
    (
        "imageMessage",
        "audioMessage",
        "documentMessage",
        "videoMessage",
        "stickerMessage",
        "locationMessage",
        "contactMessage",
    ),
)
def test_evolution_media_types_are_classified_as_unsupported(message_type: str) -> None:
    fallback = unsupported_whatsapp_media(message_type)

    assert fallback is not None
    assert fallback.reason == "unsupported_media"
    assert "não consegue analisar" in fallback.text


@pytest.mark.parametrize("message_type", ("", "conversation", "extendedTextMessage"))
def test_evolution_text_types_do_not_trigger_media_fallback(message_type: str) -> None:
    assert unsupported_whatsapp_media(message_type) is None


def test_local_ticket_external_id_is_stable_hmac_without_raw_identifier() -> None:
    from app.services.chat_pipeline import Channel, pseudonymize_conversation_id

    raw_external_id = "private-whatsapp-test-identifier"

    first = pseudonymize_external_id(
        "whatsapp",
        raw_external_id,
        hmac_key=TEST_HMAC_KEY,
    )
    repeated = pseudonymize_external_id(
        "whatsapp",
        raw_external_id,
        hmac_key=TEST_HMAC_KEY,
    )
    telegram = pseudonymize_external_id(
        "telegram",
        raw_external_id,
        hmac_key=TEST_HMAC_KEY,
    )

    assert first == repeated
    assert first != telegram
    assert first.startswith("hmac:v1:")
    assert first == (
        "hmac:v1:"
        + pseudonymize_conversation_id(
            Channel.WHATSAPP,
            raw_external_id,
            hmac_key=TEST_HMAC_KEY,
        )
    )
    assert raw_external_id not in first


def test_local_ticket_requires_db_and_audit_success(monkeypatch) -> None:
    from app.services import local_handoff_ticket

    monkeypatch.setattr(
        local_handoff_ticket.settings,
        "pietra_conversation_hmac_key",
        TEST_HMAC_KEY,
    )
    db = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = db
    context.__exit__.return_value = False

    def assign_ticket_id() -> None:
        db.add.call_args.args[0].id = 42

    db.flush.side_effect = assign_ticket_id
    audit = MagicMock(return_value=SimpleNamespace(id=7))

    with (
        patch("app.services.local_handoff_ticket.session_scope", return_value=context),
        patch("app.services.local_handoff_ticket.AuditService.log", new=audit),
    ):
        result = create_local_handoff_ticket(
            channel="whatsapp",
            external_id="private-whatsapp-test-identifier",
            action="humano",
            request_id="local-ticket-test",
        )

    ticket = db.add.call_args.args[0]
    assert result == LocalHandoffTicket(atendimento_id=42, status="aguardando_escrevente")
    assert ticket.status == "aguardando_escrevente"
    assert ticket.chatwoot_conversation_id is None
    assert ticket.external_id.startswith("hmac:v1:")
    assert "private-whatsapp-test-identifier" not in ticket.external_id
    assert audit.call_args.kwargs["payload"]["chatwoot_dispatched"] is False
    assert audit.call_args.kwargs["payload"]["n8n_dispatched"] is False


def test_local_ticket_does_not_report_success_when_audit_fails(monkeypatch) -> None:
    from app.services import local_handoff_ticket

    monkeypatch.setattr(
        local_handoff_ticket.settings,
        "pietra_conversation_hmac_key",
        TEST_HMAC_KEY,
    )
    db = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = db
    context.__exit__.return_value = False

    def assign_ticket_id() -> None:
        db.add.call_args.args[0].id = 42

    db.flush.side_effect = assign_ticket_id

    with (
        patch("app.services.local_handoff_ticket.session_scope", return_value=context),
        patch(
            "app.services.local_handoff_ticket.AuditService.log",
            side_effect=RuntimeError("audit unavailable"),
        ),
        pytest.raises(RuntimeError, match="audit unavailable"),
    ):
        create_local_handoff_ticket(
            channel="whatsapp",
            external_id="private-whatsapp-test-identifier",
            action="humano",
        )


@pytest.mark.asyncio
async def test_unsupported_media_is_answered_without_queue_or_llm() -> None:
    adapter = MagicMock()
    adapter.send = AsyncMock(return_value=True)
    enqueue = AsyncMock()
    audit = AsyncMock()
    message = InboundMessage(
        channel=Channel.WHATSAPP,
        sender_id="authorized-test-jid",
        update_id="media-message-1",
        message_ids=["media-message-1"],
        extra={"message_type": "audioMessage"},
    )

    with (
        patch("app.services.chat_pipeline.check_idempotency", new=AsyncMock(return_value=False)),
        patch("app.services.chat_pipeline.get_bus", return_value=None),
        patch(
            "app.services.local_handoff_ticket.create_local_handoff_ticket",
            side_effect=RuntimeError("database unavailable"),
        ),
        patch("app.services.chat_pipeline.enqueue_message", new=enqueue),
        patch("app.services.chat_pipeline.audit_log", new=audit),
    ):
        result = await process_message(message, adapter, request_id="failsafe-media-test")

    assert result is not None
    assert result.metadata == {"failsafe_reason": "unsupported_media"}
    assert "não consegue analisar" in result.text
    adapter.send.assert_awaited_once_with(result)
    enqueue.assert_not_awaited()
    fallback_audits = [call for call in audit.await_args_list if call.args[3] == "fallback"]
    assert [call.args[4] for call in fallback_audits] == [
        "unsupported_media_pending",
        "unsupported_media_sent",
    ]


@pytest.mark.parametrize(
    ("action", "forbidden_claim", "expected_reason"),
    (
        ("humano", "Transferi você para o atendente.", "human_handoff_unavailable"),
        ("agendar", "Seu agendamento está confirmado.", "scheduling_confirmation_unavailable"),
    ),
)
@pytest.mark.asyncio
async def test_agent_action_claim_is_replaced_before_send_and_audited(
    action: str,
    forbidden_claim: str,
    expected_reason: str,
) -> None:
    adapter = MagicMock()
    adapter.send = AsyncMock(return_value=True)
    adapter.react = AsyncMock(return_value=True)
    audit = AsyncMock()

    with (
        patch(
            "app.services.chat_pipeline.fetch_queue",
            new=AsyncMock(return_value=[{"text": "pedido", "msg_id": "message-1"}]),
        ),
        patch("app.services.chat_pipeline.check_rate_limit", new=AsyncMock(return_value=True)),
        patch("app.services.chat_pipeline.typing_loop", new=AsyncMock(return_value=None)),
        patch("app.services.chat_pipeline.get_bus", return_value=None),
        patch(
            "app.services.local_handoff_ticket.create_local_handoff_ticket",
            side_effect=RuntimeError("database unavailable"),
        ),
        patch(
            "app.services.cartorio_agent.run_cartorio_agent",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    text=forbidden_claim,
                    extra_messages=["integração externa acionada"],
                    action=action,
                )
            ),
        ),
        patch("app.api.v1.telegram.format_bot_text", side_effect=lambda text: text),
        patch("app.api.v1.telegram.strip_emojis", side_effect=lambda text: text),
        patch("app.services.chat_pipeline.audit_log", new=audit),
    ):
        await process_debounced(
            Channel.WHATSAPP,
            "authorized-test-jid",
            adapter,
            request_id="failsafe-action-test",
        )

    sent_message = adapter.send.await_args.args[0]
    assert forbidden_claim not in sent_message.text
    assert "integração externa acionada" not in sent_message.text
    assert "escrevente" in sent_message.text
    fallback_audits = [call for call in audit.await_args_list if call.args[3] == "fallback"]
    assert fallback_audits[-1].args[4] == f"{expected_reason}_sent"


@pytest.mark.asyncio
async def test_persisted_local_ticket_changes_claim_to_registered_not_transferred() -> None:
    adapter = MagicMock()
    adapter.send = AsyncMock(return_value=True)
    audit = AsyncMock()

    with (
        patch(
            "app.services.chat_pipeline.fetch_queue",
            new=AsyncMock(return_value=[{"text": "quero agendar", "msg_id": "message-1"}]),
        ),
        patch("app.services.chat_pipeline.check_rate_limit", new=AsyncMock(return_value=True)),
        patch("app.services.chat_pipeline.typing_loop", new=AsyncMock(return_value=None)),
        patch("app.services.chat_pipeline.get_bus", return_value=None),
        patch(
            "app.services.cartorio_agent.run_cartorio_agent",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    text="Seu agendamento está confirmado.",
                    extra_messages=[],
                    action="agendar",
                )
            ),
        ),
        patch(
            "app.services.local_handoff_ticket.create_local_handoff_ticket",
            return_value=LocalHandoffTicket(
                atendimento_id=42,
                status="aguardando_escrevente",
            ),
        ),
        patch("app.api.v1.telegram.format_bot_text", side_effect=lambda text: text),
        patch("app.api.v1.telegram.strip_emojis", side_effect=lambda text: text),
        patch("app.services.chat_pipeline.audit_log", new=audit),
    ):
        await process_debounced(
            Channel.WHATSAPP,
            "authorized-test-jid",
            adapter,
            request_id="registered-ticket-test",
        )

    sent_message = adapter.send.await_args.args[0]
    assert "registrado na fila local" in sent_message.text
    assert "Nenhuma data ou horário está confirmado" in sent_message.text
    assert "agendamento está confirmado" not in sent_message.text
    fallback_audits = [call for call in audit.await_args_list if call.args[3] == "fallback"]
    assert fallback_audits[0].args[4] == "scheduling_request_registered_sent"
