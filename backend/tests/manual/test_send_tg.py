"""Smoke manual: getUpdates do bot Telegram.

Token SOMENTE via env var TELEGRAM_BOT_TOKEN — nunca colar literal aqui
(segredos vazados neste arquivo foram scrubbed em 2026-07-20, G9).
"""

import asyncio
import os
import sys

import httpx


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"ERRO: defina a env var {name} (nunca cole o valor no codigo).")
    return value


async def main() -> None:
    token = _required_env("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        print(resp.json())


asyncio.run(main())
