"""CartorioBot Chat CLI (G6.E.T9).

Conecta via WebSocket no OpenClaw e conversa com cartorio-bot.
Util para testar deploy do bot sem precisar de UI completa.

Uso:
    python3 scripts/cartorio_bot_chat.py                    # default URL
    python3 scripts/cartorio_bot_chat.py --message "oi"     # 1 mensagem
    python3 scripts/cartorio_bot_chat.py --interactive      # modo interativo
    python3 scripts/cartorio_bot_chat.py --dry-run          # mostra request

Exit codes:
    0 = bot respondeu
    1 = erro de conexao
    2 = erro pre-requisito

Modified by Gustavo Almeida + cartorio-llm — G6 wave 18.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone

DEFAULT_URL = "wss://agent.2notasudi.com.br/v1/chat"
TIMEOUT = 30.0


def build_message(text: str, session_id: str | None = None) -> dict:
    """Constroi payload OpenClaw v1 chat."""
    return {
        "type": "message",
        "agent": "cartorio-bot",
        "session_id": session_id or f"cli-{datetime.now(timezone.utc).timestamp()}",
        "message": {
            "role": "user",
            "content": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


async def send_one_message(url: str, text: str, timeout: float) -> dict | None:
    """Envia 1 mensagem e aguarda resposta."""
    try:
        import websockets  # type: ignore[import-untyped]
    except ImportError:
        print("[ERROR] websockets nao instalado: uv add websockets", file=sys.stderr)
        return None

    payload = build_message(text)
    try:
        async with websockets.connect(url, open_timeout=timeout) as ws:
            await ws.send(json.dumps(payload))
            response_raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            return json.loads(response_raw)
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return None


async def interactive_session(url: str, timeout: float) -> None:
    """Sessao interativa: user digita, bot responde."""
    try:
        import websockets  # type: ignore[import-untyped]
    except ImportError:
        print("[ERROR] websockets nao instalado", file=sys.stderr)
        return

    session_id = f"cli-interactive-{datetime.now(timezone.utc).timestamp()}"
    try:
        async with websockets.connect(url, open_timeout=timeout) as ws:
            print(f"=== CartorioBot Chat (sessao {session_id}) ===", file=sys.stderr)
            print("Digite 'exit' para sair, 'reset' para nova sessao.\n", file=sys.stderr)
            while True:
                try:
                    user_input = input("voce> ")
                except EOFError:
                    print("\n[EOF]", file=sys.stderr)
                    break
                if user_input.lower() in ("exit", "quit"):
                    break
                if user_input.lower() == "reset":
                    session_id = f"cli-interactive-{datetime.now(timezone.utc).timestamp()}"
                    print(f"[nova sessao {session_id}]", file=sys.stderr)
                    continue
                if not user_input.strip():
                    continue
                payload = build_message(user_input, session_id)
                await ws.send(json.dumps(payload))
                response_raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                response = json.loads(response_raw)
                content = (
                    response.get("message", {}).get("content")
                    or response.get("content")
                    or response.get("response")
                    or str(response)
                )
                print(f"bot> {content}")
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="CartorioBot Chat CLI")
    parser.add_argument("--url", default=DEFAULT_URL, help="OpenClaw WebSocket URL")
    parser.add_argument("--message", help="enviar 1 mensagem e sair")
    parser.add_argument("--interactive", action="store_true", help="modo interativo (REPL)")
    parser.add_argument("--timeout", type=float, default=TIMEOUT, help="timeout em segundos")
    parser.add_argument("--dry-run", action="store_true", help="apenas mostra request sem enviar")
    args = parser.parse_args()

    if args.dry_run:
        print(json.dumps(build_message("(mensagem exemplo)"), indent=2, ensure_ascii=False))
        return 0

    if not args.message and not args.interactive:
        parser.error("especifique --message ou --interactive")

    if args.interactive:
        try:
            asyncio.run(interactive_session(args.url, args.timeout))
        except KeyboardInterrupt:
            print("\n[interrupted]", file=sys.stderr)
        return 0

    response = asyncio.run(send_one_message(args.url, args.message, args.timeout))
    if response is None:
        return 1
    content = (
        response.get("message", {}).get("content")
        or response.get("content")
        or response.get("response")
        or str(response)
    )
    print(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())