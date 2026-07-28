"""Smoke manual: chat completion no OpenCode Zen (max_tokens=700).

Chave SOMENTE via env var (OPENCODE_ZEN_ACCOUNT_1_API_KEY ou
OPENCODE_FREE_1_API_KEY) — nunca colar literal aqui (segredos vazados
neste arquivo foram scrubbed em 2026-07-20, G9).
"""

import asyncio
import os
import sys

import httpx

BASE_URL = os.environ.get(
    "OPENCODE_ZEN_ACCOUNT_1_BASE_URL",
    "https://opencode.ai/zen/v1",
).rstrip("/")
MODEL = os.environ.get("OPENCODE_ZEN_ACCOUNT_1_MODEL", "deepseek-v4-flash-free")


def _zen_key() -> str:
    for name in ("OPENCODE_ZEN_ACCOUNT_1_API_KEY", "OPENCODE_FREE_1_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    sys.exit(
        "ERRO: defina OPENCODE_ZEN_ACCOUNT_1_API_KEY (ou OPENCODE_FREE_1_API_KEY) "
        "no ambiente — nunca cole a chave no codigo."
    )


async def main() -> None:
    url = f"{BASE_URL}/chat/completions"
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Quais serviços vocês oferecem?"}],
        "max_tokens": 700,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(50.0)) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {_zen_key()}"},
            json=payload,
        )
        print("Status:", resp.status_code)
        print("Response:", resp.text)


if __name__ == "__main__":
    asyncio.run(main())
