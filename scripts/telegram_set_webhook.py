#!/usr/bin/env python3
"""Telegram setWebhook helper (G7.03.T1).

Nunca imprime o token completo. Lê TELEGRAM_BOT_TOKEN e
TELEGRAM_WEBHOOK_SECRET do ambiente.

Uso:
  python3 scripts/telegram_set_webhook.py --dry-run
  python3 scripts/telegram_set_webhook.py --apply
  python3 scripts/telegram_set_webhook.py --info

Modified by Gustavo Almeida — G7 Wave 21.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_WEBHOOK_URL = "https://api.2notasudi.com.br/api/v1/telegram/webhook"
API = "https://api.telegram.org"


def _mask(token: str) -> str:
    if len(token) < 12:
        return "***"
    return token[:6] + "…" + token[-4:]


def _post(path: str, data: dict) -> dict:
    body = urlencode(data).encode()
    req = Request(path, data=body, method="POST")
    with urlopen(req, timeout=20) as resp:  # noqa: S310 — Telegram API only
        return json.loads(resp.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="chama setWebhook de verdade")
    parser.add_argument("--dry-run", action="store_true", help="só mostra plano (default)")
    parser.add_argument("--info", action="store_true", help="getWebhookInfo")
    parser.add_argument("--url", default=DEFAULT_WEBHOOK_URL)
    args = parser.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()

    if not token:
        print("[FAIL] TELEGRAM_BOT_TOKEN não setado", file=sys.stderr)
        return 2

    print(f"token: {_mask(token)}")
    print(f"webhook_url: {args.url}")
    print(f"secret_token: {'set' if secret else 'MISSING (backend dev-mode aceita vazio)'}")

    base = f"{API}/bot{token}"

    if args.info or (not args.apply and not args.dry_run):
        try:
            info = _post(f"{base}/getWebhookInfo", {})
            # strip sensitive
            res = info.get("result") or info
            safe = {
                k: res.get(k)
                for k in (
                    "url",
                    "has_custom_certificate",
                    "pending_update_count",
                    "last_error_date",
                    "last_error_message",
                    "max_connections",
                )
                if isinstance(res, dict)
            }
            print("getWebhookInfo:", json.dumps(safe, indent=2, ensure_ascii=False))
        except Exception as exc:
            print(f"[ERROR] getWebhookInfo: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        if not args.apply:
            return 0

    if args.dry_run or not args.apply:
        print("[DRY-RUN] setWebhook NÃO enviado. Use --apply para executar.")
        print(
            "params: allowed_updates=message,edited_message,callback_query,my_chat_member "
            "drop_pending_updates=true"
        )
        return 0

    payload = {
        "url": args.url,
        "allowed_updates": json.dumps(
            ["message", "edited_message", "callback_query", "my_chat_member"]
        ),
        "drop_pending_updates": "true",
    }
    if secret:
        payload["secret_token"] = secret

    try:
        out = _post(f"{base}/setWebhook", payload)
    except Exception as exc:
        print(f"[ERROR] setWebhook: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    ok = bool(out.get("ok"))
    print("setWebhook ok=", ok, "description=", out.get("description"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
