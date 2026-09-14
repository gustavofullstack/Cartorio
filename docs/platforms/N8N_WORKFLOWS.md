# N8N Workflows — Cartório 2º Notas Uberlândia

> Inventário canônico dos workflows ativos no N8N de produção.
> Fonte da verdade: **`https://cartorio-n8n.dfgdxq.easypanel.host`** (instância Easypanel).
> Última sincronização: **2026-06-23 13:55 BRT** (export via API REST v1).
> Owner: `cartorio-n8n` rein.

---

## TL;DR

- **12 workflows ativos** (sem duplicatas).
- **4 credenciais** registradas no N8N (`opencode-go-deepseek`, `supabase-postgres`, `cartorio-api-bearer`, `evolution-api-cartorio`).
- **3 webhooks expostos** (`/webhook/consulta-emolumento`, `/webhook/criar-protocolo`, `/webhook/handoff-human`, `/webhook/boas-vindas`, `/webhook/consulta-protocolo`, `/webhook/agendamento`, `/webhook/segunda-via`).
- **5 cron jobs** rodando (Satisfação 24h, Audit Verify diário 03:30, Backup 04:00, Monitor Cartório 5min, Monitor Cartório webhook).
- **Latência alvo webhook→resposta: < 2s** (validar em staging antes de declarar prod-ready).

---

## Workflows por sprint

### Sprint 1 — MVP WhatsApp (E1.S1) ✅ DONE 2026-06-23

| # | ID N8N | Nome | Trigger | Nodes | Credenciais | LGPD gate |
|---|--------|------|---------|-------|-------------|-----------|
| 01 | `bR7qIo3bFpG4zgxO` | Consulta Emolumento WhatsApp (v2) | Webhook POST `/webhook/consulta-emolumento` | 4 | `cartorio-api-bearer` | PII scrub in-node + HITL escalation |
| 02 | `MzeYTSDouymzdpRw` | Criar Protocolo (LGPD) | Webhook POST `/webhook/criar-protocolo` | 6 | — | LGPD_BLOCKED sem consent, provisional c/ consent |
| 03 | `OQRIOVHcOjpkQ0Of` | Handoff Humano (Chatwoot) | Webhook POST `/webhook/handoff-human` | 4 | — | Inbox URL fallback (PENDÊNCIA SUI #3) |
| 04 | `sDtkfOJ5BA7M73wB` | Boas-Vindas + Consentimento LGPD | Webhook POST `/webhook/boas-vindas` | 5 | — | Texto jurídico defensável (art. 7º I + art. 8º §5º) |

### Sprint 1 bonus / Sprint 2 antecipado ✅ DONE 2026-06-23

| # | ID N8N | Nome | Trigger | Nodes | Credenciais | Notas |
|---|--------|------|---------|-------|-------------|-------|
| 04b | `iXWuZRYZLR3FYPYB` | Consulta Protocolo | Webhook POST `/webhook/consulta-protocolo` | 6 | — | GET `/api/v1/protocolo/{id}` |
| 05 | `UUW8ulDTxZUqBsci` | Agendamento Atendimento | Webhook POST `/webhook/agendamento` | 6 | — | Parse dia/hora + GET `/disponibilidade` |
| 06 | `ukbRUEudoX3SvsqD` | Segunda Via Documento | Webhook POST `/webhook/segunda-via` | 6 | — | POST `/documento/segunda-via` (gera URL PDF 24h) |
| 07 | `D9XJmlJRXZ3lavoa` | Pesquisa Satisfação | Cron 24h | 3 | `evolution-api-cartorio` | instanceName=`cartorio-2notas` ✅ |
| 08 | `3rr2WFBCJZ16U4DH` | Audit Verify Diario | Cron 03:30 diário | 6 | — | `$env.CARTORIO_API_KEY` + `$env.CHATWOOT_BOT_TOKEN` |
| 09 | `pgtlDqGaMW1MGawt` | Monitor Backup Diario | Cron 04:00 diário | 4 | — | Alerta Chatwoot se backup falhou |
| 10 | `jZhgQbJQ5z7atYfK` | FAQ Bot | Webhook POST `/webhook/faq` | 3 | — | KB local, sem LLM (latência zero) |

### Monitoramento (Sprint 1.5) ✅ DONE 2026-06-23

| # | ID N8N | Nome | Trigger | Nodes | Credenciais | Notas |
|---|--------|------|---------|-------|-------------|-------|
| 11 | `5ABAZCQVRLd7AmM5` | Monitor Cartório | Cron 5min **+** Webhook POST `/webhook/monitor-cartorio` | 13 | — | Health check 6 serviços (api, evolution, openclaw, chatwoot, redis, supabase) + alerta Chatwoot se degradado |

> **Não confundir** com `infra/n8n-workflows/11_monitor_cartorio.js` — esse é o **script de health check** que pode ser chamado de fora do N8N via `node 11_monitor_cartorio.js`. O workflow N8N tem a mesma lógica mas roda dentro do N8N (com credential management + Alert via Chatwoot).

---

## Credenciais (estado em 2026-06-23 13:48 UTC)

| ID N8N | Tipo | Nome | Onde é usada |
|--------|------|------|--------------|
| `FU7E7QJF6YTV89kU` | `openAiApi` | `opencode-go-deepseek` | WF-NOVO-02 OpenCode-Go Router (Sprint 2, ainda não deployed) |
| `OWib5Hitym2Y6FkS` | `postgres` | `supabase-postgres` | ⚠️ Reservado — workflows NÃO acessam Postgres direto (per AGENTS.md). Mantida para uso do cartorio-dev em scripts internos. |
| `22Q8OUbeZ1bsGnlt` | `httpHeaderAuth` | `cartorio-api-bearer` | WF 01 (e qualquer HTTP Request ao backend `api.2notasudi.com.br`) |
| `adbzRn9sEZD7VZbs` | `evolutionApi` | `evolution-api-cartorio` | WF 07 (Pesquisa Satisfação) |

### Variáveis (workaround `$env`)

A instância N8N **NÃO tem licença para `feat:variables`** (verificado em 2026-06-23 13:50 via `GET /api/v1/variables` → 401 "license does not allow"). Workaround em uso:

- `$env.CARTORIO_API_KEY` — backend auth
- `$env.CHATWOOT_BOT_TOKEN` — Chatwoot agent bot token (PENDÊNCIA SUI #3)
- `$env.CHATWOOT_ACCOUNT_ID` (default `1`)
- `$env.CHATWOOT_INBOX_ID` (default `1`)
- `$env.CHATWOOT_BASE_URL` (default `https://chat.2notasudi.com.br`)
- `$env.CARTORIO_API_HEALTH_URL` (default `https://api.2notasudi.com.br/health`)
- `$env.EVOLUTION_HEALTH_URL`
- `$env.OPENCLAW_HEALTH_URL`
- `$env.CHATWOOT_HEALTH_URL`
- `$env.REDIS_HEALTH_URL`
- `$env.SUPABASE_HEALTH_URL`

**Upgrade de licença** (Gustavo comprar) é pré-requisito para migrar de `$env` para Variables workspace-level.

---

## Pendências (SUI — dependem de UI)

| # | Pendência | Owner | ETA | Impacto |
|---|-----------|-------|-----|---------|
| 1 | WF #07 cred Evolution — **RESOLVIDO** 2026-06-23 13:48 (já vinculada) | — | — | — |
| 2 | Chatwoot domínio custom + DNS (`chat.2notasudi.com.br`) | Gustavo UI | 10 min | WF #03 fallback URL só funciona com DNS público |
| 3 | Chatwoot Agent Bot + Inbox (super_admin password) | Gustavo UI | 30 min | WF #03 usa inbox URL fallback enquanto isso |
| 4 | Easypanel API key regerar (antiga 401) | Gustavo UI | 2 min | Operações via Easypanel API |
| 5 | DNS `supbase` → `supabase` (typo histórico) | Gustavo UI | 15 min | Cosmético |
| 6 | OpenClaw LLM key (OPENAI_API_KEY ou ANTHROPIC_API_KEY) | Gustavo UI | 2 min | OpenClaw serve só UI gateway, sem inference real |

Ver detalhes em `docs/PENDENCIAS_SUI_2026-06-23.md`.

---

## Arquitetura do fluxo (end-to-end)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  WhatsApp/Tg/Web│────▶│  Evolution API  │────▶│  OpenClaw GW    │
│  (cliente)      │     │  (webhook in)   │     │  (normaliza)    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
                                               ┌──────────────────┐
                                               │  N8N workflow    │
                                               │  (orquestra)     │
                                               └────────┬─────────┘
                                                        │
                          ┌─────────────────────────────┼─────────────────────────────┐
                          ▼                             ▼                             ▼
                ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
                │ Backend FastAPI  │         │  Evolution API   │         │   Chatwoot       │
                │ api.2notasudi.   │         │  sendText        │         │   (handoff)      │
                │ com.br           │         │  (resposta)      │         │                  │
                └────────┬─────────┘         └──────────────────┘         └──────────────────┘
                         │
                         ▼
                ┌──────────────────┐
                │  Supabase        │
                │  (audit_log      │
                │  append-only)    │
                └──────────────────┘
```

**Regra de ouro**: workflows N8N **NUNCA acessam Postgres/Supabase direto** (per `cartorio-n8n/AGENTS.md`). Toda operação passa pelo backend FastAPI para garantir append em `audit_log` + PII scrub + LGPD gate.

---

## Convenções

### Convenção de nomes
- `{NN} - {Nome descritivo}` — `01` a `11` na ordem cronológica de criação.
- ID N8N é gerado pelo servidor (não determinístico). Sempre referenciar por **nome + ID** em docs.

### Convenção de credenciais
- **NUNCA** hardcode secrets nos workflows. Sempre usar creds registradas no N8N ou `$env.*`.
- Auditoria feita em 2026-06-23 11:25 BRT (ver `SESSION_SUMMARY_2026-06-23.md`): 11/11 workflows LIMPOS.

### Convenção de triggers
- Webhooks públicos: `/webhook/<slug-kebab-case>` (lowercase, sem versão no path).
- Cron: horário em BRT, com comentário no node explicando o que faz.

### Convenção de export
- JSON exportado **diretamente** via `GET /api/v1/workflows/{id}`.
- Salvo em `infra/n8n-workflows/<NN>-<slug>.json`.
- Commit: `chore(n8n): re-export workflow <NN>` ou parte de PR maior.

---

## Como importar (idempotente)

```bash
# Importar workflow do repo para N8N
curl -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
     -H "Content-Type: application/json" \
     -d @infra/n8n-workflows/01-consulta-emolumento.json \
     "https://cartorio-n8n.dfgdxq.easypanel.host/api/v1/workflows"

# Ativar (id do workflow vem do retorno acima)
curl -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
     "https://cartorio-n8n.dfgdxq.easypanel.host/api/v1/workflows/{id}/activate"

# Re-export para repo (sync)
curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
     "https://cartorio-n8n.dfgdxq.easypanel.host/api/v1/workflows/{id}" \
     -o infra/n8n-workflows/<NN>-<slug>.json
```

Ver `infra/n8n-workflows/README.md` para detalhes.

---

## Métricas (KPI Sprint 1)

- **100 consultas/dia** (alvo)
- **0 erro de valor** (target: zero divergência entre API e resposta WhatsApp)
- **0 handoff humano** (target: tudo automatizado exceto casos LGPD bloqueados)

Dashboards:
- `/api/v1/health/radar` — health 6 serviços
- `/api/v1/health/backup` — backup status
- `/api/v1/audit/verify` — hash chain integrity

---

Modified by Gustavo Almeida · 2026-06-23 13:55 BRT