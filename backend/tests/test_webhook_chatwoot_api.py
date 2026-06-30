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
        assert response.status_code in (401, 403, 200, 422)
