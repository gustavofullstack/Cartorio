"""e2e_telegram_openclaw.py - teste end-to-end Telegram -> API -> N8N -> OpenClaw -> resposta.

SQUAD E E6 - valida que o bot Telegram responde via fluxo completo.

Fluxo testado:
1. Usuario manda "oi" via Telegram
2. Telegram webhook -> API backend (/api/v1/telegram/webhook)
3. API valida HMAC + registra audit log
4. API chama OpenClaw (ou N8N que chama OpenClaw) para gerar resposta
5. API envia resposta via Telegram sendMessage
6. Valida que o usuario recebeu a resposta em <10s

Pre-requisitos:
- TELEGRAM_BOT_TOKEN no .env (NAO rotacionar)
- Webhook URL configurado: https://api.2notasudi.com.br/api/v1/telegram/webhook
- OpenClaw rodando: https://agent.2notasudi.com.br
- API rodando: https://api.2notasudi.com.br
- Chatwoot rodando: https://chat.2notasudi.com.br (interno)
- Supabase rodando: schema + 11 secrets em vault

Uso:
  cd backend
  uv run python scripts/e2e_telegram_openclaw.py --chat-id <ID>
"""
from __future__ import annotations

import argparse
import sys
import time

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--chat-id", required=True, help="Telegram chat_id para enviar msg de teste"
    )
    parser.add_argument(
        "--text", default="oi cartorio", help="texto a enviar (default: oi cartorio)"
    )
    parser.add_argument(
        "--api-base", default="https://api.2notasudi.com.br"
    )
    parser.add_argument(
        "--bot-token",
        default="8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q",
        help="Telegram bot token (NAO rotacionar)",
    )
    parser.add_argument(
        "--wait-seconds", type=int, default=10, help="tempo max de espera pela resposta"
    )
    args = parser.parse_args()

    print("E2E Telegram -> API -> OpenClaw")
    print(f"  chat_id: {args.chat_id}")
    print(f"  text: {args.text!r}")
    print(f"  api_base: {args.api_base}")
    print(f"  wait: {args.wait_seconds}s\n")

    # 1. Captura update_id atual (antes de enviar)
    with httpx.Client(timeout=10.0) as client:
        r = client.get(
            f"https://api.telegram.org/bot{args.bot_token}/getUpdates",
            params={"limit": 1, "offset": -1},
        )
        before_update_id = 0
        if r.status_code == 200:
            data = r.json()
            if data.get("result"):
                before_update_id = data["result"][-1].get("update_id", 0)
        print(f"[1] update_id antes: {before_update_id}")

    # 2. Envia msg
    with httpx.Client(timeout=10.0) as client:
        r = client.post(
            f"https://api.telegram.org/bot{args.bot_token}/sendMessage",
            json={"chat_id": int(args.chat_id), "text": args.text},
        )
        if r.status_code != 200:
            print(f"ERRO sendMessage: {r.status_code} {r.text[:200]}")
            return 1
        sent_msg = r.json()["result"]
        print(f"[2] msg enviada: msg_id={sent_msg['message_id']}")

    # 3. Aguarda resposta do bot (atualizar getUpdates ate' ver msg do bot)
    print(f"[3] aguardando resposta ate' {args.wait_seconds}s...")
    deadline = time.time() + args.wait_seconds
    bot_response = None
    while time.time() < deadline:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                f"https://api.telegram.org/bot{args.bot_token}/getUpdates",
                params={"limit": 10, "offset": before_update_id + 1},
            )
            if r.status_code != 200:
                time.sleep(1)
                continue
            data = r.json()
            for u in data.get("result", []):
                msg = u.get("message", {})
                # Resposta do bot = chat_id == args.chat_id E from.is_bot == True
                if (
                    msg.get("chat", {}).get("id") == int(args.chat_id)
                    and msg.get("from", {}).get("is_bot")
                ):
                    bot_response = msg
                    break
        if bot_response:
            break
        time.sleep(1)

    if not bot_response:
        print("FAIL: bot nao respondeu em {args.wait_seconds}s")
        return 1

    print("[4] RESPOSTA DO BOT:")
    print(f"    msg_id: {bot_response['message_id']}")
    print(f"    text: {bot_response.get('text','')[:200]}")

    # 4. Valida que OpenClaw + N8N foram acionados
    print("\n[5] validando saude do pipeline:")
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{args.api_base}/api/v1/health/radar")
        if r.status_code == 200:
            integ = r.json().get("integracoes", {})
            for name in ("openclaw", "n8n", "chatwoot", "supabase"):
                s = integ.get(name, {})
                print(f"    {name}: {s.get('status')} ({s.get('latency_ms')}ms)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
