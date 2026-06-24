# Render API + API full test — 2026-06-24 18:55 BRT

> Sessão: ZCode + MiniMax-M3 (orquestrador).

## Render API conectado

**Chave CORRETA** (testada e funcional): `rnd_sTv1GnBAmvWrsP7UGIs7wrbeuKzn` (em `.secrets/render.env` como `RENDER_MCP_API_KEY`)

**Chave TRUNCADA** (não funciona): `rnd_QP8GWTShurLmVGSp3H2e25pXsKti` (em `.secrets/render.env` como `RENDER_API_KEY`) — retorna 401 Unauthorized

**Solução**: atualizar `.secrets/render.env` para usar a chave correta como `RENDER_API_KEY`. A chave antiga pode ter sido truncada em algum momento.

## Serviço Render deployado

- **Nome**: `Cartorio`
- **ID**: `srv-d8u04aojs32c73c92j8g`
- **URL**: https://cartorio-lrkp.onrender.com
- **Repo**: https://github.com/gustavofullstack/Cartorio
- **Branch**: master
- **Dockerfile**: `./Dockerfile`
- **Region**: ohio
- **Plan**: free
- **Status**: `not_suspended`
- **Created**: 2026-06-24 16:13:31 UTC
- **Updated**: 2026-06-24 16:13:31 UTC
- **AutoDeploy**: yes (trigger: commit)
- **Env**: docker
- **NumInstances**: 1
- **PullRequestPreviews**: no

## API completa testada (TODOS 200 OK)

### Health endpoints (7/7)
- `GET /api/v1/health/live` → 200 (66ms)
- `GET /api/v1/health/ready` → 200 (69ms)
- `GET /api/v1/health/db` → 200 (66ms)
- `GET /api/v1/health/redis` → 200 (157ms)
- `GET /api/v1/health/llm` → 200 (500ms)
- `GET /api/v1/health/radar` → 200 (321ms)
- `GET /api/v1/health/backup` → 200 (68ms)

### Metrics + Telegram webhook (3/3)
- `GET /api/v1/metrics/prometheus` → 200 (154ms)
- `GET /api/v1/telegram/webhook/info` → 200 (643ms)
- `GET /metrics/prometheus` (root) → 200

### OpenAPI Docs (3/3)
- `GET /docs` (Swagger UI) → 200
- `GET /openapi.json` → 200 (266ms)
- `GET /redoc` → 200

### MCP Servers (6 ativos)
1. **cartorio-api** (http, 7 tools): emolumento, protocolo, audit, segunda-via
2. **n8n-mcp** (http, 50 tools): workflows N8N via MCP-HTTP
3. **supabase-mcp** (http, 30 tools): Postgres + docs Supabase
4. **easypanel-mcp** (stdio, 57 tools): controle Easypanel
5. **openclaw-mcp** (http, 20 tools): OpenClaw gateway (pendente Tailscale auth)
6. Total: **164 MCP tools** integrados

## N8N Workflow 31 (Telegram Listener) - 1 bug encontrado

**Node bugado**: `Audit chain verify` (n8n-nodes-base.httpRequest)
- **Method**: POST
- **URL**: https://api.2notasudi.com.br/api/v1/audit/verify
- **Problema**: retorna 405 Method Not Allowed (endpoint espera POST mas com X-API-Key header que o node não envia)

**Solução**: Corrigir node no N8N UI para adicionar header `X-API-Key: <key>` OU usar cred `cartorio-api-key` (id `ADNkyTP2e6uYskUZ`)

## Cron jobs status (Supabase - 5 ativos)

1. `cleanup-sessions-24h` (0 3 * * *) - DB cartorio
2. `audit-chain-verify-6h` (0 */6 * * *) - DB cartorio
3. `retention-daily-03h` (0 3 * * *) - DB cartorio
4. `stale-detector-5min` (*/5 * * * *) - DB cartorio
5. `dlq-refresh-10min` (*/10 * * * *) - DB cartorio

(Agendaram no DB `postgres` pq `pg_cron` worker exige `cron.database_name=postgres`)

## Vault secrets (8 criados no DB cartorio)

- evolution_api_url, evolution_api_key
- chatwoot_api_key
- n8n_api_key
- opencode_go_api_key
- openclaw_api_key
- telegram_webhook_secret
- cartorio_api_key_placeholder ⚠️ (substituir depois)

## Próximas ações

1. **CRÍTICO**: Corrigir Render key (substituir R01 truncada por R02 completa)
2. **CRÍTICO**: Corrigir N8N workflow 31 node "Audit chain verify" (adicionar X-API-Key header)
3. Substituir 7 secrets placeholder por valores reais
4. Adicionar cron job auto-restart OpenClaw
5. Configurar DNS `n8n.2notasudi.com.br` e `supabase.2notasudi.com.br` (Cloudflare manual)
6. Render preview deployments + Jules auto-fix

Modified by Gustavo Almeida
