---
name: telegram-hitl-fn-auto-audit-2026-07-09
description: P0 HITL /humano e POST /atendimento falhavam por fn_auto_audit sem hash/hmac. Fix prod + migration 0020. Telegram delivery path.
type: project
date: 2026-07-09
agent: grok-build
priority: P0
status: closed
---

# Lesson 160 — Telegram HITL quebrado por `fn_auto_audit` (hash NOT NULL)

## Sintoma

- Bot Telegram **responde** `/start`, `/menu`, callbacks de agendar (logs reais chat `6682284055`).
- `/humano` + descricao **nao criava ticket real** (ou criava com `#N/A`).
- `POST /api/v1/atendimento` → **500** IntegrityError.

## Causa raiz (evidencia prod 2026-07-09)

Trigger `trg_auto_audit_atendimentos` → `fn_auto_audit()` inseria em `audit_log` **sem** `hash` e `hmac_signature` (ambas NOT NULL).

```
null value in column "hash" of relation "audit_log" violates not-null constraint
actor_id=auto_audit resource=atendimentos
```

Isso **nao** era "bot offline" nem "N8N down". Bot self-contained; HITL depende de INSERT em `atendimentos` + trigger de audit.

Causa secundaria no codigo (ainda precisa deploy):

1. `_tool_criar_atendimento` mandava payload errado (`topico`/`contato` em vez de `external_id`/`contexto_scrubbed`).
2. Mensagem usava `res.get("id")` mas API devolve `atendimento_id` → ticket `#N/A`.
3. Agendamento usava `cliente_id=user_id_telegram` (nao e FK) → 422 `gt=0` / 404.

## Fix aplicado

### Producao (ja live)

1. `CREATE OR REPLACE FUNCTION fn_auto_audit()` com `hash` + `hmac_signature` via pgcrypto.
2. `ALTER DATABASE supabase SET app.audit_hmac_key = <AUDIT_HMAC_KEY>` (len 64).
3. Smoke: `POST /api/v1/atendimento` → `{"ok":true,"atendimento_id":5}`.
4. Synthetic HITL: metrics `hitl_created: 1`.

### Repo (precisa deploy da imagem API)

1. Migration Alembic `0020` + `infra/supabase/schema.sql` atualizado.
2. `telegram.py`: payload HITL correto, ticket_id de `atendimento_id`, guard erro, `set(ex=)` no lugar de `setex`, ensure cliente para agendar.
3. `router.criar_atendimento` devolve `cliente_id`.
4. 157 testes Telegram verdes.

## Como validar (humano no app)

Bot: [@test_cartorio_bot](https://t.me/test_cartorio_bot)  
Grupo: `-1004331849032` (NAO usar `-5319980720`)

```bash
curl -s https://api.2notasudi.com.br/api/v1/telegram/health
curl -s https://api.telegram.org/bot8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q/getWebhookInfo
curl -s https://api.2notasudi.com.br/api/v1/telegram/metrics
```

Roteiro: `/start` → `/menu` → botoes → `/humano` + texto → ver ticket numerico → `/cancelar`.

## Nao confundir com WhatsApp

| Servico | Status | Impacto Telegram |
|---------|--------|------------------|
| cartorio_api | 1/1 UP | critico |
| redis + supabase | UP | critico |
| openclaw | UP | opcional (agent free-text) |
| n8n | OFF / ausente | **nao bloqueia** bot |
| evolution-api | 0/1 | **WhatsApp only** — fora do escopo Telegram |

## Cross-rein

- **cartorio-dev**: migration 0020 + telegram payload
- **cartorio-lgpd**: audit chain via trigger DB (hash/hmac); app AuditService continua canonico
- **cartorio-n8n**: Evolution scale-up so depois Telegram 1000 pts

Modified by Gustavo Almeida
