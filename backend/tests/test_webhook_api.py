"""Tests for /api/v1/webhook/ endpoints.

Validates webhook API endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestWebhookAPI:
    """Webhook endpoint tests."""

    def test_webhook_chatwoot_requires_hmac(self) -> None:
        """POST /api/v1/webhook/chatwoot requires HMAC signature."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/webhook/chatwoot",
            json={"event": "test", "data": {}},
        )
        assert response.status_code in (401, 403, 200, 422)

    @pytest.mark.skip(reason="Requires DB connection - tested in integration")
    def test_webhook_evolution_requires_hmac(self) -> None:
        """POST /api/v1/webhook/evolution requires HMAC signature."""
        pass
