from unittest.mock import AsyncMock
import asyncio

async def main():
    mock = AsyncMock()
    mock.return_value = {"status": "ok", "chat_id": 123, "scheduled": True}
    print(await mock())

asyncio.run(main())
