"""Regressoes P0 das fronteiras Telegram Agent, WS e Chatwoot."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.telegram import _chatwoot_handoff, _publish_agent_event
from app.services.chatwoot_handoff import _format_body


@pytest.mark.asyncio
async def test_agent_ws_event_scrubs_preview_and_pseudonymizes_identifiers() -> None:
    bus = MagicMock()
    bus.publish = AsyncMock()

    await _publish_agent_event(
        bus,
        "agent.start",
        {"chat_id": 123456789, "key": "123456789", "text_preview": "CPF 123.456.789-09"},
    )

    _channel, event = bus.publish.await_args.args
    assert "123.456.789-09" not in event["text_preview"]
    assert event["chat_id"] != 123456789
    assert event["key"] != "123456789"
    assert len(event["chat_id"]) == 16


def test_chatwoot_handoff_body_scrubs_pii_and_omits_local_paths() -> None:
    body = _format_body(
        "Meu CPF e 123.456.789-09",
        [
            {
                "type": "document",
                "file_name": "cpf-123.456.789-09.pdf",
                "caption": "contato pessoa@example.test",
                "local_path": "/private/tmp/cliente/cpf.pdf",
            }
        ],
        ["user: telefone 11987654321"],
    )

    assert "123.456.789-09" not in body
    assert "pessoa@example.test" not in body
    assert "11987654321" not in body
    assert "/private/tmp" not in body


@pytest.mark.asyncio
async def test_agent_handoff_creates_local_conversation_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resposta humana so pode voltar ao Telegram com vinculo local do CRM."""

    async def handoff_to_chatwoot(**kwargs: object) -> tuple[bool, dict[str, object]]:
        return True, {"conversation_id": "501"}

    create_ticket = AsyncMock(return_value={"ok": True, "atendimento_id": 7})
    send_message = AsyncMock(return_value=True)
    monkeypatch.setattr("app.services.chatwoot_handoff.handoff_to_chatwoot", handoff_to_chatwoot)
    monkeypatch.setattr("app.api.v1.telegram._tool_criar_atendimento", create_ticket)
    monkeypatch.setattr("app.api.v1.telegram._send_message", send_message)

    await _chatwoot_handoff(123, "preciso de escrevente", [], [])

    assert create_ticket.await_args.kwargs["chatwoot_conversation_id"] == 501
    assert create_ticket.await_args.args[2] == "123"
