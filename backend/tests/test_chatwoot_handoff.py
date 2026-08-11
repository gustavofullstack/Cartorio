"""Testes do service chatwoot_handoff.

Cobre:
- Validacao de signature HMAC-SHA256 (se secret configurado)
- Processamento de conversation_status_changed -> resolved
- Idempotencia via WebhookEvent
- Eventos desconhecidos sao ignorados
"""

import hashlib
import hmac
from unittest.mock import MagicMock, patch


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


def test_missing_signature_secret_fails_closed(monkeypatch):
    from app.config import settings
    from app.services.chatwoot_handoff import _validate_signature

    monkeypatch.setattr(settings, "chatwoot_webhook_secret", None)

    assert _validate_signature(b"{}", None) is False


def test_chatwoot_integrations_are_disabled_by_default() -> None:
    from app.config import settings

    assert settings.chatwoot_webhook_enabled is False
    assert settings.chatwoot_outbound_enabled is False


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


def test_outgoing_human_reply_mutes_same_pseudonymous_channel_key(monkeypatch):
    """Primeira resposta humana silencia a chave realmente consumida pelo pipeline."""
    from app.config import settings
    from app.services.chat_pipeline import Channel, pseudonymize_conversation_id
    from app.services.chatwoot_handoff import _handle_message_created

    monkeypatch.setattr(settings, "pietra_conversation_hmac_key", "c" * 64)
    raw_external_id = "private-telegram-test-id"
    atendimento = Atendimento(
        id=1,
        canal="telegram",
        external_id=raw_external_id,
        tipo="duvida",
        chatwoot_conversation_id=42,
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = atendimento
    client = MagicMock()
    bus = MagicMock(client=client)
    mute = MagicMock()

    payload = {
        "event": "message_created",
        "message_type": "outgoing",
        "content": "Atendimento humano iniciado.",
        "conversation": {"id": 42},
        "sender": {"id": 7, "name": "Escrevente"},
    }
    with (
        patch("app.services.redis_bus.get_bus", return_value=bus),
        patch("app.services.bot_mute.mute_bot", new=mute),
        patch("app.services.chatwoot_handoff.AuditService.log") as audit,
    ):
        _handle_message_created(db, payload)

    expected = pseudonymize_conversation_id(Channel.TELEGRAM, raw_external_id)
    mute.assert_any_call(client, "telegram", expected, reason="hitl_outgoing")
    assert audit.call_args.kwargs["action"] == "chatwoot.sync.outgoing_dispatch_blocked"
    audit_payload = audit.call_args.kwargs["payload"]
    assert audit_payload["channel_conversation_id_pseudonymized"] == expected
    assert audit_payload["dispatch"] == "disabled_requires_transactional_outbox"
    assert raw_external_id not in str(audit_payload)


def test_local_hmac_ticket_uses_pipeline_mute_identity(monkeypatch):
    from app.config import settings
    from app.services.chat_pipeline import Channel, pseudonymize_conversation_id
    from app.services.chatwoot_handoff import _mute_conversation_id
    from app.services.local_handoff_ticket import pseudonymize_external_id

    monkeypatch.setattr(settings, "pietra_conversation_hmac_key", "c" * 64)
    raw_external_id = "private-whatsapp-test-id"
    atendimento = Atendimento(
        canal="whatsapp",
        external_id=pseudonymize_external_id("whatsapp", raw_external_id),
        tipo="duvida",
    )

    target = _mute_conversation_id(atendimento)

    assert target == (
        "whatsapp",
        pseudonymize_conversation_id(Channel.WHATSAPP, raw_external_id),
    )
