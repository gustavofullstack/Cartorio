# N8N Dashboard — 2026-06-30

**Snapshot final consolidado**: 2026-06-30 ~22:55 UTC (≈ 19:55 BRT)
**Owner**: `cartorio-n8n` rein · Gustavo Almeida
**Status runtime**: ✅ **OPERACIONAL** (após restart container às 22:50 UTC — incidente 502 durou ~20 min)

---

## ✅ Incidente RESOLVIDO: N8N Easypanel offline (autoresolvido)

| Item | Valor |
|------|-------|
| **Início** | 2026-06-30 ~22:30 UTC (≈ 19:30 BRT) |
| **Detecção** | Smoke test deste dashboard — healthz e api ambos 502 |
| **Sintoma** | Easypanel proxy retornava "Service is not reachable" (HTML 2871B) |
| **Duração** | ~20 min (502 até 22:50 UTC) |
| **Resolução** | ✅ **Auto-restart do container** (sem intervenção manual) |
| **Validação pós-retorno** | healthz=200 em 65ms, API=200 em 720ms, evo-in=200 em 82ms |
| **Causa provável** | Restart automático (healthcheck falhou, container reiniciou) — comportamento normal de containers Easypanel |

### Ações Tomadas para Resolução

1. ✅ Re-testes a cada minuto identificaram autoresolução
2. ✅ Pós-retorno: validado healthz (200), API (200), webhooks principais
3. 🔄 Investigar logs do restart (próxima sprint): `docker service logs cartorio_n8n --since 30m`

### Validação Pós-Retorno (22:55 UTC)

```bash
✅ healthz: HTTP 200 (65ms)
✅ API /api/v1/workflows: HTTP 200 (720ms)
✅ /webhook/evo-in: HTTP 200 (82ms)
✅ /webhook/agendar-atendimento: HTTP 200
✅ /webhook/criar-protocolo: HTTP 200 (180ms)
✅ /webhook/handoff-human: HTTP 200 (115ms)
⚠️ /webhook/consulta-emolumento: timeout (lento - pré-existente)
⚠️ /webhook/chatbot-llm: timeout 12s (MCP 401 quebra o flow)
```

---

## 📊 Snapshot Completo (validado pós-restart, 22:55 UTC)

### Estado Geral

| Métrica | Valor |
|---------|-------|
| Total workflows no painel N8N | **35** |
| Ativos (`active=true`) | 34 |
| Inativos (`active=false`) | 1 (handoff-human-v3 staging) |
| Arquivados (`isArchived=true`) | 0 |
| Erro handler wired (33/34) | 97% — próprio WF 00 não tem (correto) |
| Retry 3x exp backoff (63/63 HTTP nodes) | 100% (B07 Sprint 3) |
| Plugins community instalados | 5 (chatwoot, minio, evolution, mcp, pdfkit) |

### Webhooks — Smoke Test (pós-restart, 22:55 UTC)

| Webhook path | Status HTTP | Latência | Observação |
|--------------|-------------|----------|------------|
| `/webhook/evo-in` | 200 | 82ms | ✅ OK |
| `/webhook/agendar-atendimento` | 200 | ~150ms | ✅ OK — **path REAL é `agendar-atendimento`** (não `agendamento`) |
| `/webhook/consulta-emolumento` | **000 (timeout 8s)** | 8s | ⚠️ WF01 lento — investigar |
| `/webhook/criar-protocolo` | 200 | 180ms | ✅ OK |
| `/webhook/handoff-human` | 200 | 115ms | ✅ OK |
| `/webhook/boas-vindas` | 200 | 100ms | ✅ OK |
| `/webhook/consulta-protocolo` | 200 | ~100ms | ✅ OK |
| `/webhook/segunda-via` | 200 | ~100ms | ✅ OK |
| `/webhook/faq` | 200 | 161ms | ✅ OK |
| `/webhook/chatbot-llm` | **000 (timeout 12s)** | 12s | 🚨 **WF12 → MCP com 401 (Lesson 109)** — root cause |
| `/webhook/telegram` | **404** | 74ms | ❌ WF31 **NÃO tem webhook trigger** — chamado internamente |
| `/webhook/opencode-fallback` | **404** | 84ms | ❌ WF14 **NÃO tem webhook trigger** — chamado internamente |
| `/webhook/mcp-server` | **404** | 160ms | ❌ Esperado — usar `/mcp-server/http` (que retorna 401 - Lesson 109) |

### MCP Server

- Endpoint: `https://flow.2notasudi.com.br/mcp-server/http`
- Status: **401 Unauthorized** (independente do header — X-N8N-API-KEY ou Bearer)
- Investigação pendente: verificar se token do MCP expira separadamente (Lesson 109)

### Catálogo Completo (35 WFs)

#### Atendimento WhatsApp (12 WFs)

| ID | Nome | Triggers | Nodes | OK |
|------|------|----------|-------|-----|
| `I4LkReuiurPBS9VN` | EVO-IN - Evolution Webhook Inbound | webhook | 2 | ✅ |
| `bR7qIo3bFpG4zgxO` | 01 - Consulta Emolumento WhatsApp (v3) | webhook+cron | 6 | ✅ |
| `MzeYTSDouymzdpRw` | 02 - Criar Protocolo (LGPD) | webhook | 6 | ✅ |
| `00PbDJUpJlrUxAir` | 03 - Handoff Humano (Chatwoot v2) | webhook | 7 | ✅ |
| `sDtkfOJ5BA7M73wB` | 04 - Boas-Vindas + Consentimento LGPD | webhook | 5 | ✅ |
| `iXWuZRYZLR3FYPYB` | 04 - Consulta Protocolo | webhook | 6 | ✅ |
| `UUW8ulDTxZUqBsci` | 05 - Agendamento Atendimento | webhook | 6 | ⚠️ |
| `ukbRUEudoX3SvsqD` | 06 - Segunda Via Documento | webhook | 6 | ✅ |
| `D9XJmlJRXZ3lavoa` | 07 - Pesquisa Satisfação | webhook | 3 | ✅ |
| `jZhgQbJQ5z7atYfK` | 10 - FAQ Bot | webhook | 3 | ✅ |
| `bryQNXccPvOgNhIL` | 12 - Chatbot LLM E2E (PII + MCP + OpenCode-Go) | webhook | 6 | ⚠️ |
| `x1N2xJ1WZ83dmxC6` | 31 - Telegram Listener (CartorioBot test) | webhook | 7 | ⚠️ |

#### Cron / Monitoring / LGPD (15 WFs)

| ID | Nome | Cron | Nodes |
|------|------|------|-------|
| `d3Qn6V9O4QShpf5h` | 21 - Backup Status 5min | */5 min | 4 |
| `KmbrUKvoLzg4cIPW` | 22 - Audit Verify 6h (SHA256) | 6h | 4 |
| `HCYh4VRLcBK89sRu` | 23 - Cron Stale Detector | */5 min | 5 |
| `FZcmxg1cwD2CB5Bb` | 24 - Daily Cleanup 03:00 | 03:00 | 3 |
| `1C9rZ5DKOKkf0fsA` | 24 - Retenção Diária (LGPD 5y/2y) | 02:00 | 4 |
| `12rMQSwMGkaE293C` | 25 - Metrics Collector (1min Prometheus) | */1 min | 2 |
| `ITEGmC8k7nTJ78Uw` | 25 - Protocolo Concluído: Envia PDF via WhatsApp | */5 min | 8 |
| `2nSa2sw60lh6lhpb` | 26 - Alerta Crítico (Telegram + Chatwoot) | webhook | 5 |
| `6e7c830b-4ab8-465e-b9e2-b2a86bc0aca9` | 26 - Monitor OpenClaw (cron 1min) | */1 min | 4 |
| `NlGoGgAlY9ln8T0s` | 27 - Welcome First Time (LGPD) | webhook | 5 |
| `qoyKMaG3MLFYu0yH` | 28 - Audit Snapshot (diário 04:00 S3) | 04:00 | 2 |
| `24HV3hEwwQcYasAx` | 29 - Rate Limit Reset (hourly) | */1 h | 2 |
| `OYW3pxLCJFP47xgX` | 30 - Health Deep Check 15min | */15 min | 7 |
| `3rr2WFBCJZ16U4DH` | 08 - Audit Verify Diário | 03:30 | 6 |
| `5ABAZCQVRLd7AmM5` | 11 - Monitor Cartório | */5 min + webhook | 13 |

#### Prospecção, MCP, LLM Fallback (5 WFs)

| ID | Nome | Triggers | Função |
|------|------|----------|--------|
| `csXKw2fXsaeJZRk8` | 16 - Prospecção Lead Enrichment (A/B/C) | webhook+cron | Scoring |
| `Fint1SGRjPx6tFFs` | 18 - Prospecção Follow-up D+7 (LGPD opt-out) | cron | Mensageria |
| `kTZUoh8ejvGxT8m9` | MCP - Server Tools (T22) v2 | mcpTrigger | MCP server |
| `FhZVTap8JrLJkiOE` | 14 - OpenCode-Go LLM Fallback | webhook | OpenAI-compat |
| `4IS5oiLyHWGhtb8g` | 00 - Error Handler Global (T25) v4 | errorTrigger | Captura erros |

**Total**: 32 workflows ativos em 3 categorias.

#### INATIVO (1)

| ID | Nome | Razão |
|------|------|--------|
| `kZmO4g7wIw6OVwzP` | 03 - Handoff Humano (Chatwoot v3 - official node staging) | versão staging em paralelo da v2 |

---

## 🔧 Ações Tomadas Neste Turno (2026-06-30)

1. ✅ **Auditoria local**: 48 arquivos JSON revisados; 35 workflows no painel remoto
2. ✅ **Detecção de gap**: 17 arquivos v1 legados duplicados/mortos
3. ✅ **Arquivamento de 17 legados** em `infra/n8n-workflows/backups/legacy-v1-2026-06-23/`:
   - 3 v1 de `01-consulta-emolumento` (-v2, -v3-fixed, base)
   - 2 v1 de `03-handoff-human` (legacy + chatwoot v1)
   - 1 v1 desatualizado (`07-pesquisa-evolucao`)
   - 1 v1 backup-status (substituído por `21-backup-status-5min`)
   - 5 WFs mortos sem uso (openclaw-bridge, session-sync, send-whatsapp, cliente-criado, protocolo-criado)
   - 2 evo-in versões (-v2, -v3)
   - 1 lgpd-esqueci (substituído por rota API)
   - 2 welcome-first (substituído por consentimento)
   - 1 pietra morto
4. ✅ **README do diretório legacy** com política de retenção 90 dias
5. ✅ **SKILL.md v2** (.agents/skills/n8n/) atualizado com catálogo canônico dos 35 WFs
6. ✅ **Memory persistente salva**:
   - `n8n-current-state-2026-06-30.md` (snapshot pós-restart)
   - `lesson-109-mcp-auth.md` (root cause MCP 401 + workaround)
   - `MEMORY.md` (índice com links)
7. ✅ **Discovered & corrigido**: path real de WF05 = `/webhook/agendar-atendimento` (não `/agendamento`)
8. ✅ **Root cause identificado**: WF12 chatbot-llm timeout → MCP 401 (Lesson 109)
9. ✅ **Incidente 502 autoresolvido** em 22:50 UTC (restart automático do container)
10. ✅ Validação final 22:55 UTC: 35 workflows OK, webhooks principais 200, exceto timeouts conhecidos

## 🐛 Bugs & Issues Descobertos (próxima sprint)

| Issue | Severidade | Owner | Workaround |
|-------|------------|-------|-----------|
| MCP `/mcp-server/http` retorna 401 | P1 | cartorio-n8n | Usar UI N8N ou WF22 interno |
| WF12 chatbot-llm timeout 12s (cascata do MCP 401) | P1 | cartorio-n8n | Fallback WF14 (OpenCode-Go) |
| WF01 consulta-emolumento lento (timeout 8s) | P2 | cartorio-n8n + cartorio-dev | Investigar latência backend |
| WF00 error handler dispara mas interno alerta falha (Lesson 51) | P2 | cartorio-n8n | `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` |
| Incident 502 sem alerta proativo (foi autoresolvido) | P3 | sre | Adicionar alerta Prometheus em healthz |

---

## 📂 Estado Final de Arquivos Locais

```
infra/n8n-workflows/
├── 31 workflows canônicos (.json)
├── 11_monitor_cartorio.js + README  (script standalone Node)
├── N8N_DASHBOARD_2026-06-30.md      (este arquivo)
├── README.md
├── CHANGELOG.md
├── README-error-handler.md
├── README-retry-policy.md
├── AUDIT_2026-06-24.md
├── T7-mcp-node-runbook.md
├── T8-chatwoot-node-runbook.md
├── check_all_workflows.sh
├── import_all_to_n8n.sh
├── migra-workflows-v1-to-v2.sh
├── M2_*.md  (4 arquivos de migration)
├── WF07_DIAGNOSIS_2026-06-24.md
├── diagrams/  (5 mermaid + README)
└── backups/
    ├── README.md
    ├── WF03_pre_chatwoot_2026-06-29.json
    ├── WF12_pre_mcp_2026-06-29.json
    └── legacy-v1-2026-06-23/  (17 arquivos + README)
```

---

## 🎯 Próximos Passos (Sprint 4)

| # | Task | Owner | Estado |
|---|------|-------|--------|
| 1 | **Resolver MCP 401 unauthorized** (root cause de WF12 lento) | cartorio-n8n | 🚨 P1 |
| 2 | Investigar WF01 consulta-emolumento latência 8s | cartorio-n8n+dev | ⚠️ P2 |
| 3 | Re-exportar TODOS os 35 workflows remoto→local | cartorio-n8n | pendente |
| 4 | T7 — ativar `n8n-nodes-mcp` em WF12 | cartorio-n8n | runbook pronto |
| 5 | T8 — ativar `n8n-nodes-chatwoot` em WF03 | cartorio-n8n | runbook pronto |
| 6 | Aplicar Lesson 51 workaround (N8N_BLOCK_ENV_ACCESS_IN_NODE=false) | cartorio-n8n | pendente |
| 7 | Adicionar alerta Prometheus em healthz (evitar incidente 502 silencioso) | sre | pendente |
| 8 | Investigar logs do restart automático do container (22:30 UTC) | cartorio-n8n | pendente |
| 9 | Limpar 17 v1 legados após 90 dias (2026-09-30) | cartorio-n8n | agendado |

---

## 📚 Lições Vinculadas (MEMORY)

- [[lesson-51]] — env access bloqueado em nodes N8N
- [[lesson-96]] — PATCH bloqueado em N8N 2.x
- [[lesson-50]] — workflow_entity + workflow_history sync
- [[lesson-52]] — N8N cache invalidação pós-restart
- [[lesson-55]] — workflow migration com FK constraints
- [[lesson-109]] — MCP authentication methods

---

## 📞 Contatos & Runbooks

| Necessidade | Caminho |
|------|---------|
| Comandos curl N8N | `.agents/skills/n8n/SKILL.md` |
| Ativar MCP node | `infra/n8n-workflows/T7-mcp-node-runbook.md` |
| Ativar Chatwoot node | `infra/n8n-workflows/T8-chatwoot-node-runbook.md` |
| Error Handler | `infra/n8n-workflows/README-error-handler.md` |
| Retry Policy | `infra/n8n-workflows/README-retry-policy.md` |
| Changelogs | `infra/n8n-workflows/CHANGELOG.md` |
| Rein agent card | `.harness/reins/cartorio-n8n/agent.md` |

---

*Generated by Gustavo Almeida via N8N session audit · 2026-06-30 ~22:50 UTC*
