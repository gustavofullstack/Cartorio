# ENV PRODUCTION - Cartorio 2 Notas Uberlandia

> Documentacao dos valores REAIS de .env em PRODUCAO na VPS Hostinger.
> v0.4.0 (2026-06-23).
>
> **ATENCAO**: Este arquivo documenta nomes de variaveis e formato, NAO contem secrets.
> Os valores reais estao em:
> - VPS: `/etc/easypanel/projects/cartorio/api/code/.env` (chmod 600)
> - VPS: `/etc/cartorio-backup/n8n-api-key.env` (chmod 600)
> - Mac (apenas para consulta): `~/.mavis/secrets/cartorio.env` (chmod 600)
> - Easypanel UI: Services > cartorio_api > Env (UI)

---

## 1. Aplicacao

```bash
APP_ENV=production
APP_NAME=cartorio-backend
APP_PORT=8000
LOG_LEVEL=INFO
```

## 2. Database (Supabase / Postgres)

```bash
# Conexao via hostname 'db' na rede Compose cartorio_supabase_default.
# O monitor em /usr/local/bin/cartorio-network-monitor.sh mantem
# os containers Swarm conectados a essa rede a cada 5 min.
DATABASE_URL=postgresql+psycopg://supabase_admin:<SENHA>@db:5432/cartorio?sslmode=disable
```

**Outros databases no mesmo Postgres** (cada servico tem seu DB proprio, isolado do `cartorio`):

| DB | Owner | Usado por |
|---|---|---|
| `cartorio` | supabase_admin | Backend Python (este repo) |
| `n8n` | supabase_admin | N8N workflows + creds + executions |
| `evolution` | supabase_admin | Evolution API WhatsApp (instances, messages) |
| `chatwoot` | supabase_admin | Chatwoot CRM (conversations, contacts) |
| `_supabase` | supabase_admin | Sistema Supabase (auth, storage, realtime) |
| `postgres` | postgres | Database padrao (nao usar) |

## 3. Redis (cartorio_redis - global)

```bash
# Hostname compose: cartorio_redis
# Senha URL-encoded: %40Techno832466
REDIS_URL=redis://default:<SENHA>@cartorio_redis:6379/0
REDIS_SESSION_TTL_SECONDS=86400
```

**Acesso externo (Mac/SSH)**: `redis://default:<SENHA>@187.77.236.77:1001`

**Regra firewall**: DOCKER-USER DROP bloqueia 6379 externo, apenas porta host 1001.

## 4. Audit Log (LGPD)

```bash
# HMAC key 64 chars hex. Gerar: openssl rand -hex 32
AUDIT_HMAC_KEY=<64_HEX_CHARS>
AUDIT_VERIFY_CRON=0 3 * * *
```

Endpoint: `POST https://api.2notasudi.com.br/api/v1/audit/verify`
Job diario: N8N workflow #8 (Audit Verify Diario, 03:30).

## 5. PII Scrubber

```bash
PII_SCRUB_ENABLED=true
PII_BLOCK_ON_DETECT=true   # bloqueia mensagem se PII detectada (LGPD)
```

Patterns regex aplicados em 3 camadas (input / pre-LLM / output):
- CPF: `\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b`
- RG: `\b\d{1,2}\.?\d{3}\.?\d{3}-?\d{1}\b`
- Phone: `\(\d{2}\)\s?9?\d{4}-?\d{4}`
- Email: `[\w.-]+@[\w.-]+\.\w+`

## 6. LLM Providers

```bash
# Opencode-Go (LOW COST primario - DeepSeek-v4 flash)
OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1
OPENCODE_GO_MODEL=deepseek-v4-flash
OPENCODE_GO_API_KEY=<OPENCODE_GO_KEY>

# OpenClaw gateway (secundario, fallback Anthropic/OpenAI)
OPENCLAW_BASE_URL=http://cartorio_openclaw-gateway:18789
OPENCLAW_API_KEY=<OPENCLAW_GATEWAY_TOKEN>

# Provider default
LLM_DEFAULT_PROVIDER=opencode_go
```

**Decisao (ADR-005)**: LiteLLM foi REMOVIDO após incident de segurança. Chamada direta Opencode-Go + fallback OpenClaw.

## 7. Evolution API (WhatsApp)

```bash
EVOLUTION_BASE_URL=http://cartorio_evolution-api:8080
EVOLUTION_INSTANCE=cartorio-2notas
EVOLUTION_API_KEY=<EVOLUTION_API_KEY>
```

URL publica: `https://whatsapp.2notasudi.com.br/manager`
Versao: Evolution v2.3.7

## 8. Chatwoot (CRM atendimento humano)

```bash
CHATWOOT_BASE_URL=http://cartorio_chatwoot:3000
CHATWOOT_API_KEY=<CHATWOOT_PLATFORM_API_KEY>
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=<INBOX_ID>
```

URL publica (a configurar): `https://chatwoot.2notasudi.com.br`

**Pendencia SUI**: agent bot `cartorio-bot` ainda nao criado. Quando criar via UI, adicionar env `CHATWOOT_BOT_TOKEN` (gerado automaticamente pelo Chatwoot).

## 9. n8n (workflows)

```bash
N8N_BASE_URL=http://cartorio_n8n:5678
N8N_API_KEY=<JWT_API_KEY>
N8N_MCP_URL=https://cartorio-n8n.dfgdxq.easypanel.host/mcp-server/http
N8N_WEBHOOK_SECRET=<HMAC_SECRET_PARA_WEBHOOKS>
```

URL publica: `https://flow.2notasudi.com.br`
Versao: N8N 2.27.3
Workflows ativos: 10 (1-6 meus, 7-10 reais, mais LGPD boas-vindas do Gustavo).
API Key para backup: `/etc/cartorio-backup/n8n-api-key.env` (chmod 600).

## 10. Supabase (acesso direto via Kong)

```bash
# DNS typo 'supbase' mantido por compatibilidade (decisao SUI)
SUPABASE_URL=https://supbase.2notasudi.com.br
SUPABASE_ANON_KEY=<ANON_KEY>
SUPABASE_SERVICE_ROLE_KEY=<SERVICE_ROLE_KEY>
```

**Decisao pendente**: corrigir typo `supbase` -> `supabase` (afeta todos .env + DNS).

## 11. LGPD

```bash
DPO_EMAIL=dpo@2notasudi.com.br
RETENTION_DAYS_CONVERSAS=365
RETENTION_DAYS_AUDIT=1825  # 5 anos
```

## 12. CORS

```bash
CORS_ORIGINS=["http://localhost:3000","https://admin.2notasudi.com.br","https://app.2notasudi.com.br"]
```

## 13. MCP server (expõe API como MCP tools)

```bash
MCP_SERVER_ENABLED=true
MCP_SERVER_TRANSPORT=http
MCP_SERVER_PORT=8100
MCP_API_KEY=<32_CHARS_API_KEY>
```

Endpoint: `http://api.2notasudi.com.br:8100/mcp` (Tailscale only)

---

## Rotacao de chaves

| Quando | O que |
|---|---|
| A cada 90 dias | `AUDIT_HMAC_KEY` (forca re-hash de chain - quebrar chain intencionalmente) |
| Quando exposto em chat | regenerar via UI |
| Quando LiteLLM-like incident | rotacionar TODAS as chaves LLM |

Modified by Gustavo Almeida
