# G7.08.T3 — RLS audit (sample tables)

**Task:** G7.08.T3  
**Agent:** cartorio-dev (Wave 25 slot A1)  
**Data (análise local):** 2026-07-17  
**Escopo:** inventário de policies a partir de **código** (Alembic + `schema.sql`).  
**Status:** **DONE agent-side** — inventário estático; **HOLD** para validação live em prod (`pg_policies`).

> Não se assume acesso ao Supabase/Postgres de produção nesta sessão. Tudo abaixo deriva de migrations e dump SQL versionados no repo.

---

## Resultado executivo

| Fonte | Tabelas com RLS | Policies nomeadas (amostra) | FORCE RLS |
|-------|-----------------|-----------------------------|-----------|
| Alembic `2026_06_25_0004` | **11** (se existirem no DB no upgrade) | `service_role_full_access`, `dpo_read_access`, `authenticated_read_own` | Não |
| `infra/supabase/schema.sql` | **15** | Alembic + extras (`anon_*`, `auth_all_*`, `service_all_*`) | Sim em `audit_log`, `clientes` |

**Conclusão:** RLS está modelado no repositório para as tabelas PII core + auxiliares LGPD/outbox. Há **drift** entre migration canônica (0004) e dump `schema.sql` (policies mais permissivas e tabelas extras). Validar em prod com `pg_policies` antes de declarar compliance.

---

## 1. Fonte canônica (Alembic)

**Arquivo:**  
`/Users/gustavoalmeida/Projetos/Cartorio/backend/alembic/versions/2026_06_25_0004-supabase-rls-policies-and-audit-chain-fn.py`

**Revision:** `2026_06_25_0004`  
**Docstring:** S0 S02 — 4 roles (`anon`, `authenticated`, `service_role`, `dpo`).

### 1.1 Roles criadas (se ausentes)

| Role | Login | Intenção |
|------|-------|----------|
| `anon` | NOLOGIN | PostgREST público — **sem policy de acesso** nas tabelas 0004 (deny-by-default com RLS on) |
| `authenticated` | NOLOGIN | JWT Supabase — SELECT na própria linha |
| `service_role` | NOLOGIN | Backend / bypass operacional (policy FOR ALL) |
| `dpo` | NOLOGIN | DPO — SELECT em PII + audit LGPD |

Também cria stub: `CREATE SCHEMA IF NOT EXISTS auth` + `auth.uid()` (retorna `NULL::uuid` se Auth não montado).

### 1.2 Conjuntos de tabelas na migration

```python
_PII_TABLES = (
    "clientes", "protocolos", "atendimentos",
    "documentos", "conversas", "emolumentos",
)

# + auxiliares (se existirem no inspect):
# audit_log, lgpd_consents, lgpd_audit_anpd,
# outbox_messages, webhook_events
```

| Grupo | Tabelas | ENABLE RLS | Policies |
|-------|---------|------------|----------|
| PII | `clientes`, `protocolos`, `atendimentos`, `documentos`, `conversas`, `emolumentos` | Sim | `service_role_full_access`, `dpo_read_access`, `authenticated_read_own` |
| Aux | `audit_log`, `lgpd_consents`, `lgpd_audit_anpd` | Sim | `service_role_full_access` + `dpo_read_access` (sem `authenticated_read_own`) |
| Infra | `outbox_messages`, `webhook_events` | Sim | **somente** `service_role_full_access` |

### 1.3 Amostra de policy names (padrão 0004)

| Policy name | Role | Comando | USING / CHECK |
|-------------|------|---------|---------------|
| `service_role_full_access` | `service_role` | ALL | `true` / `true` |
| `dpo_read_access` | `dpo` | SELECT | `true` |
| `authenticated_read_own` | `authenticated` | SELECT | `{cliente_id\|id}::text = auth.uid()::text OR {col} IS NULL` |

**Regra de coluna (authenticated):**

- Se a tabela tem coluna `cliente_id` → filtra por `cliente_id`.
- Senão → filtra por `id` (ex.: `clientes`, `documentos`, `emolumentos`).

**Nota de segurança (gap conhecido no placeholder):**  
`OR {col} IS NULL` permite SELECT em linhas com FK nula. Documentado na migration como “placeholder, ajustado em D1x”. Em prod isso **deve ser revisado** (`cartorio-lgpd`) antes de expor PostgREST com role `authenticated`.

### 1.4 O que 0004 **não** faz

- **Não** cria policy para role `anon` (intencional: sem acesso).
- **Não** aplica `FORCE ROW LEVEL SECURITY` (superuser/table owner ainda ignora RLS sem FORCE).
- **Não** cobre `agendamentos` (existe model SQLAlchemy + policies no `schema.sql`).
- **Não** cobre `mensagens`, `sessoes_chat` (aparecem só no dump).
- Side-effects da mesma migration (fora de RLS, mas relevantes):
  - `fn_audit_chain_verify(p_from_id, p_to_id)`
  - `fn_auto_audit()` + triggers `trg_auto_audit_{table}` nas PII tables

---

## 2. Fonte dump: `infra/supabase/schema.sql`

**Arquivo:** `/Users/gustavoalmeida/Projetos/Cartorio/infra/supabase/schema.sql`  
(export histórico — pode divergir do que Alembic aplicaria limpo.)

### 2.1 Tabelas com `ENABLE ROW LEVEL SECURITY`

| Tabela | ENABLE RLS | FORCE RLS |
|--------|------------|-----------|
| `agendamentos` | Sim | Não |
| `atendimentos` | Sim | Não |
| `audit_log` | Sim | **Sim** |
| `clientes` | Sim | **Sim** |
| `conversas` | Sim | Não |
| `documentos` | Sim | Não |
| `emolumentos` | Sim | Não |
| `lgpd_audit_anpd` | Sim | Não |
| `lgpd_consents` | Sim | Não |
| `mensagens` | Sim | Não |
| `outbox_messages` | Sim | Não |
| `protocolos` | Sim | Não |
| `sessoes_chat` | Sim | Não |
| `webhook_events` | Sim | Não |

### 2.2 Inventário de policies (schema.sql) — amostra completa por nome

| Policy | Tabela | Role | Ops | Notas |
|--------|--------|------|-----|-------|
| `anon_insert_own_clientes` | `clientes` | `anon` | INSERT | `WITH CHECK (true)` — **permissivo** |
| `anon_select_own_clientes` | `clientes` | `anon` | SELECT | `USING (true)` — **permissivo / gap LGPD** |
| `auth_all_atendimentos` | `atendimentos` | `authenticated` | ALL | `true` — **mais largo que 0004** |
| `auth_all_audit_log` | `audit_log` | `authenticated` | ALL | gap: authenticated escreve audit |
| `auth_all_conversas` | `conversas` | `authenticated` | ALL | |
| `auth_all_own_agendamentos` | `agendamentos` | `authenticated` | ALL | nome “own” mas USING true |
| `auth_all_own_mensagens` | `mensagens` | `authenticated` | ALL | |
| `auth_all_own_sessoes_chat` | `sessoes_chat` | `authenticated` | ALL | |
| `auth_select_emolumentos` | `emolumentos` | `authenticated` | SELECT | tabela de referência OK |
| `authenticated_read_own` | várias PII | `authenticated` | SELECT | igual 0004 (incl. `OR IS NULL`) |
| `dpo_read_access` | PII + LGPD + audit | `dpo` | SELECT | alinhado 0004 |
| `service_all_*` | agendamentos, clientes, audit_log, emolumentos, mensagens, sessoes_chat | `service_role` | ALL | naming legacy no dump |
| `service_role_full_access` | atendimentos, audit_log, clientes, conversas, documentos, emolumentos, lgpd_*, outbox, protocolos, webhook_events | `service_role` | ALL | naming canônico 0004 |

**Drift crítico schema.sql vs 0004:**

1. Dump cria policies `anon_*` em `clientes` → **quebra** o desenho “anon SEM acesso”.
2. Dump cria `auth_all_*` (FOR ALL USING true) **em paralelo** a `authenticated_read_own` → OR de policies no Postgres = se **qualquer** policy permitir, a linha passa → `auth_all_*` anula o filtro “own”.
3. Tabelas `agendamentos` / `mensagens` / `sessoes_chat` só no dump (e/ou seed manual).

---

## 3. Models SQLAlchemy vs cobertura RLS (0004)

| Model (`app/models/`) | `__tablename__` | RLS na 0004 | RLS no schema.sql |
|-----------------------|-----------------|-------------|-------------------|
| `Cliente` | `clientes` | Sim | Sim + FORCE |
| `Protocolo` | `protocolos` | Sim | Sim |
| `Atendimento` | `atendimentos` | Sim | Sim |
| `Documento` | `documentos` | Sim | Sim |
| `Conversa` | `conversas` | Sim | Sim |
| `Agendamento` | `agendamentos` | **Não** | Sim |
| `AuditLog` | `audit_log` | Sim | Sim + FORCE |
| `OutboxMessage` | `outbox_messages` | Sim | Sim |
| `WebhookEvent` | `webhook_events` | Sim | Sim |
| `LGPDConsentLog` | `lgpd_consent_log`* | via rename `lgpd_consents` (0011) | `lgpd_consents` |

\* Model ainda declara `lgpd_consent_log`; migration `2026_06_25_0011` renomeia para `lgpd_consents`. RLS 0004 depende de `lgpd_consents` no inspect (down_revision chain coloca 0011 antes de 0004 no grafo atual).

**Tabela sem model ORM mas com RLS:** `emolumentos`, `lgpd_audit_anpd`, `mensagens`, `sessoes_chat` (últimas duas só dump).

---

## 4. Gaps e riscos (priorizados)

| ID | Gap | Severidade | Ação sugerida |
|----|-----|------------|---------------|
| G1 | `OR col IS NULL` em `authenticated_read_own` | Alta (se PostgREST auth exposto) | Remover `OR IS NULL`; exigir match estrito `auth.uid()` |
| G2 | Policies `anon_*` + `auth_all_*` no dump | Alta | Em prod: dropar se 0004 for a verdade canônica; alinhar dump |
| G3 | Sem `FORCE ROW LEVEL SECURITY` na 0004 (exceto dump em 2 tabelas) | Média | `ALTER TABLE ... FORCE ROW LEVEL SECURITY` em PII + audit |
| G4 | `agendamentos` fora da 0004 | Média | Incluir em próxima migration RLS (tem PII de cliente) |
| G5 | Model `lgpd_consent_log` vs tabela `lgpd_consents` | Baixa (ops) | Alinhar `__tablename__` ou view de compat |
| G6 | Backend FastAPI usa `DATABASE_URL` como superuser/owner | Info | RLS **não** protege o path app→Postgres se role for table owner; RLS protege PostgREST/roles limitadas |
| G7 | Validação live `pg_policies` não executada nesta task | Processo | Runbook §5 |

**G6 é arquitetural:** o bot/API com role owner **bypassa** RLS. Mitigações: PII scrubbing app-side, audit chain, HITL — RLS é camada extra para REST Supabase / roles não-owner.

---

## 5. Como verificar em produção

### 5.1 Inventário de policies

```sql
-- Todas as policies do schema public
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual AS using_expr,
  with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

### 5.2 Quais tabelas têm RLS / FORCE

```sql
SELECT
  c.relname AS table_name,
  c.relrowsecurity AS rls_enabled,
  c.relforcerowsecurity AS rls_forced
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
  AND (c.relrowsecurity OR c.relforcerowsecurity)
ORDER BY c.relname;
```

### 5.3 Sample tables (checklist G7 — mínimo)

Rodar e copiar resultado para o runbook de go-live:

```sql
SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN (
    'clientes', 'protocolos', 'documentos', 'audit_log',
    'conversas', 'atendimentos', 'emolumentos',
    'lgpd_consents', 'lgpd_audit_anpd',
    'outbox_messages', 'webhook_events', 'agendamentos'
  )
ORDER BY tablename, policyname;
```

**Esperado se só 0004 aplicou (sem drift dump):**

| Tabela | Policies esperadas (nomes) |
|--------|----------------------------|
| PII (6) | `service_role_full_access`, `dpo_read_access`, `authenticated_read_own` |
| `audit_log`, `lgpd_consents`, `lgpd_audit_anpd` | `service_role_full_access`, `dpo_read_access` |
| `outbox_messages`, `webhook_events` | `service_role_full_access` |
| `agendamentos` | **vazio** na 0004 (gap G4) |

**Red flags se aparecerem em prod:**

- `anon_select_own_clientes` / `anon_insert_own_clientes`
- `auth_all_*` em tabelas PII ou `audit_log`
- RLS disabled (`relrowsecurity = false`) em `clientes` / `audit_log`

### 5.4 Smoke de role (opcional, em staging)

```sql
-- Como dpo: deve ler clientes
SET ROLE dpo;
SELECT count(*) FROM clientes;  -- OK se policy dpo_read_access
RESET ROLE;

-- Como anon: deve falhar / zero rows se 0004 canônico
SET ROLE anon;
SELECT count(*) FROM clientes;  -- esperado: 0 ou permission denied
RESET ROLE;
```

### 5.5 Comandos ops (fora do SQL)

```bash
# Via Studio / psql no container db (sem colar secrets no chat)
# docker exec -it <supabase-db> psql -U postgres -d cartorio -c "SELECT * FROM pg_policies LIMIT 20;"

# Conferir se migration 0004 está no histórico aplicado
# cd backend && uv run alembic history | grep 0004
# cd backend && uv run alembic current
```

---

## 6. Matriz sample (para auditoria LGPD)

Amostra **mínima** de 4 tabelas citadas em relatórios de validação antigos (`clientes`, `protocolos`, `documentos`, `audit_log`) + 2 de controle:

| Tabela | RLS 0004 | dpo SELECT | service ALL | auth own | FORCE (dump) |
|--------|----------|------------|-------------|----------|--------------|
| `clientes` | Sim | Sim | Sim | Sim (`id`) | Sim (dump) |
| `protocolos` | Sim | Sim | Sim | Sim (`cliente_id`) | Não |
| `documentos` | Sim | Sim | Sim | Sim (`id`) | Não |
| `audit_log` | Sim | Sim | Sim | Não | Sim (dump) |
| `outbox_messages` | Sim | Não | Sim | Não | Não |
| `agendamentos` | **Não** | N/A (0004) | N/A | N/A | Não (0004) |

---

## 7. Status G7.08.T3

| Item | Status |
|------|--------|
| Inventário migrations/SQL | **DONE** |
| Sample policy names | **DONE** |
| Gaps documentados | **DONE** |
| Runbook `pg_policies` | **DONE** |
| Execução live em prod | **HOLD** (sem acesso Supabase nesta sessão) |

**Próximo passo (ops / cartorio-lgpd):** rodar §5.1–5.3 em prod, anexar CSV/JSON ao incidente ou ao `docs/AUDIT_INTEGRITY_REPORT.md`, e decidir se dump `auth_all_*` / `anon_*` deve ser removido.

---

Modified by Gustavo Almeida
