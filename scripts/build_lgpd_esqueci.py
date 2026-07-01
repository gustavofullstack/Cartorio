#!/usr/bin/env python3
"""Cria o workflow 23 - LGPD Esqueci com respondToWebhook (fix P0)."""

import json
from pathlib import Path

WF = {
    "name": "23 - LGPD Esqueci (DELETE cliente + cascade + audit)",
    "nodes": [
        {
            "name": "LGPD Esqueci Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1,
            "position": [200, 200],
            "parameters": {
                "httpMethod": "POST",
                "path": "lgpd-esqueci",
                "responseMode": "responseNode",
                "responseData": "allEntries",
            },
        },
        {
            "name": "Extract Cliente ID",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [420, 200],
            "parameters": {
                "assignments": {
                    "assignments": [
                        {
                            "id": "a1",
                            "name": "cliente_id",
                            "value": "={{ $json.body.cliente_id || '' }}",
                            "type": "string",
                        },
                        {
                            "id": "a2",
                            "name": "request_id",
                            "value": "={{ $json.headers['x-correlation-id'] || ('req-' + $now.toMillis()) }}",
                            "type": "string",
                        },
                    ]
                }
            },
        },
        {
            "name": "GET Cliente Historico",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [640, 200],
            "parameters": {
                "method": "GET",
                "url": "=https://api.2notasudi.com.br/api/v1/cliente/{{ $json.cliente_id }}/historico",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "X-API-Key", "value": "={{ $env.CARTORIO_API_KEY }}"},
                        {
                            "name": "X-Correlation-Id",
                            "value": "={{ $json.request_id }}",
                        },
                        {"name": "Content-Type", "value": "application/json"},
                    ]
                },
                "options": {"timeout": 15000, "retry": {"maxTries": 3}},
            },
        },
        {
            "name": "Pode Deletar?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [860, 200],
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "typeValidation": "strict"},
                    "conditions": [
                        {
                            "id": "c1",
                            "leftValue": "={{ $json.consent_granted }}",
                            "rightValue": "true",
                            "operator": {"type": "string", "operation": "equals"},
                        }
                    ],
                }
            },
        },
        {
            "name": "POST Soft Delete",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1080, 100],
            "parameters": {
                "method": "POST",
                "url": "=https://api.2notasudi.com.br/api/v1/cliente/{{ $('Extract Cliente ID').item.json.cliente_id }}/soft-delete",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "X-API-Key", "value": "={{ $env.CARTORIO_API_KEY }}"},
                        {
                            "name": "X-Correlation-Id",
                            "value": "={{ $('Extract Cliente ID').item.json.request_id }}",
                        },
                        {"name": "Content-Type", "value": "application/json"},
                    ]
                },
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {
                            "name": "motivo",
                            "value": "LGPD art. 18 VI - direito ao esquecimento",
                        },
                        {"name": "solicitante", "value": "cliente"},
                    ]
                },
                "options": {"timeout": 30000, "retry": {"maxTries": 3}},
            },
        },
        {
            "name": "POST Audit LGPD",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1300, 100],
            "parameters": {
                "method": "POST",
                "url": "https://api.2notasudi.com.br/api/v1/audit/log",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "X-API-Key", "value": "={{ $env.CARTORIO_API_KEY }}"},
                        {
                            "name": "X-Correlation-Id",
                            "value": "={{ $('Extract Cliente ID').item.json.request_id }}",
                        },
                        {"name": "Content-Type", "value": "application/json"},
                    ]
                },
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {"name": "action", "value": "lgpd.esquecimento"},
                        {"name": "actor", "value": "sistema"},
                        {
                            "name": "target_id",
                            "value": "={{ $('Extract Cliente ID').item.json.cliente_id }}",
                        },
                        {"name": "base_legal", "value": "LGPD art. 18, VI"},
                    ]
                },
                "options": {"timeout": 15000, "retry": {"maxTries": 3}},
            },
        },
        {
            "name": "Respond OK",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1,
            "position": [1520, 100],
            "parameters": {
                "respondWith": "json",
                "responseBody": '={{ JSON.stringify({status: "ok", action: "lgpd.esquecimento.executado", cliente_id: $("Extract Cliente ID").item.json.cliente_id, correlation: $("Extract Cliente ID").item.json.request_id}) }}',
            },
        },
        {
            "name": "Cliente nao encontrado",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1,
            "position": [1080, 360],
            "parameters": {
                "respondWith": "json",
                "responseBody": '={{ JSON.stringify({status: "not_found", mensagem: "Cliente nao encontrado ou sem consentimento. LGPD esquecimento NAO executado.", correlation: $("Extract Cliente ID").item.json.request_id}) }}',
                "options": {"responseCode": 404},
            },
        },
    ],
    "connections": {
        "LGPD Esqueci Webhook": {
            "main": [[{"node": "Extract Cliente ID", "type": "main", "index": 0}]]
        },
        "Extract Cliente ID": {
            "main": [[{"node": "GET Cliente Historico", "type": "main", "index": 0}]]
        },
        "GET Cliente Historico": {
            "main": [[{"node": "Pode Deletar?", "type": "main", "index": 0}]]
        },
        "Pode Deletar?": {
            "main": [
                [{"node": "POST Soft Delete", "type": "main", "index": 0}],
                [{"node": "Cliente nao encontrado", "type": "main", "index": 0}],
            ]
        },
        "POST Soft Delete": {
            "main": [[{"node": "POST Audit LGPD", "type": "main", "index": 0}]]
        },
        "POST Audit LGPD": {
            "main": [[{"node": "Respond OK", "type": "main", "index": 0}]]
        },
    },
    "settings": {
        "executionOrder": "v1",
        "saveExecutionProgress": True,
        "saveDataSuccessExecution": "all",
        "saveDataErrorExecution": "all",
    },
}

out = Path(
    "/Users/gustavoalmeida/projetos/Cartorio/infra/n8n-workflows/23-lgpd-esqueci-v2.json"
)
out.write_text(json.dumps(WF, indent=2, ensure_ascii=False))
print(f"Wrote {out} ({out.stat().st_size} bytes)")

import requests

s = requests.Session()
r = s.post(
    "https://flow.2notasudi.com.br/rest/login",
    json={
        "emailOrLdapLoginId": "gustavomar.fullstack@gmail.com",
        "password": "@Techno832466",
    },
    timeout=20,
)
print("Login:", r.status_code)

r = s.post("https://flow.2notasudi.com.br/rest/workflows", json=WF, timeout=30)
print("Create:", r.status_code, r.text[:300])
if r.ok:
    data = r.json().get("data", {})
    wid = data.get("id")
    ver = data.get("versionId")
    print(f"ID={wid} v={ver[:8]}")
    r = s.post(
        f"https://flow.2notasudi.com.br/rest/workflows/{wid}/activate",
        json={"versionId": ver},
        timeout=15,
    )
    print("Activate:", r.status_code, r.text[:200])
    # testar webhook
    r3 = s.post(
        "https://flow.2notasudi.com.br/webhook/lgpd-esqueci", json={}, timeout=10
    )
    print(f"Webhook test: HTTP {r3.status_code}")
    print(r3.text[:400])
