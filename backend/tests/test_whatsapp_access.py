"""Regressoes P0 da allowlist HMAC do WhatsApp."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.whatsapp_access import (
    decide_whatsapp_access,
    hmac_sender,
    normalize_whatsapp_number,
)


HMAC_KEY = "synthetic-allowlist-key-with-at-least-32-characters"
ALLOWED = "+5511998765432"
DENIED = "+5511988888888"


def _hashes(*numbers: str) -> str:
    return ",".join(hmac_sender(number, hmac_key=HMAC_KEY) for number in numbers)


def _payload(sender: str, message_id: str, *, alt: str | None = None) -> dict:
    key = {
        "remoteJid": sender,
        "fromMe": False,
        "id": message_id,
    }
    if alt:
        key["remoteJidAlt"] = alt
    return {
        "event": "messages.upsert",
        "instance": "cartorio-agent",
        "data": {"key": key, "message": {"conversation": "mensagem sintetica"}},
    }


def test_normalizes_current_and_legacy_mobile_jids() -> None:
    assert normalize_whatsapp_number("5511998765432@s.whatsapp.net") == ALLOWED
    assert normalize_whatsapp_number("551198765432@s.whatsapp.net") == ALLOWED


def test_group_broadcast_and_lid_without_alt_are_not_numbers() -> None:
    assert normalize_whatsapp_number("120363000@g.us") is None
    assert normalize_whatsapp_number("status@broadcast") is None
    assert normalize_whatsapp_number("162023748985056@lid") is None


def test_restricted_mode_fails_closed_for_missing_configuration() -> None:
    missing_hashes = decide_whatsapp_access(
        ALLOWED,
        sender_id_alt=None,
        allowed_sender_hashes="",
        hmac_key=HMAC_KEY,
        restrict_inbound=True,
    )
    missing_key = decide_whatsapp_access(
        ALLOWED,
        sender_id_alt=None,
        allowed_sender_hashes=_hashes(ALLOWED),
        hmac_key="short",
        restrict_inbound=True,
    )
    assert missing_hashes.reason == "allowlist_not_configured"
    assert missing_key.reason == "allowlist_key_not_configured"
    assert not missing_hashes.allowed
    assert not missing_key.allowed


def test_only_hash_configured_sender_or_lid_alt_is_allowed() -> None:
    direct = decide_whatsapp_access(
        ALLOWED,
        sender_id_alt=None,
        allowed_sender_hashes=_hashes(ALLOWED),
        hmac_key=HMAC_KEY,
        restrict_inbound=True,
    )
    lid = decide_whatsapp_access(
        "162023748985056@lid",
        sender_id_alt="551198765432@s.whatsapp.net",
        allowed_sender_hashes=_hashes(ALLOWED),
        hmac_key=HMAC_KEY,
        restrict_inbound=True,
    )
    denied = decide_whatsapp_access(
        DENIED,
        sender_id_alt=None,
        allowed_sender_hashes=_hashes(ALLOWED),
        hmac_key=HMAC_KEY,
        restrict_inbound=True,
    )
    assert direct.allowed and lid.allowed
    assert not denied.allowed


def test_webhook_denies_before_idempotency(monkeypatch) -> None:
    monkeypatch.setattr(settings, "pietra_whatsapp_restrict_inbound", True)
    monkeypatch.setattr(settings, "pietra_whatsapp_allowlist_hmac_key", HMAC_KEY)
    monkeypatch.setattr(settings, "pietra_whatsapp_allowed_sender_hashes", _hashes(ALLOWED))
    monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "false")
    adapter = MagicMock()
    adapter.verify_signature = AsyncMock(return_value=True)

    with (
        patch("app.api.v1.whatsapp.get_adapter", return_value=adapter),
        patch("app.api.v1.whatsapp.ingest_evolution_event") as ingest,
    ):
        response = TestClient(app).post(
            "/api/v1/whatsapp/webhook",
            json=_payload("5511988888888@s.whatsapp.net", "deny-before-db"),
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "detail": "sender_not_authorized"}
    ingest.assert_not_called()
    adapter.authorize_recipient.assert_not_called()


def test_test_send_is_hidden_in_production(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    with patch("app.api.v1.whatsapp.get_adapter") as adapter:
        response = TestClient(app).post(
            "/api/v1/whatsapp/test/send",
            params={"to": ALLOWED, "text": "mensagem sintetica"},
            headers={"X-API-Key": settings.cartorio_api_key},
        )
    assert response.status_code == 404
    adapter.assert_not_called()
