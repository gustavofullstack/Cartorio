# Supabase — Documentação Consolidada

> **Fonte**: supabase.com/docs + nossa experiência operacional
> **DB Engine**: PostgreSQL 15+
> **URL**: https://supbase.2notasudi.com.br
> **Studio**: https://supbase.2notasudi.com.br:3000
> **Health**: GET /auth/v1/health → 200 OK

---

## 📊 Estado Atual (2026-06-25)

| Item | Valor |
|------|-------|
| **Tabelas** | 134 total |
| **Tabelas Core (Cartório)** | 13 |
| **RPCs custom** | 4 funções |
| **Cron Jobs** | 5 ativos |
| **Vault Entries** | 8 reais |
| **Webhooks DB** | 3 (outbox/protocolo/consent) |
| **Realtime canais** | 5 |
| **Alembic Head** | 2026_06_25_0014 |
| **RLS ativo** | clientes, protocolos, documentos, audit_log |

---

## 🗂️ Tabelas Core do Cartório (13)

| Tabela | Função | RLS |
|--------|--------|-----|
| `clientes` | Cadastro de clientes | ✅ |
| `conversas` | Histórico conversas WhatsApp/Telegram | — |
| `protocolos` | Protocolos de atendimento (LGPD) | ✅ |
| `documentos` | Documentos cartoriais | ✅ |
| `emolumentos` | Tabela de emolumentos MG 2026 | — |
| `atendimentos` | Registro de atendimentos | — |
| `agendamentos` | Agenda de atendimentos presenciais | — |
| `audit_log` | Audit trail completo (5 anos LGPD) | ✅ |
| `outbox_messages` | Outbox pattern (pg_notify) | — |
| `webhook_events` | Eventos recebidos de webhooks externos | — |
| `lgpd_consents` | Consentimentos LGPD | — |
| `lgpd_audit_anpd` | Audit trail ANPD (compliance) | — |
| `workflow_publication_outbox` | Outbox publicação N8N | — |

---

## 🔧 Recursos Supabase Ativados

| Recurso | Status | Uso |
|---------|--------|-----|
| **PostgREST** (`/rest/v1/*`) | ✅ Ativo | CRUD direto sem SQL |
| **Auth** (`/auth/v1/*`) | ✅ Ativo | JWT + magic link + OAuth |
| **Storage** (`/storage/v1/*`) | ✅ Disponível | PDFs segunda via |
| **Realtime** (`/realtime/v1/*`) | ✅ 5 canais | Notificações tempo real |
| **Edge Functions** (`/functions/v1/*`) | ✅ Disponível | Deno runtime |
| **pg_cron** | ✅ Ativado | 5 jobs ativos |
| **pg_net** | ✅ Ativado | HTTP requests do DB |
| **pg_vector** | ✅ Ativado | Busca semântica |
| **pg_graphql** | ⚠️ Subutilizado | Queries complexas |
| **pgmq (Queues)** | ⚠️ Subutilizado | Async processing |
| **Vault** | ✅ 8 entries | Secrets produção |
| **Database Webhooks** | ✅ 3 ativos | Outbox pattern |

---

## 🔐 Conexão da API

```python
# Via Tailscale (preferido)
DATABASE_URL="postgresql://postgres:ve07sqrhminnd3clslzv@cartorio_n8n-db:5432/cartorio?sslmode=disable"
SUPABASE_URL="https://supbase.2notasudi.com.br"
```

---

## 📡 Endpoints Supabase (via Kong Gateway)

```
/auth/v1/*        → Auth (JWTs, magic links, OAuth)
/rest/v1/*        → PostgREST (CRUD completo em todas as tabelas)
/storage/v1/*     → Storage (arquivos, PDFs, documentos)
/realtime/v1/*    → Realtime WebSocket (5 canais)
/functions/v1/*   → Edge Functions (Deno runtime)
```

---

## 🛠️ Funções Custom (4 ativos)

| Função | Descrição |
|--------|-----------|
| `fn_audit_chain_verify` | Verificação integridade audit_log |
| `fn_auto_audit` | Auto-inserção audit_log em mudanças |
| `fn_set_updated_at` | Trigger updated_at automático |
| `notify_outbox_new` | pg_notify no insert em outbox_messages |

**Trigger ativo**: `trg_outbox_new` em `outbox_messages`

---

## 📚 Migrações Alembic (16 no disco)

Cadeia cronológica:
```
0001 → initial schema
0002 → emolumentos table
0003 → pg_notify outbox trigger
0004 → lgpd tables
0005 → agendamentos
0006 → webhook_events
0007 → audit improvements
0008 → realtime channels
0009 → S01 merge base
0010 → S01 merge final
0011 → lgpd_consents rename + lgpd_audit_anpd
0012 → merge migration (resolve 2 heads: 0003+0010)
0013 → agendamento cache fields
0014 → client notification fields (A26)
```

---

## 🔒 RLS (Row Level Security)

Tabelas com RLS ativo:
```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND rowsecurity = true;

-- Resultado:
-- clientes ✅
-- protocolos ✅
-- documentos ✅
-- audit_log ✅
```

---

## ⚠️ Subutilizado (A Implementar)

| Recurso | Por que |
|---------|---------|
| **PostgREST API** | Estamos usando SQL direto na API Python |
| **GraphQL** | Para queries complexas com joins |
| **Queues (pgmq)** | Async processing ainda usa Redis |
| **Realtime mais amplo** | Só 5 canais; pode expandir |
| **Edge Functions** | Subutilizado |
| **Storage** | PDFs segunda via ainda local |

---

## 🔗 Links Úteis

| Recurso | URL |
|---------|-----|
| Docs oficial | https://supabase.com/docs |
| PostgREST | https://docs.postgrest.org/ |
| Auth | https://supabase.com/docs/guides/auth |
| Realtime | https://supabase.com/docs/guides/realtime |
| Storage | https://supabase.com/docs/guides/storage |
| Edge Functions | https://supabase.com/docs/guides/functions |
| Database | https://supabase.com/docs/guides/database |
| Cron jobs | https://supabase.com/docs/guides/cron |
| Vault | https://supabase.com/docs/guides/database/vault |
| MCP server | https://supabase.com/docs/guides/ai/mcp |

---

## 🎯 Squad S0 — Supabase Foundation DONE 100%

```
S01: Schema cartório completo (13 tabelas) ✅
S02: RLS em clientes, protocolos, documentos, audit_log ✅
S03: fn_auto_audit trigger ✅
S04: fn_audit_chain_verify função ✅
S05: fn_set_updated_at trigger ✅
S06: notify_outbox_new + trg_outbox_new ✅
S07: Alembic migration chain completa ✅
S08: Merge migration (0003+0010) ✅
S09: lgpd_consents + lgpd_audit_anpd ✅
S10: workflow_publication_outbox ✅
```

**Squad S0 é 10/10 DONE = 100%!**