"""G8.03.T1 — Chatwoot webhook Pydantic schemas + process soft-reject.

Covers conversation_status_changed / message_created shapes, empty/garbage
rejection, and fail-soft invalid_payload from process_chatwoot_event.

LGPD-safe: fixtures use synthetic ids/names only (no CPF/phone/email real).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.schemas.chatwoot_webhook import (
    ChatwootConversationStatusChanged,
    ChatwootMessageCreated,
    parse_chatwoot_payload,
)
from app.services.chatwoot_handoff import process_chatwoot_event


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock(spec=Session)
    db.execute.return_value.scalar_one_or_none.return_value = None
    db.flush = MagicMock()
    db.add = MagicMock()
    return db


def test_schema_status_changed_open_with_assignee() -> None:
    """Valid status_changed open + assignee validates and parses."""
    payload = {
        "event": "conversation_status_changed",
        "id": 1001,
        "status": "open",
        "conversation": {"id": 42, "status": "open"},
        "assignee": {"id": 7, "name": "Escrevente Teste"},
    }
    model = parse_chatwoot_payload(payload)
    assert isinstance(model, ChatwootConversationStatusChanged)
    assert model.status == "open"
    assert model.conversation is not None
    assert model.conversation.id == 42
    assert model.assignee is not None


def test_schema_status_changed_resolved() -> None:
    """Valid resolved status_changed."""
    payload = {
        "event": "conversation_status_changed",
        "id": 1002,
        "status": "resolved",
        "conversation": {"id": 99},
    }
    model = parse_chatwoot_payload(payload)
    assert isinstance(model, ChatwootConversationStatusChanged)
    assert model.status == "resolved"
    assert model.conversation is not None
    assert model.conversation.id == 99


def test_schema_rejects_empty() -> None:
    """Empty payload is not a valid Chatwoot event model."""
    assert parse_chatwoot_payload({}) is None
    assert parse_chatwoot_payload(None) is None  # type: ignore[arg-type]


def test_schema_message_created_outgoing_shape() -> None:
    """message_created outgoing minimal shape validates."""
    payload = {
        "event": "message_created",
        "id": "evt_out_1",
        "message_type": "outgoing",
        "content": "Documento pronto para retirada.",
        "conversation": {"id": 55},
        "sender": {"id": 3, "name": "Agente"},
    }
    model = parse_chatwoot_payload(payload)
    assert isinstance(model, ChatwootMessageCreated)
    assert model.message_type == "outgoing"
    assert model.content is not None
    assert model.conversation is not None
    assert model.conversation.id == 55


def test_schema_rejects_garbage() -> None:
    """Garbage / wrong-typed payloads fail validation or return None."""
    assert parse_chatwoot_payload({"foo": "bar"}) is None
    assert parse_chatwoot_payload({"event": "conversation_status_changed", "status": {"bad": True}}) is None
    assert parse_chatwoot_payload({"event": "message_created", "conversation": "not-a-dict"}) is None


def test_process_valid_status_changed_open_with_assignee(
    mock_db: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """process_chatwoot_event accepts open+assignee shape (HITL path)."""
    from app.config import settings

    monkeypatch.setattr(settings, "chatwoot_webhook_secret", None)
    payload = {
        "event": "conversation_status_changed",
        "id": 2001,
        "status": "open",
        "conversation": {"id": 42, "status": "open"},
        "assignee": {"id": 7, "name": "Escrevente"},
    }
    result = process_chatwoot_event(mock_db, payload)
    assert result["status"] == "processed"
    assert result["event_type"] == "conversation_status_changed"


def test_process_valid_resolved(mock_db: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    """process_chatwoot_event accepts resolved status_changed."""
    from app.config import settings

    monkeypatch.setattr(settings, "chatwoot_webhook_secret", None)
    payload = {
        "event": "conversation_status_changed",
        "id": 2002,
        "status": "resolved",
        "conversation": {"id": 88},
    }
    result = process_chatwoot_event(mock_db, payload)
    assert result["status"] == "processed"
    assert result["event_type"] == "conversation_status_changed"


def test_process_invalid_empty_rejected(
    mock_db: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty payload → rejected invalid_payload (fail soft)."""
    from app.config import settings

    monkeypatch.setattr(settings, "chatwoot_webhook_secret", None)
    result = process_chatwoot_event(mock_db, {})
    assert result["status"] == "rejected"
    assert result["reason"] == "invalid_payload"


def test_process_message_created_outgoing(
    mock_db: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """process_chatwoot_event accepts outgoing message_created shape."""
    from app.config import settings

    monkeypatch.setattr(settings, "chatwoot_webhook_secret", None)
    payload = {
        "event": "message_created",
        "id": "evt_g8_out",
        "message_type": "outgoing",
        "content": "Sua certidao esta pronta.",
        "conversation": {"id": 12},
        "sender": {"id": 1, "name": "Escrevente"},
    }
    result = process_chatwoot_event(mock_db, payload)
    assert result["status"] == "processed"
    assert result["event_type"] == "message_created"


def test_process_garbage_rejected(mock_db: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Garbage without event → rejected invalid_payload."""
    from app.config import settings

    monkeypatch.setattr(settings, "chatwoot_webhook_secret", None)
    result = process_chatwoot_event(mock_db, {"not_an_event": True, "x": 1})
    assert result["status"] == "rejected"
    assert result["reason"] == "invalid_payload"
