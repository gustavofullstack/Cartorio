import asyncio
import httpx
import sys


async def simulate_human(total_messages=1000):
    url = "http://127.0.0.1:8000/api/v1/telegram/webhook"

    # We simulate a conversation
    success_count = 0
    error_count = 0

    async with httpx.AsyncClient() as client:
        for i in range(total_messages):
            payload = {
                "update_id": 1000000 + i,
                "message": {
                    "message_id": 100 + i,
                    "from": {
                        "id": 123456789,
                        "is_bot": False,
                        "first_name": "Gustavo",
                        "username": "gustavoalmeida",
                    },
                    "chat": {
                        "id": 123456789,
                        "first_name": "Gustavo",
                        "username": "gustavoalmeida",
                        "type": "private",
                    },
                    "date": 1718000000 + i,
                    "text": f"Olá, bot! Mensagem humana de teste {i}",
                },
            }
            try:
                # Assuming the local server is running on 8000
                response = await client.post(url, json=payload, timeout=5.0)
                if response.status_code in (200, 202):
                    success_count += 1
                else:
                    error_count += 1
                    print(f"Error status: {response.status_code} body: {response.text}")
            except Exception as e:
                error_count += 1
                print(f"Request {i} failed: {e}")

            if (i + 1) % 100 == 0:
                print(
                    f"Processed {i + 1}/{total_messages} (Success: {success_count}, Error: {error_count})"
                )

    print(f"Completed! Success: {success_count} / {total_messages}. Errors: {error_count}")
    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(simulate_human(1000))
