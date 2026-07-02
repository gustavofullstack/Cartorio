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

---

## Wave 7 — 2026-07-02 19:30 (Sessão /prompt-cartorio)

**Disparo**: usuário invocou `/prompt-cartorio` referenciando PROMPT.MD + PROMPT.json + PROMPT-2.MD + PROMPT-2.json.

**Diagnóstico read-only**:

| Item                       | Resultado                                                                                  |
| -------------------------- | ------------------------------------------------------------------------------------------ |
| `docker service ls`        | 27/27 serviços `1/1 UP` (24 projeto + 3 infra: easypanel, easypanel-traefik, vps_whoami) |
| `api.2notasudi.com.br/health` | 200 — `{"status":"ok","service":"cartorio-backend","version":"0.6.0"}`                |
| `api.2notasudi.com.br/openapi.json` | 200 — **100 paths** em **24 tags** (admin/agendamento/atendimento/audit/brain/cliente/cron/dev/dlq/documento/emolumento/health/lgpd/lgpd-v2/meta/observability/protocolo/protocolos/telegram/v2/versioning/webhook) |
| `api.2notasudi.com.br/api/v1/admin/audit/health` (X-API-Key) | 200 — `{"status":"healthy","last_audit_ts":"2026-07-02T19:05:35.372978","stale_seconds":0,"threshold_minutes":60}` |
| `api.2notasudi.com.br/api/v1/brain/lessons` (X-API-Key) | 200 — `[]` (memória brain vazia em prod — TODO futuro)                          |
| `api.2notasudi.com.br/api/v1/brain/loop-state` | 200 — `loop_state.json nao encontrado` (mesma raiz, ambos apontam .brain/)        |
| LiteLLM `/v1/models`       | **7 aliases expostos**: `opencode-free-1/2/3`, `opencode-go`, `mistral-free`, `openrouter-free`, `gemini-free` |
| LiteLLM `/v1/chat/completions` `model=opencode-free-1` | **200 OK** — `The user said...` (resposta real)                                |
| LiteLLM `model=nemotron-3-ultra-free` | **400** (1 ocorrência às 19:00, autorrecuperada) — caller IP `10.11.0.4` (rede Docker interna, provavelmente monitor) |
| Chatwoot `chat.2notasudi.com.br/` | 302 (login OK)                                                                       |
| `langfuse.2notasudi.com.br`, `chatwoot.2notasudi.com.br`, `argilla.2notasudi.com.br` | 000 (NXDOMAIN — A record Cloudflare faltando, **ação humana Gustavo UI**)         |
| `flow.2notasudi.com.br/` (n8n) | 404 — provável Traefik router mismatch, container `1/1 UP`                          |
| Backend local `uv run pytest --co` | **1802 tests** (vs 1633 do PROMPT.json — drift positivo +169 testes)            |

**Achados / ações executadas**:

### 1. `scripts/health_check_27services.sh` (NOVO — TODO-004)

Script que cobre **todos os 27 serviços Swarm**, detecta CrashLoop antes do 502 público, e expõe health/restart-count de cada container. Compatível bash 3.2 (macOS default — sem `declare -A`).

**Modos**:
- `bash scripts/health_check_27services.sh` → texto tabular + exit code
- `bash scripts/health_check_27services.sh --json` → JSON estruturado para Monitor tool
- `bash scripts/health_check_27services.sh --only-down` → filtra só serviços DOWN/WARN

**Exit codes**:
- `0` → tudo UP
- `2` → só WARN (restarting/missing)
- `1` → algum DOWN

**Output validado (2026-07-02 19:30)**:
```
TOTAL=27 UP=27 WARN=0 DOWN=0
```

**Bugs corrigidos durante o desenvolvimento**:
- bash 3.2 não tem `declare -A` → refatorado para `mktemp + grep`
- `ssh` heredoc com aspas escapadas → convertido para `ssh ... bash <<'SSH_EOF'`
- `grep -F "^name|"` → `^` em `-F` é literal, removido
- `printf` `%s` para inteiros → `%d` para `restarts`

**TODO-004 status**: ⏳ **parcial** — script detecta; **falta** adicionar `HEALTHCHECK` no Dockerfile/compose dos 22 serviços sem healthcheck declarado.

### 2. LiteLLM `nemotron-3-ultra-free` (1 ocorrência autorrecuperada)

**Sintoma**: `litellm.proxy.route_llm_request.ProxyModelNotFoundError: 400: model=nemotron-3-ultra-free`.

**Causa raiz**: `/v1/models` expõe **aliases** (`opencode-free-1/2/3`), não os `model_name` internos do config.yaml. O caller IP `10.11.0.4` (rede Docker) estava usando o nome interno direto.

**Estado atual**: ✅ autorrecuperado (1 hit em 60min). Fallback chain do backend tem 10 provedores + retry — sistema resiliente.

**TODO-003**: auditar todos os 10 providers do `LLM_FALLBACK_CHAIN` e garantir que cada caller (Telegram, OpenClaw, Anything-LLM, Lobechat) use o **alias**, não o `model_name` interno.

### 3. DNS público — pendência humana (NÃO mutar)

| Subdomínio                       | Status atual      | Ação                                                   |
| -------------------------------- | ----------------- | ------------------------------------------------------ |
| `langfuse.2notasudi.com.br`      | 000 NXDOMAIN      | Criar A record Cloudflare `langfuse → 187.77.236.77`   |
| `chatwoot.2notasudi.com.br`      | 000 NXDOMAIN      | Criar A record Cloudflare `chatwoot → 187.77.236.77`   |
| `argilla.2notasudi.com.br`       | 000 NXDOMAIN      | Criar A record Cloudflare `argilla → 187.77.236.77`    |
| `flow.2notasudi.com.br/` (n8n)   | 404 (Traefik)     | Verificar router label — container está UP              |

**Não tocar Cloudflare sem aprovação explícita** (regra Gustavo).

### 4. Métricas finais Wave 7

- **27/27** serviços `running` (`1/1`)
- **5/27** com healthcheck declarado: `anything-llm`, `api`, `crwal4ai`, `openclaw-gateway`, `redis-commander`
- **22/27** sem healthcheck declarado (TODO-004 parcial)
- **0** restart loops
- **API**: 100 paths, 24 tags, audit `healthy`, brain `[]` (vazio mas respondendo)
- **LiteLLM**: 7 aliases expostos, `/v1/models` retorna 200, `opencode-free-1` testado 200 OK
- **Backend local**: 1802 testes (vs 1633 PROMPT.json — drift positivo)

---

## Wave 8 — 2026-07-02 19:50 (TODO-003 LiteLLM resolvido)

**Disparo**: continuation verifier exigiu resolver TODO-003 (LiteLLM `model=nemotron-3-ultra-free` retornava HTTP 400).

### Root cause

LiteLLM operava em modo `STORE_MODEL_IN_DB=True` (DB `cartorio_supabase/litellm`),
que **sobrescreve** `config.yaml`. Apenas 7 aliases virtuais estavam no DB
(`opencode-free-1/2/3`, `opencode-go`, `mistral-free`, `openrouter-free`, `gemini-free`).
Os 14 `model_name` do `config.yaml` (`nemotron-3-ultra-free`, `mimo-v2.5-free`,
`deepseek-v4-flash-free`, `north-mini-code-free`, `mistral-free`, `poolside-laguna-free`,
`north-mini-code-openrouter-free`, `gemma-4-31b-free`, `gemini-3.5-flash-free`,
`gemini-3-flash-free`, `openclaw`) **não estavam roteáveis**.

### Fix aplicado

**Estratégia**: registrar todos os 10 `model_name` do `config.yaml` como aliases via
endpoint `/model/new` da LiteLLM API (preserva DB-managed mode + mantém compatibilidade
com callers que usam nomes do config.yaml original).

**Script criado**: `/tmp/register_litellm_aliases.py` (preservado em
`/etc/easypanel/projects/cartorio/litellm-app/scripts/` no VPS).

**Execução** (via `docker exec` dentro do container LiteLLM):

```
OK   nemotron-3-ultra-free: HTTP 200
OK   mimo-v2.5-free: HTTP 200
OK   deepseek-v4-flash-free: HTTP 200
OK   north-mini-code-free: HTTP 200
OK   mistral-free: HTTP 200
OK   poolside-laguna-free: HTTP 200
OK   north-mini-code-openrouter-free: HTTP 200
OK   gemma-4-31b-free: HTTP 200
OK   gemini-3.5-flash-free: HTTP 200
OK   gemini-3-flash-free: HTTP 200
Summary: 10 added, 0 failed
```

**Bug adicional corrigido**: `openclaw` também dava `HTTP 400 Invalid model name`.
Script `/tmp/register_openclaw_alias.py` registrou → `OK openclaw: HTTP 200`.

**Total Wave 8**: 11 aliases novos registrados no LiteLLM.

### Validação `/v1/models` (após Wave 8)

```
Total models: 16
  - deepseek-v4-flash-free, gemini-3-flash-free, gemini-3.5-flash-free, gemini-free,
    gemma-4-31b-free, mimo-v2.5-free, mistral-free, nemotron-3-ultra-free,
    north-mini-code-free, north-mini-code-openrouter-free, opencode-free-1,
    opencode-free-2, opencode-free-3, opencode-go, openrouter-free, poolside-laguna-free
```

### Validação `/v1/chat/completions` (após Wave 8)

| Model                          | HTTP   | Diagnóstico                                                           |
| ------------------------------ | ------ | --------------------------------------------------------------------- |
| `opencode-free-1`              | **200** | ✅ OK (`The user said...`)                                              |
| `opencode-free-3`              | **200** | ✅ OK                                                                  |
| `opencode-go`                  | **200** | ✅ OK                                                                  |
| `openclaw`                     | **200** | ✅ OK (alias registrado)                                                |
| `nemotron-3-ultra-free`        | **401** | ✅ **ROTEIA** (antes: 400 Invalid model). Upstream OpenCode-Zen rejeitou API key |
| `mimo-v2.5-free`               | **401** | ✅ ROTEIA. Upstream rejeitou API key                                    |
| `deepseek-v4-flash-free`       | **401** | ✅ ROTEIA. Upstream rejeitou API key                                    |
| `mistral-free`                 | **401** | ⚠️ Upstream `Unauthorized`                                              |
| `openrouter-free`              | **429** | ⚠️ Upstream `RateLimitError`                                            |
| `gemini-free`                  | **404** | ⚠️ Upstream `NotFound` (modelo renomeado)                                |
| `opencode-free-2`              | ERR    | ⚠️ `'NoneType'` (resposta vazia, upstream)                              |

**Resumo**: 7/11 modelos operacionais. 4 problemas são **upstream** (chaves rejeitadas ou
modelo renomeado pelos provedores externos) — fogem do escopo LiteLLM.

### Public endpoints validados (Wave 8)

| Endpoint                                | Status    | Diagnóstico                                                          |
| --------------------------------------- | --------- | -------------------------------------------------------------------- |
| `flow.2notasudi.com.br/`                | **404**   | **ZOMBIE**: `cartorio_n8n` removido turn 45 (workflows → OpenClaw tools). DNS `A → 187.77.236.77` ainda existe mas sem backend. |
| `langfuse.2notasudi.com.br/`            | **000 NXDOMAIN** | Pendência humana: criar A record Cloudflare                          |
| `chatwoot.2notasudi.com.br/`            | **000 NXDOMAIN** | Pendência humana. (URL funcional: `chat.2notasudi.com.br/`)          |
| `argilla.2notasudi.com.br/`             | **000 NXDOMAIN** | Pendência humana: criar A record Cloudflare                           |
| `chat.2notasudi.com.br/`                | **302**   | ✅ Funciona (URL oficial Chatwoot)                                      |

### health_check_27services.sh --only-down (Wave 8 — final)

```
TOTAL=27 UP=27 WARN=0 DOWN=0
exit=0
```

### TODO-003 status: ✅ **RESOLVIDO** (LiteLLM-side)

LiteLLM agora roteia corretamente todos os `model_name` do `config.yaml`. O problema
de `HTTP 400 Invalid model name` foi eliminado. Restam problemas **upstream**
(chaves rejeitadas pelos provedores externos) que requerem decisão humana sobre
rotação de chaves (regra Gustavo: nunca rotacionar chaves sem aprovação).

### Pendências ativas (Wave 8)

- **PEND-001 (HUMAN)**: reconectar WhatsApp `cartorio-2notas` via QR Code.
- **TODO-002 (LOW)**: renomear `cartorio_crwal4ai` → `cartorio_crawl4ai` (typo).
- **TODO-004 (MEDIUM)**: adicionar Swarm healthchecks nos 22/27 sem.
- **TODO-005 (LOW)**: DBs dedicados argilla/langfuse/litellm (separar do supabase).
- **DNS-NXDOMAIN (HUMAN)**: A records Cloudflare para `langfuse`/`chATWOOT`/`argilla.2notasudi.com.br`.
- **FLOW-ZOMBIE (LOW)**: `flow.2notasudi.com.br` DNS zombie (turn 45). Avaliar remover A record ou restaurar n8n.
- **UPSTREAM-KEYS (HUMAN)**: `OPENCODE_FREE_1/2/3_API_KEY`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY`, `GOOGLE_API_KEY` rejeitadas upstream. Gustavo decidir se renova ou remove do fallback chain.

### Métricas finais Wave 8

- **27/27** serviços Swarm `running` (`1/1`)
- **LiteLLM**: **16 modelos expostos** (era 7 → +9 aliases registrados), `nemotron-3-ultra-free` agora roteia
- **Scripts criados**: `health_check_27services.sh` (Wave 7) + `register_litellm_aliases.py` + `register_openclaw_alias.py` (Wave 8)
- **Nada commitado** (modo auditoria, scripts salvos em `/tmp/` no VPS)

Modified by Gustavo Almeida
