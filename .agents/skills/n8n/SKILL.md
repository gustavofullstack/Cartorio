---
name: n8n
description: |
  Skill para interagir com N8N Workflow Engine via API REST e MCP.
  Use quando precisar: listar/executar/criar workflows, verificar execuções,
  gerenciar credenciais, triggers, webhooks, e MCP tools do N8N.
  URL: https://flow.2notasudi.com.br | 34 workflows ativos (snapshot 2026-06-30)
---

# N8N Workflow Engine — Skill de Integração (v2 / 2026-06-30)

> **Atualizado em 2026-06-30** após auditoria completa + arquivamento de 17 workflows legados.
> Ver `infra/n8n-workflows/N8N_DASHBOARD_2026-06-30.md` para estado canônico completo.

## Acesso

| Item | Valor |
|------|-------|
| **URL Base (produção)** | `https://flow.2notasudi.com.br` |
| **URL Backend Easypanel** | `https://cartorio-n8n.dfgdxq.easypanel.host` (DNS resolve OK, 443 timeout 2026-07-01 ⚠️) |
| **API Key** | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (em `backend/.env` → `N8N_API_KEY`) |
| **Header de Auth** | `X-N8N-API-KEY: <jwt>` |
| **MCP URL (CORRETA 2026-07-01)** | `https://cartorio-n8n.dfgdxq.easypanel.host/mcp-server/http` ⚠️ a URL `flow.2notasudi.com.br/mcp-server/http` está em skill antiga MAS RECUSA auth |
| **MCP API Key** | `backend/.env` → `MCP_API_KEY` (token dedicado, DIFERENTE da `N8N_API_KEY`) |
| **MCP Status (2026-07-01 ~22:30 UTC)** | 🔴 OFF-LINE — host easypanel timeout porta 443 (resolver Easypanel) |
| **Health Check** | `GET /healthz` → 200 OK (200 em 2026-07-01, recuperado Turno 16:05) |
| **Porta interna** | 5678 |

## Estado atual (snapshot 2026-07-01 ~02:00 UTC)

| Métrica | Valor |
|---------|-------|
| Total workflows no painel | **32** |
| Ativos | **30** |
| Inativos | 2 (1 test criado, 1 handoff v3 staging) |
| Cobertura `errorWorkflow` | 29/31 — só error handler tem `callerPolicy` |
| Cobertura `retry 3x exp backoff` | 100% HTTP nodes |
| **Status runtime** | 🟢 **200 OK**. Migração Supabase→Postgres completa + 30 workflows reimportados + 1 LGPD Esqueci recriado com `respondToWebhook`. |

## 🆕 Mudanças Turno 43 (2026-07-01 ~01:45 UTC)

- **Migração Supabase → Postgres**: N8N agora usa `cartorio_supabase:5432/db=supabase` (não mais SQLite nem Supabase Auth)
- **Auth N8N 2.x**: Tabela `auth_identity` separada do `user` (providerType='email')
- **API endpoints N8N 2.x**:
  - `POST /rest/workflows` (criar) — requer cookie `n8n-auth` válido OU API key com scope `workflow:create`
  - `PATCH /rest/workflows/:id` (atualizar — **não PUT!**)
  - `POST /rest/workflows/:id/activate` — **requer `{"versionId": "..."}` no body**
  - `POST /rest/api-keys` — scopes regex `^[a-z][a-zA-Z]+:[a-zA-Z]+$` (sem hífens, sem wildcards)
- **Login UI**: `POST /rest/login` com `{"emailOrLdapLoginId": ..., "password": ...}` → 200 + cookie `n8n-auth` 7 dias
- **Project pessoal**: N8N 2.x exige `project.type='personal'` para cada user antes de criar workflows. Pode-se criar via DB: `INSERT INTO project (id, name, type, "creatorId", ...)`

## Endpoints Principais

### Workflows
```bash
# Listar todos os workflows (100 limit default)
GET /api/v1/workflows?limit=100

# Obter um workflow específico
GET /api/v1/workflows/{id}

# Executar workflow por ID
POST /api/v1/workflows/{id}/execute

# Ativar workflow
POST /api/v1/workflows/{id}/activate

# Desativar workflow
POST /api/v1/workflows/{id}/deactivate

# Deletar workflow
DELETE /api/v1/workflows/{id}

# ⚠️ ATENÇÃO: N8N 2.x retorna 405 em PATCH /api/v1/workflows/{id}!
# Para edits, use POST (insert) ou DB UPDATE direto (Lesson 96, 50).
```

### Execuções
```bash
# Listar execuções (todas)
GET /api/v1/executions?limit=50&includeData=false

# Execuções de 1 workflow
GET /api/v1/executions?workflowId={id}&limit=20

# Execuções últimas 24h
GET /api/v1/executions?limit=100&startedAfter=$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ)
```

### Webhooks (públicos)
```bash
# EVO-IN — Evolution API → N8N (entrada principal WhatsApp)
POST https://flow.2notasudi.com.br/webhook/evo-in

# Endpoints que devem existir para cada workflow COM webhook trigger:
# /webhook/evo-in                       (EVO-IN) ✅
# /webhook/consulta-emolumento          (WF 01) ⚠️ timeout 8s
# /webhook/criar-protocolo              (WF 02) ✅
# /webhook/handoff-human                (WF 03) ✅
# /webhook/boas-vindas                  (WF 04) ✅
# /webhook/consulta-protocolo           (WF 04b) ✅
# /webhook/agendar-atendimento          (WF 05) ✅ — path real é agendar-atendimento (NÃO /agendamento!)
# /webhook/segunda-via                  (WF 06) ✅
# /webhook/faq                          (WF 10) ✅
# /webhook/chatbot-llm                  (WF 12) ⚠️ timeout 12s — MCP 401 quebra (Lesson 109)
# 
# WFs SEM webhook trigger público (chamados internamente):
# - WF 14 (OpenCode-Go Fallback) — chamado por WF 12 quando MCP falha
# - WF 31 (Telegram Listener) — polling Telegram API direto (sem webhook)
```

### MCP Tools via N8N (⚠️ URL CORRETA + MCP_API_KEY dedicada)
```bash
# Endpoint MCP Server (N8N acts as MCP Server):
POST https://cartorio-n8n.dfgdxq.easypanel.host/mcp-server/http
Headers:
  Authorization: Bearer <MCP_API_KEY>   # NÃO é a N8N_API_KEY — usar MCP_API_KEY de backend/.env
  Content-Type: application/json
  Accept: application/json, text/event-stream
Body (JSON-RPC 2.0):
Body (JSON-RPC 2.0):
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}

# Status atual (2026-06-30): retorna 401 Unauthorized com ambos headers
# → token pode ter expirado; revisar Sprint 4 T7
```

## Catálogo de 34 Workflows Ativos (snapshot remoto 2026-06-30 ~22:30 UTC)

### Categoria: Customer Journey (WhatsApp / Texto)

| # | Nome | ID | Trigger | Webhook path | OK? |
|---|------|------|---------|--------------|-----|
| 01 | Consulta Emolumento WhatsApp (v3) | `bR7qIo3bFpG4zgxO` | webhook + cron | `/consulta-emolumento` | ✅ |
| 02 | Criar Protocolo (LGPD) | `MzeYTSDouymzdpRw` | webhook | `/criar-protocolo` | ✅ |
| 03 | Handoff Humano (Chatwoot v2) | `00PbDJUpJlrUxAir` | webhook | `/handoff-human` | ✅ |
| 04 | Boas-Vindas + Consentimento LGPD | `sDtkfOJ5BA7M73wB` | webhook | `/boas-vindas` | ✅ |
| 04b | Consulta Protocolo | `iXWuZRYZLR3FYPYB` | webhook | `/consulta-protocolo` | ✅ |
| 05 | Agendamento Atendimento | `UUW8ulDTxZUqBsci` | webhook | `/agendamento` | ⚠️ 404 |
| 06 | Segunda Via Documento | `ukbRUEudoX3SvsqD` | webhook | `/segunda-via` | ✅ |
| 07 | Pesquisa Satisfação | `D9XJmlJRXZ3lavoa` | webhook | - | ✅ |
| 10 | FAQ Bot | `jZhgQbJQ5z7atYfK` | webhook | `/faq` | ✅ |
| 12 | Chatbot LLM E2E (PII + MCP) | `bryQNXccPvOgNhIL` | webhook | `/chatbot-llm` | ⚠️ TIMEOUT |
| 31 | Telegram Listener (CartorioBot test) | `x1N2xJ1WZ83dmxC6` | webhook | `/telegram` | ⚠️ 404 |
| EVO-IN | Evolution Webhook Inbound | `I4LkReuiurPBS9VN` | webhook | `/evo-in` | ✅ |

### Categoria: Cron Jobs (operations, monitoring)

| # | Nome | ID | Cron | Função |
|---|------|------|------|--------|
| 21 | Backup Status 5min (heartbeat) | `d3Qn6V9O4QShpf5h` | */5 min | Heartbeat MinIO + alerta |
| 22 | Audit Verify 6h (SHA256 chain) | `KmbrUKvoLzg4cIPW` | 6h | Verifica hash chain audit_log |
| 23 | Cron Stale Detector | `HCYh4VRLcBK89sRu` | */5 min | Detecta workflows travados |
| 24 | Daily Cleanup 03:00 (sessões Redis) | `FZcmxg1cwD2CB5Bb` | 03:00 diário | Limpa sessões > 24h |
| 24b | Retenção Diária (LGPD 5y/2y) | `1C9rZ5DKOKkf0fsA` | 02:00 diário | Apaga dados > 5y (5y) e > 2y (inativos) |
| 25 | Metrics Collector (1min Prometheus) | `12rMQSwMGkaE293C` | 1 min | Scraping /metrics/prometheus |
| 25b | Protocolo Concluído: Envia PDF | `ITEGmC8k7nTJ78Uw` | */5 min | Detecta concluídos + envia PDF via WhatsApp |
| 26 | Alerta Crítico (Telegram + Chatwoot) | `2nSa2sw60lh6lhpb` | webhook | Canal de alertas |
| 26b | Monitor OpenClaw (cron 1min) | `6e7c830b-4ab8-465e-b9e2-b2a86bc0aca9` | 1 min | Chatwoot alerts |
| 28 | Audit Snapshot (diário 04:00 S3) | `qoyKMaG3MLFYu0yH` | 04:00 diário | Snapshot audit → S3 |
| 29 | Rate Limit Reset (hourly) | `24HV3hEwwQcYasAx` | 1h | Reset contadores rate limit |
| 30 | Health Deep Check 15min | `OYW3pxLCJFP47xgX` | 15 min | Smoke test todos endpoints |

### Categoria: LGPD

| # | Nome | ID | Trigger |
|---|------|------|---------|
| 04a | Boas-Vindas + Consentimento LGPD | `sDtkfOJ5BA7M73wB` | webhook |
| 27 | Welcome First Time | `NlGoGgAlY9ln8T0s` | webhook |

### Categoria: Prospecção

| # | Nome | ID |
|---|------|------|
| 16 | Prospecção Lead Enrichment (Tier A/B/C) | `csXKw2fXsaeJZRk8` |
| 18 | Prospecção Follow-up D+7 (LGPD opt-out) | `Fint1SGRjPx6tFFs` |

### Categoria: Observability / MCP

| # | Nome | ID | Função |
|---|------|------|--------|
| 00 | Error Handler Global (T25) v4 | `4IS5oiLyHWGhtb8g` | Captura erros de TODOS WFs ativos |
| 14 | OpenCode-Go LLM Fallback | `FhZVTap8JrLJkiOE` | Fallback OpenAI-compat |
| 22-mcp | MCP Server Tools (T22) v2 | `kTZUoh8ejvGxT8m9` | mcpTrigger — expõe 30+ tools |
| 11 | Monitor Cartório (saúde 6 serviços) | `5ABAZCQVRLd7AmM5` | cron 5min + webhook |
| 08 | Audit Verify Diário | `3rr2WFBCJZ16U4DH` | cron 03:30 diário |

**Total**: 34 ativos + 1 inativo (v3 handoff-human staging) = 35 workflows no painel N8N.

## Plugins Instalados (community packages)

| Plugin | Função | Workflows que usam |
|--------|--------|---------------------|
| `@devlikeapro/n8n-nodes-chatwoot` v1.0.2 | Nodes Chatwoot oficiais | WF 03 (handoff) |
| `@winth03/n8n-nodes-minio` | MinIO/S3 | WF 25b (PDF), WF 28 (snapshot) |
| `n8n-nodes-evolution-api` | Evolution API WhatsApp | WF 01-10, EVO-IN |
| `n8n-nodes-mcp` v0.1.37 | Model Context Protocol | WF 12 (chatbot-llm), WF 22-mcp server |
| `n8n-nodes-pdfkit` | Geração PDF | WF 25b |

**Gerenciado por env**: `N8N_COMMUNITY_PACKAGES_MANAGED_BY_ENV=true`

## Padrões Obrigatórios (todos HTTP nodes)

✅ **Retry**: 3x, exponential backoff (1s, 5s, 15s) — cobertura 100% (63/63 nodes, B07)
✅ **Timeout**: 5-60s dependendo do endpoint
✅ **Header `X-Correlation-ID`**: propagado quando vem do backend
✅ **Error Handler**: WF 00 wired em 33/34 WFs (Lesson 51 ainda exige workaround)

## Variáveis de Ambiente (no N8N)

```env
# Não comitar no repo! Estão em backend/.env e .secrets/api.env
N8N_BASE_URL=http://cartorio_n8n:5678
N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
N8N_MCP_URL=https://flow.2notasudi.com.br/mcp-server/http
N8N_WEBHOOK_SECRET=7d68047987a079bd03aec015c3c774ebec692dd96e4c4839

# Env vars USADAS nos workflow nodes:
CARTORIO_API_KEY          # WF 00, WF 12, WF 31 — auth backend
CHATWOOT_BOT_TOKEN        # WF 03, WF 21-26 (alertas)
CHATWOOT_INBOX_ID=1       # WF 03
CHATWOOT_ACCOUNT_ID=1     # WF 03
EVOLUTION_API_KEY         # WF 01-10, EVO-IN
OPENCODE_GO_TOKEN         # WF 12 (fallback OpenAI-compat)
TELEGRAM_BOT_TOKEN        # WF 31, WF 26 (alertas)
SUPABASE_SERVICE_KEY      # workflows que tocam DB direto (não recomendado)
```

## Operações Comuns

### Listar workflows ativos
```bash
N8N_KEY=$(grep N8N_API_KEY .secrets/api.env | cut -d= -f2-)
curl -H "X-N8N-API-KEY: $N8N_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows?limit=100" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d[\"data\"])} total')"
```

### Re-exportar um workflow do N8N para o repo
```bash
N8N_KEY=$(grep N8N_API_KEY .secrets/api.env | cut -d= -f2-)
WF_ID=bR7qIo3bFpG4zgxO   # ID do WF 01
curl -H "X-N8N-API-KEY: $N8N_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows/$WF_ID" \
  -o infra/n8n-workflows/01-consulta-emolumento.json
```

### Importar/atualizar workflow do repo para o N8N
```bash
N8N_KEY=$(grep N8N_API_KEY .secrets/api.env | cut -d= -f2-)
# POST = cria novo (N8N gera ID)
curl -X POST -H "X-N8N-API-KEY: $N8N_KEY" -H "Content-Type: application/json" \
  -d @infra/n8n-workflows/meu-wf.json \
  "https://flow.2notasudi.com.br/api/v1/workflows"
# Ativar
WF_ID=$(curl -s -H "X-N8N-API-KEY: $N8N_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows?limit=200" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print([w['id'] for w in d['data'] if w['name'].startswith('meu-wf')][0])")
curl -X POST -H "X-N8N-API-KEY: $N8N_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows/$WF_ID/activate"
```

### ⚠️ Editar workflow (PATCH é bloqueado em N8N 2.x)
```bash
# Não funciona:
# curl -X PATCH ... (retorna 405 Method Not Allowed)

# Opção A — POST de novo (delete + recriar):
#  1. Export atual → backup
#  2. DELETE /workflows/{id}
#  3. POST /workflows com novo JSON

# Opção B — DB UPDATE direto (Lesson 50 + 52):
ssh root@cartorio "docker exec -i cartorio_db psql -U supabase_admin -d n8n -c \
  \"UPDATE workflow_entity SET nodes = '<novo nodes JSON>' WHERE id = '<WF_ID>';\""
```

## OpenTelemetry Warning (inofensivo)

O N8N emite warnings sobre OpenTelemetry diagnostics na inicialização. Esses warnings são
**inofensivos** e não afetam o funcionamento. Não é necessário corrigir.

## Métricas & SLOs

| SLO | Target | Atual |
|-----|--------|-------|
| Workflow success rate | ≥ 99% (30d) | ⚠️ medível pós-restart |
| Webhook→response P99 | < 2s | ⚠️ medível pós-restart |
| Healthcheck uptime | ≥ 99.5% (30d) | ⚠️ 502 desde 22:30 UTC 2026-06-30 |
| Cron job completion | ≥ 99% (24h) | ⚠️ medível pós-restart |

Fonte: `infra/slo/slo-definitions.yml` (definições), `infra/slo/slo-alerts.yml` (alertas Prometheus).

## Runbooks

| Task | Doc | Estado |
|------|-----|--------|
| T7 — ativar `n8n-nodes-mcp` em WF12 | `infra/n8n-workflows/T7-mcp-node-runbook.md` | Pendente |
| T8 — ativar `n8n-nodes-chatwoot` em WF03 | `infra/n8n-workflows/T8-chatwoot-node-runbook.md` | Pendente |
| Error Handler Global | `infra/n8n-workflows/README-error-handler.md` | ✅ B06 completo |
| Retry Policy 3x exp backoff | `infra/n8n-workflows/README-retry-policy.md` | ✅ B07 completo |
| **2026-06-30 incidente 502** | `infra/n8n-workflows/N8N_DASHBOARD_2026-06-30.md` | 🚨 Em curso |

## Lições Aprendidas (vinculadas a memory)

- **Lesson 51**: `$env.CARTORIO_API_KEY` bloqueado por `N8N_BLOCK_ENV_ACCESS_IN_NODE=true`. Workaround: docker service update com `--env-add N8N_BLOCK_ENV_ACCESS_IN_NODE=false` OU trocar por N8N credential `httpHeaderAuth`.
- **Lesson 96**: PATCH `/api/v1/workflows/{id}` retorna 405 em N8N 2.x. Use POST (cria novo) ou DB UPDATE direto.
- **Lesson 50/52/55**: DB UPDATE em `workflow_entity` + INSERT em `workflow_history` requer ordem correta (FK `activeVersionId → versionId`). Restart do swarm para invalidação de cache N8N (5-10min).
- **Lesson 109**: MCP `/mcp-server/http` na flow.2notasudi exige header específico (X-N8N-API-KEY ou Bearer) — verificar qual funciona em cada setup.

## Teste Rápido

```bash
# Health
curl https://flow.2notasudi.com.br/healthz

# Listar workflows
curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows?limit=50"

# Execuções de 1 workflow
curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "https://flow.2notasudi.com.br/api/v1/executions?workflowId=bR7qIo3bFpG4zgxO&limit=5"
```

## Próximos Passos (Sprint 4 E6.S2)

1. **Investigar 502 atual** — container crash? OOM? deploy em andamento?
2. **T7 — ativar n8n-nodes-mcp em WF12** (tem runbook pronto)
3. **T8 — ativar n8n-nodes-chatwoot em WF03** (tem runbook pronto)
4. **Resolver webhook paths 404** (agendamento, telegram, opencode-fallback)
5. **Aplicar Opção A do Lesson 51** (N8N_BLOCK_ENV_ACCESS_IN_NODE=false) para WF 00 voltar a alertar
6. **Sincronizar JSONs locais com estado remoto** (re-export após restart)

---

*Modified by Gustavo Almeida · 2026-06-30 ~22:45 BRT — baseado em auditoria completa + arquivamento de 17 v1 legados*
