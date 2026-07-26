import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.telegram1000
async def test_telegram_1000_interactions_concurrent():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        async def send_interaction(i):
            payload = {
                "update_id": 1000000 + i,
                "message": {
                    "message_id": 100 + i,
                    "from": {
                        "id": 123456789,
                        "is_bot": False,
                        "first_name": "Gustavo",
                        "username": "gustavoalmeida",
                    },
                    "chat": {
                        "id": 123456789,
                        "first_name": "Gustavo",
                        "username": "gustavoalmeida",
                        "type": "group",
                    },
                    "date": 1718000000,
                    "text": f"Simulated group message {i}",
                },
            }
            # We send to the telegram webhook endpoint
            response = await client.post("/api/v1/telegram/webhook", json=payload)
            return response.status_code

        # Fire 1000 concurrent webhook requests from the SAME chat_id/user_id in a group chat.
        # This will test the debounce queue heavily (all in the same 1.2s window).
        tasks = [send_interaction(i) for i in range(1000)]
        results = await asyncio.gather(*tasks)

        # All requests should return 200 (or 202)
        assert all(status in (200, 202) for status in results)
