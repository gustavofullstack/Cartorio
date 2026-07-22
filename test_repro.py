import asyncio
from app.api.v1.telegram import _handle_state, STATE_AGENDAR_DATA
import fakeredis

async def main():
    bus = type('MockBus', (), {'client': fakeredis.FakeAsyncRedis()})()
    text, new_state, keyboard = await _handle_state(
        "data invalida xyz", STATE_AGENDAR_DATA, {}, bus, chat_id=123
    )
    print(f"text: {text!r}, new_state: {new_state}, keyboard: {keyboard}")

asyncio.run(main())
