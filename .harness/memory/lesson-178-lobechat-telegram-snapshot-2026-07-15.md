---
id: lesson-178
title: LobeChat + Telegram snapshot F4 [P1] RETRY (2026-07-15 14:45 BRT)
date: 2026-07-15
type: project + reference
scope: cartorio-evolution
task: F4 [P1] RETRY / T041-T048
---

# Lesson 178 — LobeChat + Telegram snapshot F4 [P1] RETRY (2026-07-15)

## Contexto

Em 2026-07-15 14:45 BRT a missão F4 [P1] RETRY do sub-agent `cartorio-evolution` foi executada com escopo **APENAS documentação + templates** (sem alterar backend Python, sem criar testes pytest novos, sem rodar SSH no VPS). O gatilho: (a) LobeChat UP (1/1) mas env `OPENAI_API_KEY=sk-xxxx` placeholder; (b) Telegram bot @TestCartorioBot MORTO (token revogado por Gustavo em 2026-07-XX); (c) F4 SRE já entregou DNS runbook + commit `d0332da`.

A missão foi executada sobre um repo onde Lesson 170 já tinha criado a base `infra/lobechat/{STATUS,README,SETUP}.md` + `agent_cartorio_import.json` em 2026-07-14. F4 RETRY enriqueceu essa base + adicionou monitor Telegram + catalogou 6 endpoints Telegram no `catalog.py` (F3 adicionou 9 OpenClaw, F4 RETRY adiciona 6 Telegram → total 73 endpoints).

**Cross-refs principais**:
- Lesson 170 (`lesson-170-lobechat-agent-fix-2026-07-14.md`) — root cause + fix CORS/timeout OpenClaw (commit 9b9c9e4)
- Lesson 177 (`lesson-177-openclaw-e8-finalize-2026-07-14.md`) — OpenClaw E8 catalog (218 methods + 30 events)
- Lesson 179 (`lesson-179-dns-cloudflare-fixos-2026-07-15.md`) — F4 SRE DNS runbook (3 A records NXDOMAIN)
- Lesson 176 (`lesson-176-sre-incident-2026-07-14-502-recovery.md`) — F2 [P0] 502 recovery
- Lessons 160/161/162 — Telegram HITL + memory + PII (F1 batch)

---

## Estado AGORA (snapshot 14:45 BRT)

### LobeChat (`infra/lobechat/STATUS.md`)

| Item | Status | Evidência |
|------|--------|-----------|
| Container | UP (1/1) | EasyPanel dashboard (F4 SRE validou) |
| Imagem | `lobehub/lobe-chat` v1.143+ | docker inspect |
| Health | 200 OK em `/api/health` | curl interno |
| URL funcional | `cartorio-lobechat.dfgdxq.easypanel.host` | EasyPanel wildcard |
| URL branded | `lobe.2notasudi.com.br` | **PENDING** (DNS + Traefik) |
| `OPENAI_API_KEY` | `sk-xxxx` placeholder | env EasyPanel |
| `OPENAI_PROXY_URL` | vazio | env EasyPanel |
| CORS OpenClaw | já configurado `.2notasudi.com.br` | Lesson 170 fix |
| Agent "Cartório 2º Notas" | JSON pronto | `infra/lobechat/agent_cartorio_import.json` |

### Telegram (`docs/platforms/TELEGRAM_BOT.md`)

| Item | Status | Evidência |
|------|--------|-----------|
| Bot handle | `@TestCartorioBot` | BotFather |
| Bot token | **REVOGADO** | Gustavo (2026-07-XX) |
| Webhook URL | `https://api.2notasudi.com.br/api/v1/telegram/webhook` | backend UP |
| Endpoint health | 200 OK em `/api/v1/telegram/health` | curl |
| PII scrubbing | 3 camadas ativas (input/pre-LLM/output) | `app/services/pii.py` |
| Debounce 3s | ativo | `telegram.py:64 DEBOUNCE_WINDOW=1.2s` |
| Rate limit | sliding 60/min + 3-tier API key | `rate_limit*.py` |
| Webhook secret | configurado em prod | `TELEGRAM_WEBHOOK_SECRET` |
| Alertas Telegram | `TELEGRAM_CHAT_ID_DPO=6682284055` | `.secrets/telegram.env` |

---

## Gap list (ações pendentes)

### LobeChat (4 ações Gustavo)

1. **DNS**: decidir `lobe.2notasudi.com.br` vs `lobechat.2notasudi.com.br`. Criar A record no Cloudflare → `187.77.236.77` proxy DNS only. Runbook UI 5min em `infra/dns/CLOUDFLARE_RUNBOOK.md` (F4 SRE Lesson 179).
2. **Traefik router**: commitar `infra/traefik/dynamic/lobe.yml` (template em `infra/lobechat/README.md` seção "Expor DNS público").
3. **OpenClaw operator token**: gerar novo token com scopes `chat:write,models:read` (Lesson 177 descobriu que token atual tem `hello-ok.auth.scopes=[]` = health-only). Atualizar env EasyPanel: `OPENAI_API_KEY` + `OPENAI_PROXY_URL=https://agent.2notasudi.com.br/v1` + `OPENAI_MODEL_LIST=openclaw,openclaw/default,openclaw/main`. Restart container.
4. **Import agente via UI**: seguir `infra/lobechat/SETUP.md` (5 cliques). Validar smoke `oi → saudação cartorária`.

### Telegram (3 ações Gustavo)

1. **Regenerar token**: abrir @BotFather → `/revoke` → `/token` para @TestCartorioBot. Salvar em password manager (1Password / Bitwarden).
2. **Atualizar `.secrets/telegram.env` real** (não commitar): `TELEGRAM_BOT_TOKEN_TEST_CARTORIO=<novo-token>`. Manter `TELEGRAM_WEBHOOK_SECRET` (já está bom).
3. **Re-registrar webhook**: `curl https://api.telegram.org/bot<NEW_TOKEN>/setWebhook?url=https://api.2notasudi.com.br/api/v1/telegram/webhook&secret_token=<SECRET>&drop_pending_updates=true`. Validar com `getWebhookInfo` → `pending_update_count=0`.

---

## Entregas (8 artefatos)

| Arquivo | LOC | Tipo | Status |
|---------|-----|------|--------|
| `infra/lobechat/STATUS.md` | ~125 | doc | atualizado F4 RETRY 14:45 BRT |
| `infra/lobechat/README.md` | ~217 | doc | enriquecido (3 passos + Traefik YAML + checklist) |
| `infra/lobechat/monitors.json` | ~95 | template | 3 monitores (LobeChat + Telegram + OpenClaw) |
| `infra/lobechat/SETUP.md` | (existente) | doc | mantido da Lesson 170 |
| `.secrets/telegram.env.example` | ~66 | template | cross-ref Lesson 178 adicionado |
| `docs/platforms/TELEGRAM_BOT.md` | ~340 | doc | índice + monitor + cross-ref Lesson 178 |
| `.brain/api-specs/catalog.py` | +6 endpoints | catalog | total 67 → 73 |
| `.harness/memory/lesson-178-lobechat-telegram-snapshot-2026-07-15.md` | esta lesson | memory | cross-rein |

---

## Padrões confirmados (cross-project)

### 1. UI configuration gaps são invisíveis a agents de código

Lesson 170 já documentou que **LobeChat nunca foi configurado com Custom OpenAI provider** — gap que 5 rounds de YOLO code lens não pegaram. F4 RETRY reforça: **TODO ciclo YOLO deve incluir 1 lens manual UI** (LobeChat agents, Cloudflare DNS, BotFather tokens, SUI1-3).

**Pattern**: produtos que requerem configuração humana via UI não podem ser "deploy-only-via-code". Toda delegação precisa ter 1 entregável de **runbook + checklist HOLD-GUSTAVO**.

### 2. Snapshot temporal é obrigatório quando state é HOLD-GUSTAVO

Toda missão que termina com state HOLD-GUSTAVO deve deixar:
- `STATUS.md` com snapshot timestamp (14:45 BRT)
- `monitors.json` com `current_status` + `current_status_reason`
- Cross-ref lessons (160/161/162/170 para Telegram; 170/177 para LobeChat; 179 para DNS)
- `lesson-NNN-...md` em `.harness/memory/` (cross-rein lesson)

**Pattern**: HOLD-GUSTAVO ≠ DONE. Sempre deixar trilho auditável.

### 3. Telegram parse_mode=HTML é armadilha (NÃO ESQUECER)

Lesson 152 + AGENTS.md: `parse_mode=HTML` quebra silenciosamente quando LLM output contém tags `<think>`/`<reasoning>` (502). **Default seguro**: `MarkdownV2` ou vazio (texto puro).

`.secrets/telegram.env.example` linha 22-26 documenta:
```
# Parse mode default. NAO usar HTML — tags <think>/<reasoning>
# do LLM quebram o parser e causam 502 silencioso.
TELEGRAM_DEFAULT_PARSE_MODE=MarkdownV2
```

### 4. Monitor Uptime Kuma com `current_status_reason`

Quando um monitor está DOWN por causa conhecida (token revogado, manutenção planejada), o JSON deve ter campo `current_status_reason` para evitar alerta falso. **Pattern**: dashboard Uptime Kuma mostra `current_status` (DOWN_5XX) mas silencioso enquanto reason for conhecida.

### 5. Catalog.py incrementa incrementalmente entre F-squads

F1 (saúde) catalogou 50 endpoints v1. F3 (OpenClaw E8) adicionou 9 OpenClaw → 67. F4 RETRY adiciona 6 Telegram → 73. **Pattern**: cada F-squad adiciona ~5-10 endpoints novos por missão, mantendo `get_stats()` atualizado. Fácil track via `git diff --stat .brain/api-specs/catalog.py`.

---

## Estatísticas finais (2026-07-15 14:45 BRT)

```
.brain/api-specs/catalog.py stats:
  total: 73 (era 67 antes F4 RETRY)
  v1: 60 (era 54 — +6 Telegram)
  v2: 4 (alpha)
  oc (OpenClaw): 9
  lgpd_scope: 37
  auth_required: 56
  stable: 65
  alpha: 6 (4 v2 + 1 oc + 1 telegram-admin)
```

**Cross-rein lesson inventory (2026-07-15)**:
- 142 lessons indexadas em `.harness/memory/` (144-179 + archives)
- 4 novas em 2026-07-15: 174 (super-plano), 176 (SRE 502), 177 (OpenClaw E8), 179 (DNS) + **178 (esta)**
- F4 RETRY completa: T041-T048 (8 tasks) → 1 commit `feat(evo)` + 7 artefatos

---

## Próximos passos (cross-rein)

- **cartorio-sre (F4 [P0])**: merge dos 3 Traefik routers pendentes (`chatwoot`, `n8n`, `supabase`) após Gustavo criar A records no Cloudflare. Lesson 179.
- **cartorio-dev (F5)**: implementar health check estruturado em `app/api/v1/telegram.py:health()` (hoje retorna 200 simples; pode adicionar `{token_status: revogado|valido, last_webhook_call: ts, queue_size: int}`).
- **cartorio-n8n (F4 [P2])**: workflow N8N `31-telegram-listener.json` precisa atualizar — listener está usando token revogado. Reativar após Gustavo regenerar.
- **cartorio-lgpd**: revisar `.secrets/telegram.env.example` + `infra/lobechat/` para confirmar PII scrubbing mantido em LobeChat (importante: LobeChat logs podem vazar PII se não tiver scrubbing).

---

## Modified by Gustavo Almeida — 2026-07-15 14:45 BRT — F4 [P1] RETRY