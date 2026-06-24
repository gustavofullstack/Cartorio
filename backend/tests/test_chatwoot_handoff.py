"""Testes do service chatwoot_handoff.

Cobre:
- Validacao de signature HMAC-SHA256 (se secret configurado)
- Processamento de conversation_status_changed -> resolved
- Idempotencia via WebhookEvent
- Eventos desconhecidos sao ignorados
"""

import hashlib
import hmac
from unittest.mock import MagicMock


from app.models.atendimento import Atendimento
from app.models.webhook_event import WebhookEvent


def _sign(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


def test_process_resolved_conversation_concludes_atendimento(monkeypatch):
    """conversation_status_changed -> resolved marca atendimento como concluido."""
    from app.config import settings
    from app.services.chatwoot_handoff import process_chatwoot_event

    monkeypatch.setattr(settings, "chatwoot_webhook_secret", None)  # sem signature

    payload = {
        "event": "conversation_status_changed",
        "status": "resolved",
        "conversation": {"id": 42},
    }

    atendimento = Atendimento(
        id=1,
        canal="whatsapp",
        external_id="user1",
        tipo="duvida",
        chatwoot_conversation_id=42,
        status="em_atendimento",
    )

    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = atendimento

    result = process_chatwoot_event(db, payload, signature=None)

    assert result["status"] == "processed"
    assert result["event_type"] == "conversation_status_changed"
    assert atendimento.status == "concluido"
    assert atendimento.concluido_em is not None


def test_process_invalid_signature_returns_rejected(monkeypatch):
    """Signature invalida retorna rejected sem processar."""
    from app.config import settings
    from app.services.chatwoot_handoff import process_chatwoot_event

    monkeypatch.setattr(settings, "chatwoot_webhook_secret", "secret-real")

    payload = {"event": "message_created", "id": "evt1", "conversation": {"id": 1}}
    body = b'{"event": "message_created", "id": "evt1", "conversation": {"id": 1}}'

    db = MagicMock()

    result = process_chatwoot_event(db, payload, signature="signature-fake", raw_body=body)

    assert result["status"] == "rejected"
    assert result["reason"] == "invalid_signature"


def test_process_valid_signature_passes(monkeypatch):
    """Signature valida permite processamento."""
    from app.config import settings
    from app.services.chatwoot_handoff import process_chatwoot_event

    secret = "secret-real"
    monkeypatch.setattr(settings, "chatwoot_webhook_secret", secret)

    payload = {"event": "message_created", "id": "evt1", "conversation": {"id": 1}}
    body = b'{"event": "message_created", "id": "evt1", "conversation": {"id": 1}}'
    sig = _sign(body, secret)

    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None  # idempotency check

    result = process_chatwoot_event(db, payload, signature=sig, raw_body=body)

    assert result["status"] == "processed"


def test_process_idempotent_same_event_id(monkeypatch):
    """Replay do mesmo event_id retorna idempotent sem duplicar."""
    from app.config import settings
    from app.services.chatwoot_handoff import process_chatwoot_event

    monkeypatch.setattr(settings, "chatwoot_webhook_secret", None)

    payload = {"event": "message_created", "id": "evt-dup", "conversation": {"id": 1}}

    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = WebhookEvent(
        id=1, source="chatwoot", event_id="evt-dup", payload_hash="abc"
    )
    result = process_chatwoot_event(db, payload, signature=None)
    assert result["status"] == "idempotent"


def test_process_unknown_event_returns_ignored(monkeypatch):
    """Eventos nao tratados retornam ignored."""
    from app.config import settings
    from app.services.chatwoot_handoff import process_chatwoot_event

    monkeypatch.setattr(settings, "chatwoot_webhook_secret", None)

    payload = {"event": "agent_typing", "id": "evt1", "conversation": {"id": 1}}

    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None

    result = process_chatwoot_event(db, payload, signature=None)
    assert result["status"] == "ignored"
