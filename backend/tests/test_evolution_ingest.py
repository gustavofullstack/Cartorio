"""Testes do service evolution_ingest.

Cobre:
- Normalizacao de payload Evolution API (4 campos minimos)
- Idempotencia via WebhookEvent
- Filtro de eventos que NAO sao MESSAGES_UPSERT
- Rejeicao de payload malformado (sem data)
"""

from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.models.webhook_event import WebhookEvent


def test_ingest_valid_message_returns_normalized():
    """Payload Evolution valido vira dict normalizado."""
    from app.services.evolution_ingest import ingest_evolution_event

    payload = {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "ABC123"},
            "message": {"conversation": "Ola, preciso de uma certidao"},
            "pushName": "Joao",
        },
    }
    db = MagicMock(spec=Session)
    db.execute.return_value.scalar_one_or_none.return_value = None
    result = ingest_evolution_event(db, payload)

    assert result["status"] == "accepted"
    assert result["event_type"] == "messages.upsert"
    assert result["sender"] == "5511999999999@s.whatsapp.net"
    assert result["text"] == "Ola, preciso de uma certidao"
    assert result["message_id"] == "ABC123"
    assert result["instance"] == "cartorio-2notas"


def test_ingest_ignores_non_message_events():
    """Eventos que nao sao MESSAGES_UPSERT sao ignorados."""
    from app.services.evolution_ingest import ingest_evolution_event

    payload = {"event": "connection.update", "instance": "x", "data": {"state": "open"}}
    db = MagicMock(spec=Session)
    result = ingest_evolution_event(db, payload)

    assert result["status"] == "ignored"
    assert result["reason"] == "event_not_messages_upsert"


def test_ingest_idempotent_same_message_id():
    """Replay do mesmo message_id nao duplica processamento."""
    from app.services.evolution_ingest import ingest_evolution_event

    payload = {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "DUP123"},
            "message": {"conversation": "teste"},
        },
    }

    # Segunda chamada: ja existe, retorna idempotent
    db = MagicMock(spec=Session)
    db.execute.return_value.scalar_one_or_none.return_value = WebhookEvent(
        id=1, source="evolution", event_id="DUP123", payload_hash="abc"
    )
    result = ingest_evolution_event(db, payload)
    assert result["status"] == "idempotent"
    assert result["message_id"] == "DUP123"


def test_ingest_handles_missing_fields_gracefully():
    """Payload malformado nao quebra o webhook."""
    from app.services.evolution_ingest import ingest_evolution_event

    payload = {"event": "messages.upsert", "instance": "x"}  # sem data
    db = MagicMock(spec=Session)
    db.execute.return_value.scalar_one_or_none.return_value = None
    result = ingest_evolution_event(db, payload)

    assert result["status"] == "rejected"
    assert "missing_data" in result["reason"]


def test_ingest_extracts_text_from_extended_message():
    """Texto em extendedTextMessage.text e extraido corretamente."""
    from app.services.evolution_ingest import ingest_evolution_event

    payload = {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {"remoteJid": "5511@s.whatsapp.net", "id": "EXT1"},
            "message": {"extendedTextMessage": {"text": "mensagem estendida"}},
        },
    }
    db = MagicMock(spec=Session)
    db.execute.return_value.scalar_one_or_none.return_value = None
    result = ingest_evolution_event(db, payload)

    assert result["status"] == "accepted"
    assert result["text"] == "mensagem estendida"


def test_ingest_rejects_missing_message_id_or_sender():
    """Payload sem message_id ou sender e rejeitado."""
    from app.services.evolution_ingest import ingest_evolution_event

    payload = {
        "event": "messages.upsert",
        "instance": "x",
        "data": {
            "key": {},  # sem id nem remoteJid
            "message": {"conversation": "oi"},
        },
    }
    db = MagicMock(spec=Session)
    db.execute.return_value.scalar_one_or_none.return_value = None
    result = ingest_evolution_event(db, payload)

    assert result["status"] == "rejected"
    assert "missing_message_id_or_sender" in result["reason"]
