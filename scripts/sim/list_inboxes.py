"""list_inboxes.py — Lista inboxes (helper)."""

import os

import httpx

TOKEN = os.environ["CHATWOOT_API_KEY"]
HDR = {"api_access_token": TOKEN}
BASE = "http://cartorio_chatwoot:3000"

r = httpx.get(f"{BASE}/api/v1/accounts/1/inboxes", headers=HDR, timeout=10)
print(f"STATUS={r.status_code}")
for ib in r.json().get("payload", []):
    print(f"  inbox#{ib['id']} name={ib['name']} type={ib['channel_type']}")

# Deletar duplicados whatsapp-sim (mantém o primeiro)
keep_id = None
for ib in r.json().get("payload", []):
    if ib["name"] == "whatsapp-sim":
        if keep_id is None:
            keep_id = ib["id"]
            print(f"KEEP inbox#{keep_id}")
        else:
            print(f"DELETE inbox#{ib['id']}")
            rd = httpx.delete(
                f"{BASE}/api/v1/accounts/1/inboxes/{ib['id']}",
                headers=HDR,
                timeout=10,
            )
            print(f"  DELETE status={rd.status_code}")
