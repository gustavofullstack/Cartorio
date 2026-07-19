"""Testes unitários para os endpoints de integração com o Chatwoot (Wave 6 S6.T1/S6.T3).

Valida:
- GET /api/v1/integrations/chatwoot/health (com mock de HTTP)
- POST /api/v1/integrations/chatwoot/consent-propagation (com mock de HTTP)

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)
TEST_HEADERS = {"X-API-Key": "a" * 64}


@respx.mock
def test_chatwoot_health_check_online() -> None:
    """GET /api/v1/integrations/chatwoot/health deve retornar online se o Chatwoot responder com sucesso."""
    settings.chatwoot_base_url = "https://chat.test.com"

    # Mock do endpoint de login do Chatwoot
    respx.get("https://chat.test.com/auth/sign_in").mock(
        return_value=httpx.Response(200, text="Sign In Page")
    )

    resp = client.get("/api/v1/integrations/chatwoot/health", headers=TEST_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "online"
    assert body["http_status"] == 200
    assert body["base_url"] == "https://chat.test.com"


@respx.mock
def test_chatwoot_health_legacy_alias_remains_available() -> None:
    """Clientes v1 antigos mantem health enquanto migram ao prefixo integrations."""
    settings.chatwoot_base_url = "https://chat.test.com"
    respx.get("https://chat.test.com/auth/sign_in").mock(return_value=httpx.Response(200))

    resp = client.get("/api/v1/chatwoot/health", headers=TEST_HEADERS)

    assert resp.status_code == 200
    assert resp.json()["status"] == "online"


@respx.mock
def test_chatwoot_health_check_offline() -> None:
    """GET /api/v1/integrations/chatwoot/health deve retornar offline se a chamada falhar ou der timeout."""
    settings.chatwoot_base_url = "https://chat.test.com"

    respx.get("https://chat.test.com/auth/sign_in").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    resp = client.get("/api/v1/integrations/chatwoot/health", headers=TEST_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "offline"
    assert "Connection refused" in body["error"]


@respx.mock
def test_chatwoot_consent_propagation_success() -> None:
    """POST /api/v1/integrations/chatwoot/consent-propagation deve aplicar labels com sucesso no Chatwoot."""
    settings.chatwoot_base_url = "https://chat.test.com"
    settings.chatwoot_api_key = "test_key"
    settings.chatwoot_account_id = 1

    # Mock do endpoint de labels do Chatwoot
    respx.post("https://chat.test.com/api/v1/accounts/1/conversations/42/labels").mock(
        return_value=httpx.Response(200, json={"payload": ["consent-lgpd-telegram"]})
    )

    payload = {
        "chatwoot_conversation_id": 42,
        "telegram_chat_id": "12345678",
        "labels": ["consent-lgpd-telegram"],
        "consent_source": "telegram",
    }

    resp = client.post(
        "/api/v1/integrations/chatwoot/consent-propagation", json=payload, headers=TEST_HEADERS
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "propagated"
    assert body["labels_applied"] is True
    assert body["chatwoot_conversation_id"] == 42


@respx.mock
def test_chatwoot_consent_propagation_legacy_alias_remains_available() -> None:
    """A mudanca de namespace nao pode quebrar automacoes Chatwoot existentes."""
    settings.chatwoot_base_url = "https://chat.test.com"
    settings.chatwoot_api_key = "test_key"
    settings.chatwoot_account_id = 1
    respx.post("https://chat.test.com/api/v1/accounts/1/conversations/42/labels").mock(
        return_value=httpx.Response(200, json={"payload": ["consent-lgpd-telegram"]})
    )

    resp = client.post(
        "/api/v1/chatwoot/consent-propagation",
        json={"chatwoot_conversation_id": 42, "telegram_chat_id": "12345678"},
        headers=TEST_HEADERS,
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "propagated"


@respx.mock
def test_chatwoot_consent_propagation_skipped_when_not_configured() -> None:
    """POST /api/v1/integrations/chatwoot/consent-propagation deve retornar skipped se chaves do Chatwoot não configuradas."""
    settings.chatwoot_base_url = None  # Desliga config

    payload = {
        "chatwoot_conversation_id": 42,
        "telegram_chat_id": "12345678",
        "labels": ["consent-lgpd-telegram"],
        "consent_source": "telegram",
    }

    resp = client.post(
        "/api/v1/integrations/chatwoot/consent-propagation", json=payload, headers=TEST_HEADERS
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "skipped"
    assert body["reason"] == "chatwoot_not_configured"
