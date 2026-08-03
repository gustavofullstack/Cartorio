"""list_all_convs.py — Lista TODAS conversas de TODOS inboxes, todos status."""

import json
import os

import httpx

TOKEN = os.environ["CHATWOOT_API_KEY"]
HDR = {"api_access_token": TOKEN}
BASE = "http://cartorio_chatwoot:3000"


def main() -> None:
    r = httpx.get(
        f"{BASE}/api/v1/accounts/1/conversations",
        headers=HDR,
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    payload = data.get("payload") or data.get("data", {}).get("payload") or []
    print(f"STATUS={r.status_code} payload_type={type(data).__name__}")
    if isinstance(data, dict):
        print(f"TOP KEYS: {list(data.keys())}")
    print(f"TOTAL: {len(payload)}")
    for c in payload[:30]:
        cid = c.get("id")
        status = c.get("status")
        inbox_id = c.get("inbox_id")
        msgs_count = c.get("messages_count") or c.get("unread_count")
        sender = c.get("sender") or {}
        sender_name = sender.get("name") if isinstance(sender, dict) else "?"
        print(
            f"  conv#{cid} inbox={inbox_id} status={status} msgs={msgs_count} sender={sender_name}"
        )


if __name__ == "__main__":
    main()
