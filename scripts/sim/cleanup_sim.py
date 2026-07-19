"""cleanup_sim.py — Limpa contatos + conversas duplicados da POC anterior."""
import json
import os

import httpx

TOKEN = os.environ["CHATWOOT_API_KEY"]
HDR = {"api_access_token": TOKEN}
BASE = "http://cartorio_chatwoot:3000"


def main() -> None:
    # 1. Listar conversas inbox 2
    r = httpx.get(
        f"{BASE}/api/v1/accounts/1/conversations?inbox_id=2&status=all",
        headers=HDR,
        timeout=10,
    )
    r.raise_for_status()
    payload = r.json().get("payload") or r.json().get("data", {}).get("payload") or []
    if not payload and isinstance(r.json(), list):
        payload = r.json()
    print(f"conversations_found={len(payload)}")
    for c in payload:
        cid = c.get("id")
        if cid:
            print(f"  resolve conv#{cid}")
            httpx.put(
                f"{BASE}/api/v1/accounts/1/conversations/{cid}",
                headers=HDR,
                json={"status": "resolved"},
                timeout=10,
            )

    # 2. Listar contatos (paginado simples)
    deleted = 0
    page = 1
    while True:
        r = httpx.get(
            f"{BASE}/api/v1/accounts/1/contacts?page={page}",
            headers=HDR,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        meta = data.get("meta") or {}
        contact_list = data.get("payload") or data.get("contacts") or []
        if isinstance(data, list):
            contact_list = data
        if not contact_list:
            break
        for c in contact_list:
            ca = c.get("custom_attributes") or {}
            if ca.get("pii_sintetico") is True:
                cid = c.get("id")
                if cid:
                    rd = httpx.delete(
                        f"{BASE}/api/v1/accounts/1/contacts/{cid}",
                        headers=HDR,
                        timeout=10,
                    )
                    deleted += 1
                    print(f"  delete contact#{cid} ({c.get('name')}) status={rd.status_code}")
        # Paginação
        if meta.get("total_pages") and page >= meta["total_pages"]:
            break
        if len(contact_list) < 25:
            break
        page += 1

    print(f"contacts_deleted={deleted}")


if __name__ == "__main__":
    main()
