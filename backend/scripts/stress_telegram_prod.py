"""Stress manual: 1000 updates no webhook Telegram de PROD.

Webhook secret SOMENTE via env var TELEGRAM_WEBHOOK_SECRET (obrigatoria
— sem ela o webhook responde 401 e o teste nao mede nada). URL alvo
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


async def simulate_human(total_messages: int = 1000) -> None:
    headers = {"X-Telegram-Bot-Api-Secret-Token": _required_env("TELEGRAM_WEBHOOK_SECRET")}
    success_count = 0
    error_count = 0
    start_time = time.time()

    limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
    async with httpx.AsyncClient(limits=limits) as client:
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

            tasks.append(client.post(TARGET_URL, json=payload, headers=headers, timeout=15.0))

            # Batching to not overload the local network stack instantly
            if len(tasks) >= 50:
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for res in responses:
                    if isinstance(res, Exception):
                        error_count += 1
                    elif res.status_code in (200, 202):
                        success_count += 1
                    else:
                        error_count += 1
                tasks = []
                print(f"Processed batch. Success: {success_count}, Error: {error_count}")
                await asyncio.sleep(0.5)

        if tasks:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for res in responses:
                if isinstance(res, Exception):
                    error_count += 1
                elif res.status_code in (200, 202):
                    success_count += 1
                else:
                    error_count += 1

    duration = time.time() - start_time
    total = total_messages
    print(f"Completed in {duration:.2f}s! Success: {success_count} / {total}. Errors: {error_count}")


if __name__ == "__main__":
    asyncio.run(simulate_human(1000))
