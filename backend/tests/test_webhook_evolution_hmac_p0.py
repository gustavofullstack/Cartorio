"""P0 — HMAC fail-closed no endpoint canônico /api/v1/webhook/evolution.

A URL de produção (EVOLUTION_WEBHOOK_URL) aponta para este path. Antes da
Wave Final P0 o handler processava payload sem validar assinatura.

Contrato (paridade com /api/v1/whatsapp/webhook):
- EVOLUTION_REQUIRE_SIGNATURE=true + secret configurado + sig inválida → 401
- secret ausente + require true → 503
- sig válida → processa (não 401)
- require false (dev/test default) → processa sem sig

Sem secrets em assertions. Modified by Gustavo Almeida.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

ENDPOINT = "/api/v1/webhook/evolution"


def _payload(message_id: str = "evo-hmac-p0-1") -> dict:
    return {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {
                "remoteJid": "5534999999999@s.whatsapp.net",
                "fromMe": False,
                "id": message_id,
            },
            "message": {"conversation": "mensagem sintetica teste"},
            "pushName": "Usuario Sintetico",
        },
    }


def _raw(message_id: str = "evo-hmac-p0-1") -> bytes:
    return json.dumps(_payload(message_id), separators=(",", ":")).encode("utf-8")


def _sig(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestWebhookEvolutionHmacP0:
    """Regressão de segurança no path canônico Evolution."""

    def test_invalid_signature_rejected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "true")
        monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "p0-evolution-secret")
        raw = _raw()
        resp = client.post(
            ENDPOINT,
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "deadbeef",
            },
        )
        assert resp.status_code == 401
        assert "invalid" in resp.json().get("detail", "").lower()

    def test_missing_signature_rejected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "true")
        monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "p0-evolution-secret")
        resp = client.post(
            ENDPOINT,
            content=_raw(),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401

    def test_malformed_sha256_prefix_rejected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "true")
        monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "p0-evolution-secret")
        resp = client.post(
            ENDPOINT,
            content=_raw(),
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=not-hex",
            },
        )
        assert resp.status_code == 401

    def test_required_without_secret_fails_closed(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "true")
        monkeypatch.delenv("EVOLUTION_WEBHOOK_SECRET", raising=False)
        monkeypatch.delenv("EVOLUTION_WEBHOOK_SECRET_PREV", raising=False)
        resp = client.post(
            ENDPOINT,
            content=_raw(),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 503

    def test_valid_signature_not_401(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        secret = "p0-evolution-secret"
        monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "true")
        monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", secret)
        raw = _raw("evo-hmac-p0-valid")
        # Evita LLM real no caminho feliz
        with patch("app.api.v1.router.scrub") as scrub_mock:
            from app.services.pii import ScrubResult

            scrub_mock.return_value = ScrubResult(
                text="mensagem sintetica teste",
                findings=[],
                redaction_count=0,
            )
            resp = client.post(
                ENDPOINT,
                content=raw,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": _sig(secret, raw),
                },
            )
        assert resp.status_code != 401
        assert resp.status_code != 503
        assert resp.status_code in (200, 422)

    def test_x_evolution_signature_header_accepted(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        secret = "p0-evolution-secret"
        monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "true")
        monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", secret)
        raw = _raw("evo-hmac-p0-alt-hdr")
        with patch("app.api.v1.router.scrub") as scrub_mock:
            from app.services.pii import ScrubResult

            scrub_mock.return_value = ScrubResult(
                text="mensagem sintetica teste",
                findings=[],
                redaction_count=0,
            )
            resp = client.post(
                ENDPOINT,
                content=raw,
                headers={
                    "Content-Type": "application/json",
                    "X-Evolution-Signature": _sig(secret, raw),
                },
            )
        assert resp.status_code != 401

    def test_require_false_allows_unsigned_dev(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Modo dev/test (conftest): REQUIRE=false não bloqueia unsigned."""
        monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "false")
        monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "")
        with patch("app.api.v1.router.scrub") as scrub_mock:
            from app.services.pii import ScrubResult

            scrub_mock.return_value = ScrubResult(
                text="mensagem sintetica teste",
                findings=[],
                redaction_count=0,
            )
            resp = client.post(ENDPOINT, json=_payload("evo-hmac-p0-dev"))
        assert resp.status_code != 401
        assert resp.status_code != 503
