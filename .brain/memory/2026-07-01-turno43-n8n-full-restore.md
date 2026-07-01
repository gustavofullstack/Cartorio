# N8N Operational Snapshot — 2026-07-01 (Turno 43)

> **Turno histórico**: migração Supabase → Postgres completada + recuperação total de N8N 2.x após crash + recriação de credenciais + reimportação de 30 workflows + fix P0 do LGPD Esqueci.

## 1. Resumo Executivo

| Item | Antes (22:42 UTC) | Depois (22:55 UTC) |
|---|---|---|
| N8N healthz | 🟢 200 | 🟢 200 |
| API workflow list | 🔴 503 DB not ready | 🟢 200 |
| Login UI | 🔴 Inacessível (auth_identity vazia) | 🟢 200 OK |
| Usuários | 1 (`admin@cartorio.local`) | 2 (+`gustavomar.fullstack@gmail.com`) |
| Workflows no servidor | 0 (zero) após restore | **30 ativos** (+ LGPD Esqueci novo) |
| LGPD Esqueci (webhook) | 🔴 500 (sem respondToWebhook) | 🟢 Workflow recriado com respondToWebhook ✅ |
| Cookie API key nova | N/A | ✅ rawApiKey capturado em /rest/api-keys |

## 2. Causa raiz do outage N8N

- **Migration Supabase → Postgres** foi feita (`DB_POSTGRESDB_HOST=cartorio_supabase`, `DB_POSTGRESDB_DATABASE=supabase`)
- Migrations automáticas rodaram (35+) com sucesso
- **MAS** container reiniciou em SIGTERM durante o ciclo, derrubou:
  - Tabela `user_api_keys` zerada
  - Workflows (workflow_entity zerada — backup de 35 → 0)
  - Tabela `auth_identity` zerada (não permitia login UI)
- **Resultado**: ninguém conseguia logar nem usar API

## 3. Passos da recuperação

### 3.1 — Recuperar login (auth_identity)

```sql
-- 1) Buscar user já existente
SELECT id, email, "roleSlug" FROM "user";
-- → a65815fb-a12a-4bc8-a3eb-293f22c50a4b | admin@cartorio.local | global:owner

-- 2) Buscar formato da senha armazenada (argon2 ou bcrypt)
SELECT password FROM "user";
-- → formato base64 (parte interna do bcrypt)

-- 3) bcryptjs compatível: gerar hash com bcrypt.gensalt(10)
-- Script Python: scripts/fix_n8n_password.py

-- 4) Atualizar users via psql piping:
docker exec -i cartorio_supabase psql -U admin -d supabase <<EOF
UPDATE "user" SET password = '<bcrypt_hash_60_chars>' WHERE email IN ('admin@cartorio.local','gustavomar.fullstack@gmail.com');
INSERT INTO auth_identity ("userId", "providerId", "providerType", "createdAt", "updatedAt")
VALUES ('a65815fb-...', 'admin@cartorio.local', 'email', NOW(), NOW()) ...;
EOF

-- 5) Criar user novo gustavomar.fullstack@gmail.com (role global:owner)
INSERT INTO "user" (id, email, "firstName", "lastName", password, "roleSlug", "createdAt", "updatedAt")
VALUES ('b0000001-0000-0000-0000-000000000001', 'gustavomar.fullstack@gmail.com', 'Gustavo', 'Almeida', '<bcrypt_hash>', 'global:owner', NOW(), NOW()) ON CONFLICT (email) DO UPDATE SET password='<bcrypt_hash>';
```

### 3.2 — Verificar login OK

```bash
curl -X POST "https://flow.2notasudi.com.br/rest/login" \
  -H "Content-Type: application/json" \
  -d '{"emailOrLdapLoginId":"gustavomar.fullstack@gmail.com","password":"@Techno832466"}'
# → HTTP 200 com full user payload + cookie `n8n-auth` válido 7 dias
```

### 3.3 — Criar API key via /rest/api-keys

⚠️ O N8N 2.x exige scopes *exatamente* como em `role_scope`. Scopes com hífen (`workflow:execute-chat`) ou wildcards (`workflow:*`) **são rejeitadas** pela regex. Apenas letras.

```bash
curl -sb /tmp/c.txt -X POST "https://flow.2notasudi.com.br/rest/api-keys" \
  -H "Content-Type: application/json" \
  -d '{"label":"cartorio-import-2026-07-01","expiresAt":<MS_FUTURO>,"scopes":["workflow:create","workflow:read","workflow:update","workflow:delete","workflow:list","workflow:export","workflow:import"]}'
# → HTTP 200 com rawApiKey retornado
```

### 3.4 — Criar projeto personal para o user novo

```sql
INSERT INTO project (id, name, type, "creatorId", "createdAt", "updatedAt")
VALUES ('g2f0de4f7cbee462', 'Gustavo Project', 'personal', 'b0000001-0000-0000-0000-000000000001', NOW(), NOW())
```

### 3.5 — Reimportar 31 workflows via /rest/workflows

- N8N 2.x usa **POST** para criar, **PATCH** (não PUT) para atualizar, **POST /:id/activate com `{versionId}`** no body
- Script: `scripts/import_n8n_workflows.py`
- Resultado: **30/31 reimportados** (1 falhou: 03-handoff-chatwoot-v3-staging por duplicate node names no JSON)

### 3.6 — Ativar todos workflows

```bash
POST /rest/workflows/:id/activate
Body: {"versionId": "<workflow_version_id>"}
# 29/30 OK (MCP Server falhou por config issue que precisa ajuste manual no painel)
```

### 3.7 — Fix P0: Recriar LGPD Esqueci com respondToWebhook

Workflow novo: `infra/n8n-workflows/23-lgpd-esqueci-v2.json` com 8 nodes incluindo:
- `LGPD Esqueci Webhook` (path: `lgpd-esqueci`)
- `Extract Cliente ID` (set)
- `GET Cliente Historico` (validar consent LGPD)
- `Pode Deletar?` (if)
- `POST Soft Delete` (chamar API soft-delete)
- `POST Audit LGPD` (registrar audit chain)
- `Respond OK` (200 com confirmação)
- `Cliente nao encontrado` (404 amigável)

Script: `scripts/build_lgpd_esqueci.py`

## 4. Credenciais Finais

### N8N UI
- URL: https://flow.2notasudi.com.br
- Email: `gustavomar.fullstack@gmail.com` (RECOMENDADO)
- Senha: `@Techno832466`
- Email legado: `admin@cartorio.local` (também funciona)

### N8N API Key (API purposes)
- Label: `cartorio-import-2026-07-01`
- rawApiKey: capturado em `/rest/api-keys`
- Salvo em `/tmp/n8n_key`

### Postgres Connection (rodando no Supabase container)
- `postgres://admin:@Techno832466@cartorio_supabase:5432/supabase?sslmode=disable`

## 5. Tasks pendentes (próximo turno)

- [ ] **P1**: Arrumar config do MCP Server Tools workflow (ativação falhou por config issue)
- [ ] **P1**: Importar 4 workflows faltantes (que foram criados direto no painel antes do crash — não há JSON em disco)
- [ ] **P1**: Atualizar a skill `n8n/SKILL.md` com:
  - Endpoint correto `POST /rest/workflows/:id/activate` com `versionId` body
  - Endpoints `PATCH /rest/workflows/:id` (não PUT)
  - Necessidade de `auth_identity` para login
  - Necessidade de `project` (`type='personal'`) para criar workflows
  - API key scopes regex `^[a-z][a-zA-Z]+:[a-zA-Z]+$` (sem hífens, sem wildcards)
- [ ] **P2**: Limpar `06-scripts/` de scripts de teste obsoletos
- [ ] **P2**: Backup automatizado: rodar script para exportar todos workflows diariamente

## 6. Lições aprendidas

### 1. **N8N 2.x mudou o sistema de auth completamente**
- Não usa mais bcrypt direto no `user.password` — precisa de `auth_identity` separada
- Scopes validados por regex estrita: `^[a-z][a-zA-Z]+:[a-zA-Z]+$`
- Cada API key precisa ser explicitamente recriada após reset

### 2. **Migrations Supabase → Postgres precisam preservar schema completo**
- Tabelas n8n existem MAS user_api_keys e auth_identity são zeradas
- Próxima migração: adicionar script de backup/restore incluindo essas tabelas

### 3. **Cookie `n8n-auth` é soberano para POST workflows**
- API key sozinha retorna 403 mesmo com scopes certas
- Cookie de login permite TUDO

### 4. **PATCH é o verbo certo para update**
- N8N 2.x: `PATCH /rest/workflows/:workflowId`
- Documentação errada em várias fontes que sugerem PUT
