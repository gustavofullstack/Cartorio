import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import BackgroundTasks
import app.api.v1.telegram as tg

async def run():
    class _FakeBus:
        def __init__(self) -> None:
            self.store: dict[str, str] = {}
            self.store["lgpd:4242"] = "1"
            self.client = self

        async def set(
            self, key: str, value: str, *, ex: int | None = None, nx: bool = False
        ) -> str | None:
            if nx and key in self.store:
                return None
            self.store[key] = value
            return "OK"

        async def get(self, key: str) -> str | None:
            return self.store.get(key)

        async def delete(self, key: str) -> int:
            return 1 if self.store.pop(key, None) is not None else 0

        def pipeline(self, transaction: bool = True):
            return _FakePipeline(self)

    class _FakePipeline:
        def __init__(self, bus) -> None:
            self.bus = bus
            self.cmds = []

        def rpush(self, key: str, val: str) -> "_FakePipeline":
            self.cmds.append(("rpush", key, val))
            return self

        def expire(self, key: str, ttl: int) -> "_FakePipeline":
            self.cmds.append(("expire", key, ttl))
            return self

        async def execute(self) -> list:
            for cmd, key, val in self.cmds:
                if cmd == "rpush":
                    pass
            return [1] * len(self.cmds)

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
