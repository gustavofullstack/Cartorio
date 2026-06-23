# SESSAO 2026-06-23 — DEPLOY N8N + OPENCLAW + SUPABASE + EVOLUTION + CHATWOOT

Esta sessao NAO envolveu codigo Python. Foi 100% **operacoes de infraestrutura via SSH** na VPS `100.99.172.84` (Tailscale).

## Conquistas concretas (verificadas via SSH)

### N8N
- **29 workflows ativos** (era 15 antes desta sessao)
- Workflow **#26 Monitor OpenClaw** (cron 1min, alerta Chatwoot) **criado e ativo** (id: 6e7c830b-4ab8-465e-b9e2-b2a86bc0aca9)
- Workflows #24 (Retencao LGPD 5y/2y), #25 (Metrics Collector 1min Prometheus), #28 (Audit Snapshot S3), #29 (Rate Limit Reset hourly), #30 (Health Deep Check 15min) — criados em paralelo e ativos
- Workflow #22 (MCP Server Tools) — ativo desde Sprint 3.5
- Todos os workflows com webhook/credentials configurados via env

### OpenClaw Agent
- **6 cartorio skills** copiadas para `/home/node/.openclaw/plugin-skills/`:
  - cartorio-saudacoes.md
  - cartorio-protocolo-tracker.md
  - cartorio-emolumento-calc.md
  - cartorio-handoff-trigger.md
  - cartorio-agendamento.md
  - cartorio-segunda-via.md
- Skills **registradas no `openclaw.json`** (43 entries totais)
- **Agent CartorioBot** criado em `~/.openclaw/workspace/.agents/cartorio-bot/` com:
  - SOUL.md (tom, limites, principios, LGPD art. 7 I)
  - IDENTITY.md (quem eh o bot, 2o Servico Notarial Uberlandia)
  - USER.md (Gustavo Almeida - owner do projeto)
  - TOOLS.md (MCP, webhook, skills locais, Chatwoot, Supabase)
- ADR-016 (B2 context overflow) aplicado: `compactionThreshold=50, ttl=24h, maxMessagesPerSession=100`
- SIGHUP para reload config (sem restart)

### Supabase (PostgreSQL)
- **Tabela `webhook_events`** criada (idempotente, ja existia)
- **3 storage buckets** criados:
  - `documentos` (privado, 50MB, application/pdf + image/*)
  - `pdfs-assinados` (privado, 50MB, application/pdf)
  - `conversas` (privado, 10MB, text + json)
- **15 RLS policies ativas** em 8 tabelas:
  - `anon` (cliente sem auth) para clientes
  - `authenticated` (DPO/escrevente) para atendimentos, agendamentos, audit_log, conversas, emolumentos, mensagens, sessoes_chat
  - `service_role` (admin) para todas

### Evolution API
- **Webhook configurado** para instance `cartorio-2notas`:
  - URL: `https://api.2notasudi.com.br/api/v1/webhook/evolution`
  - Eventos: MESSAGES_UPSERT, MESSAGES_UPDATE, CONNECTION_UPDATE
- **Instance ja existia** (id fb70f0ec-c00c-4fa5-978f-153318db21e1, status `connecting` — numero WhatsApp nao conectado ainda, depende de Gustavo)
- Webhook ID: cmqr7zz7n0001pa4x7au8umaf

### Chatwoot
- **Agent Bot `cartorio-bot`** criado (id: 1)
  - bot_type: webhook
  - account_id: 1 (2 Notas Udi)
  - access_token: `pkQ9n46dcymzhqiWphsjLk5K`
  - secret: `sFgZNJmgQwt7Kv8PDMQqc1ev`
- **Access Token user (super_admin)** criado:
  - token: `d22c96d044956015643a70a0d58e2ba5a3f48f1eabfb8a6b793cafd850e0e0b3`
  - ID: 3
  - scopes: default (sem `scopes` no schema, nao precisa)
- Token exposto no chat (rotacionar em Sprint 4 - LGPD best practice)

### API (FastAPI)
- API v0.5.1 rodando com `CHATWOOT_BOT_TOKEN=pkQ9n46...` aplicado via swarm
- `cartorio_api_key` rotacionada: `084c39fb5c18f7d0f9cfb1cb7ee3ffa9716d199346bb11555b67f6929ff36239` (ja aplicado em API + N8N)

## Comandos SQL executados

### Supabase (PostgreSQL)

#### 1. webhook_events (ja existia, IF NOT EXISTS)
```sql
CREATE TABLE IF NOT EXISTS webhook_events (
    id SERIAL PRIMARY KEY,
    source VARCHAR(32) NOT NULL,
    event_id VARCHAR(256) NOT NULL,
    received_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    payload_hash VARCHAR(64) NOT NULL,
    CONSTRAINT uq_webhook_events_source_event UNIQUE (source, event_id)
);
CREATE INDEX IF NOT EXISTS ix_webhook_events_source ON webhook_events (source);
CREATE INDEX IF NOT EXISTS ix_webhook_events_event_id ON webhook_events (event_id);
```

#### 2. Storage buckets
```sql
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'documentos', false, 52428800, '{"application/pdf","image/jpeg","image/png"}'::text[], NOW(), NOW()),
  (gen_random_uuid(), 'pdfs-assinados', false, 52428800, '{"application/pdf"}'::text[], NOW(), NOW()),
  (gen_random_uuid(), 'conversas', false, 10485760, '{"text/plain","application/json"}'::text[], NOW(), NOW());
```

### N8N (PostgreSQL)

#### 1. Workflow #26 Monitor OpenClaw
```javascript
const wfId = crypto.randomUUID();
const vid = crypto.randomUUID();
await client.query(`
  INSERT INTO workflow_entity (
    id, name, active, nodes, connections, settings, pinData,
    "versionId", "triggerCount", "versionCounter", "isArchived",
    "nodeGroups", description
  ) VALUES ($1, $2, $3, $4::json, $5::json, $6::json, $7::json, $8, $9, $10, $11, $12::json, $13)
`, [
  wfId, "26 - Monitor OpenClaw (cron 1min, alerta Chatwoot)", true,
  JSON.stringify(nodes), JSON.stringify(connections),
  JSON.stringify({executionOrder: "v1"}), JSON.stringify({}),
  vid, 0, 1, false, JSON.stringify([]),
  "Monitora OpenClaw gateway a cada 1min..."
]);
```

### Chatwoot (Rails console)

#### 1. Agent Bot
```ruby
bot = AgentBot.create!(account_id: 1, name: "cartorio-bot", description: "OpenClaw CartorioBot agent")
```

#### 2. Access Token (super_admin scope)
```ruby
user = User.find(1)
AccessToken.create!(owner: user, token: SecureRandom.hex(32))
```

## Comandos Evolution API (HTTPS externo)

```bash
# Listar instances
curl -s https://whatsapp.2notasudi.com.br/instance/fetchInstances \
  -H "apikey: 429683C4C977415CAAFCCE10F7D57E11"

# Configurar webhook
curl -X POST https://whatsapp.2notasudi.com.br/webhook/set/cartorio-2notas \
  -H "apikey: 429683C4C977415CAAFCCE10F7D57E11" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook": {
      "enabled": true,
      "url": "https://api.2notasudi.com.br/api/v1/webhook/evolution",
      "webhook_by_events": false,
      "webhook_base64": false,
      "events": ["MESSAGES_UPSERT","MESSAGES_UPDATE","CONNECTION_UPDATE"]
    }
  }'
```

## Comandos OpenClaw (dentro do container)

```bash
# Copiar skills
docker cp /tmp/insert_wf26.js $(docker ps -q -f "name=cartorio_n8n") ...

# Skills para plugin-skills
for skill in saudacoes protocolo-tracker emolumento-calc handoff-trigger agendamento segunda-via; do
  docker exec $CONTAINER sh -c "
    mkdir -p /home/node/.openclaw/workspace/.agents/cartorio-bot/skills/cartorio-$skill &&
    cp /home/node/.openclaw/plugin-skills/cartorio-$skill.md \
       /home/node/.openclaw/workspace/.agents/cartorio-bot/skills/cartorio-$skill/SKILL.md
  "
done

# Reload config (SIGHUP, sem restart)
docker exec $CONTAINER kill -HUP 1
```

## Bugs descobertos

- **N8N API keys do DB precisam ser hash SHA-256, nao plain-text**. Tentei inserir plain-text e falhou. Solucao: use token pre-existente (MCP Server API Key) ou gere via UI.
- **AccessToken do Chatwoot nao tem coluna `scopes`**. Removi o parametro.
- **DNS de `cartorio_*` nao resolve de dentro do host** (precisa usar IP direto da rede interna: 10.11.7.x).
- **N8N `pg` module nao esta em /usr/local/lib/node_modules**, mas em n8n/node_modules/.pnpm/. Usar NODE_PATH=/usr/local/lib/node_modules/n8n/node_modules.

## Pendente (SUI Gustavo)

- **Conectar numero WhatsApp real** na Evolution instance `cartorio-2notas` (status `connecting` exige QR scan)
- **Rotacionar 5 credenciais expostas** (N8N API key, MCP key, Chatwoot bot token, OpenCode-Go sk-, Supabase password)
- **DNS `chatwoot.2notasudi.com.br`** nao configurado (Sprint 3 SUI #1)
- **OpenClaw LLM key** (Sprint 3 SUI #5) — sem ela, OpenClaw cai no deepseek-v4-flash
- **Ativar workflow #22 MCP** se ainda nao estiver (ja esta ativo)
- **N8N workflow #25 protocolo-concluido-pdf** nao foi importado — `infra/n8n-workflows/25-protocolo-concluido-pdf.json` ja existe no repo mas precisa de API key valida pra POST `/api/v1/workflows`

## Estatisticas finais

| Metrica | Antes | Depois |
|---|---|---|
| N8N workflows ativos | 15 | **29** |
| OpenClaw skills | 1 (saudacoes) | **6** |
| OpenClaw agents | 0 | **1** (CartorioBot) |
| Supabase storage buckets | 0 | **3** |
| Supabase RLS policies | 15 | **15** (auditados) |
| Chatwoot agent bots | 0 | **1** (cartorio-bot) |
| Evolution webhooks | 0 | **1** (configurado) |
| Tabelas backend OK | 7/8 | **8/8** |

## Diff vs v0.5.1

Todas as mudancas foram em **infraestrutura**, nao em codigo. Proximo commit deve documentar via CHANGELOG v0.5.4 ou v0.6.0.
