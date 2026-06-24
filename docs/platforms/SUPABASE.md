# Supabase — Cartório 2º Ofício

> **Backend-as-a-Service** (Postgres + Auth + Storage + Realtime + Edge).
> Self-hosted (LGPD). 14 containers. DB: `cartorio`.

## Status atual (2026-06-24)

| Campo | Valor |
|---|---|
| Containers | 14 (Kong, Studio, DB, Auth, Storage, Realtime, Functions, etc) |
| Up time | 23h (todos healthy) |
| URL pública | `https://supbase.2notasudi.com.br` (typo histórico) |
| URL EasyPanel | `https://cartorio-supabase.dfgdxq.easypanel.host` |
| Kong | `:8000` → 401 (esperado, sem JWT) |
| Studio | `:3000` → 307 (auth redirect) |
| DB | `cartorio` (Postgres 15) |
| DB tabelas | 133 (121 antigas + 11 Sprint 3 + 1 metadata) |
| RPCs | 3 (criar_protocolo, opt_out_global, registrar_auditoria) |
| Extensões DB `postgres` | 5 (pg_cron, pg_net, pgmq, pg_graphql, supabase_vault) |
| Versão cliente | supabase-py 2.x |
| Pendência | pg_cron jobs + vault secrets no DB cartorio + DNS público |

## Endpoints consumidos

| Método | Path | Auth | Descrição |
|---|---|---|---|
| GET | `:8000/` | none | Kong root (401 esperado) |
| POST | `:8000/rest/v1/{table}` | bearer JWT/service_role | PostgREST CRUD |
| POST | `:8000/auth/v1/token` | anon | Login (signInWithPassword) |
| POST | `:8000/realtime/v1/*` | bearer | WebSocket subscriptions |
| POST | `:8000/storage/v1/object/*` | bearer | Upload/download |
| POST | `:8000/functions/v1/*` | bearer | Edge functions (Deno) |
| POST | `:8000/rpc/{fn_name}` | bearer | Chama RPC (Postgres function) |

**Auth**: JWT user (anon + authenticated) ou `service_role` key (backend bypassa RLS).

## Integrações ativas

- **API FastAPI** → service_role key para CRUD (bypassa RLS)
- **N8N** → credential Supabase API (host + service_role) para nodes nativos
- **OpenClaw** → tool `supabase` (queries RLS) + tool `audit-log` (RPC `registrar_auditoria`)
- **Redis** → NÃO integra direto; outbox dispatch usa Redis Streams (Squad I06)
- **Chatwoot** → NÃO integra direto (independente)
- **Evolution** → NÃO integra direto (webhook vai pra N8N → API → Supabase)

## Tabelas / Schemas / Workflows

- **133 tabelas** no schema `public`:
  - 121 antigas (Sprint 0-2: atendimentos, clientes, emolumentos, sessoes_chat, agendamentos, etc)
  - 11 novas Sprint 3 (`webhook_event`, `outbox_messages`, `conversa`, `atendimento_link`, `cpf_cnpj_validator`, `lgpd_consent_log`, `opt_out_log`, `evolution_instance`, `n8n_run_log`, `chatwoot_conversation_meta`, `telegram_chat_meta`)
  - 1 metadata (`alembic_version = 2026_06_24_0001`)
- **3 RPCs** criadas: `criar_protocolo`, `opt_out_global`, `registrar_auditoria`
- **5 extensões** habilitadas no DB `postgres` (NÃO no `cartorio`): pg_cron, pg_net, pgmq, pg_graphql, supabase_vault
- **Migration file**: `infra/supabase/migrations/2026_06_24_0001-supabase-real-rollout.sql`

## Problemas conhecidos + fixes aplicados

- **Dockerfile NÃO copia `alembic/`** → prod usa `Base.metadata.create_all()` no lifespan, NÃO Alembic
- **Model `outbox_messages` faltava** → fix `aab3774` (registrado em `models/__init__.py`)
- **N8N criou tabelas próprias no DB cartorio** → poluição schema public (separar DB no futuro)
- **`cpf_cnpj_validator.py` é só util** (NÃO model SQLAlchemy) → mover pra Sprint 4
- **Tabelas sem model** (`emolumentos`, `sessoes_chat`, `agendamentos`) → Sprint 0 antigo, ainda válido
- **pg_cron jobs pendentes** (stale_detector 5min, retention 03:00, audit_verify 6h, dlq 10min, outbox 1min) → Squad A05
- **Vault secrets pendentes** (7: EVOLUTION/CHATWOOT/N8N/OPENCLAW/OPENCODE-GO/RENDER/JULES) → Squad A07
- **DNS `supabase.2notasudi.com.br` não resolve** → criar A record Cloudflare (Squad J01)

## Próximas tasks (Squad A do plan 2026-06-24)

- **A01** Listar tabelas reais (done)
- **A02** Versionar schema SQL em `infra/supabase/migrations/` (done)
- **A03** Criar tabelas faltantes (done 11/11)
- **A04** Criar RPCs: criar_protocolo, calcular_emolumento, registrar_auditoria, opt_out_global, lgpd_direito_<X> (3/5 done)
- **A05** Ativar pg_cron: stale_detector 5min, retention 03:00, audit_verify 6h, dlq_refresh 10min, outbox_flush 1min
- **A06** Ativar Database Webhooks: outbox→dispatch, protocolo→n8n
- **A07** Vault: 7 secrets + migrar consumers
- **A08** Ativar pg_graphql e documentar schema
- **A09** Realtime channels: atendimento, conversa, lgpd_consent
- **A10** Backup automatizado: snapshot diário + WAL + restore drill

Ver plano completo: `.harness/reins/cartorio-dev/tasks/2026-06-24-plan.json` (Squad A).

---

# Supabase - Quick Reference (Python)

> **8 comandos prioritarios + RLS + service_role vs anon.**
> Versao: supabase-py 2.x (2026-06-24)
> Base URL prod: `https://supbase.2notasudi.com.br` (typo intencional historico)
> Doc oficial: https://supabase.com/docs/reference/python

## Visao geral

Supabase e' uma plataforma **Backend-as-a-Service** que combina Postgres + Auth + Storage + Realtime + Edge Functions. Oferece cliente Python (`supabase-py`) e PostgREST (REST automatico a partir do schema).

**Por que usamos**: BaaS completo (Auth, DB, Storage), self-hosted (LGPD), PostgREST evita ORM, RLS para seguranca, cliente Python oficial.

## Init (executar 1x no backend FastAPI)

```python
from supabase import create_client

SUPABASE_URL = "https://supbase.2notasudi.com.br"
SUPABASE_KEY = "service_role_key"  # backend usa service_role (bypassa RLS)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
```

**Auth automatico**: SDK injeta `Authorization: Bearer <jwt>` em todas chamadas.

## 8 Comandos prioritarios (Cartorio usa esses)

### 1. auth.sign_in_with_password

Login de usuario (atendente, escrevente, DPO).

```python
response = supabase.auth.sign_in_with_password({
    "email": "escrevente@cartorio.com",
    "password": "senha_secreta"
})
session = response.session
user = response.user
# session.access_token: JWT 1h
# session.refresh_token: para renovar
# user.id: UUID do usuario
```

**Cartorio**: login do atendente; guardar `access_token` em cookie httpOnly.

### 2. auth.sign_up

Cadastro de usuario interno.

```python
response = supabase.auth.sign_up({
    "email": "novo@cartorio.com",
    "password": "senha_temporaria",
    "options": {
        "data": {
            "full_name": "Joao da Silva",
            "role": "escrevente"
        }
    }
})
user = response.user
# user.id: UUID
# role salvo em user_metadata (nao em user.role!)
```

**Cartorio**: cadastrar usuarios internos (atendentes, oficiais) com role em `user_metadata`.

### 3. auth.get_user

Usuario atual (do JWT).

```python
# Com token explicito
user = supabase.auth.get_user(jwt_token)

# Ou da sessao atual
user = supabase.auth.get_user()
# user.email, user.id, user.user_metadata
```

**Cartorio**: middleware FastAPI decodifica JWT do cookie e popula `request.state.user`.

### 4. table('clientes').select('*').eq('cpf', '123').execute()

Query com filtros PostgREST.

```python
response = supabase.table('clientes').select('*').eq('cpf', '12345678900').execute()
clientes = response.data  # lista de dicts

# Filtros disponiveis:
# .eq(col, val), .in_(col, [vals]), .gte(col, val), .lte(col, val)
# .like(col, '%padrao%'), .or_('col1.eq.val,col2.eq.val')
# .order(col, desc=True), .limit(10), .range(0, 9)
```

**Cartorio**: buscar cliente por CPF, listar protocolos por status.

### 5. table('protocolos').insert({...}).execute()

Insert linha.

```python
novo = {
    "cliente_id": 42,
    "tipo": "certidao_negativa",
    "status": "draft"
}
response = supabase.table('protocolos').insert(novo).execute()
protocolo = response.data[0]
# protocolo['id'], protocolo['created_at'] (auto)
```

**Cartorio**: abrir novo protocolo de atendimento.

### 6. table('atendimentos').update({...}).eq('id', 1).execute()

Update linha(s).

```python
updates = {"status": "concluido", "concluido_em": "now()"}
response = supabase.table('atendimentos').update(updates).eq('id', 1).execute()
atendimentos = response.data  # linhas atualizadas
```

**Cartorio**: mudar status de protocolo/atendimento.

### 7. storage.from_('documentos').upload(path, bytes)

Upload arquivo para Storage.

```python
with open('/tmp/rg.pdf', 'rb') as f:
    file_bytes = f.read()

response = supabase.storage.from_('documentos').upload(
    'protocolo-123/rg.pdf',
    file_bytes,
    file_options={
        "content-type": "application/pdf",
        "upsert": "true"  # sobrescreve se ja existir
    }
)
# response: {"Key": "protocolo-123/rg.pdf"}
```

**Cartorio**: salvar PDF de RG, CPF, certidoes em `documentos/{protocolo_id}/`.

### 8. storage.from_('documentos').create_signed_url(path, 3600)

URL temporaria (1h) para download privado.

```python
url = supabase.storage.from_('documentos').create_signed_url(
    'protocolo-123/rg.pdf',
    3600  # expira em 1h
)
# url = {"signedURL": "/storage/v1/object/sign/...?token=..."}
```

**Cartorio**: gerar link de 1h para o atendente baixar documento escaneado (bucket privado).

## Conceitos Fundamentais

### Row Level Security (RLS)

**Politica a nivel de linha no Postgres** (nao no cliente). Ativar em **TODA tabela**:

```sql
ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "atendente_le_clientes" ON clientes
  FOR SELECT
  USING (auth.uid() IS NOT NULL);  -- usuario logado pode ler
```

**SEM RLS = qualquer usuario ve todos os dados via PostgREST.**

### Service Role Key vs Anon Key

| Tipo | Permissao | Onde usar |
|---|---|---|
| **anon** (publica) | Respeita RLS, usa JWT do usuario | Frontend (browser/web) |
| **service_role** (SECRETA) | Bypassa RLS, acesso total | **Backend only** (FastAPI) |

**REGRA**: `service_role` NUNCA vai para frontend/browser. Se vazar, RLS e' desfeito.

### Realtime (opcional, Sprint 4+)

```python
channel = supabase.channel('protocolos')
channel.on(
    'postgres_changes',
    {'event': 'INSERT', 'schema': 'public', 'table': 'protocolos'},
    lambda payload: print('Novo protocolo:', payload)
).subscribe()
```

**Cartorio**: dashboard de escrevente mostrando novos protocolos ao vivo.

## Cenarios de uso no Cartorio

| Fluxo | Comandos usados |
|---|---|
| Login escrevente | 1, 3 (middleware) |
| Cadastro de usuario interno | 2 |
| Buscar cliente por CPF | 4 |
| Abrir protocolo | 5 |
| Atualizar status | 6 |
| Upload de documento (RG, CPF) | 7 |
| Gerar link download (1h) | 8 |

## Migracao do SQLAlchemy para Supabase-py

O backend FastAPI atual usa **SQLAlchemy direto** (sync) para Supabase via `postgresql+psycopg://`. Para usar supabase-py:

**Pros**:
- PostgREST automatico (sem migrations para queries simples)
- Auth integrado
- Storage embutido

**Contras**:
- Adiciona dependencia `supabase-py`
- Operacoes complexas (joins, transactions) ainda exigem SQLAlchemy

**Recomendacao**: manter SQLAlchemy para regras de negocio + usar supabase-py APENAS para Auth/Storage. **Decisao registrada no Sprint 3.5+ backlog**.

## Troubleshooting

| Problema | Solucao |
|---|---|
| 401 Unauthorized | JWT expirado ou invalido - refresh via `auth.refresh_session()` |
| 403 Forbidden | RLS bloqueando - verificar politica SQL ou usar service_role (backend) |
| 404 Not Found | tabela/bucket nao existe - verificar no Supabase Studio |
| 400 Bad Request | payload invalido - verificar schema |
| CORS error | Supabase configura CORS para origens permitidas - ajustar em Settings > API |

## Referencias

- Doc oficial: https://supabase.com/docs/reference/python
- Auth guide: https://supabase.com/docs/guides/auth
- Storage: https://supabase.com/docs/guides/storage
- RLS: https://supabase.com/docs/guides/auth/row-level-security
- Plataforma prod: https://supbase.2notasudi.com.br
- README oficial: `docs/platforms/SUPABASE_OFFICIAL_README.md`
- Integração: `backend/app/integrations/` (a criar)
