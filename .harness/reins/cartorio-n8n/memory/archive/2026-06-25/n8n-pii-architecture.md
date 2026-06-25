---
description: Mapa de signal flow PII entre N8N, backend FastAPI e WebSocket orfao. Quem produz, quem consome, onde signal morre, drift de label. Carregar quando for auditar LGPD, debugar pii_blocked/handoff_reason, ou alinhar N8N com backend.
---

# N8N PII Architecture

## Signal flow: quem produz/consome pii_blocked hoje

**N8N WF #12** (`12-chatbot-llm-mcp.json`, ATIVO):
- Faz PII scrub INLINE em Code node JS (espelho de `backend/app/services/pii.py`)
- Decide Response gera shape `{pii_blocked, pii_redaction_count, needs_human_handoff, handoff_reason, model, tokens_in/out, latency_ms, provider, transport}`
- RespondToWebhook retorna ESSE shape para o caller (OpenClaw/Evolution)
- NAO chama backend `/api/v1/webhook/evolution`. LLM eh local via MCP tool

**N8N WF #03** (`03-handoff-human-chatwoot.json`, ATIVO):
- Recebe `{sender, message.text, reason, message_id, instance, canal}` no body
- `reason` vem no REQUEST, nao do response de #12. N8N NAO acopla #12 -> #03
- Cria conversation + message no Chatwoot (node oficial `n8n-nodes-chatwoot` v1.0.2)

**Backend `router.py:439` `webhook_evolution`**:
- Faz PII scrub, salva `conversas.handoff_to_human=True` + `handoff_reason='PII detectada'` no DB
- MAS return em `router.py:631` eh MENTIRA: `{status:ok, response, scrubbed}` — **perdeu** `pii_blocked/needs_human_handoff/handoff_reason`
- Esse endpoint NAO eh chamado pelo N8N. Chamado por Evolution API direto (caminho paralelo)

**T19 (WebSocket atendimentos)**:
- `backend/app/api/v1/ws/atendimentos.py` existe + RedisBus `cartorio:atendimentos`
- 0 publishers em runtime, 0 consumers N8N → **canal ORFAO** (construido mas nao usado)

## Regra LGPD: mapear signal flow completo

Quando audit LGPD apontar gap de signal, SEMPRE mapear:
1. Quem produz o signal (qual node/endpoint)
2. Quem consome (qual downstream)
3. Onde signal morre no caminho (linha exata)

N8N pode estar OK enquanto backend mente, ou vice-versa. Em cartorio: N8N OK, backend mente (router.py:631), T19 descoberto.

## Fix conhecido pendente

- `tests/test_webhook_evolution_e2e.py:170` (`test_payload_com_pii_bloqueia_e_marca_pii_blocked`) ja espera `pii_blocked` no response
- Fix do `router.py:631` (~10 linhas) recupera o contrato do test
- Gate: PR LGPD-015 merged + cartorio-lgpd review (mvs_d4fa1b1a)

## Drift de label PII: N8N vs backend

PII Scrubber JS do N8N diverge do backend em 1 label:
- Backend usa `'placa_veiculo'`
- N8N usa `'placa'`

**Backend eh a fonte de verdade**. Se for comparar findings, normalizar para `placa_veiculo`.