"""Stress debug manual: poucos updates no webhook Telegram de PROD.

Webhook secret SOMENTE via env var TELEGRAM_WEBHOOK_SECRET (obrigatoria
— sem ela o webhook responde 401 e o debug nao mede nada). URL alvo
configuravel via TELEGRAM_WEBHOOK_URL. Auditado em 2026-07-20 (G9):
nenhum literal de secret; header de secret adicionado via env.
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


async def simulate_human(total_messages: int = 10) -> None:
    secret = _required_env("TELEGRAM_WEBHOOK_SECRET")
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=100)) as client:
        tasks = []
        for i in range(total_messages):
            payload = {
                "update_id": 1000000 + i,
                "message": {
                    "message_id": 100 + i,
                    "from": {
                        "id": 999999999,
                        "is_bot": False,
                        "first_name": "Gustavo",
                        "username": "gustavoalmeida",
                    },
                    "chat": {
                        "id": 999999999,
                        "first_name": "Gustavo",
                        "username": "gustavoalmeida",
                        "type": "private",
                    },
                    "date": int(time.time()),
                    "text": f"Olá, bot! Teste massivo {i}",
                },
            }

            headers = {
                "X-Forwarded-For": f"1.1.1.{i % 250}",
                "X-Telegram-Bot-Api-Secret-Token": secret,
            }

            tasks.append(client.post(TARGET_URL, json=payload, headers=headers, timeout=15.0))

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for res in responses:
            if isinstance(res, Exception):
                print(f"Exception: {res}")
            else:
                print(f"Status: {res.status_code}, Body: {res.text}")


if __name__ == "__main__":
    asyncio.run(simulate_human(5))
