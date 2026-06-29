# SESSION_SUMMARY — 2026-06-29 (Cartório Sprint 3 — N8N nodes oficiais)

## TL;DR
- **Task A (WF #12 mcpClient)**: ✅ DONE — WF já estava migrada, smoke test PASS (executions #24294/#24295/#24296, latency 1.57s cold + 0.10s warm)
- **Task B (WF #03 Chatwoot)**: ⚠️ BLOCKED em 2 gates hard-fail
- **Bugs reais identificados** (além do briefing): URL canon `chatwoot.2notasudi.com.br` é NXDOMAIN + env `CHATWOOT_BOT_TOKEN` faltando no container N8N

## Gate 1 — Task A (WF #12 mcpClient) ✅ DONE

### Estado real verificado
- WF #12 prod (UUID `bryQNXccPvOgNhIL`) **já usa `n8n-nodes-mcp.mcpClient`** — briefing tinha premissa stale (Task A era "migrate" mas já estava migrado)
- 6 nodes: webhook → set (extract) → code (PII scrub) → mcpClient (cartorio_chatbot_responder) → code (decide) → respondToWebhook
- Tool name: `cartorio_chatbot_responder`, MCP server: `cartorio-mcp-server`

### Smoke test (3 execuções)
- Cold start: 1.57s
- Warm cache (idempotência): 0.10-0.11s
- **Todas com HTTP 200, mode=webhook, no error at WF level**
- Status retornado pelo bot: `llm_error` (deepseek-v4-flash indisponível → graceful fallback + `needs_human_handoff=true`) — **fora do escopo da Task A**

## Gate 2 — Task B (WF #03 Chatwoot) ⚠️ BLOCKED em 2 SUB-GATES

### SUB-GATE B1 — Lesson 50 confirmed
- Custom node `@devlikeapro/n8n-nodes-chatwoot.Chatwoot` (e `chatWoot`) rejeita `POST /api/v1/workflows/{id}/activate` com:
  > `{"message":"Unrecognized node type: @devlikeapro/n8n-nodes-chatwoot.Chatwoot"}`
- Testei 3 formatações de type name (`@devlikeapro/...Chatwoot`, `@devlikeapro/...chatWoot`, `n8n-nodes-chatwoot.chatWoot`) — todas rejeitadas
- **Workaround documentado**: DB UPDATE direto em `workflow_entity.nodes/connections/activeVersionId` + restart Swarm (Lesson 49+50)
- **Não apliquei** porque (a) risco de tocar prod N8N, (b) pietra pediu gates pré-activate; DB UPDATE seria "force activate" sem gates

### SUB-GATE B2 — Chatwoot API endpoint unreachable (404/500)
- `POST https://chat.2notasudi.com.br/api/v1/accounts/1/conversations` retorna **404** com body `{"error":"Resource could not be found"}`
- Testei via Swarm DNS interno (`cartorio_chatwoot:3000`) — mesmo 404
- Token funciona em OUTROS endpoints: `POST /contacts` → 200 (criou contato id=2), `GET /agents` → 200, `GET /inboxes` → 200
- Inbox id=1 é **Channel::Telegram** (não Website/WhatsApp) — pode ser a causa
- POST /conversations com `contact_id` (sem `source_id`) → 500 internal server error → rota existe parcialmente mas lógica broken
- **Não tenho visibilidade da config do chatwoot** (admin tasks fora do meu escopo)

## Ações executadas (mesmo com BLOCKED)

| Ação | Status | ID/Path |
|------|--------|---------|
| Backup WF #12 prod | ✅ | `infra/n8n-workflows/backups/WF12_pre_mcp_2026-06-29.json` (15637 bytes) |
| Backup WF #03 prod | ✅ | `infra/n8n-workflows/backups/WF03_pre_chatwoot_2026-06-29.json` (11260 bytes) |
| Auditoria credencial `chatwoot-api` (qGyW9nc36pWXo7ow) | ✅ | tipo `httpHeaderAuth` (travava o node oficial) |
| Criei nova credencial `chatwoot-api` (D9HNG2CI3DD6T0CK) tipo `chatwootApi` | ✅ | mesmo token (re-tipado, NÃO rotacionado) |
| Staging JSON spec com node oficial | ✅ | `infra/n8n-workflows/03-handoff-human-chatwoot-v3-staging.json` |
| Staging clone POST INATIVO em N8N | ✅ | `kZmO4g7wIw6OVwzP` (último) |
| Validate credencial via curl direto | ✅ | HTTP 200 / 401 conforme esperado |
| Validate Chatwoot API contract (POST /contacts etc) | ✅ | HTTP 200 para contacts/agents/inboxes |
| Validate Chatwoot API contract (POST /conversations) | ❌ | 404 (gate B2) |
| Activate staging clone | ❌ | Lesson 50 (gate B1) |

## Rollback / cleanup

```bash
# Reverter staging clone (kZmO4g7wIw6OVwzP — INATIVO, seguro deletar)
curl -X DELETE -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows/kZmO4g7wIw6OVwzP"

# WF #03 prod original (00PbDJUpJlrUxAir) intacto e ativo — não deletar
# WF #12 prod original (bryQNXccPvOgNhIL) intacto e ativo — não deletar
# Credencial nova D9HNG2CI3DD6T0CK é independente (não usada por prod) — pode deletar via UI ou API:
# curl -X DELETE -H "X-N8N-API-KEY: $N8N_API_KEY" \
#   "https://flow.2notasudi.com.br/api/v1/credentials/D9HNG2CI3DD6T0CK"
```

## Lição nova (Lesson 187 candidate)

- `@devlikeapro/n8n-nodes-chatwoot` (v1.0.2) deploya OK mas `POST /workflows/{id}/activate` rejeita — **Lesson 50 confirma que custom nodes não aceitam activate**. Para esses nodes, **activation SEMPRE precisa do workaround DB UPDATE** (Lesson 49+50). Aplica também a `n8n-nodes-evolution-api`.

Modified by Gustavo Almeida
