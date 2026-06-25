# N8N — Documentação Consolidada

> **Fonte**: docs.n8n.io + nossa experiência operacional
> **Versão**: Latest (Docker Swarm via Easypanel)
> **URL**: https://flow.2notasudi.com.br
> **MCP URL**: https://flow.2notasudi.com.br/mcp-server/http

---

## 🎯 Conceitos Fundamentais

| Conceito | Descrição |
|----------|-----------|
| **Workflow** | Sequência automatizada de ações (nodes conectados) |
| **Node** | Unidade básica de ação (HTTP, Code, IF, Set, etc) |
| **Trigger** | Node que inicia workflow (Webhook, Schedule, Manual) |
| **Execution** | Uma rodada do workflow (registrada em DB) |
| **Credentials** | Secrets gerenciados separadamente (HTTP Basic, API Keys, OAuth) |
| **Expressions** | `{{ $json.field }}` para acessar dados dinâmicos |
| **Webhook** | Endpoint HTTP para receber dados externos |

---

## 📡 Nós Principais (Core Nodes)

| Nó | Função | Uso típico |
|----|--------|-----------|
| **HTTP Request** | Chamar API REST | Chamar nossa API, Supabase, etc |
| **Webhook** | Receber HTTP POST | Receber eventos Evolution, Chatwoot |
| **Code (JS/Python)** | Lógica custom | Transformar dados, calcular |
| **Schedule** | Trigger por cron | Cron jobs (backup, audit) |
| **IF / Switch** | Condicional | Roteamento por tipo de evento |
| **Set** | Setar campos | Adicionar metadados (correlation_id) |
| **Function** | Code legacy | Igual Code mas limitado |
| **Merge** | Combinar fluxos | Wait + Join |
| **Wait** | Delay controlado | Rate limiting entre chamadas |
| **Stop and Error** | Parar com erro | Encerrar workflow com falha |

---

## 🔌 Plugins Instalados (Cartório)

| Plugin | Função |
|--------|--------|
| `@devlikeapro/n8n-nodes-chatwoot` | Nodes para Chatwoot |
| `@winth03/n8n-nodes-minio` | Nodes para MinIO (S3) |
| `n8n-nodes-evolution-api` | Nodes Evolution API |
| `n8n-nodes-mcp` | Nodes MCP |
| `n8n-nodes-pdfkit` | Geração de PDFs |

---

## ✅ Padrões Já Aplicados (B07-B11)

- **B07** Retry policy 3x exp backoff em 63/63 HTTP nodes
- **B08** Timeout 5s/10s em 130/130 HTTP nodes
- **B09** X-Correlation-ID em todos os HTTP nodes
- **B10** Métricas Prometheus adicionadas
- **B11** Error handler v6 conectado em todos os workflows

---

## 📚 Workflows Ativos (34)

| # | Workflow | Status |
|---|----------|--------|
| 00 | Error Handler Global (T25) v4 | ✅ |
| 01 | Consulta Emolumento WhatsApp v3 | ✅ |
| 02 | Criar Protocolo LGPD | ✅ |
| 03 | Handoff Humano Chatwoot | ✅ |
| 04 | Boas-Vindas + Consentimento LGPD | ✅ |
| 04b | Consulta Protocolo | ✅ |
| 05 | Agendamento Atendimento | ✅ |
| 06 | Segunda Via Documento | ✅ |
| 07 | Pesquisa Satisfação 24h | ⚠️ (aguarda cred Evolution) |
| 08 | Audit Verify Diário (cron 03:30) | ✅ |
| 09 | Monitor Backup Diário (cron 04:00) | ✅ |
| 10 | FAQ Bot | ✅ |
| 11 | Monitor Cartório (13 nodes) | ✅ |
| 12 | Chatbot LLM End-to-End PII + OpenCode-Go | ✅ |
| 22 | MCP Server Tools v2 | ✅ |
| + | 19 workflows adicionais | ✅ |

---

## ⚠️ Pendências (Sprint 5+)

- [ ] **B12**: Test runner automatizado para workflows
- [ ] **B13**: Templates de workflow padrão
- [ ] **B14**: Dashboard de monitoramento N8N
- [ ] **B15**: Alertas Telegram para falhas críticas
- [ ] Agent: configurar credential Evolution API (WF #07)
- [ ] Agent: testar todos os 34 workflows individualmente
- [ ] Agent: corrigir workflows com problemas identificados

---

## 🔗 Links Úteis

| Recurso | URL |
|---------|-----|
| Docs oficial | https://docs.n8n.io/ |
| GitHub | https://github.com/n8n-io/n8n |
| Hospedagem cloud | https://n8n.cloud/ |
| Comunidade | https://community.n8n.io/ |
| Workflows templates | https://n8n.io/workflows/ |
| HTTP Request docs | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/ |
| Webhook docs | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/ |
| Error handling | https://docs.n8n.io/flow-logic/error-handling/ |
| Production checklist | https://docs.n8n.io/hosting/production-checklist/ |

---

## 🎯 Nossa Arquitetura

```
EVOLUTION-API webhook → N8N (flow.2notasudi.com.br)
                            ↓
                       Workflow #01-34
                            ↓
                       HTTP Request → API (api.2notasudi.com.br)
                            ↓
                       Process + Audit + Log
                            ↓
                       Webhook N8N out → Evolution API (sendText)
                            ↓
                       WhatsApp do cliente
```

---

## 📊 Métricas Prometheus

N8N expõe métricas em `/metrics`:
- `n8n_wf_executions_total{workflow, status}`
- `n8n_wf_latency_seconds{workflow}`
- `n8n_node_executions_total{node, type}`
- `n8n_api_errors_total{endpoint}`