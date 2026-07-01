#!/usr/bin/env python3
"""Recria o workflow 03 - Handoff Humano (Chatwoot v2) — estava deletado."""

import json
import sys
import time
from pathlib import Path

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


WF = {
    "name": "03 - Handoff Humano (Chatwoot v2)",
    "nodes": [
        {
            "name": "Handoff Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1,
            "position": [200, 200],
            "parameters": {
                "httpMethod": "POST",
                "path": "handoff-human",
                "responseMode": "responseNode",
                "responseData": "allEntries",
            },
        },
        {
            "name": "Init Correlation",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [420, 200],
            "parameters": {
                "assignments": {
                    "assignments": [
                        {
                            "id": "a1",
                            "name": "correlation_id",
                            "value": "={{ $json.headers['x-correlation-id'] || ('cor-' + $now.toMillis()) }}",
                            "type": "string",
                        },
                        {
                            "id": "a2",
                            "name": "canal",
                            "value": "={{ $json.body.canal || 'whatsapp' }}",
                            "type": "string",
                        },
                        {
                            "id": "a3",
                            "name": "cliente_id",
                            "value": "={{ $json.body.cliente_id || '' }}",
                            "type": "string",
                        },
                        {
                            "id": "a4",
                            "name": "mensagem",
                            "value": "={{ $json.body.mensagem || $json.body.message || '' }}",
                            "type": "string",
                        },
                        {
                            "id": "a5",
                            "name": "motivo_handoff",
                            "value": "={{ $json.body.motivo || 'solicitacao_cliente' }}",
                            "type": "string",
                        },
                    ]
                }
            },
        },
        {
            "name": "Resolve Cliente Info",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [640, 200],
            "parameters": {
                "method": "GET",
                "url": "=https://api.2notasudi.com.br/api/v1/cliente/by-phone/{{ $json.phone_e164 || $json.canal_id || 'unknown' }}",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "X-API-Key", "value": "={{ $env.CARTORIO_API_KEY }}"},
                        {
                            "name": "X-Correlation-Id",
                            "value": "={{ $json.correlation_id }}",
                        },
                    ]
                },
                "options": {"timeout": 10000, "retry": {"maxTries": 3}},
            },
        },
        {
            "name": "POST Chatwoot Handoff",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [860, 100],
            "parameters": {
                "method": "POST",
                "url": "https://chat.2notasudi.com.br/api/v1/accounts/1/conversations",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "api_access_token",
                            "value": "={{ $env.CHATWOOT_BOT_TOKEN }}",
                        },
                        {"name": "Content-Type", "value": "application/json"},
                        {
                            "name": "X-Correlation-Id",
                            "value": "={{ $json.correlation_id }}",
                        },
                    ]
                },
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {"name": "inbox_id", "value": "1"},
                        {
                            "name": "contact_id",
                            "value": "={{ $('Init Correlation').item.json.cliente_id }}",
                        },
                        {"name": "status", "value": "open"},
                        {"name": "assignee_id", "value": ""},
                        {
                            "name": "custom_attributes",
                            "value": "={{ JSON.stringify({motivo: $('Init Correlation').item.json.motivo_handoff, correlation_id: $('Init Correlation').item.json.correlation_id}) }}",
                        },
                    ]
                },
                "options": {"timeout": 15000, "retry": {"maxTries": 3}},
            },
        },
        {
            "name": "POST Mensagem Chatwoot",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1080, 100],
            "parameters": {
                "method": "POST",
                "url": "=https://chat.2notasudi.com.br/api/v1/accounts/1/conversations/{{ $('POST Chatwoot Handoff').item.json.id }}/messages",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "api_access_token",
                            "value": "={{ $env.CHATWOOT_BOT_TOKEN }}",
                        },
                        {"name": "Content-Type", "value": "application/json"},
                        {
                            "name": "X-Correlation-Id",
                            "value": "={{ $('Init Correlation').item.json.correlation_id }}",
                        },
                    ]
                },
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {
                            "name": "content",
                            "value": "={{ '[BOT→HUMANO] Cliente solicitou atendimento. Mensagem original: ' + $('Init Correlation').item.json.mensagem }}",
                        },
                        {"name": "message_type", "value": "outgoing"},
                        {"name": "private", "value": "false"},
                    ]
                },
                "options": {"timeout": 15000, "retry": {"maxTries": 3}},
            },
        },
        {
            "name": "POST Audit Handoff",
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
                            "value": "={{ $('Init Correlation').item.json.correlation_id }}",
                        },
                        {"name": "Content-Type", "value": "application/json"},
                    ]
                },
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {"name": "action", "value": "handoff.humano"},
                        {"name": "actor", "value": "sistema"},
                        {
                            "name": "target_id",
                            "value": "={{ $('Init Correlation').item.json.cliente_id }}",
                        },
                        {
                            "name": "metadata",
                            "value": "={{ JSON.stringify({chatwoot_conv_id: $('POST Chatwoot Handoff').item.json.id, motivo: $('Init Correlation').item.json.motivo_handoff}) }}",
                        },
                    ]
                },
                "options": {"timeout": 10000, "retry": {"maxTries": 3}},
            },
        },
        {
            "name": "Respond OK",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1,
            "position": [1520, 100],
            "parameters": {
                "respondWith": "json",
                "responseBody": '={{ JSON.stringify({status: "handoff_iniciado", chatwoot_conversation_id: $("POST Chatwoot Handoff").item.json.id, correlation_id: $("Init Correlation").item.json.correlation_id, mensagem_humano: true}) }}',
            },
        },
        {
            "name": "Respond Erro",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1,
            "position": [1080, 320],
            "parameters": {
                "respondWith": "json",
                "responseBody": '={{ JSON.stringify({status: "erro", mensagem: "Falha ao abrir conversa no Chatwoot. Tentaremos novamente.", correlation_id: $("Init Correlation").item.json.correlation_id}) }}',
                "options": {"responseCode": 502},
            },
        },
    ],
    "connections": {
        "Handoff Webhook": {
            "main": [[{"node": "Init Correlation", "type": "main", "index": 0}]]
        },
        "Init Correlation": {
            "main": [[{"node": "Resolve Cliente Info", "type": "main", "index": 0}]]
        },
        "Resolve Cliente Info": {
            "main": [[{"node": "POST Chatwoot Handoff", "type": "main", "index": 0}]]
        },
        "POST Chatwoot Handoff": {
            "main": [
                [{"node": "POST Mensagem Chatwoot", "type": "main", "index": 0}],
                [{"node": "Respond Erro", "type": "main", "index": 0}],
            ]
        },
        "POST Mensagem Chatwoot": {
            "main": [[{"node": "POST Audit Handoff", "type": "main", "index": 0}]]
        },
        "POST Audit Handoff": {
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


def main():
    s = login("admin@cartorio.local", "@Techno832466")
    time.sleep(2)
    r = s.post(BASE + "/rest/workflows", json=WF, timeout=30)
    print(f"CREATE: {r.status_code}")
    if not r.ok:
        print(r.text[:500])
        return
    data = r.json()["data"]
    wid = data["id"]
    ver = data["versionId"]
    print(f"  id={wid[:18]} versionId={ver[:8]}")
    time.sleep(2)
    r = s.post(
        f"{BASE}/rest/workflows/{wid}/activate", json={"versionId": ver}, timeout=15
    )
    print(f"ACTIVATE: {r.status_code} {r.text[:150]}")
    time.sleep(2)
    # testar
    r = s.post(
        f"{BASE}/webhook/handoff-human",
        json={
            "canal": "whatsapp",
            "cliente_id": "test-001",
            "mensagem": "Preciso de ajuda",
            "motivo": "test_recreate",
        },
        timeout=10,
    )
    print(f"WEBHOOK TEST: {r.status_code}")
    print(r.text[:300])
    # salvar json
    Path(
        "/Users/gustavoalmeida/projetos/Cartorio/infra/n8n-workflows/03-handoff-human-chatwoot.json"
    ).write_text(json.dumps(WF, indent=2))


if __name__ == "__main__":
    main()
