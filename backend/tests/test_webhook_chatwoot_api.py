"""Tests for /api/v1/webhook/chatwoot endpoint.

Validates Chatwoot webhook endpoint.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestWebhookChatwootAPI:
    """Webhook Chatwoot endpoint tests."""

    def test_webhook_chatwoot_requires_hmac(self) -> None:
        """POST /api/v1/webhook/chatwoot requires HMAC signature."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/webhook/chatwoot",
            json={"event": "conversation_updated", "data": {}},
        )
        assert response.status_code in (401, 403, 422, 503)

    def test_enabled_webhook_fails_closed_without_secret(self, monkeypatch) -> None:
        from app.config import settings

        monkeypatch.setattr(settings, "chatwoot_webhook_enabled", True)
        monkeypatch.setattr(settings, "chatwoot_webhook_secret", None)
        client = TestClient(app)

        response = client.post(
            "/api/v1/webhook/chatwoot",
            content=b"{}",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 401
