---
name: supabase
description: |
  Skill para interagir com Supabase auto-hospedado via REST, Auth, Storage, Realtime e Edge Functions.
  Use quando precisar: CRUD em tabelas, autenticação JWT, upload de arquivos,
  realtime channels, edge functions, cron jobs, vault entries e database webhooks.
  URL: https://supbase.2notasudi.com.br | 134 tabelas | Alembic head: 0015
---

# Supabase — Skill de Integração Completa

## Acesso

| Item | Valor |
|------|-------|
| **URL Base** | `https://supbase.2notasudi.com.br` |
| **Studio** | `https://supbase.2notasudi.com.br:3000` |
| **ANON Key** | Ver `backend/.env` SUPABASE_ANON_KEY |
| **Service Role Key** | Ver `backend/.env` SUPABASE_SERVICE_ROLE_KEY |
| **DB Direto** | `postgresql+psycopg://supabase_admin:e999b7...@db:5432/cartorio` |
| **Alembic Head** | `0015` |
| **Tabelas Total** | 134 (public schema) |
| **Tabelas Core** | 13 tabelas aplicativas do Cartório |

## Endpoints via Kong Gateway

```
/auth/v1/*        → Auth (JWT, OTP, OAuth, magic links)
/rest/v1/*        → PostgREST (CRUD automático em TODAS as tabelas)
/storage/v1/*     → Storage (arquivos, PDFs, documentos)
/realtime/v1/*    → WebSocket Realtime (5 canais)
/functions/v1/*   → Edge Functions (Deno runtime)
/graphql/v1       → GraphQL (pg_graphql)
```

## 13 Tabelas Core do Cartório

| Tabela | Descrição |
|--------|-----------|
| `clientes` | Dados dos clientes (CPF hasheado) |
| `conversas` | Histórico de conversas WhatsApp/Telegram |
| `protocolos` | Protocolos de atendimento |
| `documentos` | Documentos e segunda via |
| `agendamentos` | Agendamentos presenciais |
| `audit_log` | Log de auditoria (SHA256 chain, LGPD) |
| `lgpd_consents` | Consentimentos LGPD |
| `lgpd_audit_anpd` | Auditoria para ANPD |
| `emolumentos` | Tabela de emolumentos MG 2026 |
| `sessoes_chat` | Sessões de chat ativas |
| `chatwoot_conversation_meta` | Metadados Chatwoot |
| `telegram_chat_meta` | Metadados Telegram |
| `atendimentos` | Registro de atendimentos |

## PostgREST (CRUD via REST)

```bash
# SELECT com filtros
curl -H "apikey: $ANON_KEY" \
  -H "Authorization: Bearer $ANON_KEY" \
  "https://supbase.2notasudi.com.br/rest/v1/clientes?select=id,nome&limit=10"

# INSERT
curl -X POST \
  -H "apikey: $SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '{"nome": "João Silva", "cpf_hash": "abc123"}' \
  "https://supbase.2notasudi.com.br/rest/v1/clientes"

# RPC (função PostgreSQL)
curl -X POST \
  -H "apikey: $SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tipo": "certidao_casamento"}' \
  "https://supbase.2notasudi.com.br/rest/v1/rpc/get_emolumento_valor"
```

## Auth (JWT)

```bash
# Sign up (criar usuário)
curl -X POST \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@2notasudi.com.br", "password": "securepass"}' \
  "https://supbase.2notasudi.com.br/auth/v1/signup"

# Sign in
curl -X POST \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@2notasudi.com.br", "password": "securepass"}' \
  "https://supbase.2notasudi.com.br/auth/v1/token?grant_type=password"
```

## Storage

```bash
# Upload de documento
curl -X POST \
  -H "apikey: $SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SERVICE_ROLE_KEY" \
  -H "Content-Type: application/pdf" \
  --data-binary @documento.pdf \
  "https://supbase.2notasudi.com.br/storage/v1/object/documentos/protocolos/2026/001.pdf"

# URL pública
"https://supbase.2notasudi.com.br/storage/v1/object/public/documentos/protocolos/2026/001.pdf"
```

## RLS (Row Level Security)

Ativo nas tabelas:
- `clientes` — usuário vê apenas seus dados
- `protocolos` — acesso por account_id
- `documentos` — acesso por protocolo_id
- `audit_log` — read-only via service_role

## Recursos Habilitados

| Recurso | Status |
|---------|--------|
| pg_vector | ✅ Ativo — busca semântica |
| pg_cron (via schema) | ✅ Ativo |
| pg_net | ✅ Ativo — HTTP do DB |
| pgmq | ✅ Ativo — filas |
| Vault | ✅ 8 entries |
| Realtime | ✅ 5 canais |
| GraphQL | ✅ pg_graphql |
| Edge Functions | ✅ Deno runtime |

## Acesso Direto ao DB (psql via SSH)

```bash
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84
DB_ID=$(docker ps --format '{{.ID}} {{.Names}}' | grep 'supabase-db' | awk '{print $1}')
docker exec $DB_ID psql -U supabase_admin -d cartorio
```

## Integração Python

```python
from app.integrations.supabase_client import supabase_rest, supabase_storage, supabase_health

# Health check
ok = await supabase_health()

# SELECT
clientes = await supabase_rest.select("clientes", limit=10)

# INSERT
novo = await supabase_rest.insert("protocolos", {"numero": "2026-001", "status": "aberto"})

# RPC
emolumento = await supabase_rest.rpc("get_emolumento_valor", {"tipo": "certidao_casamento"})

# Upload
await supabase_storage.upload("documentos", "test.pdf", pdf_bytes, "application/pdf")
```

## Variáveis de Ambiente

```env
SUPABASE_URL=https://supbase.2notasudi.com.br
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_DB_URL=postgresql+psycopg://supabase_admin:...@db:5432/cartorio
```
