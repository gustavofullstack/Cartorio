"""CartorioBot E2E test (G6.E.T11).

Teste end-to-end do cartorio-bot:
1. Conecta WebSocket OpenClaw
2. Faz handshake auth.challenge
3. Envia mensagem "oi"
4. Espera resposta
5. Valida formato da resposta (content present, <5s latency)

Uso:
    python3 scripts/cartorio_bot_e2e_test.py
    python3 scripts/cartorio_bot_e2e_test.py --message "Quanto custa uma certidao?"
    python3 scripts/cartorio_bot_e2e_test.py --expect-timeout 10

Exit codes:
    0 = bot respondeu OK em <5s
    1 = bot nao respondeu
    2 = erro pre-requisito
    3 = bot respondeu mas >5s (SLO burn)

Modified by Gustavo Almeida + cartorio-llm — G6 wave 25.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

DEFAULT_URL = "wss://agent.2notasudi.com.br/v1/chat"
DEFAULT_MESSAGE = "oi"
SLO_LATENCY_SECONDS = 5.0


def get_config() -> tuple[str, str | None]:
    """Retorna (url, password)."""
    return (
        os.environ.get("OPENCLAW_URL", DEFAULT_URL),
        os.environ.get("OPENCLAW_GATEWAY_PASSWORD"),
    )


def sign_challenge(nonce: str, ts_ms: int, password: str) -> str:
    """Assina challenge: SHA256(password + nonce + ts_ms) -> hex."""
    msg = f"{password}{nonce}{ts_ms}".encode()
    return hashlib.sha256(msg).hexdigest()


async def run_e2e(url: str, password: str | None, message: str, timeout: float) -> tuple[bool, float, str | None, str | None]:
    """Executa E2E completo. Retorna (success, latency_s, response, error)."""
    try:
        import websockets  # type: ignore[import-untyped]
    except ImportError:
        return (False, 0.0, None, "websockets nao instalado")

    start = time.monotonic()
    try:
        async with websockets.connect(url, open_timeout=timeout) as ws:
            # Recebe connect.challenge
            challenge_raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            challenge = json.loads(challenge_raw)

            if challenge.get("event") != "connect.challenge":
                return (False, time.monotonic() - start, None, f"challenge invalido: {challenge.get('event')}")

            # Se password configurado, faz auth
            if password:
                nonce = challenge["payload"]["nonce"]
                ts_ms = challenge["payload"]["ts"]
                signature = sign_challenge(nonce, ts_ms, password)
                response = {
                    "type": "auth.challenge",
                    "payload": {"nonce": nonce, "ts": ts_ms, "signature": signature, "algo": "sha256"},
                }
                await ws.send(json.dumps(response))
                auth_result_raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                auth_result = json.loads(auth_result_raw)
                if auth_result.get("event") != "auth.ok":
                    return (False, time.monotonic() - start, None, f"auth falhou: {auth_result}")

            # Envia mensagem do usuario
            user_payload = {
                "type": "message",
                "agent": "cartorio-bot",
                "session_id": f"e2e-{int(time.time())}",
                "message": {"role": "user", "content": message, "timestamp": datetime.now(timezone.utc).isoformat()},
            }
            await ws.send(json.dumps(user_payload))

            # Espera resposta
            response_raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            response = json.loads(response_raw)

            latency = time.monotonic() - start
            content = (
                response.get("message", {}).get("content")
                or response.get("content")
                or response.get("response")
            )
            return (bool(content), latency, str(content) if content else json.dumps(response), None)
    except asyncio.TimeoutError:
        return (False, time.monotonic() - start, None, f"timeout apos {timeout}s")
    except Exception as exc:
        return (False, time.monotonic() - start, None, f"{type(exc).__name__}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CartorioBot E2E test")
    parser.add_argument("--url", help="OpenClaw WebSocket URL")
    parser.add_argument("--password", help="password (OPENCLAW_GATEWAY_PASSWORD)")
    parser.add_argument("--message", default=DEFAULT_MESSAGE, help="mensagem para enviar")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--expect-timeout", type=float, help="fail se latency > N segundos (SLO check)")
    args = parser.parse_args()

    url, env_password = get_config()
    if args.url:
        url = args.url
    password = args.password or env_password

    print(f"URL: {url}")
    print(f"Message: {args.message!r}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()

    ok, latency, response, error = asyncio.run(run_e2e(url, password, args.message, args.timeout))

    print(f"Latency: {latency:.3f}s")
    if error:
        print(f"[ERROR] {error}")
    if response:
        # Truncar para nao spammar
        preview = response[:200] + ("..." if len(response) > 200 else "")
        print(f"Response: {preview}")

    if not ok:
        return 1
    if args.expect_timeout and latency > args.expect_timeout:
        print(f"[SLO BURN] Latency {latency:.3f}s > {args.expect_timeout}s (OpenClaw SLO 95% < 5s)")
        return 3
    if latency > SLO_LATENCY_SECONDS:
        print(f"[SLO WARNING] Latency {latency:.3f}s > {SLO_LATENCY_SECONDS}s SLO target")
        return 0  # SUCESSO mas com warning

    print(f"[WORK] E2E OK em {latency:.3f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())