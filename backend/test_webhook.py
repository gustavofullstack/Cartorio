"""Smoke manual: POST no webhook Telegram LOCAL com secret via env.

Secret SOMENTE via env var TELEGRAM_WEBHOOK_SECRET — nunca colar literal
aqui (segredos vazados neste arquivo foram scrubbed em 2026-07-20, G9).
URL alvo configuravel via TELEGRAM_WEBHOOK_URL (default: localhost:8000).
"""

import asyncio
import os
import sys
import time

import httpx

TARGET_URL = os.environ.get(
    "TELEGRAM_WEBHOOK_URL",
    "http://localhost:8000/api/v1/telegram/webhook",
)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"ERRO: defina a env var {name} (nunca cole o valor no codigo).")
    return value


async def main() -> None:
    secret = _required_env("TELEGRAM_WEBHOOK_SECRET")
    payload = {
        "update_id": int(time.time()),
        "message": {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "Test"},
            "chat": {"id": 123456789, "type": "private"},
            "date": int(time.time()),
            "text": "Quais servicos voces oferecem?",
        },
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TARGET_URL,
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        )
        print("Status:", resp.status_code)
        print("Response:", resp.json())

    # Wait for the background task
    await asyncio.sleep(8)


asyncio.run(main())
