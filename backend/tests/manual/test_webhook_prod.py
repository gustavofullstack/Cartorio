"""Smoke manual: POST no webhook Telegram de PROD com secret via env.

Secret SOMENTE via env var TELEGRAM_WEBHOOK_SECRET — nunca colar literal
aqui (segredos vazados neste arquivo foram scrubbed em 2026-07-20, G9).
URL alvo configuravel via TELEGRAM_WEBHOOK_URL (default: api.2notasudi.com.br).
"""

import asyncio
import os
import sys
import time

import httpx

TARGET_URL = os.environ.get(
    "TELEGRAM_WEBHOOK_URL",
    "https://api.2notasudi.com.br/api/v1/telegram/webhook",
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
            "from": {"id": 885920626, "first_name": "Test"},
            "chat": {"id": 885920626, "type": "private"},
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


asyncio.run(main())
