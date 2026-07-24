"""validate_poc.py — Valida estado da simulação após POC persona 1."""
import os

import httpx

TOKEN = os.environ["CHATWOOT_API_KEY"]
HDR = {"api_access_token": TOKEN}
BASE = os.environ.get("CHATWOOT_BASE_URL_INTERNAL", "http://cartorio_chatwoot:3000")


def main() -> None:
    print(f"BASE={BASE}")
    print(f"TOKEN_LEN={len(TOKEN)}")

    print("\n=== INBOXES ===")
    r = httpx.get(f"{BASE}/api/v1/accounts/1/inboxes", headers=HDR, timeout=10)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and "payload" in data:
        data = data["payload"]
    for ib in data:
        print(f"  inbox#{ib['id']} name={ib['name']} type={ib['channel_type']}")

    print("\n=== CONVERSATIONS inbox=2 status=open ===")
    r = httpx.get(
        f"{BASE}/api/v1/accounts/1/conversations?inbox_id=2&status=open",
        headers=HDR,
        timeout=10,
    )
    r.raise_for_status()
    payload = r.json()
    convs = payload.get("payload") or payload.get("data", {}).get("payload") or []
    if isinstance(payload, list):
        convs = payload
    if not convs:
        for k, v in payload.items():
            if isinstance(v, list):
                convs = v
                break
    for c in convs:
        cid = c.get("id")
        msgs = c.get("messages_count", "?")
        print(f"  conv#{cid} contact_id={c.get('contact_id')} status={c.get('status')} msgs={msgs}")

    if convs:
        cid = convs[0]["id"]
        print(f"\n=== MESSAGES conv={cid} ===")
        r = httpx.get(
            f"{BASE}/api/v1/accounts/1/conversations/{cid}/messages",
            headers=HDR,
            timeout=10,
        )
        r.raise_for_status()
        msgs = r.json().get("payload") or []
        for m in msgs:
            content = m.get("content", "")[:90]
            mt = m.get("message_type")
            if isinstance(mt, int):
                mt = {0: "incoming", 1: "outgoing", 2: "activity"}.get(mt, str(mt))
            print(f"  msg#{m['id']} type={mt:8s} {content}")

    print("\n=== CONTACT 1 ===")
    r = httpx.get(f"{BASE}/api/v1/accounts/1/contacts/1", headers=HDR, timeout=10)
    if r.status_code == 200:
        c = r.json().get("payload") or r.json()
        ca = c.get("custom_attributes") or {}
        print(f"  name={c.get('name')} phone={c.get('phone_number')} email={c.get('email')}")
        print(f"  idade={ca.get('idade')} cenario={ca.get('cenario')} cpf_masc={ca.get('cpf_mascarado')} pii_sint={ca.get('pii_sintetico')}")


if __name__ == "__main__":
    main()