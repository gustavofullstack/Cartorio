---
name: n8n
description: |
  Skill para interagir com N8N Workflow Engine via API REST e MCP.
  Use quando precisar: listar/executar/criar workflows, verificar execuções,
  gerenciar credenciais, triggers, webhooks, e MCP tools do N8N.
  URL: https://flow.2notasudi.com.br | 34 workflows ativos
---

# N8N Workflow Engine — Skill de Integração

## Acesso

| Item | Valor |
|------|-------|
| **URL Base** | `https://flow.2notasudi.com.br` |
| **API Key** | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (ver backend/.env N8N_API_KEY) |
| **Header de Auth** | `X-N8N-API-KEY: <jwt>` |
| **MCP URL** | `https://flow.2notasudi.com.br/mcp-server/http` |
| **Health Check** | `GET /healthz` → 200 OK |
| **Porta interna** | 5678 |

## Endpoints Principais

### Workflows
```bash
# Listar todos os workflows
GET /api/v1/workflows?limit=100

# Executar workflow por ID
POST /api/v1/workflows/{id}/execute

# Obter execuções de um workflow
GET /api/v1/executions?workflowId={id}&limit=20

# Ativar/desativar workflow
PATCH /api/v1/workflows/{id}
{"active": true}
```

### Webhooks (via URL pública)
```bash
# Webhook EVO-IN (Evolution API → N8N)
POST https://flow.2notasudi.com.br/webhook/evo-in

# Webhook Consulta Emolumento
POST https://flow.2notasudi.com.br/webhook/consulta-emolumento

# Webhook Chatbot LLM
POST https://flow.2notasudi.com.br/webhook/chatbot-llm
```

### MCP Tools via N8N
```bash
# Acessar tools MCP expostas pelo N8N
POST https://flow.2notasudi.com.br/mcp-server/http
Authorization: Bearer <N8N_API_KEY>
Content-Type: application/json
{
  "method": "tools/list"
}
```

## 34 Workflows Ativos (2026-06-26)

| # | Nome | Status |
|---|------|--------|
| EVO-IN | Evolution Webhook Inbound | ✅ ON |
| 31 | Telegram Listener (CartorioBot test) | ✅ ON |
| 12 | Chatbot LLM E2E (PII + MCP + OpenCode-Go) | ✅ ON |
| 03 | Handoff Humano (Chatwoot v2) | ✅ ON |
| 00 | Error Handler Global (T25) v4 | ✅ ON |
| MCP | Server Tools (T22) v2 | ✅ ON |
| 21 | Backup Status 5min (heartbeat + alerta) | ✅ ON |
| 22 | Audit Verify 6h (SHA256 chain check) | ✅ ON |
| 23 | Cron Stale Detector (5min) | ✅ ON |
| 24 | Daily Cleanup 03:00 (sessões > 24h Redis) | ✅ ON |
| 25 | Metrics Collector (1min Prometheus) | ✅ ON |
| 26 | Alerta Crítico (Telegram + Chatwoot) | ✅ ON |
| 27 | Welcome First Time (consentimento LGPD) | ✅ ON |
| 28 | Audit Snapshot (diário 04:00) | ✅ ON |
| 29 | Rate Limit Reset (hourly) | ✅ ON |
| 30 | Health Deep Check 15min | ✅ ON |
| 01 | Consulta Emolumento WhatsApp (v3) | ✅ ON |
| 02 | Criar Protocolo (LGPD) | ✅ ON |
| 04 | Boas-Vindas + Consentimento LGPD | ✅ ON |
| 05 | Agendamento Atendimento | ✅ ON |
| 06 | Segunda Via Documento | ✅ ON |
| 07 | Pesquisa Satisfação | ✅ ON |
| 08 | Audit Verify Diário | ✅ ON |
| 09 | Monitor Backup Diário | ✅ ON |
| 10 | FAQ Bot | ✅ ON |
| 11 | Monitor Cartório | ✅ ON |
| 14 | OpenCode-Go LLM Fallback | ✅ ON |
| 16 | Prospecção Lead Enrichment | ✅ ON |
| 18 | Prospecção Follow-up D+7 | ✅ ON |
| 23 | LGPD Esqueci (DELETE cascata) | ✅ ON |
| 24 | Retenção Diária (LGPD 5y/2y) | ✅ ON |
| 25 | Protocolo Concluído: PDF WhatsApp | ✅ ON |
| 26 | Monitor OpenClaw (cron 1min) | ✅ ON |
| 04 | Consulta Protocolo | ✅ ON |

## Plugins Instalados

| Plugin | Função |
|--------|--------|
| `@devlikeapro/n8n-nodes-chatwoot` | Nodes Chatwoot |
| `@winth03/n8n-nodes-minio` | MinIO/S3 |
| `n8n-nodes-evolution-api` | Evolution API (WhatsApp) |
| `n8n-nodes-mcp` | Model Context Protocol |
| `n8n-nodes-pdfkit` | Geração de PDFs |

## Padrões Obrigatórios

Todos os HTTP nodes do N8N **devem** ter:
- ✅ Retry: 3x, exponential backoff
- ✅ Timeout configurado
- ✅ Header `X-Correlation-ID` propagado
- ✅ Error Handler conectado ao WF 00 (Error Handler Global)

## Variáveis de Ambiente

```env
N8N_BASE_URL=http://cartorio_n8n:5678
N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
N8N_MCP_URL=https://flow.2notasudi.com.br/mcp-server/http
N8N_WEBHOOK_SECRET=7d68047987a079bd03aec015c3c774ebec692dd96e4c4839
```

## OpenTelemetry Warning

O N8N emite warnings sobre OpenTelemetry diagnostics na inicialização. Esses warnings são **inofensivos** e não afetam o funcionamento. Não é necessário corrigir.

## Teste Rápido

```bash
# Health
curl https://flow.2notasudi.com.br/healthz

# Listar workflows
curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows?limit=50"
```

## MCP Server & Client Integration

- **N8N MCP Client/Server**: O plugin `n8n-nodes-mcp` permite que workflows do N8N atuem como clientes/servidores MCP.
- **MCP Endpoint**: `https://flow.2notasudi.com.br/mcp-server/http`
- **Exemplo de Chamada MCP (Listar Tools)**:
  ```bash
  curl -X POST https://flow.2notasudi.com.br/mcp-server/http \
    -H "Authorization: Bearer $N8N_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"method": "tools/list"}'
  ```

