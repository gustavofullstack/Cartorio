import asyncio
from app.api.v1.telegram import _handle_state, STATE_AGENDAR_DATA
class MockBus:
    async def set(self, k, v, ex=None): pass
    async def delete(self, k): pass
async def main():
    bus = MockBus()
    text, new_state, keyboard = await _handle_state("data invalida xyz", STATE_AGENDAR_DATA, {}, bus, chat_id=123)
    print(f"text: {text!r}")
    print(f"new_state: {new_state!r}")
    print(f"keyboard: {keyboard!r}")

asyncio.run(main())
