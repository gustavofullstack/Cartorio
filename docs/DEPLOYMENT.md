# Deployment — Cartório Chatbot

> Guia completo de deploy em Easypanel + Traefik + Tailscale.
> Última atualização: 2026-06-24.

## TL;DR

Stack roda em Swarm mode no Hostinger VPS, gerenciado pelo Easypanel UI.

```
VPS Hostinger srv1769726 (187.77.236.77)
├── Traefik (proxy + SSL auto-renew)
├── Easypanel (UI :3000)
└── Stack cartorio_* (14 services Swarm)
    ├── api (FastAPI :8000)
    ├── n8n + n8n-runner (:5678 + :5680)
    ├── chatwoot + chatwoot-sidekiq (:3000)
    ├── evolution-api (:8080)
    ├── openclaw-gateway (:18789)
    ├── redis (:6379)
    └── supabase (14 sub-services)
```

## Pré-requisitos

- VPS Hostinger (srv1769726) com Docker Swarm mode ativo
- Easypanel instalado (porta 3000)
- Domínio `2notasudi.com.br` apontando para o VPS
- Traefik configurado com Let's Encrypt
- SSH Tailscale ativo (recomendado para gestão)

## Variáveis de ambiente

Todas configuradas via Easypanel UI > Service > Edit > Env.

### API (cartorio_api)

```bash
DATABASE_URL=postgresql+psycopg://supabase_admin:$PG_PWD@10.0.1.34:5432/cartorio
REDIS_URL=redis://default:$REDIS_PWD@cartorio_redis:6379/0
AUDIT_HMAC_KEY=<openssl rand hex 32>
CARTORIO_API_KEY=<openssl rand hex 32>
EVOLUTION_API_KEY=<token Evolution>
EVOLUTION_BASE_URL=http://cartorio_evolution-api:8080
OPENCLAW_BASE_URL=http://cartorio_openclaw-gateway:18789
OPENCLAW_API_KEY=<token OpenClaw>
N8N_WEBHOOK_SECRET=<hmac N8N>
N8N_BASE_URL=http://cartorio_n8n:5678
N8N_API_KEY=<N8N global:owner token>
SUPABASE_URL=http://cartorio_supabase-kong:8000
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service_role key>
OPENCODE_GO_API_KEY=<sk-deepseek-v4-flash>
OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1
OPENCODE_GO_MODEL=deepseek-v4-flash
WEBHOOK_EVOLUTION_HMAC_SECRET=<hmac shared>
WEBHOOK_CHATWOOT_HMAC_SECRET=<hmac shared>
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### N8N (cartorio_n8n)

```bash
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=10.0.1.34
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=cartorio
DB_POSTGRESDB_USER=supabase_admin
DB_POSTGRESDB_PASSWORD=$PG_PWD
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http
WEBHOOK_URL=https://flow.2notasudi.com.br/
N8N_COMMUNITY_PACKAGES=["@devlikeapro/n8n-nodes-chatwoot","@winth03/n8n-nodes-minio","n8n-nodes-evolution-api","n8n-nodes-mcp","n8n-nodes-pdfkit"]
TELEGRAM_BOT_TOKEN=<telegram bot token>
EVOLUTION_API_KEY=<token Evolution>
EVOLUTION_API_URL=http://cartorio_evolution-api:8080
CARTORIO_API_KEY=<mesmo da API>
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service_role key>
CHATWOOT_BOT_TOKEN=<chatwoot bot token>
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1
CHATWOOT_BASE_URL=http://cartorio_chatwoot:3000
```

### Evolution API (cartorio_evolution-api)

```bash
DATABASE_CONNECTION_URI=postgres://supabase_admin:$PG_PWD@10.0.1.34:5432/cartorio
AUTHENTICATION_API_KEY=<token Evolution>
STORE_MESSAGES=true
STORE_MESSAGE_UP=true
STORE_CONTACTS=true
```

### OpenClaw Gateway (cartorio_openclaw-gateway)

```bash
OPENCLAW_GATEWAY_TOKEN=<openssl rand hex 32>
OPENCLAW_BIND=auto
OPENCLAW_PORT=18789
OPENCLAW_ALLOW_UNCONFIGURED=true
OPENAI_API_KEY=<sk-...>   # ou ANTHROPIC_API_KEY
OPENAI_BASE_URL=https://api.openai.com/v1   # ou outro LLM provider
```

### Redis (cartorio_redis)

```bash
REDIS_PASSWORD=<senha forte>
```

### Supabase (cartorio_supabase-*)

```bash
POSTGRES_PASSWORD=$PG_PWD
JWT_SECRET=<openssl rand hex 32>
ANON_KEY=<anon key>
SERVICE_ROLE_KEY=<service_role key>
SITE_URL=https://api.2notasudi.com.br
API_EXTERNAL_URL=https://supbase.2notasudi.com.br
```

## Domínios públicos

| Domínio | Container | Porta | Notas |
|---------|-----------|-------|-------|
| `api.2notasudi.com.br` | cartorio_api | 8000 | FastAPI |
| `flow.2notasudi.com.br` | cartorio_n8n | 5678 | N8N UI + webhooks |
| `whatsapp.2notasudi.com.br` | cartorio_evolution-api | 8080 | Evolution Manager + webhook |
| `agent.2notasudi.com.br` | cartorio_openclaw-gateway | 18789 | OpenClaw gateway |
| `easypanel.2notasudi.com.br` | easypanel | 3000 | Easypanel UI |
| `supbase.2notasudi.com.br` | supabase-kong | 8000 | Supabase API gateway (typo intencional) |
| `chatwoot.2notasudi.com.br` | cartorio_chatwoot | 3000 | Chatwoot UI (DNS pendente) |

## Deploy manual

### Atualizar API

```bash
# 1. SSH na VPS
ssh root@100.99.172.84

# 2. Build local + push
cd /Users/gustavoalmeida/projetos/Cartorio
git pull origin master
cd backend
uv sync

# 3. Restart no Swarm (Easypanel cuida disso)
docker service ps cartorio_api
# Trigger redeploy via Easypanel UI ou:
docker service update --force cartorio_api
```

### Atualizar N8N workflows

```bash
# 1. Export workflows para JSON
cd /Users/gustavoalmeida/projetos/Cartorio
git pull origin master
# Workflows já estão em infra/n8n-workflows/

# 2. Import via API N8N
N8N_API_KEY=...
curl -X POST https://flow.2notasudi.com.br/api/v1/workflows \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @infra/n8n-workflows/01-consulta-emolumento.json
```

### Backup pré-deploy

```bash
# Backup Postgres
ssh root@100.99.172.84
docker exec cartorio_supabase-db-1 pg_dump -U supabase_admin cartorio | gzip > /var/backups/cartorio/db-pre-deploy-$(date +%Y%m%d-%H%M%S).sql.gz

# Backup volumes
cd /etc/easypanel/projects/cartorio/
tar czf /var/backups/cartorio/volumes-$(date +%Y%m%d-%H%M%S).tar.gz \
  api/code \
  n8n/code \
  evolution-api/code \
  chatwoot/code \
  openclaw-gateway/code
```

### Rollback

```bash
# Reverter último commit
cd /Users/gustavoalmeida/projetos/Cartorio
git revert HEAD
git push origin master

# Forçar redeploy
docker service update --force cartorio_api
docker service update --force cartorio_n8n
```

## Health checks

| Endpoint | Esperado | Significa |
|----------|----------|-----------|
| `GET /health` (API) | 200 | FastAPI UP |
| `GET /api/v1/health/radar` (API) | 200 + status=green | Todos serviços UP |
| `GET /healthz` (N8N) | 200 | N8N UP |
| `GET /` (Evolution) | 200 | Evolution UP |
| `GET /health` (OpenClaw) | 200 | OpenClaw UP |
| `GET /api/v1/accounts/1` (Chatwoot) | 200 | Chatwoot UP |
| `GET /auth/v1/health` (Supabase) | 200 | Supabase UP |
| `redis-cli PING` (Redis) | PONG | Redis UP |

## CI/CD (TODO — Sprint 3 M6.SMETA.T5)

GitHub Actions planejado:
- Pre-commit: ruff + mypy + pytest com coverage gate 90%
- Pre-push: pytest full + coverage check
- Deploy: trigger Easypanel webhook on master push

## Monitoramento

- **Logs**: `docker service logs -f cartorio_<service>` (stdout JSON)
- **Métricas Prometheus**: `GET /api/v1/metrics/prometheus`
- **Audit chain**: `POST /api/v1/audit/verify` diário 06:00 (WF #22)
- **Alertas**: Telegram IM imediato se QUALQUER service down
- **Radar**: cron `cartorio-radar-consolidado` (5min tick)

## Troubleshooting

### API retorna 500
```bash
docker service logs --tail 100 cartorio_api
docker service ps cartorio_api
docker exec cartorio_api.1.<id> curl http://localhost:8000/health
```

### N8N workflow não executa
```bash
# 1. Verifica execution log
curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
  https://flow.2notasudi.com.br/api/v1/executions?workflowId={id}&limit=3

# 2. Testa webhook manualmente
curl -X POST https://flow.2notasudi.com.br/webhook/{path} \
  -H "Content-Type: application/json" -d '{}'

# 3. Verifica env vars
docker exec cartorio_n8n.1.<id> env | grep -E "API_KEY|URL"
```

### Evolution API não conecta WhatsApp
```bash
# 1. Verifica Manager UI
https://whatsapp.2notasudi.com.br/manager

# 2. Verifica logs Evolution
docker service logs --tail 100 cartorio_evolution-api

# 3. Restart Evolution
docker service update --force cartorio_evolution-api
```

### Supabase auth falha
```bash
# 1. Verifica pg_hba.conf
docker exec cartorio_supabase-db-1 cat /etc/postgresql/pg_hba.conf

# 2. Testa conexão direta
docker exec cartorio_supabase-db-1 psql -U supabase_admin -h 127.0.0.1 -d cartorio -c "SELECT 1"

# 3. Verifica SCRAM hash
docker exec cartorio_supabase-db-1 psql -U supabase_admin -h 127.0.0.1 -d postgres -c "SELECT rolname, rolpassword FROM pg_authid WHERE rolname='supabase_admin'"
```

### Redis AUTH falhou
```bash
# 1. Verifica REDIS_PASSWORD no env
docker exec cartorio_redis.1.<id> env | grep REDIS_PASSWORD

# 2. Testa AUTH manual
docker exec cartorio_redis.1.<id> redis-cli -p 6379 AUTH "<senha>"

# 3. Restart Redis
docker service update --force cartorio_redis
```

## Links úteis

- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — diagrama arquitetural
- [docs/ROADMAP.md](ROADMAP.md) — timeline 12 semanas
- [docs/API.md](API.md) — 31 endpoints
- [docs/CONTRIBUTING.md](CONTRIBUTING.md) — workflow + conventional commits
- [.harness/AGENTS.md](../.harness/AGENTS.md) — regras do projeto
- [.harness/TASKS.md](../.harness/TASKS.md) — task tree

Modified by Mavis (Pietra root mvs_410a1b1266d64830b9dfa31973fdd9fe — 2026-06-24 10:45 BRT)