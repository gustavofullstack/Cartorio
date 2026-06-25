# N8N — Documentação Oficial (DOCS2)

> **Versão N8N**: 1.94.x
> **Data download**: 2026-06-26
> **Fonte**: https://docs.n8n.io (llms.txt index)
> **Workflows ativos**: 34 (no nosso sistema)

Workflow automation engine — combina AI capabilities com automação de processos de negócio.

---

## 🏗️ Arquitetura

- **Engine**: TypeScript + Node.js 20+
- **DB**: PostgreSQL (próprio schema, separado do cartorio DB)
- **UI**: Vue 3 frontend
- **Execução**: DAG-based workflow runtime
- **Runner**: External (n8n-runner) — separa execução da UI
- **Licença**: Fair-code (Sustainable Use License + Enterprise)

---

## 🔵 Trigger Nodes (10+ nodes)

| Nome | Descrição |
|------|-----------|
| **Webhook** | Dispara workflows ao receber requisições HTTP em endpoint configurado |
| **Schedule Trigger** | Inicia workflows em intervalos programados (cron) |
| **Manual Trigger** | Permite executar workflow manualmente (testes) |
| **Chat Trigger** | Dispara workflows a partir de mensagens de chat |
| **Email Trigger (IMAP)** | Aciona ao receber novos e-mails via IMAP |
| **n8n Trigger** | Inicia workflows em eventos de outra instância n8n |
| **Error Trigger** | Dispara workflow dedicado quando outro falha |
| **Workflow Trigger** | Chama sub-workflows (Execute Sub-workflow) |
| **SSE Trigger** | Escuta eventos Server-Sent Events em tempo real |
| **Local File Trigger** | Detecta mudanças em arquivos locais |
| **RSS Feed Trigger** | Monitora feeds RSS e dispara ao encontrar novos itens |

---

## 🟢 Action Nodes (Core)

| Nome | Descrição |
|------|-----------|
| **HTTP Request** | Faz chamada HTTP para qualquer API externa |
| **Code** | Executa JavaScript/Python customizado |
| **Function** | Versão simples do Code (deprecated, use Code) |
| **Set** | Define/modifica campos do JSON de saída |
| **If** | Condicional (if/else binário) |
| **Switch** | Condicional multi-caminho (case/when) |
| **Merge** | Combina outputs de múltiplos branches |
| **Loop / SplitInBatches** | Itera sobre array |
| **Wait** | Aguarda N segundos/minutes |
| **Execute Workflow** | Chama outro workflow |
| **Respond to Webhook** | Retorna resposta para webhook caller |
| **Error Trigger** | Captura erros para workflow de tratamento |

---

## 🟣 Plugins Comunitários (5 instalados no nosso Cartório)

| Plugin | Função | Uso no nosso projeto |
|--------|--------|---------------------|
| **@devlikeapro/n8n-nodes-chatwoot** | Nodes para Chatwoot CRM | WF03 handoff humano, registro de conversas |
| **@winth03/n8n-nodes-minio** | Nodes para MinIO S3 storage | Backup de workflows, storage de PDFs |
| **n8n-nodes-evolution-api** | Nodes nativos Evolution API | WF01 consulta emolumento, WF02 criar protocolo |
| **n8n-nodes-mcp** | Nodes para Model Context Protocol | Brain memory, chamadas LLM |
| **n8n-nodes-pdfkit** | Nodes para geração de PDFs | Segunda via de documentos |

---

## 🟡 Integrações Nativas (Core)

| Categoria | Nodes |
|-----------|-------|
| **Comunicação** | Slack, Telegram, Discord, Email (SMTP), Twilio |
| **Banco de Dados** | Postgres, MySQL, MongoDB, Redis |
| **Storage** | AWS S3, Google Drive, Dropbox |
| **DevOps** | GitHub, GitLab, Jenkins |
| **CRM** | HubSpot, Salesforce, Pipedrive |
| **Marketing** | Mailchimp, Sendgrid |
| **Google** | Sheets, Docs, Calendar, Gmail |
| **AI/ML** | OpenAI, Anthropic, HuggingFace, Ollama |

---

## 🔧 Padrões Obrigatórios no nosso Projeto (Squad B DONE)

Padrões verificados em **63/63 HTTP nodes** (B07) + **130/130 nodes** (B08):

| Padrão | Cobertura | Comando/Validação |
|--------|-----------|-------------------|
| **Retry policy 3x exp backoff** | 100% HTTP | `options.retry.maxTries: 3` + `waitBetweenTries: 1000ms` |
| **Timeout 5s/10s** | 100% HTTP | `options.timeout: 5000` ou `10000` |
| **X-Correlation-ID header** | 100% HTTP | `headers.X-Correlation-ID: {{ $execution.id }}` |
| **Error Handler global** | 100% workflows | Workflow #00 conectado em cada workflow |
| **Logs estruturados JSON** | 100% workflows | `code` node com JSON.stringify() |
| **Métricas Prometheus** | 100% workflows | `code` node emite métricas para API |
| **Settings.errorWorkflow** | 41/45 workflows ⚠️ | Falta em 4 (B12 detectou) |

---

## 📊 Nossos Workflows Ativos (34)

```
WF #00 — Error Handler Global (T25) v4 ✅
WF #01 — Consulta Emolumento WhatsApp v3 ✅
WF #02 — Criar Protocolo LGPD ✅
WF #03 — Handoff Humano Chatwoot ✅
WF #04 — Boas-Vindas + Consentimento LGPD ✅
WF #04b — Consulta Protocolo ✅
WF #05 — Agendamento Atendimento ✅
WF #06 — Segunda Via Documento ✅
WF #07 — Pesquisa Satisfação 24h ⚠️ (aguarda cred Evolution)
WF #08 — Audit Verify Diário (cron 03:30) ✅
WF #09 — Monitor Backup Diário (cron 04:00) ✅
WF #10 — FAQ Bot ✅
WF #11 — Monitor Cartório ✅
WF #12 — Chatbot LLM End-to-End ✅
WF #MCP — Server Tools (T22) v2 ✅
+ 19 workflows adicionais
```

---

## 🔐 Autenticação

| Tipo | Como usar |
|------|-----------|
| **API Key (N8N_API_KEY)** | `Authorization: Bearer <jwt>` em chamadas à API N8N |
| **Basic Auth** | Usuário/senha no header |
| **OAuth 2.0** | Para integrações externas (Google, Slack, etc) |
| **Header Auth** | Header customizado por workflow |
| **Credential Vault** | Storage criptografado de credenciais por workflow |

---

## ⚙️ Variáveis de Ambiente Essenciais

```bash
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=https
N8N_BASE_URL=https://flow.2notasudi.com.br
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=<secret>
N8N_USER_MANAGEMENT_DISABLED=true
N8N_ENCRYPTION_KEY=<secret>
EXECUTIONS_DATA_PRUNE=true
```

---

## 🔗 MCP N8N Server

N8N expõe MCP server em `/mcp-server/http`:
- 30 tools disponíveis
- Permite agents orquestrarem workflows via MCP
- Endpoint: `https://flow.2notasudi.com.br/mcp-server/http`

---

## 📚 Fontes Adicionais

- **Docs oficial**: https://docs.n8n.io
- **llms.txt**: https://docs.n8n.io/llms.txt
- **Forum**: https://community.n8n.io
- **GitHub**: https://github.com/n8n-io/n8n
- **Workflows templates**: https://n8n.io/workflows

---

**Modified by**: ZCode/Mavis (orquestrador)
**Próxima ação**: integrar este catálogo na skill `prompt-cartorio` para uso por agents
**Status**: ✅ DOCS2 DONE — N8N catalogado + padrões verificados no nosso sistema