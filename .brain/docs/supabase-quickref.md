# Supabase Self-Hosted — Quick Reference

**Source**: https://supabase.com/docs
**Versao em uso**: self-hosted (14 containers, supbase.2notasudi.com.br)
**Atualizado**: 2026-06-25

## 1. Stack Supabase Self-Hosted (14 containers)

| Container | Funcao | Porta |
|---|---|---|
| `cartorio_supabase-db-1` | Postgres 15 + ext (pg_cron, pgsodium, pg_graphql) | 5432 |
| `cartorio_supabase-auth-1` | GoTrue (auth) | -- |
| `cartorio_supabase-rest-1` | PostgREST (REST API) | 3000 |
| `cartorio_supabase-storage-1` | Storage API | -- |
| `cartorio_supabase-realtime-1` | Realtime WebSocket | -- |
| `cartorio_supabase-kong-1` | API gateway | 8000 |
| `cartorio_supabase-studio-1` | Studio UI | 3000 |
| `cartorio_supabase-meta-1` | Metadata DB | -- |
| `cartorio_supabase-analytics-1` | Logflare analytics | -- |
| `cartorio_supabase-functions-1` | Edge Functions | -- |
| `cartorio_supabase-vector-1` | pgvector (embeddings) | -- |
| `cartorio_supabase-imgproxy-1` | Image processing | -- |
| `cartorio_supabase-supavisor-1` | Connection pooler | 6543 |
| `cartorio_supabase-mongo-1` (ou similar) | Migracoes | -- |

## 2. Conexao Direta Postgres

```bash
# Via container
docker exec cartorio_supabase-db-1 psql -U supabase_admin -h 127.0.0.1

# Via DATABASE_URL do backend
DATABASE_URL="postgresql+psycopg://supabase_admin:e999b7439deb35dfe05c33f265dae1ea@db:5432/cartorio?sslmode=disable"
```

## 3. PostgREST (REST API)

```bash
SUPABASE_URL="https://supbase.2notasudi.com.br"
ANON_KEY="eyJhbGc..."  # default imagem Docker

# Listar tabelas (schema public)
curl $SUPABASE_URL/rest/v1/ -H "apikey: $ANON_KEY" | jq

# Query tabela
curl "$SUPABASE_URL/rest/v1/protocolos?select=id,numero,status" \
  -H "apikey: $ANON_KEY" \
  -H "Authorization: Bearer $ANON_KEY"

# Insert
curl -X POST "$SUPABASE_URL/rest/v1/clientes" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"nome": "Joao", "cpf": "123.456.789-09"}'
```

## 4. GraphQL (pg_graphql)

```bash
# Endpoint: /graphql/v1
curl -X POST $SUPABASE_URL/graphql/v1 \
  -H "apikey: $ANON_KEY" \
  -H "Authorization: Bearer $ANON_KEY" \
  -d '{"query": "{ protocolos { id numero status } }"}'
```

## 5. Realtime WebSocket

```bash
# Endpoint: /realtime/v1/websocket
# Schema: postgrest
# Tables com publication: protocolos, atendimentos, lgpd_consents (S0 S07)
```

Cliente JS:
```javascript
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(SUPABASE_URL, ANON_KEY)
const channel = supabase.channel('protocolo_updates')
  .on('postgres_changes',
      { event: '*', schema: 'public', table: 'protocolos' },
      (payload) => console.log(payload))
  .subscribe()
```

## 6. Storage

```bash
# Upload arquivo
curl -X POST "$SUPABASE_URL/storage/v1/object/cliente-docs/joao/rg.pdf" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" \
  -H "Content-Type: application/pdf" \
  --data-binary @/tmp/rg.pdf

# Download
curl "$SUPABASE_URL/storage/v1/object/cliente-docs/joao/rg.pdf" \
  -H "apikey: $SERVICE_KEY" -o rg.pdf

# Signed URL (1h)
curl -X POST "$SUPABASE_URL/storage/v1/object/sign/cliente-docs/joao/rg.pdf" \
  -H "apikey: $SERVICE_KEY" \
  -d '{"expiresIn": 3600}'
```

Buckets (S0 S06):
- cliente-docs (PRIVATE, 50MB, pdf/jpeg/png)
- protocolo-pdfs (PRIVATE, 100MB, pdf)
- satisfacao-forms (PUBLIC READ, 5MB, json)

## 7. RLS Policies (S0 S02)

```sql
-- service_role: acesso total
CREATE POLICY service_role_full_access ON clientes
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- dpo: SELECT em PII + audit
CREATE POLICY dpo_read_access ON clientes
  FOR SELECT TO dpo USING (true);

-- authenticated: SELECT na propria linha
CREATE POLICY authenticated_read_own ON clientes
  FOR SELECT TO authenticated
  USING (cliente_id::text = auth.uid()::text OR cliente_id IS NULL);
```

## 8. Vault Secrets (S0 S08)

```sql
-- Listar secrets (service_role only)
SELECT name, decrypted_secret FROM vault.decrypted_secrets;

-- Criar
SELECT vault.create_secret('valor', 'nome', 'descricao');

-- Helper fail-loud
SELECT vault_get_or_create('cartorio_api_key');  -- retorna 'AWAITING_OPERATOR' se nao existir
```

## 9. pg_cron (S0 S03)

```sql
-- Listar jobs
SELECT * FROM cron.job;

-- 4 jobs ativos (S0 S03):
-- - audit_verify_diario  (06:00 UTC = 03:00 BRT)
-- - dlq_retry_5min         (a cada 5 min)
-- - cache_warm_06h         (09:00 UTC = 06:00 BRT)
-- - snapshot_diario_2355   (02:55 UTC = 23:55 BRT)
```

## 10. Database Webhooks (S0 S04)

```sql
-- Tabela: supabase_functions.hooks
SELECT * FROM supabase_functions.hooks;

-- Hook ativo (S0 S04):
-- - outbox_to_api: INSERT em outbox_messages -> POST /api/v1/integrations/outbox/process
```

## 11. Gotchas

- ANON_KEY + SERVICE_ROLE_KEY da imagem Docker Supabase (NAO rotacionar, sao defaults)
- Schema public NAO e auto-criado (precisa migration Alembic)
- Realtime precisa publication supabase_realtime com tabelas
- RLS policies aplicam em REST + GraphQL + Realtime
- Storage URLs assinadas expiram (default 1h)

## 12. Backup

```bash
# Backup diario 4x/dia (A14)
docker exec cartorio_supabase-db-1 pg_basebackup \
  -D /var/backups/postgres/$(date +%Y%m%d-%H%M) \
  -Ft -z -P
```

Modified by Pietra + Gustavo Almeida 2026-06-25
