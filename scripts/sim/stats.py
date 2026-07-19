"""stats.py — Estatísticas pós-simulação."""
import httpx
import os

TOKEN = os.environ["CHATWOOT_API_KEY"]
HDR = {"api_access_token": TOKEN}
BASE = "http://cartorio_chatwoot:3000"


def main() -> None:
    # Inboxes
    r = httpx.get(f"{BASE}/api/v1/accounts/1/inboxes", headers=HDR, timeout=10)
    print(f"INBOXES total: {len(r.json()['payload'])}")
    for ib in r.json()["payload"]:
        print(f"  #{ib['id']:3d} {ib['name']:20s} {ib['channel_type']}")

    # Contatos sintéticos (paginação completa)
    sint_total = 0
    sint_by_agent: dict[str, list[dict]] = {}
    page = 1
    while True:
        r = httpx.get(f"{BASE}/api/v1/accounts/1/contacts?page={page}", headers=HDR, timeout=10)
        r.raise_for_status()
        data = r.json()
        contacts = data.get("payload") or data.get("contacts") or []
        if not contacts:
            break
        for c in contacts:
            ca = c.get("custom_attributes") or {}
            if ca.get("pii_sintetico") is True:
                sint_total += 1
                agent = ca.get("agent_owner", "?")
                sint_by_agent.setdefault(agent, []).append(c)
        if data.get("meta", {}).get("total_pages") and page >= data["meta"]["total_pages"]:
            break
        if len(contacts) < 25:
            break
        page += 1

    print(f"\nCONTACTS sinteticos total: {sint_total}")
    for agent in sorted(sint_by_agent):
        cs = sint_by_agent[agent]
        print(f"  agent={agent} count={len(cs)}")
        for c in cs:
            ca = c.get("custom_attributes") or {}
            print(
                f"    #{c['id']:3d} slot={ca.get('persona_id')} {c['name']:30s} "
                f"{ca.get('idade')} anos cenario={ca.get('cenario')}"
            )

    # Conversas inbox 2 (status=open + status=resolved + status=pending)
    all_convs = []
    for status in ("open", "resolved", "pending"):
        r = httpx.get(
            f"{BASE}/api/v1/accounts/1/conversations?inbox_id=2&status={status}",
            headers=HDR,
            timeout=10,
        )
        data = r.json()
        payload = data.get("data", {}).get("payload") if isinstance(data, dict) else None
        if payload is None:
            payload = data.get("payload") or []
        all_convs.extend(payload)
    print(f"\nCONVERSATIONS inbox=2 total (open+resolved+pending): {len(all_convs)}")
    for c in all_convs:
        cid = c.get("id")
        msgs = httpx.get(
            f"{BASE}/api/v1/accounts/1/conversations/{cid}/messages",
            headers=HDR,
            timeout=10,
        ).json().get("payload", [])
        incoming = sum(1 for m in msgs if m.get("message_type") == 0)
        outgoing = sum(1 for m in msgs if m.get("message_type") == 1)
        contact_id = c.get("contact_id") or c.get("sender", {}).get("id")
        print(f"  conv#{cid:3d} contact={contact_id} status={c['status']:8s} incoming={incoming} outgoing={outgoing} total={len(msgs)}")


if __name__ == "__main__":
    main()
