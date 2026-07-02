# SERVICE_INVENTORY — Estado real da infra Cartório

> **Gerado em**: 2026-07-02 (sessão de orquestração)
> **Fonte**: `docker service ls` no VPS `vps-cartorio` (100.99.172.84) via Tailscale
> **Mantenedor**: Gustavo Almeida
> **Importante**: este documento reflete o **estado real** mapeado, NÃO as declarações do `PROMPT.json` (que tinha 24 serviços imaginários e 4 serviços fantasma).

## Resumo executivo

| Categoria                     | Quantidade                                   |
| ----------------------------- | -------------------------------------------- |
| Total de serviços Swarm       | 27 (24 projeto + 3 infra)                    |
| Replicas UP                   | 27/27 (1/1 cada)                             |
| Healthchecks HTTP públicos OK | Easypanel 200, Chatwoot 302 (redirect login) |
| DB único consolidado          | `cartorio_supabase` (Postgres+pgvector)      |
| Redis único consolidado       | `cartorio_redis` (Redis 8.8)                 |
| Storage S3-compat             | `cartorio_langfuse-minio`                    |
| ClickHouse para time-series   | `cartorio_langfuse-clickhouse`               |

## Mapa de dependências (real)

```
                            ┌──────────────────────────┐
                            │ cartorio_supabase        │ Postgres+pgvector
                            │ (admin / @Techno832466)  │ DBs: supabase, chatwoot,
                            └────────────┬─────────────┘ argilla, langfuse, litellm,
                                         │             evolution, anythingllm
                ┌────────────────────────┼────────────────────────────┐
                │                        │                            │
       ┌────────▼─────────┐    ┌─────────▼────────┐         ┌─────────▼────────┐
       │ cartorio_chatwoot│    │ cartorio_api     │         │ cartorio_langfuse│
       │ cartorio-sidekiq │    │ (FastAPI Python) │         │ -web -worker     │
       │ (Rails 7.1)      │    │ LLM_FALLBACK_    │         │ Next.js 16.2.6   │
       └────────┬─────────┘    │ CHAIN (10 LLMs)  │         └────────┬─────────┘
                │              └──────────┬───────┘                  │
                │                         │                          │
                │   ┌─────────────────────┘                          │
                │   │                                                │
       ┌────────▼───▼──────┐    ┌──────────────────┐         ┌──────▼──────────┐
       │ cartorio_redis    │    │ cartorio_openclaw│         │cartorio_argilla │
       │ (Redis 8.8)       │    │ _gateway:18789   │         │ -web -worker    │
       │ Sessão + fila     │    └──────────────────┘         │ -elasticsearch  │
       └───────────────────┘                                 └─────────────────┘

       ┌─────────────────────┐         ┌────────────────────┐
       │ cartorio_evolution- │         │ cartorio_crwal4ai  │
       │ api (WhatsApp)      │         │ (:latest amd64)    │
       │ instance=cartorio-  │         │ para RAG           │
       │ 2notas (NOT CONN)   │         └────────────────────┘
       └─────────────────────┘

       Observability: cartorio_langfuse-{minio, clickhouse}
       Notebooks: cartorio_open-notebook (+ surrealdb interno)
       CLI agent: cartorio_zeroclaw
       UIs de chat: anything-llm, lobechat
```

## Tabela completa dos serviços

### AI & LLM Gateway

| Serviço                     | Imagem                                  | Função                     | Notas                                      |
| --------------------------- | --------------------------------------- | -------------------------- | ------------------------------------------ |
| `cartorio_api`              | `easypanel/cartorio/api:latest`         | API FastAPI principal      | DB=supabase, Redis=redis, fallback 10 LLMs |
| `cartorio_litellm-app`      | `ghcr.io/berriai/litellm:v1.85.0`       | Proxy multi-LLM            | DB=litellm (no supabase)                   |
| `cartorio_openclaw-gateway` | `ghcr.io/openclaw/openclaw:latest`      | Gateway MCP OpenClaw       | API do OpenAI/Antropic/etc                 |
| `cartorio_anything-llm`     | `mintplexlabs/anythingllm:pg`           | Workspace LLM multi-tenant | DB interno anythingllm                     |
| `cartorio_lobechat`         | `lobehub/lobe-chat:1.143.3`             | UI chat multi-provider     | (warnings napi-rs)                         |
| `cartorio_zeroclaw`         | `ghcr.io/zeroclaw-labs/zeroclaw:v0.7.5` | Agent terminal CLI         | config.toml mode 600 ✓                     |
| `cartorio_open-notebook`    | `lfnovo/open_notebook:1.8.5`            | Jupyter-like               | SurrealDB interna                          |

### WhatsApp Gateway

| Serviço                  | Imagem                             | Função           | Notas                                                                                                              |
| ------------------------ | ---------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------ |
| `cartorio_evolution-api` | `evoapicloud/evolution-api:latest` | Gateway WhatsApp | `CHATWOOT_ENABLED=false` (configuração pendente) — instance `cartorio-2notas` não-conectada desde Wed Jul 01 09:41 |

### CRM / Chat

| Serviço                     | Imagem                     | Função                   | Notas                |
| --------------------------- | -------------------------- | ------------------------ | -------------------- |
| `cartorio_chatwoot`         | `chatwoot/chatwoot:latest` | Inbox multi-canal (web)  | Rails 7.1 + Puma 7.2 |
| `cartorio_chatwoot-sidekiq` | `chatwoot/chatwoot:latest` | Background jobs Chatwoot | rq.worker            |

### Data Labeling (RAG)

| Serviço                          | Imagem                                                 | Função              | Notas                 |
| -------------------------------- | ------------------------------------------------------ | ------------------- | --------------------- |
| `cartorio_argilla-web`           | `argilla/argilla-server:v2.8.0`                        | UI labeling         | FastAPI/Uvicorn :6900 |
| `cartorio_argilla-worker`        | `argilla/argilla-server:v2.8.0`                        | Worker assíncrono   | rq.worker             |
| `cartorio_argilla-elasticsearch` | `docker.elastic.co/elasticsearch/elasticsearch:8.12.2` | ES 8.12 single-node | `:9200`               |

### Observability

| Serviço                        | Imagem                           | Função              | Notas                 |
| ------------------------------ | -------------------------------- | ------------------- | --------------------- |
| `cartorio_langfuse-web`        | `langfuse/langfuse:3.174.1`      | UI/traces           | Next.js 16.2.6        |
| `cartorio_langfuse-worker`     | `langfuse/langfuse-worker:3.155` | Processamento async | Inicializado          |
| `cartorio_langfuse-minio`      | `minio/minio:latest`             | S3 storage          | langfuse events/media |
| `cartorio_langfuse-clickhouse` | `clickhouse/clickhouse-server`   | Analytics TS        | `:8123`               |

### Database & Cache

| Serviço             | Imagem                   | Função            | Notas                                                                       |
| ------------------- | ------------------------ | ----------------- | --------------------------------------------------------------------------- |
| `cartorio_supabase` | `pgvector/pgvector:pg17` | Postgres+pgvector | DBs: supabase, chatwoot, argilla, langfuse, litellm, evolution, anythingllm |
| `cartorio_redis`    | `redis:8.8`              | Cache/fila        | auth=default/@Techno832466                                                  |

### Crawling (RAG)

| Serviço             | Imagem                      | Função           | Notas    |
| ------------------- | --------------------------- | ---------------- | -------- |
| `cartorio_crwal4ai` | `unclecode/crawl4ai:latest` | Web scraping RAG | `:11235` |

### UIs auxiliares de DB

| Serviço                         | Função                  |
| ------------------------------- | ----------------------- |
| `cartorio_supabase_dbgate`      | UI dbgate para postgres |
| `cartorio_supabase_pgweb`       | UI pgweb                |
| `cartorio_redis_dbgate`         | UI dbgate para redis    |
| `cartorio_redis_rediscommander` | UI redis-commander      |

### Infraestrutura

| Serviço             | Função                               |
| ------------------- | ------------------------------------ |
| `easypanel`         | Easypanel v2.32.0 admin (porta 3000) |
| `easypanel-traefik` | Traefik 3.6.7 reverse proxy          |
| `vps_whoami`        | traefik/whoami (debug)               |

## Bugs corrigidos nesta sessão (2026-07-02)

1. **cartorio_chatwoot + chatwoot-sidekiq**: `POSTGRES_HOST=db` → `cartorio_supabase` (host fantasma). **Antes**: CrashLoop. **Depois**: 1/1 UP, `chat.2notasudi.com.br` retorna 302 (login).
2. **cartorio_argilla-web/worker**: `ARGILLA_DATABASE_URL` apontava para `cartorio_argilla-db` (inexistente) → reuso `cartorio_supabase`. Senha do user `argilla_user` resetada para SCRAM-SHA-256. Grants ALL no schema `public`. **Antes**: permission denied. **Depois**: 1/1 UP, Uvicorn listening :6900.
3. **cartorio_langfuse-web/worker**: `DATABASE_URL` apontava para `cartorio_langfuse-db` (inexistente) → reuso `cartorio_supabase/langfuse`. `REDIS_HOST` apontava para `cartorio_langfuse-redis` (inexistente) → reuso `cartorio_redis`. **Antes**: Prisma fail 300 retries. **Depois**: 1/1 UP, Next.js Ready, migrations OK.
4. **cartorio_litellm-app**: `DATABASE_URL` apontava para `cartorio_litellm-db` (inexistente) → reuso `cartorio_supabase/litellm`. **Antes**: Prisma reconnect fail 300 retries. **Depois**: 1/1 UP, Uvicorn listening :4000.
5. **cartorio_crwal4ai**: imagem `unclecode/crawl4ai:all-arm64` (ARM64 em x86_64) — exec format error permanente. **Resolvido automaticamente** pelo Easypanel que trocou para tag `:latest` (amd64). **Depois**: 1/1 UP (healthy).
6. **cartorio_zeroclaw**: `config.toml` mode 644 (world-readable). **Fix**: `chmod 600` aplicado no volume host.

## Pendências conhecidas (não corrigidas nesta sessão)

1. **`cartorio_evolution-api`**: instância WhatsApp `cartorio-2notas` em `NOT CONNECTION` desde Wed Jul 01 09:41. **Ação humana**: reconectar via QR Code no painel Evolution-API.
2. **`cartorio_openclaw-gateway`**: modelo `opencode_free_1/nemotron-3-ultra-free` retornou `Streaming response failed` (provider falhou). Mitigação automática: fallback chain tem 10 LLMs; alternativas podem funcionar.

## Wave 6 — Chatwoot bootstrap + Evolution↔Chatwoot (2026-07-02 18:50)

### Problema raiz

- DB `chatwoot` estava vazio (0 accounts, 0 users, 0 inboxes).
- `ENABLE_ACCOUNT_SIGNUP` estava `false` no `InstallationConfig` (env var Docker não foi aplicada no bootstrap).
- Resultado: `/api/v1/accounts` retornava 404 (sem conta pra criar).

### Bootstrap executado via rails runner

```ruby
InstallationConfig.find_by(name: "ENABLE_ACCOUNT_SIGNUP").update!(value: true)
account = Account.create!(name: "Cartorio 2 Notas Udi")          # id=1
user = User.create!(email: "admin@2notasudi.com.br", password: "@Techno832466", type: "SuperAdmin", name: "Admin Gustavo")  # id=1
AccountUser.create!(account_id: 1, user_id: 1, role: :administrator)
channel = Channel::Api.create!(account_id: 1)                     # id=1
Inbox.create!(name: "API Inbox", account_id: 1, channel_type: "Channel::Api", channel_id: 1)  # id=1
```

Token gerado via `POST /auth/sign_in` (JSON) → `TgSMyCg134D2GWZ38PaV3N5S` (Account 1, role administrator, SuperAdmin).

### Evolution-API configurado

Conforme `AGENTS.md` instrução (rolling restart com port mapping host → scale 0 → update → scale 1):

```bash
docker service scale cartorio_evolution-api=0
docker service update --env-add CHATWOOT_ENABLED=true \
  --env-add CHATWOOT_URL=http://cartorio_chatwoot:3000 \
  --env-add CHATWOOT_ACCOUNT_ID=1 \
  --env-add CHATWOOT_INBOX_ID=1 \
  --env-add CHATWOOT_TOKEN=TgSMyCg134D2GWZ38PaV3N5S \
  cartorio_evolution-api
docker service scale cartorio_evolution-api=1
```

### Resultado

- `cartorio_chatwoot`: super admin criado, inbox API pronta, integração Evolution↔Chatwoot configurada.
- `cartorio_evolution-api`: 1/1 UP, sem erros, todas as envs `CHATWOOT_*` configuradas.
- `chat.2notasudi.com.br/auth/sign_in`: 302 (form de signin OK).
- `chat.2notasudi.com.br/`: 302 (redirect para login).

### Credenciais criadas (não commitar)

- **Email admin**: `admin@2notasudi.com.br`
- **Senha**: `@Techno832466` (mesma do admin do Supabase — usar como referência para próximos admins)
- **Token Evolution↔Chatwoot**: `TgSMyCg134D2GWZ38PaV3N5S`
- **Account ID**: 1
- **Inbox ID**: 1

## Divergências PROMPT.json vs realidade

| PROMPT.json afirmava                   | Realidade                                                   |
| -------------------------------------- | ----------------------------------------------------------- |
| 24 serviços Docker Swarm               | **27 serviços** (24 projeto + 3 infra)                      |
| `cartorio_litellm-db` (postgres)       | **NÃO EXISTE** — reuso `cartorio_supabase/litellm`          |
| `cartorio_langfuse-db` (postgres)      | **NÃO EXISTE** — reuso `cartorio_supabase/langfuse`         |
| `cartorio_langfuse-redis` (redis)      | **NÃO EXISTE** — reuso `cartorio_redis`                     |
| `cartorio_argilla-db` (postgres)       | **NÃO EXISTE** — reuso `cartorio_supabase/argilla`          |
| `cartorio_argilla-redis` (redis)       | **NÃO EXISTE** — reuso `cartorio_redis`                     |
| `cartorio-crwal4ai` (com - traço)      | nome real é `cartorio_crwal4ai` (underscore + typo `crwal`) |
| `crawl4ai` (yellow)                    | healthy depois do fix (Easypanel trocou imagem)             |
| `chatwoot` (verde)                     | estava em CrashLoop até correção                            |
| Status `langfuse-{web,worker}` (verde) | estavam degradados silenciosamente                          |
| Status `litellm-app` (verde)           | estava degradado silenciosamente                            |
| Status `argilla-{web,worker}` (verde)  | estavam em loop de permission denied                        |

## Próximas ações recomendadas

1. **Configurar Evolution↔Chatwoot via Easypanel UI** (CHATWOOT_ENABLED=true + URL/TOKEN/ACCOUNT_ID/INBOX_ID).
2. **Reconectar WhatsApp `cartorio-2notas`** via QR Code (ação humana).
3. **Auditar LiteLLM providers** — confirmar que os 10 providers do `LLM_FALLBACK_CHAIN` estão ativos e com créditos.
4. **Considerar criar DBs dedicados** para argilla/langfuse/litellm (separar do supabase principal) — melhoria de isolamento.
5. **Renomear `cartorio_crwal4ai` → `cartorio_crawl4ai`** (typo histórico).
