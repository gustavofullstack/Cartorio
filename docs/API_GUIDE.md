# API Guide — 2o Servico Notarial de Uberlandia

> Guia completo de uso da API REST para desenvolvedores, operadores e integradores.
> v0.6.0 — 2026-07-15 / Missao F6 [P2] / Squad cartorio-front.

## Visao geral

A API do **2o Servico Notarial de Uberlandia** expoe **73 endpoints** versionados sob `/api/v1` (stable) e `/api/v2` (alpha, sunset 2027-12-31). Endpoints estao organizados em 17 tags (Health, Telegram, WhatsApp, LGPD, Audit, Brain, OpenClaw, Auth, Cliente, Protocolo, Emolumento, Atendimento, Integrations, Webhooks, Observability, Admin, Meta).

- **Producao**: `https://api.2notasudi.com.br`
- **Stack**: FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL 16 + Redis 8
- **OpenAPI**: `/openapi.json` (auto-gerado pelo FastAPI)
- **Swagger UI**: `/docs` (customizado com header institucional dark blue)
- **ReDoc**: `/redoc`
- **MCP server**: `/mcp` (sub-app FastMCP, protocolo 2025-03-26)

## Como acessar a documentacao

| Recurso | URL | Descricao |
|---------|-----|-----------|
| Swagger UI | `/docs` | Try-it-out direto, exemplos inline, auth via header |
| ReDoc | `/redoc` | Documentacao read-only estetica |
| OpenAPI JSON | `/openapi.json` | Schema canonico OpenAPI 3.0+ |
| MCP discovery | `/mcp-servers` | Lista MCP servers registrados (5 servers) |
| Version | `/version` | Versao da API + links uteis |

## 5 exemplos curl por canal

### 1. Telegram (webhook inbound)

```bash
curl -X POST https://api.2notasudi.com.br/api/v1/telegram/webhook \
  -H "X-Telegram-Bot-Api-Secret-Token: ${TELEGRAM_WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 123456789,
    "message": {
      "message_id": 1,
      "from": {"id": 111, "is_bot": false, "first_name": "Teste"},
      "chat": {"id": 111, "type": "private"},
      "date": 1717450000,
      "text": "/menu"
    }
  }'
```

Resposta: HTTP 200 com `{status: "ok", response: "..."}` ou HTTP 200 com debounce/idempotency.

### 2. WhatsApp (Evolution API)

```bash
curl -X POST https://api.2notasudi.com.br/api/v1/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "cartorio-2notas",
    "data": {
      "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": false, "id": "wa-1"},
      "message": {"conversation": "oi"},
      "messageType": "conversation",
      "pushName": "Joao"
    }
  }'
```

### 3. Brain (BRAIN2)

```bash
# Listar tasks do .brain/tasks
curl https://api.2notasudi.com.br/api/v1/brain/tasks

# Forcar sync local <-> VPS
curl -X POST https://api.2notasudi.com.br/api/v1/brain/sync

# Estado do loop
curl https://api.2notasudi.com.br/api/v1/brain/loop-state
```

### 4. LGPD (direitos do titular)

```bash
# Solicitar portabilidade (Art. 18 V)
curl -X POST https://api.2notasudi.com.br/api/v1/cliente/123/lgpd/portabilidade \
  -H "X-API-Key: ${CARTORIO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{}'

# Download da portabilidade (ZIP)
curl https://api.2notasudi.com.br/api/v1/cliente/123/lgpd/portabilidade/download \
  -o portabilidade_cliente_123.zip

# RIPD (Relatorio de Impacto a Protecao de Dados)
curl https://api.2notasudi.com.br/api/v1/lgpd/ripd | jq

# Privacy Policy personalizada por titular
curl https://api.2notasudi.com.br/api/v1/lgpd/privacy-policy
```

### 5. Emolumento + Protocolo

```bash
# Calcular emolumento (TABELA_2026_MG)
curl -X POST https://api.2notasudi.com.br/api/v1/emolumento/calcular \
  -H "Content-Type: application/json" \
  -d '{"ato": "certidao_negativa", "valor_declarado": 100000.00}'

# Criar protocolo (HITL obrigatorio: nasce DRAFT)
curl -X POST https://api.2notasudi.com.br/api/v1/protocolo \
  -H "X-API-Key: ${CARTORIO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"tipo": "certidao_negativa", "cliente_id": 1, "observacoes": "Solicitacao inicial"}'

# Escrevente valida e conclui
curl -X POST https://api.2notasudi.com.br/api/v1/protocolo/456/concluir \
  -H "X-API-Key: ${CARTORIO_API_KEY}"
```

## Postman: passo-a-passo

### 1. Importar Collection

1. File > Import
2. Selecionar `postman/Cartorio_API_v1.postman_collection.json`
3. Confirmar (Postman v9+ detecta schema v2.1.0)
4. Collection "Cartorio API v1" aparece na sidebar

### 2. Importar Environment

1. File > Import
2. Selecionar `postman/Cartorio_Env.production.postman_environment.json`
3. Environment "Cartorio Env - Production" aparece em Environments
4. Selecionar no dropdown superior direito

### 3. Configurar secrets

1. Clicar no olho (eye icon) > Edit
2. Substituir `REPLACE_WITH_*` pelos valores reais:
   - `telegram_bot_token` — BotFather token
   - `telegram_webhook_secret` — env `TELEGRAM_WEBHOOK_SECRET`
   - `x_api_key_dpo` — env `CARTORIO_API_KEY`
   - `x_api_key_n8n` — env `N8N_API_KEY`
   - `openclaw_gateway_token` — env `OPENCLAW_GATEWAY_TOKEN`
   - `jwt_dpo` — obtido via `POST /api/v1/auth/login`
3. **NAO commitar** environment modificado.

### 4. Newman CLI (CI/CD)

```bash
npm install -g newman
newman run postman/Cartorio_API_v1.postman_collection.json \
  --environment postman/Cartorio_Env.production.postman_environment.json \
  --reporters cli,html \
  --reporter-html-export newman-report.html
```

Ver `postman/README.md` para detalhes completos.

## Swagger UI tour

1. Acesse `https://api.2notasudi.com.br/docs`.
2. Topo: header institucional "Cartorio 2 Notas Uberlandia - Backend API" + links para ReDoc/openapi.json/MCP/MCP Servers.
3. Secoes (tags) em ordem canonica: Health, Telegram, WhatsApp, LGPD, Audit, Brain, OpenClaw, Auth, Cliente, Protocolo, Emolumento, Atendimento, Integrations, Webhooks, Observability, Admin, Meta, Dev.
4. Click em qualquer endpoint para expandir:
   - `Try it out` (botao cinza) para editar parametros
   - `Authorize` (cadeado verde) para setar X-API-Key
   - Schema de request/response expandido
5. Filtro por texto (topo direito) — busca por path, tag, descricao.

## Health Radar interpretation guide

### Categorias de status

| Cor | Status | Significado | Acao |
|-----|--------|-------------|------|
| Verde | `up` | Servico saudavel | Nenhuma |
| Amarelo | `warn` | Degradado mas funcional | Investigar (latencia alta, capacidade) |
| Vermelho | `down` | Servico indisponivel | Alert imediato + runbook |

### Endpoints

- `GET /health` — liveness probe simples
- `GET /ready` — readiness probe (DB + audit chain inicializados)
- `GET /api/v1/health/radar` — 7 servicos (database/redis/openclaw/chatwoot/supabase/n8n/evolution). Publico.
- `GET /api/v1/health/radar/expanded` — 6 categorias (health + DNS + Traefik + SSH + Disk). F6 [P2].
- `GET /api/v1/health/integracoes` — 8 servicos com `latency_ms` + `status_code` + `erro` (workflow N8N #30).

### Interpretacao do radar expanded

```json
{
  "status": "yellow",
  "categories": {
    "health": {"database": {"status": "up", "latency_ms": 5, "detail": "..."}, ...},
    "dns": {"2notasudi.com.br": {"status": "up", "latency_ms": 213, "detail": "resolved: 195.35.60.67"}},
    "traefik": {"api.2notasudi.com.br": {"status": "warn", "latency_ms": 93, "detail": "Traefik router not matched (404 + cl=2901)"}},
    "ssh": {"ssh_vps": {"status": "down", "latency_ms": 16, "detail": "187.77.236.77:22 ConnectionRefusedError"}},
    "disk": {"docker_volumes": {"status": "warn", "latency_ms": 0, "detail": "free=5.2GB / total=100GB (94.8% used)"}}
  },
  "metadata": {"version": "0.6.0", "domain_count_dns": 10, ...}
}
```

- `status` agregado:
  - `red` — database OU redis down (critico).
  - `yellow` — qualquer outro check `down` OU qualquer check `warn`.
  - `green` — todos up.

Ver [API_HEALTH_RADAR.md](platforms/API_HEALTH_RADAR.md) para detalhes.

## Cross-references

- **Postman**: `postman/Cartorio_API_v1.postman_collection.json` + `postman/Cartorio_Env.production.postman_environment.json` + `postman/README.md`.
- **Catalog**: `.brain/api-specs/catalog.py` (73 endpoints catalogados).
- **Platforms docs**: `docs/platforms/` (N8N, Chatwoot, Evolution API, OpenClaw, Supabase, Redis).
- **Architecture**: `docs/ARCHITECTURE.md` (C4 + ADRs).
- **LGPD**: `docs/LGPD.md`.

## Autenticacao

### X-API-Key (admin/integrations)

```bash
curl https://api.2notasudi.com.br/api/v1/admin/audit/health \
  -H "X-API-Key: ${CARTORIO_API_KEY}"
```

3-tier rate limit (sliding window 60/min): N8N 600/min, DPO 60/min, default 30/min. Fail-open se Redis cair.

### JWT DPO (LGPD v2)

```bash
# 1. Login
JWT=$(curl -s -X POST https://api.2notasudi.com.br/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "dpo", "password": "'${DPO_PASSWORD}'"}' | jq -r .access_token)

# 2. Endpoint LGPD v2 com JWT
curl https://api.2notasudi.com.br/api/v1/lgpd/dpo/metrics \
  -H "Authorization: Bearer ${JWT}"
```

### HMAC Telegram webhook

```bash
curl -X POST https://api.2notasudi.com.br/api/v1/telegram/webhook \
  -H "X-Telegram-Bot-Api-Secret-Token: ${TELEGRAM_WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d @payload.json
```

## Compliance LGPD

- **HITL obrigatorio**: protocolo nasce como `DRAFT`. Escrevente valida antes de processar.
- **PII NUNCA raw**: CPF/telefone/email hasheados (sha256+salt) antes de qualquer LLM externa.
- **Audit log imutavel**: SHA256 chain + HMAC. Cada acao deixa rastro verificavel.
- **Retencao**: 365 dias conversas / 1825 dias (5 anos) audit log.
- **DPO**: dpo@2notasudi.com.br
- **LGPD Art. 18**: anonimizar, corrigir, oposicao, optout, portabilidade, esquecimento.

## MCP (Model Context Protocol)

A propria API expoe tools MCP em `/mcp` (sub-app FastMCP 3.4.2, protocolo 2025-03-26). Tools discovery em `/mcp-servers`. Lista canonica de tools em `backend/mcp_server.py` (grep `@mcp.tool(`).

Modified by Gustavo Almeida.