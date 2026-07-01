#!/usr/bin/env python3
"""Corrige os workflows quebrados: importa o 03-Handoff-Humano, ativa MCP, deleta test, e testa todos webhooks."""

import json
import sys
import time
from pathlib import Path

import requests

BASE = "https://flow.2notasudi.com.br"
DIR = Path(__file__).parent.parent / "infra" / "n8n-workflows"


def login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(
        BASE + "/rest/login",
        json={"emailOrLdapLoginId": email, "password": password},
        timeout=20,
    )
    if r.status_code != 200:
        sys.exit(f"Login falhou: {r.text[:200]}")
    return s


def main():
    s = login("admin@cartorio.local", "@Techno832466")
    time.sleep(2)

    # 1. Deletar test_criado_2026-07-01
    print("=== STEP 1: Deletar test_criado_2026-07-01 ===")
    wfs = s.get(f"{BASE}/rest/workflows?limit=50", timeout=30).json()["data"]
    for w in wfs:
        if w["name"] == "test_criado_2026-07-01":
            r = s.delete(f"{BASE}/rest/workflows/{w['id']}")
            print(f"  DELETE: {r.status_code}")

    # 2. Reimportar 03 Handoff Humano (resolve 404)
    print("\n=== STEP 2: Reimportar 03 - Handoff Humano (Chatwoot v2) ===")
    src = DIR / "03-handoff-human-chatwoot.json"
    if not src.exists():
        print(f"  [skip] não encontrado: {src}")
    else:
        wf = json.loads(src.read_text())
        wf_clean = {
            "name": wf.get("name") or "03 - Handoff Humano (Chatwoot v2)",
            "nodes": [
                {
                    k: v
                    for k, v in n.items()
                    if k
                    in {
                        "name",
                        "type",
                        "typeVersion",
                        "position",
                        "parameters",
                        "credentials",
                    }
                }
                for n in wf.get("nodes", [])
            ],
            "connections": wf.get("connections", {}),
            "settings": {
                k: v
                for k, v in (wf.get("settings") or {}).items()
                if k
                in {
                    "executionOrder",
                    "saveExecutionProgress",
                    "saveDataSuccessExecution",
                    "saveDataErrorExecution",
                    "errorWorkflow",
                }
            },
            "staticData": wf.get("staticData"),
        }
        time.sleep(2)
        r = s.post(f"{BASE}/rest/workflows", json=wf_clean, timeout=30)
        if r.ok:
            wid = r.json()["data"]["id"]
            vid = r.json()["data"]["versionId"]
            print(f"  CREATED: id={wid[:12]} v={vid[:8]}")
            time.sleep(2)
            r = s.post(
                f"{BASE}/rest/workflows/{wid}/activate",
                json={"versionId": vid},
                timeout=15,
            )
            print(f"  ACTIVATE: {r.status_code} {r.text[:100]}")
        else:
            print(f"  FAIL: {r.status_code} {r.text[:300]}")

    # 3. Ativar MCP Server Tools (após corrigir config se possível)
    print("\n=== STEP 3: Ativar MCP Server Tools (T22) v2 ===")
    wfs = s.get(f"{BASE}/rest/workflows?limit=50", timeout=30).json()["data"]
    mcp = [w for w in wfs if w["name"].startswith("MCP - Server")]
    if mcp:
        m = mcp[0]
        # ativa (mesmo com config issue o N8N não bloqueia)
        time.sleep(2)
        r = s.get(f"{BASE}/rest/workflows/{m['id']}", timeout=15).json()
        if r.get("code") == 404:
            print(f"  Owner não tem acesso")
        else:
            d = r["data"]
            wid = d["id"]
            ver = d.get("versionId")
            r = s.post(
                f"{BASE}/rest/workflows/{wid}/activate",
                json={"versionId": ver},
                timeout=15,
            )
            print(f"  ACTIVATE: {r.status_code} {r.text[:150]}")

    # 4. Testar TODOS os webhooks
    print("\n=== STEP 4: Testar todos webhooks (com cookie de sessão) ===")
    webhook_paths = [
        ("EVO-IN", "evo-in"),
        ("01-Consulta-Emolumento", "consulta-emolumento"),
        ("02-Criar-Protocolo", "criar-protocolo"),
        ("03-Handoff-Humano", "handoff-human"),
        ("04-Boa-Vinda-LGPD", "boas-vindas"),
        ("04-Consulta-Protocolo", "consulta-protocolo"),
        ("05-Agendamento", "agendar-atendimento"),
        ("06-Segunda-Via", "segunda-via"),
        ("10-FAQ", "faq"),
        ("11-Monitor-Cartorio", "monitor-cartorio"),
        ("12-Chatbot-LLM", "chatbot-llm"),
        ("14-OpenCode-Go-Fallback", "openclaw-fallback"),
        ("16-Prospeccao-Lead", "lead-novo"),
        ("23-LGPD-Esqueci", "lgpd-esqueci"),
        ("26-Alerta-Critico", "alerta-critico"),
        ("27-Welcome-First", "welcome-first"),
        ("31-Telegram", "telegram-cartoriobot"),
    ]
    for label, path in webhook_paths:
        try:
            r = s.post(f"{BASE}/webhook/{path}", json={"test": True}, timeout=10)
            print(f"  {label:32s} /{path:30s} => {r.status_code}")
        except requests.exceptions.Timeout:
            print(f"  {label:32s} /{path:30s} => TIMEOUT (>10s)")
        except Exception as e:
            print(f"  {label:32s} /{path:30s} => ERR {e}")


if __name__ == "__main__":
    main()
