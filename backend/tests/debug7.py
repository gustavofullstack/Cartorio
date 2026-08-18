import asyncio
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock
from tests.test_telegram_e2e_5x import _telegram_update, StatefulBus

def test_manual():
    client = TestClient(app)
    bus = StatefulBus()
    # PRE SET LGPD CONSENT TO AVOID PARTIAL RESPONSE FROM LGPD GATE
    bus.store["tg:lgpd:consent:889900"] = "1" # Hardcoded user_id in the mock

    update = _telegram_update(update_id=20001, text="/protocolo")
    with (
        patch("app.api.v1.telegram.get_bus", return_value=bus),
        patch("app.api.v1.telegram._send_typing_fast", new=AsyncMock()),
        patch("app.api.v1.telegram._send_message", new=AsyncMock(return_value=True)) as mock_send,
    ):
        resp = client.post("/api/v1/telegram/webhook", json=update)
        print("RESPONSE CODE:", resp.status_code)
        print("RESPONSE JSON:", resp.json())

test_manual()
