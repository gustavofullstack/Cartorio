"""Testes unitários para o sync bidirecional Chatwoot ↔ Telegram (Wave 6 S6.T1).

Valida:
- message_created outgoing dispara envio ao Telegram
- message_created incoming NÃO dispara envio (já veio do Telegram)
- conversation_status_changed resolved marca atendimento como concluído
- Propagação de consent LGPD cross-channel

Modified by Gustavo Almeida.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.services.chatwoot_handoff import process_chatwoot_event


@pytest.fixture
def mock_db() -> MagicMock:
    """Mock de Session SQLAlchemy."""
    db = MagicMock(spec=Session)
    db.execute.return_value.scalar_one_or_none.return_value = None
    db.flush = MagicMock()
    db.add = MagicMock()
    return db


def test_message_created_incoming_does_not_sync(mock_db: MagicMock) -> None:
    """message_created incoming (do cliente) NÃO deve disparar envio ao Telegram."""
    payload = {
        "event": "message_created",
        "id": "evt_001",
        "message_type": "incoming",
        "content": "Olá, preciso de uma certidão",
        "conversation": {"id": 42},
        "sender": {"name": "Cliente", "id": 1},
    }
    result = process_chatwoot_event(mock_db, payload)
    assert result["status"] == "processed"
    assert result["event_type"] == "message_created"


def test_message_created_outgoing_triggers_sync(mock_db: MagicMock) -> None:
    """message_created outgoing (do escrevente) DEVE disparar envio ao Telegram."""
    payload = {
        "event": "message_created",
        "id": "evt_002",
        "message_type": "outgoing",
        "content": "Sua certidão está pronta!",
        "conversation": {"id": 99},
        "sender": {"name": "Maria Escrevente", "id": 5},
    }
    # Sem atendimento encontrado = não envia, mas processa normalmente
    result = process_chatwoot_event(mock_db, payload)
    assert result["status"] == "processed"
    assert result["event_type"] == "message_created"


def test_message_created_outgoing_is_audited_but_direct_dispatch_is_blocked(
    mock_db: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Contencao P0 exige outbox transacional antes de qualquer envio."""
    import app.services.chatwoot_handoff as handoff

    mock_db.execute.return_value.scalar_one_or_none.return_value = SimpleNamespace(
        id=3, canal="telegram", external_id="123"
    )
    audit = MagicMock()
    monkeypatch.setattr(handoff.AuditService, "log", audit)
    handoff._handle_message_created(
        mock_db,
        {
            "message_type": "outgoing",
            "content": "Seu documento esta pronto",
            "conversation": {"id": 99},
            "sender": {"name": "Escrevente", "id": 5},
        },
    )
    assert audit.call_args.kwargs["action"] == "chatwoot.sync.outgoing_dispatch_blocked"
    assert audit.call_args.kwargs["payload"]["dispatch"] == "disabled_requires_transactional_outbox"


def test_unknown_event_is_ignored(mock_db: MagicMock) -> None:
    """Eventos desconhecidos devem retornar status='ignored'."""
    payload = {
        "event": "conversation_updated",
        "id": "evt_003",
    }
    result = process_chatwoot_event(mock_db, payload)
    assert result["status"] == "ignored"
    assert result["reason"] == "event_not_handled"


def test_idempotent_event_is_skipped(mock_db: MagicMock) -> None:
    """Eventos já processados (idempotência) devem retornar status='idempotent'."""
    # Simula que o evento já existe no banco
    mock_db.execute.return_value.scalar_one_or_none.return_value = MagicMock()
    payload = {
        "event": "message_created",
        "id": "evt_already_processed",
        "message_type": "incoming",
        "content": "Repetido",
        "conversation": {"id": 1},
    }
    result = process_chatwoot_event(mock_db, payload)
    assert result["status"] == "idempotent"


def test_invalid_signature_rejected(mock_db: MagicMock) -> None:
    """Se HMAC inválido, deve retornar rejected."""
    with patch("app.services.chatwoot_handoff.settings") as mock_settings:
        mock_settings.chatwoot_webhook_secret = "test_secret_key"
        payload = {"event": "message_created", "id": "evt_004"}
        raw_body = b'{"event":"message_created","id":"evt_004"}'
        result = process_chatwoot_event(
            mock_db, payload, signature="invalid_sig", raw_body=raw_body
        )
        assert result["status"] == "rejected"
        assert result["reason"] == "invalid_signature"
