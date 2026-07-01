#!/usr/bin/env python3
"""Corrige o workflow 27 - Welcome First Time que retorna 500 por falta de respondToWebhook."""

import json
import sys
import time

import requests

BASE = "https://flow.2notasudi.com.br"


def login(email, pwd):
    s = requests.Session()
    r = s.post(
        BASE + "/rest/login",
        json={"emailOrLdapLoginId": email, "password": pwd},
        timeout=20,
    )
    if r.status_code != 200:
        sys.exit(f"Login falhou: {r.text[:200]}")
    return s


def main():
    s = login("admin@cartorio.local", "@Techno832466")
    time.sleep(2)
    wfs = s.get(f"{BASE}/rest/workflows?limit=50", timeout=30).json()["data"]
    target = None
    for w in wfs:
        if "Welcome First" in w.get("name", ""):
            target = w
            break
    if not target:
        print("Workflow 27 Welcome First não encontrado")
        return
    wid = target["id"]
    print(f"Encontrado: {target['name']} ({wid})")
    r = s.get(f"{BASE}/rest/workflows/{wid}", timeout=15)
    d = r.json()["data"]
    print(f"Nodes: {len(d.get('nodes', []))}")
    print(
        f"Has respondToWebhook: {any('Respond' in n.get('type', '') for n in d.get('nodes', []))}"
    )

    nodes = d["nodes"]
    # Adicionar node respondToWebhook se não existir
    if not any("Respond" in n.get("type", "") for n in nodes):
        # Criar novo nó
        x_max = max((n["position"][0] for n in nodes), default=400)
        y_max = max((n["position"][1] for n in nodes), default=200)
        respond_node = {
            "name": "Respond Webhook",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1,
            "position": [x_max + 200, y_max],
            "parameters": {
                "respondWith": "json",
                "responseBody": '={{ JSON.stringify({status: "lgpd_consent_iniciado", correlation_id: $("Extract Fields").first().json.correlation_id, cliente_id: $("Extract Fields").first().json.cliente_id, mensagem: "Termos LGPD enviados ao cliente via WhatsApp. Aguardando consentimento."}) }}',
            },
        }
        nodes.append(respond_node)
        # Conectar do último node ao respond
        # Encontrar um node terminal (sem sucessores)
        connections = d.get("connections", {})
        # Conectar o último nó principal
        last_main = None
        for n in nodes[:-1]:  # exclude respond node itself
            t = n.get("type", "")
            if (
                "webhook" in t.lower()
                or "httpRequest" in t
                or n.get("name") == nodes[-2].get("name")
            ):
                last_main = n.get("name")
        if not last_main:
            last_main = nodes[-2]["name"]
        connections.setdefault(last_main, {})
        connections[last_main].setdefault("main", [[]])
        connections[last_main]["main"][0].append(
            {"node": "Respond Webhook", "type": "main", "index": 0}
        )

        # update no DB
        body = {
            "name": d.get("name"),
            "nodes": nodes,
            "connections": connections,
            "settings": d.get("settings", {}),
            "staticData": d.get("staticData"),
        }
        time.sleep(2)
        r = s.patch(f"{BASE}/rest/workflows/{wid}", json=body, timeout=30)
        print(f"PATCH: {r.status_code} {r.text[:300]}")
        if r.ok:
            ver = r.json()["data"].get("versionId")
            time.sleep(2)
            r2 = s.post(
                f"{BASE}/rest/workflows/{wid}/activate",
                json={"versionId": ver},
                timeout=15,
            )
            print(f"ACTIVATE: {r2.status_code} {r2.text[:200]}")

    # Testar webhook
    time.sleep(2)
    r = s.post(
        f"{BASE}/webhook/welcome-first",
        json={"canal": "whatsapp", "cliente_id": "fix-test"},
        timeout=10,
    )
    print(f"\nWEBHOOK TEST: {r.status_code}")
    print(r.text[:400])


if __name__ == "__main__":
    main()
