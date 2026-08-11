"""Regressoes da allowlist HMAC de remetentes da Pietra no WhatsApp."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.whatsapp_access import (
    PIETRA_WHATSAPP_PILOT_E164,
    decide_whatsapp_access,
    hmac_sender,
    normalize_whatsapp_number,
    parse_allowed_sender_hashes,
)


HMAC_KEY = "test-only-hmac-key-with-32-characters-minimum"
ALLOWED = "+5511998765432"
DENIED = "+5511988888888"


def _allowlist(*numbers: str) -> str:
    return ",".join(hmac_sender(number, hmac_key=HMAC_KEY) for number in numbers)


def _decide(
    sender: str,
    *,
    alt: str | None = None,
    hashes: str = "",
    key: str = HMAC_KEY,
    restrict: bool = True,
) -> object:
    return decide_whatsapp_access(
        sender,
        sender_id_alt=alt,
        allowed_sender_hashes=hashes,
        hmac_key=key,
        app_env="test",
        restrict_inbound=restrict,
    )


def _payload(sender: str, message_id: str) -> dict:
    return {
        "event": "messages.upsert",
        "instance": "cartorio-agent",
        "data": {
            "key": {
                "remoteJid": f"{sender.lstrip('+')}@s.whatsapp.net",
                "fromMe": False,
                "id": message_id,
            },
            "message": {"conversation": "mensagem sintetica"},
        },
    }


def test_normalize_accepts_e164_private_jid_and_legacy_mobile() -> None:
    assert normalize_whatsapp_number("+55 (11) 99876-5432") == ALLOWED
    assert normalize_whatsapp_number("5511998765432@s.whatsapp.net") == ALLOWED
    assert normalize_whatsapp_number("551198765432") == ALLOWED
    assert normalize_whatsapp_number("+55 34 99880-7228") == "+5534998807228"
    assert normalize_whatsapp_number("+55 34 99280-0250") == "+5534992800250"


def test_normalize_rejects_group_broadcast_and_lid_without_alternative() -> None:
    assert normalize_whatsapp_number("120363000@g.us") is None
    assert normalize_whatsapp_number("status@broadcast") is None
    assert normalize_whatsapp_number("162023748985056@lid") is None


def test_allowlist_authorizes_only_configured_sender() -> None:
    allowed = _decide(ALLOWED, hashes=_allowlist(ALLOWED))
    denied = _decide(DENIED, hashes=_allowlist(ALLOWED))
    assert allowed.allowed is True
    assert denied.allowed is False
    assert denied.reason == "sender_not_allowed"


def test_lid_uses_alternate_phone_for_authorization() -> None:
    result = _decide(
        "162023748985056@lid",
        alt="5511998765432@s.whatsapp.net",
        hashes=_allowlist(ALLOWED),
    )
    assert result.allowed is True


def test_restricted_empty_hashes_uses_pilot_felipe_and_gustavo() -> None:
    """Hashes vazios nao abrem o publico: so Felipe e Gustavo."""
    felipe = _decide("+5534998807228", hashes="")
    gustavo = _decide("5534992800250", hashes="")
    stranger = _decide(ALLOWED, hashes="")
    no_key = _decide(ALLOWED, hashes=_allowlist(ALLOWED), key="short")
    assert felipe.allowed is True
    assert felipe.reason == "sender_allowed_pilot"
    assert gustavo.allowed is True
    assert stranger.allowed is False
    assert stranger.reason == "sender_not_allowed"
    assert no_key.allowed is False
    assert no_key.reason == "allowlist_key_not_configured"
    assert PIETRA_WHATSAPP_PILOT_E164 == ("+5534998807228", "+5534992800250")


def test_explicit_unrestricted_mode_remains_testable() -> None:
    result = _decide(DENIED, restrict=False)
    assert result.allowed is True
    assert result.reason == "allowlist_disabled_nonproduction"


def test_invalid_allowlist_entries_are_ignored() -> None:
    good_hash = hmac_sender(ALLOWED, hmac_key=HMAC_KEY)
    assert parse_allowed_sender_hashes(f"invalid,{good_hash}") == {good_hash}


def test_primary_webhook_blocks_before_idempotency(monkeypatch) -> None:
    monkeypatch.setattr(settings, "pietra_whatsapp_restrict_inbound", True)
    monkeypatch.setattr(settings, "pietra_whatsapp_allowlist_hmac_key", HMAC_KEY)
    monkeypatch.setattr(settings, "pietra_whatsapp_allowed_sender_hashes", _allowlist(ALLOWED))
    monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "false")
    adapter = AsyncMock()
    adapter.verify_signature = AsyncMock(return_value=True)

    with (
        patch("app.api.v1.whatsapp.get_adapter", return_value=adapter),
        patch("app.api.v1.whatsapp.ingest_evolution_event") as ingest,
    ):
        response = TestClient(app).post(
            "/api/v1/whatsapp/webhook",
            json=_payload(DENIED, "blocked-primary-1"),
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "detail": "sender_not_authorized"}
    ingest.assert_not_called()


def test_legacy_webhook_blocks_before_idempotency(monkeypatch) -> None:
    monkeypatch.setattr(settings, "evolution_legacy_webhook_enabled", True)
    monkeypatch.setattr(settings, "pietra_whatsapp_restrict_inbound", True)
    monkeypatch.setattr(settings, "pietra_whatsapp_allowlist_hmac_key", HMAC_KEY)
    monkeypatch.setattr(settings, "pietra_whatsapp_allowed_sender_hashes", _allowlist(ALLOWED))
    monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "false")

    with patch("app.services.evolution_ingest.ingest_evolution_event") as ingest:
        response = TestClient(app).post(
            "/api/v1/webhook/evolution",
            json=_payload(DENIED, "blocked-legacy-1"),
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "detail": "sender_not_authorized"}
    ingest.assert_not_called()


def test_test_send_is_hidden_in_production(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    with patch("app.api.v1.whatsapp.get_adapter") as get_adapter:
        response = TestClient(app).post(
            "/api/v1/whatsapp/test/send",
            params={"to": ALLOWED, "text": "mensagem sintetica"},
            headers={"X-API-Key": settings.cartorio_api_key},
        )
    assert response.status_code == 404
    get_adapter.assert_not_called()
