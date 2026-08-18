import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import BackgroundTasks
import app.api.v1.telegram as tg

async def run():
    class _FakeBus:
        def __init__(self):
            self.client = AsyncMock()
            self.client.get.return_value = None
            self.client.set.return_value = True

    bus = _FakeBus()

    update = {
        "update_id": 7004,
        "message": {
            "message_id": 7004,
            "date": 1721308500,
            "from": {"id": 4242},
            "chat": {"id": 4242, "type": "private"},
            "text": "quero agendar uma escritura",
        },
    }

    req = MagicMock()
    req.json = AsyncMock(return_value=update)

    bt = BackgroundTasks()

    with patch.object(tg, "get_bus", return_value=bus), \
         patch.object(tg, "_send_typing_fast", new=AsyncMock()), \
         patch.object(tg, "_react", new=AsyncMock()), \
         patch.object(tg, "_client_profile_upsert", new=AsyncMock()):
        resp = await tg.telegram_webhook(req, bt, None, MagicMock())
        print(f"Resp: {resp}")

if __name__ == "__main__":
    asyncio.run(run())
