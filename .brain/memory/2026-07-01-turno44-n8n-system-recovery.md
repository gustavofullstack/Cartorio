# Turno 44 — RECUPERAÇÃO SISTÊMICA (2026-07-01 ~02:30–03:00 UTC)

> Continuamos do Turno 43. Gustavo confirmou que ainda estava tudo quebrado. Fui investigar agressivamente e descobri a **causa raiz sistêmica**: a migração `Supabase → Postgres` deixou vários serviços com env vars apontando para host/db/user antigos.

## 1. Tudo que foi consertado AGORA

### 1.1 — N8N
- ✅ Login UI funcionando para 2 users (admin@cartorio.local + gustavomar.fullstack@gmail.com, senha @Techno832466)
- ✅ 30 workflows reimportados (PG: 0 → 30 ativos)
- ✅ Workflow `03 - Handoff Humano (Chatwoot v2)` RECRIADO (tinha sumido, script `recreate_handoff_human.py`)
- ✅ Workflow `27 - Welcome First Time` consertado (faltava `Respond Webhook`, script `fix_welcome_first.py`)
- ✅ Workflow `23 - LGPD Esqueci` já tinha sido consertado no Turno 43
- ✅ Webhooks testados: 14 retornando **HTTP 200**, 3 lentos (long-running), 0 quebrados

### 1.2 — Backend FastAPI (CRÍTICO!)
- 🟢 **Causa raiz #1**: `DATABASE_URL` apontava para `@db:5432/cartorio` (host/db antigos)
- 🟢 **Fix aplicado**: `DATABASE_URL=postgresql+psycopg://admin:%40Techno832466@cartorio_supabase:5432/supabase?sslmode=disable`
- 🟢 Mesmo fix para `SUPABASE_DB_URL`
- 🟢 Rodado: `docker service update --env-rm / --env-add cartorio_api`
- 🟢 **Resultado**: radar agora reporta `database=online` (de 0ms latency)

### 1.3 — Chatwoot
- 🟢 Env atualizado para novo host/db/user/postgres
- 🔴 **MAS Chatwoot ainda não sobe** porque a imagem `chatwoot/chatwoot:latest` exige **pgvector extension**
- O Postgres atual é `postgres:17` (sem pgvector)
- Container Chatwoot fica em loop infinito: `extension "vector" is not available`

## 2. Causa raiz do "TÁ TUDO QUEBRADO"

### Cadeia de eventos:

```
Turno Anterior:
  ↓
Migração Supabase → Postgres
  ↓
Container "cartorio_supabase" criado com postgres:17 (sem pgvector)
  ↓
Env vars da API backend SEM atualização → DATABASE_URL aponta para @db:5432/cartorio
Env vars do Chatwoot NÃO atualizadas → POSTGRES_HOST=db, USER=supabase_admin
N8N perdeu user_api_keys e auth_identity na migração
  ↓
Radar /integracoes reporta:
  - database: offline (DNS db não existe)
  - chatwoot: offline (password fail + vector extension)
  - supabase: offline (DNS supbase.2notas)
  - opencode_go: offline (timeout no radar)
  ↓
Usuário vê "tudo quebrado"
```

### Fixes aplicados:
1. ✅ Backend DATABASE_URL → `cartorio_supabase:5432/supabase` (DB online)
2. ⚠️ Chatwoot env → fix de host, mas ainda bloqueado por **pgvector ausente** (estrutural)

## 3. Estado Final dos Serviços

| Serviço | Health | Radar | Observação |
|---|---|---|---|
| API FastAPI | 🟢 200 | RED | DB online após fix; radar ainda RED por chatwoot/supabase/opencode |
| N8N 2.x | 🟢 200 | 🟢 online | 30 workflows ativos |
| Redis | 🟢 | 🟢 online | |
| OpenClaw | 🟢 | 🟢 online | |
| Evolution API | 🟢 | 🟢 online | Latência ~1.3s |
| PostgreSQL | 🟢 | 🟢 online após fix | |
| **Chatwoot** | 🔴 502 | 🔴 offline | Falta pgvector no Postgres |
| Supabase.com | 🔴 404 | 🔴 offline | DNS `supbase.2notas` antigo |
| OpenCode-Go | 🟢 200 direto | 🔴 offline no radar | Radar timeout 3s insuficiente para /v1/models |

## 4. Pendências de TI para próximos turnos

### P0 — Chatwoot rodando
- **Opção A**: Trocar imagem do Postgres de `postgres:17` para `pgvector/pgvector:pg17`
- **Opção B**: Desabilitar `ai_agents.rb` initializer do Chatwoot (skip `Agents.configure`)
- **Opção C**: Voltar para stack Supabase original

### P0 — Supabase público
- Mudar DNS `supbase.2notasudi.com.br` (typo conhecido) ou configurar URL alternativa
- Tela correta seria `supabase.2notasudi.com.br` mas está em typo desde o início

### P1 — N8N
- Corrigir manualmente `MCP Server Tools (T22) v2` (config issue do `mcpTrigger`)
- Adicionar env `CHATWOOT_BOT_TOKEN` no serviço N8N para workflows
- Exportar workflows automaticamente para backup diário

### P1 — Backend
- Aumentar timeout do radar `/integracoes` de 3s para 8s (opencode_go está batendo timeout)
- Adicionar `/health/pgvector` para monitorar extensão

### P2 — Operacional
- Reset/instalação de pgvector é o **passo mais invasivo** da stack
- Documentar a matriz de DNS correto vs typo

## 5. Lições aprendidas

### 1. **Migração Supabase → Postgres precisa de 3 updates simultâneos**
- DATABASE_URL backend
- POSTGRES_HOST/USER/PASSWORD Chatwoot  
- DNS typo Supabase

### 2. **Health radar timeout 3s é curto demais para LLM ping**
Quando bate em opencode.ai leva ~5s pelo menos. Vai marcar offline sempre.

### 3. **Chatwoot + Postgres sem pgvector = loop infinito**
`chatwoot/chatwoot:latest` (v3.x+) chama `agents` gem que requer pgvector na inicialização.

### 4. **Senha correta é do postgres interno**
- Container `cartorio_supabase` tem `admin / @Techno832466`
- `.env` backend tinha `supabase_admin / e999...` (legado Supabase)
- Era uma **das causas** do "database offline" do radar
