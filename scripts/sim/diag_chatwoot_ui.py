"""diag_chatwoot_ui.py — Diagnostica por que conversas não aparecem na UI.

Compara:
1. Account 1 (onde criei inbox) vs Account 2 (onde Gustavo está logado)
2. Inboxes visíveis em cada account
3. Conversas inbox=2 por status (open/resolved/pending)
4. Usuários no Account 1 e seus access_tokens
"""
import httpx
import os

TOKEN = os.environ["CHATWOOT_API_KEY"]
HDR = {"api_access_token": TOKEN}
BASE = "http://cartorio_chatwoot:3000"


def list_accounts() -> None:
    print("=== ACCOUNTS ===")
    for acct_id in (1, 2):
        try:
            r = httpx.get(f"{BASE}/api/v1/accounts/{acct_id}", headers=HDR, timeout=10)
            print(f"account#{acct_id}: {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"account#{acct_id}: ERR {e}")


def list_inboxes(account_id: int) -> list[dict]:
    r = httpx.get(f"{BASE}/api/v1/accounts/{account_id}/inboxes", headers=HDR, timeout=10)
    return r.json().get("payload", []) if r.status_code == 200 else []


def list_conv_count(account_id: int, inbox_id: int, status: str) -> int:
    r = httpx.get(
        f"{BASE}/api/v1/accounts/{account_id}/conversations?inbox_id={inbox_id}&status={status}",
        headers=HDR,
        timeout=10,
    )
    if r.status_code != 200:
        return -1
    data = r.json()
    payload = data.get("data", {}).get("payload") if isinstance(data, dict) else None
    if payload is None:
        payload = data.get("payload") or []
    return len(payload)


def list_users(account_id: int) -> list[dict]:
    r = httpx.get(f"{BASE}/api/v1/accounts/{account_id}/agents", headers=HDR, timeout=10)
    if r.status_code != 200:
        return []
    return r.json()


def main() -> None:
    list_accounts()

    for acct in (1, 2):
        print(f"\n=== ACCOUNT {acct} ===")
        inboxes = list_inboxes(acct)
        print(f"inboxes: {len(inboxes)}")
        for ib in inboxes:
            ib_id = ib["id"]
            counts = {s: list_conv_count(acct, ib_id, s) for s in ("open", "resolved", "pending", "all")}
            print(f"  inbox#{ib_id} {ib['name']:20s} open={counts['open']} resolved={counts['resolved']} pending={counts['pending']}")

        agents = list_users(acct)
        print(f"agents: {len(agents)}")
        for a in (agents if isinstance(agents, list) else agents.get("payload", [])):
            print(f"  agent#{a.get('id')} {a.get('name')} email={a.get('email')} role={a.get('role')}")

    # Quero entender o contexto geral
    print("\n=== ADMIN: TODOS USERS (account-wide) ===")
    r = httpx.get(f"{BASE}/api/v1/users", headers=HDR, timeout=10)
    if r.status_code == 200:
        for u in r.json():
            print(f"  user#{u.get('id')} email={u.get('email')} type={u.get('type', 'User')}")

    print("\n=== ACCESS TOKENS ===")
    # Vou tentar via rails runner no container (mais confiável)
    print("(rodar rails runner no container para listar tokens)")


if __name__ == "__main__":
    main()
