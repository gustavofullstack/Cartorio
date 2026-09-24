"""OpenClaw auth.challenge handler (G6.E.T10).

Implementa o handshake de autenticacao OpenClaw v1 (lesson 64 super prompt).
Recebe connect.challenge com nonce, responde auth.challenge com HMAC-SHA256
do nonce + password.

OpenClaw protocolo:
1. server -> client: connect.challenge {nonce, ts}
2. client -> server: auth.challenge {nonce, signature}
3. server -> client: auth.ok OU auth.failed
4. connection mantida

Uso:
    python3 scripts/openclaw_auth_handler.py --dry-run
    python3 scripts/openclaw_auth_handler.py --connect    # WS real

Exit codes:
    0 = handshake OK
    1 = auth failed
    2 = erro pre-requisito

Modified by Gustavo Almeida + cartorio-llm — G6 wave 22.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone

DEFAULT_URL = "wss://agent.2notasudi.com.br/v1/chat"


def get_password() -> str | None:
    """Pega password do env (NUNCA commitar valor)."""
    return os.environ.get("OPENCLAW_GATEWAY_PASSWORD")


def sign_challenge(nonce: str, ts_ms: int, password: str) -> str:
    """Assina challenge: SHA256(password + nonce + ts_ms) -> hex."""
    msg = f"{password}{nonce}{ts_ms}".encode()
    return hashlib.sha256(msg).hexdigest()


def render_dry_run(nonce: str, ts_ms: int, password: str) -> str:
    """Renderiza JSON de dry-run."""
    signature = sign_challenge(nonce, ts_ms, password)
    return json.dumps(
        {
            "type": "auth.challenge",
            "payload": {
                "nonce": nonce,
                "ts": ts_ms,
                "signature": signature,
                "algo": "sha256",
            },
        },
        indent=2,
        ensure_ascii=False,
    )


async def connect_and_auth(url: str, password: str, timeout: float) -> bool:
    """Conecta WS, responde challenge, espera auth.ok."""
    try:
        import websockets  # type: ignore[import-untyped]
    except ImportError:
        print("[ERROR] websockets nao instalado", file=sys.stderr)
        return False

    try:
        async with websockets.connect(url, open_timeout=timeout) as ws:
            # Recebe connect.challenge
            challenge_raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            challenge = json.loads(challenge_raw)
            print(f"[challenge] {challenge}", file=sys.stderr)

            if challenge.get("type") != "event" or challenge.get("event") != "connect.challenge":
                print(f"[ERROR] esperado connect.challenge, recebeu {challenge.get('event')}", file=sys.stderr)
                return False

            nonce = challenge["payload"]["nonce"]
            ts_ms = challenge["payload"]["ts"]
            signature = sign_challenge(nonce, ts_ms, password)

            # Envia auth.challenge
            response = {
                "type": "auth.challenge",
                "payload": {"nonce": nonce, "ts": ts_ms, "signature": signature, "algo": "sha256"},
            }
            await ws.send(json.dumps(response))
            print(f"[sent] auth.challenge com signature {signature[:16]}...", file=sys.stderr)

            # Espera auth.ok / auth.failed
            result_raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            result = json.loads(result_raw)
            print(f"[result] {result}", file=sys.stderr)

            if result.get("event") == "auth.ok":
                print("[WORK] auth OK, pode usar cartorio-bot")
                return True
            print(f"[HOLD] auth falhou: {result}")
            return False
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw auth.challenge handler")
    parser.add_argument("--url", default=DEFAULT_URL, help="OpenClaw WebSocket URL")
    parser.add_argument("--password", help="password (default: OPENCLAW_GATEWAY_PASSWORD)")
    parser.add_argument("--connect", action="store_true", help="conectar real (default: dry-run)")
    parser.add_argument("--timeout", type=float, default=15.0, help="timeout em segundos")
    args = parser.parse_args()

    password = args.password or get_password()
    if not password:
        print("[ERROR] OPENCLAW_GATEWAY_PASSWORD nao definido", file=sys.stderr)
        return 2

    print(f"URL: {args.url}")
    print(f"Mode: {'connect' if args.connect else 'dry-run'}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()

    if not args.connect:
        # Dry-run: simula challenge
        fake_nonce = "00000000-0000-0000-0000-000000000000"
        fake_ts = 1784226940000
        print(render_dry_run(fake_nonce, fake_ts, password))
        return 0

    ok = asyncio.run(connect_and_auth(args.url, password, args.timeout))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())