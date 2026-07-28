# 🗺️ SUPER PLANO v0.6.0 — Cartório 2 Notas Uberlândia

> **Data**: 2026-06-23 14:30 BRT
> **Versão**: 0.6.0 (após incidente SSH)
> **Status**: AGUARDANDO APROVAÇÃO DO PIETRA
> **Owner**: ZCode (orquestrador) + 3 squads (cartorio-dev, cartorio-n8n, cartorio-lgpd)
> **Mandato**: Sprint 0 = Estabilidade; depois Sprint 1+ = Features

---

## 📊 Estado Atual (ground truth validado)

| Item | Status | Evidência |
|---|---|---|
| 12 containers `cartorio_*` Swarm | ✅ UP 1/1 | `docker service ls` via SSH cartorio |
| API FastAPI `/health` | ✅ 200 | curl |
| API Swagger `/docs` | ✅ 200 | curl |
| API Radar `/api/v1/health/radar` | ✅ 200 | curl |
| N8N Flow | ✅ 200 | curl flow.2notasudi.com.br |
| Evolution API (WhatsApp) | ✅ 200 | curl whatsapp.2notasudi.com.br |
| OpenClaw Gateway | ✅ 200 (healthy) | curl + docker inspect |
| Easypanel | ✅ 200 | curl |
| Supabase | ✅ 401 esperado | curl supbase.2notasudi.com.br/auth/v1/health |
| Chatwoot | ❌ DNS não configurado | curl chatwoot.2notasudi.com.br → 000 |
| Tailscale subdomínios | ❌ pendente | tail2fe279.ts.net (cartorio-devops) |
| OpenClaw LLM key | ❌ L4 pendente | L1 DPA bloqueia |
| OpenClaw `/v1/chat` 404 | ⚠️ bug upstream | conhecido MEMORY |

**Resumo**: 8/9 domínios OK, 1 DNS pendente, sistema funcional. Tu reclamou "nada funciona" mas **funciona** — o SSH local estava com IP stale.

---

## 🎯 100 Tasks agrupadas em 6 Sprints Temáticas

### SPRINT 0 — ESTABILIDADE (12 tasks) ⭐ FOCO IMEDIATO

> Mandato Pietra: "deixar tudo pronto, domínios, ambientes, Tailscale". Tudo que está em cinza é DNS/UI que **só Gustavo pode fazer**.

**API/Serviços** (eu executo):
- [T0.1] Criar skill `using-mavis-cross-session` (cross-session comms ZCode↔MiniMax)
- [T0.2] Atualizar `.env.example` local com IPs/domínios REAIS validados via curl
- [T0.3] Documentar em `docs/RUNBOOK_VPS.md` o uso correto de `ssh cartorio` (NUNCA `ssh vps`)
- [T0.4] Adicionar healthcheck nos 3 containers sem check (N8N, Evo, Redis)
- [T0.5] Validar via API que os 4 workflows N8N críticos estão ACTIVE: 01-consulta-emolumento, 02-criar-protocolo, 03-handoff-human, 04-boas-vindas
- [T0.6] Re-executar cada um dos 11 workflows exportados e checar `nodesExecuted > 0`

**Infra/Tailscale** (cartorio-devops):
- [T0.7] Gerar cert wildcard + Traefik router pra `*.tail2fe279.ts.net`
- [T0.8] Validar Tailscale ACL: tag `tag:cartorio` no node vps-cartorio + ssh only via Tailscale

**UI/Externo** (Gustavo):
- [T0.9] Configurar DNS `chatwoot.2notasudi.com.br` (Hostinger ou Cloudflare)
- [T0.10] Criar Chatwoot Agent Bot (webhook → API `/api/v1/webhook/chatwoot`)
- [T0.11] Gerar nova Easypanel API key (a antiga morreu 401)
- [T0.12] Decidir typo DNS: corrigir `supbase` → `supabase` (P2, opcional)

---

### SPRINT 1 — INTEGRAÇÃO CHATWOOT + OPENCLAW LLM (15 tasks)

> Após Sprint 0 fechado, foco em plugar Chatwoot como CRM/handoff.

- [T1.1] Webhook receiver `/api/v1/webhook/chatwoot` (FastAPI)
- [T1.2] Schema Pydantic `ChatwootEvent` (message_created, conversation_status_changed)
- [T1.3] Endpoint `POST /api/v1/chatwoot/handoff` (N8N → Chatwoot inbox)
- [T1.4] Integração Chatwoot ↔ Supabase (contacts mirror em `chatwoot_contacts` table)
- [T1.5] Integração Chatwoot ↔ Redis (sessão WhatsApp ↔ conversation_id)
- [T1.6] Workflow N8N #12 "Chatwoot handoff bridge" (webhook → API → Chatwoot API)
- [T1.7] Workflow N8N #13 "Chatwoot inbound → agent cartório" (webhook Chatwoot → API → N8N → reply)
- [T1.8] OpenClaw: setar `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY` (após L1 DPA)
- [T1.9] OpenClaw: configurar `gateway.mode=local` + `OPENCLAW_GATEWAY_TOKEN`
- [T1.10] OpenClaw: expor `agent.2notasudi.com.br` via Tailscale (subdomínio)
- [T1.11] Investigar OpenClaw `/v1/chat` 404 — abrir issue upstream ou workaround
- [T1.12] Teste E2E: WhatsApp → N8N → API → OpenClaw → reply WhatsApp
- [T1.13] PII scrubbing ANTES de enviar pro OpenClaw (LGPD art. 46)
- [T1.14] Audit log de cada chamada OpenClaw (LGPD art. 50)
- [T1.15] Load test: 100 req/min sustained em OpenClaw

---

### SPRINT 2 — OPENCODE-GO PLUGADO EM TUDO (12 tasks)

> Mandato Pietra: "OpenCode-Go como primary LLM, plug em TUDO".

- [T2.1] `backend/app/integrations/opencode_go.py` — endpoint dedicado (já feito, refactor pra Pydantic v2)
- [T2.2] `backend/app/integrations/opencode_go.py` — fallback chain (OpenCode-Go → OpenClaw → cache)
- [T2.3] N8N credential `opencode-go-deepseek` (POST https://api.opencode.ai/zen/go/v1/chat/completions)
- [T2.4] N8N Workflow #14 "LLM Router" — recebe prompt, decide provider (opencode_go vs openclaw)
- [T2.5] Supabase Edge Function `opencode-router` — chama OpenCode-Go server-side
- [T2.6] Supabase SQL function `call_opencode(prompt text) returns text` — pra usar em queries
- [T2.7] Evolution API webhook → API → OpenCode-Go (summary de mensagem antes de salvar)
- [T2.8] Rate limit OpenCode-Go: 60 req/min por sessão (env `OPENCODE_GO_RATE_LIMIT_PER_MINUTE`)
- [T2.9] Audit log toda chamada OpenCode-Go com hash do payload (LGPD)
- [T2.10] Teste integração: 5 cenários (saudação, dúvida simples, cálculo emolumento, PII detect, handoff)
- [T2.11] Doc `docs/OPENCODE_GO_INTEGRATION.md` com arquitetura, fallbacks, custos estimados
- [T2.12] Dashboard custo: contador de tokens/req por dia (Supabase view)

---

### SPRINT 3 — N8N WORKFLOWS COMPLEXOS + MCP (18 tasks)

> Mandato Pietra: "workflows muito simples, faltam integrações, MCP server/client, credenciais, executions, variables, data tables".

**MCP server (expor tools da API como MCP)**:
- [T3.1] `backend/mcp_server.py` — já existe, validar tools list
- [T3.2] Tool MCP `consultar_emolumento(tipo, uf)` 
- [T3.3] Tool MCP `criar_protocolo(cliente_id, tipo, doc_url)`
- [T3.4] Tool MCP `consultar_protocolo(protocolo_id)`
- [T3.5] Tool MCP `agendar_atendimento(cliente_id, data, servico)`
- [T3.6] Tool MCP `transferir_humano(cliente_id, motivo)`
- [T3.7] Tool MCP `buscar_cep(endereco)` (via ViaCEP)
- [T3.8] Tool MCP `validar_cpf(cpf)` (PII-safe, retorna só hash)

**MCP client (N8N consumindo tools)**:
- [T3.9] N8N credential `mcp-server-api` (auth via `MCP_API_KEY`)
- [T3.10] Workflow #15 "FAQ Bot" com tool calls MCP
- [T3.11] Workflow #16 "Pesquisa Satisfação" com tool `criar_protocolo` se NPS < 7

**Credenciais faltantes (auditar JSONs)**:
- [T3.12] N8N credential `redis-cartorio` (host=cartorio_redis:6379)
- [T3.13] N8N credential `supabase-rest` (apikey service_role)
- [T3.14] N8N credential `chatwoot-api` (apikey)
- [T3.15] N8N credential `openclaw-bearer` (token)

**Variables workaround ($env.NOME)**:
- [T3.16] Workflow #17 "Daily Backup" usando `$env.CARTORIO_API_KEY`
- [T3.17] Workflow #18 "Audit Verify" usando `$env.SUPABASE_SERVICE_ROLE_KEY`
- [T3.18] Doc `docs/N8N_VARIABLES.md` listando todas as env vars obrigatórias

---

### SPRINT 4 — MCP SERVER FULL + PLUGINS + HOOKS (15 tasks)

> Mandato Pietra: "MCP-SERVER FULL, MCP CLIENTE FULL, em VPS/Easypanel/Evolution/N8N/Chatwoot/Redis/Supabase/API/OpenClaw".

**Plugins N8N**:
- [T4.1] N8N node `n8n-nodes-chatwoot` (já instalado, validar v1.0.2)
- [T4.2] N8N node `n8n-nodes-evolution-api` (v1.0.4)
- [T4.3] N8N node `n8n-nodes-mcp` (v0.1.37) — MCP client
- [T4.4] N8N node `n8n-nodes-pdfkit` (v0.1.2) — gerar PDF de protocolo
- [T4.5] Instalar `n8n-nodes-minio` (S3-compatible, pro backup)
- [T4.6] Custom node `n8n-nodes-cartorio-protocolo` (interno, no monorepo)

**MCP server (cada serviço expõe tools)**:
- [T4.7] `mcp-server-supabase` (queries + edge functions)
- [T4.8] `mcp-server-redis` (get/set/keys + ttl)
- [T4.9] `mcp-server-evolution` (sendText, sendMedia, getMessages)
- [T4.10] `mcp-server-chatwoot` (createContact, createConversation, sendMessage)
- [T4.11] `mcp-server-openclaw` (chat, mcp passthrough)
- [T4.12] `mcp-server-easypanel` (deploy, restart, env)

**Hooks (interceptar eventos)**:
- [T4.13] Hook `pre_send_message` (PII scrub antes de enviar WhatsApp)
- [T4.14] Hook `post_protocolo_created` (audit log + notificar Chatwoot)
- [T4.15] Hook `on_handoff_human` (pausar bot, abrir inbox)

---

### SPRINT 5 — LGPD + SEGURANÇA + COMPLIANCE (15 tasks)

> Mandato Pietra: "TOMA MUITO CUIDADO COM A SEGURANÇA DA VPS. LITELLM JÁ FOI HACKEADO."

**LGPD**:
- [T5.1] DPA MiniMax (juru: 2-4 semanas) — draft + enviar
- [T5.2] Encryption at-rest Postgres (pgcrypto + gpg backup)
- [T5.3] Job retenção 5y COM protocolo / até-revogação SEM (backend/app/jobs/retencao.py)
- [T5.4] Endpoint `DELETE /api/v1/cliente/{id}` (LGPD art. 18 VI)
- [T5.5] Atualizar RIPD addendum Sprint 1+2+3

**Segurança VPS**:
- [T5.6] Auditar LiteLLM: confirmar 0 processos rodando (já feito, revalidar)
- [T5.7] Firewall UFW: bloquear 5432/6379 externos, manter 22/80/443
- [T5.8] Fail2ban configurado (ssh + traefik)
- [T5.9] Renovação SSL/TLS automática (já via Traefik, validar cron)
- [T5.10] Secrets: rotação 90d de `CARTORIO_API_KEY`, `MCP_API_KEY`, `AUDIT_HMAC_KEY`

**Compliance**:
- [T5.11] Política formal de credenciais (Supabase Vault vs Hostinger Secret Manager)
- [T5.12] Penetration test básico: scan com `nmap` + `nikto` na VPS
- [T5.13] Backup encrypted push pra S3/B2 (rclone + cron diário)
- [T5.14] Monitor anomalia: alert se >100 req/min de IP único
- [T5.15] Doc `docs/SECURITY_HARDENING.md` consolidado

---

### SPRINT 6 — PROSPECÇÃO + GO-TO-MARKET (13 tasks) ← opcional, sprint final

> Mandato Pietra: "ACHE OS MELHORES CARTORIOS DO GOOGLE E USE MEU WHATSAPP PESSOAL".

- [T6.1] `docs/leads/cartorios-br-top30.md` (já existe, atualizar com scoring)
- [T6.2] `docs/leads/roteiros/whatsapp-tier-a.md` (5 modelos)
- [T6.3] `docs/leads/roteiros/email-tier-b.md` (3 modelos)
- [T6.4] `docs/leads/roteiros/linkedin-tier-c.md` (3 modelos)
- [T6.5] Template Canva de proposta (PDF) com branding cartório
- [T6.6] CRM interno: `leads` table no Supabase (nome, contato, tier, status)
- [T6.7] API `GET /api/v1/leads?status=quente&tier=A`
- [T6.8] N8N Workflow #19 "Lead scoring automático" (parse site + score)
- [T6.9] N8N Workflow #20 "Disparo WhatsApp" (template + opt-out check)
- [T6.10] Bot Telegram (CEO-assistant) pra aprovar copy bloco a bloco
- [T6.11] KPI dashboard: leads/mês, conversion rate, tier breakdown
- [T6.12] A/B test 2 copies Tier A, medir open + reply
- [T6.13] Doc `docs/PROSPECCAO_RESULTADOS.md` mensal

---

## 📋 Critério de Pronto (DoD) por sprint

Cada task DEVE ter:
1. ✅ Commit com Conventional Commits + `Modified by [squad]`
2. ✅ Teste (se código) — pytest ou workflow validation
3. ✅ Doc atualizada (se mudou comportamento)
4. ✅ MEMORY.md atualizado (se lesson aprendida)
5. ✅ Report pro Pietra via `mavis communication messages` se cross-squad

---

## 🚦 Status

| Sprint | Tasks | Bloqueio principal |
|---|---|---|
| **Sprint 0** | 12 | T0.9-T0.12 (UI/Externo - Pietra) |
| Sprint 1 | 15 | L1 DPA (L4 OpenClaw key) |
| Sprint 2 | 12 | nenhum (já tem key) |
| Sprint 3 | 18 | nenhum (N8N funcional) |
| Sprint 4 | 15 | plugins N8N precisam de licença |
| Sprint 5 | 15 | DPA MiniMax (jurídico) |
| Sprint 6 | 13 | decisão CEO (prospecção bot vs manual) |

**Recomendação**: começar Sprint 0 HOJE. Pietra faz as 4 tasks UI dele em paralelo. Daqui a 1 semana, Sprint 1 fechado.

---

## 🤝 Comunicação cross-session (ZCode ↔ MiniMax)

**Comando padrão pra report cross-squad**:
```bash
mavis communication send --to <session_id> --command prompt --content "..."
```

**Quando usar**:
- Sprint review entre squads
- Decisão arquitetural que afeta > 1 squad
- Bloqueador técnico que precisa de escalação

**Quando NÃO usar**:
- Mudanças locais (commit + push basta)
- Dúvidas sobre estado de um único serviço
- Updates incrementais

---

## ⏸️ Próximo passo

**Aguardando aprovação do Pietra** pra começar Sprint 0. Concorda com:
1. Agrupamento das 100 tasks em 6 sprints temáticas?
2. Sprint 0 com 12 tasks (4 UI dele + 8 eu executo)?
3. DoD (Definition of Done) por task: commit + test + doc + memory + report?
4. Comunicação cross-session via `mavis communication send`?

Modified by ZCode (Pietra session 2026-06-23)
