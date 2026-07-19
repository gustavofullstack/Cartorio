"""dump_antigrav.py — Salva JSON dos 5 contatos ANTIGRAV."""
import json
import os

import httpx

TOKEN = os.environ["CHATWOOT_API_KEY"]
HDR = {"api_access_token": TOKEN}
BASE = "http://cartorio_chatwoot:3000"

r = httpx.get(f"{BASE}/api/v1/accounts/1/contacts?page=1", headers=HDR, timeout=10)
r.raise_for_status()
contacts = r.json().get("payload") or r.json().get("contacts") or []

resultados = []
for c in contacts:
    ca = c.get("custom_attributes") or {}
    if ca.get("pii_sintetico") and ca.get("agent_owner") == "ANTIGRAV":
        slot = int(ca.get("persona_id", "sim-XX").split("-")[1])
        resultados.append({
            "slot": slot,
            "agent": "ANTIGRAV",
            "nome": c.get("name"),
            "idade": ca.get("idade"),
            "cenario": ca.get("cenario"),
            "contact_id": c["id"],
            "cpf_mascarado": ca.get("cpf_mascarado", ""),
            "phone": c.get("phone_number"),
            "email": c.get("email"),
            "rg_mascarado": ca.get("rg_mascarado", ""),
        })

resultados.sort(key=lambda x: x["slot"])

out = "/tmp/chatwoot_sim_results_antigrav_5.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False)
print(f"SAVED {len(resultados)} personas -> {out}")
print(json.dumps(resultados, indent=2, ensure_ascii=False))
