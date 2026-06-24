# API — Cartório Chatbot

> **34 endpoints REST + 4 MCP tools + 16 N8N workflows + 6 webhooks.**
> Base URL prod: `https://api.2notasudi.com.br`
> OpenAPI/Swagger: `https://api.2notasudi.com.br/docs`
> ReDoc: `https://api.2notasudi.com.br/redoc`
> Versão: 0.6.0 (master)

---

## Autenticação

**3 modos de auth**:

| Tipo | Header | Uso |
|---|---|---|
| X-API-Key | `X-API-Key: <64hex>` | Endpoints internos + admin + DPO |
| HMAC SHA256 | `X-Signature: sha256=<hex>` | Webhooks externos (Evolution, Chatwoot) |
| Idempotency-Key | `Idempotency-Key: <uuid>` | POST idempotente (Redis SETNX 24h) |

### Como gerar X-API-Key
```bash
openssl rand -hex 32  # 64 chars hex
```

### Como calcular HMAC SHA256
```bash
BODY='{"event":"message","data":{"key":{"id":"abc123"}}}'
SECRET="<AUDIT_HMAC_KEY>"
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')
curl -X POST https://api.2notasudi.com.br/api/v1/webhook/chatwoot \
  -H "Content-Type: application/json" \
  -H "X-Signature: sha256=$SIG" \
  -d "$BODY"
```

### Rate limiting
- `X-RateLimit-Limit: 60`
- `X-RateLimit-Remaining: 42`
- `X-RateLimit-Reset: <epoch>`

Sliding window 60 req/min/IP. Se excedido: `429 Too Many Requests`.

### Versionamento
- `/api/v1/*` — estável
- `/api/v2/*` — alpha (sunset 2027)

---

## Endpoints (34 total)

### Health (8 — sem auth)

| Método | Path | Summary |
|---|---|---|
| GET | `/` | Root info |
| GET | `/health` | FastAPI default |
| GET | `/health/live` | Liveness |
| GET | `/health/ready` | Readiness (DB+Redis) |
| GET | `/health/db` | DB latência |
| GET | `/health/redis` | Redis check |
| GET | `/health/llm` | LLM provider |
| GET | `/health/radar` | 7 serviços paralelo |

```bash
curl -s https://api.2notasudi.com.br/api/v1/health/live
# {"status":"alive","service":"cartorio-api","version":"0.6.0"}
```

### Emolumento (1)

```bash
curl -s "https://api.2notasudi.com.br/api/v1/emolumento/calcular?tipo_documento=escritura&valor=150000" \
  -H "X-API-Key: $CARTORIO_API_KEY"
# {"valor_base":1500.00,"valor_total":1620.00,"tabela_referencia":"TABELA_2026_MG","valido_ate":"2026-12-31"}
```

### Protocolo (5)

```bash
curl -X POST https://api.2notasudi.com.br/api/v1/protocolo/criar-api \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $CARTORIO_API_KEY" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "cliente_id": "uuid-cliente-1234",
    "tipo_documento": "escritura_compra_venda",
    "valor_ato": 150000.00,
    "consent_granted": true,
    "actor_id": "escrevente-001"
  }'
# {"protocolo_id":"uuid-...","numero":"CART-2026-000123","status":"draft","hitl_required":true}

curl -s "https://api.2notasudi.com.br/api/v1/protocolo/CART-2026-000123" \
  -H "X-API-Key: $CARTORIO_API_KEY"
```

### Cliente (4)

```bash
# LGPD direito portabilidade
curl -s "https://api.2notasudi.com.br/api/v1/cliente/uuid-1234/export?formato=json" \
  -H "X-API-Key: $CARTORIO_API_KEY" -o cliente-1234-export.json
```

### Documento (3)

```bash
curl -X POST https://api.2notasudi.com.br/api/v1/documento/upload \
  -H "X-API-Key: $CARTORIO_API_KEY" \
  -F "file=@/path/to/cpf.pdf" \
  -F "cliente_id=uuid-1234" \
  -F "tipo_documento=rg"
```

### Atendimento (5)
- POST `/atendimento` — cria
- GET `/atendimento/{id}` — busca
- POST `/atendimento/{id}/concluir` — encerra
- POST `/atendimento/{id}/pesquisa-enviada` — marca pesquisa
- GET `/atendimento/{id}/pesquisa` — resultado

### Cron (1)

```bash
curl -X POST https://api.2notasudi.com.br/api/v1/cron/stale-detector \
  -H "X-API-Key: $CARTORIO_API_KEY"
# {"stale_count":3,"atendimentos":["uuid1","uuid2","uuid3"]}
```

### Webhooks (3)

| Método | Path | Auth | Summary |
|---|---|---|---|
| POST | `/webhook/evolution` | HMAC | WhatsApp (idempotente) |
| POST | `/webhook/chatwoot` | HMAC | Chatwoot (handoff) |
| POST | `/webhook/telegram` | (interno) | Telegram bot |

### DLQ (2)

```bash
curl -X POST https://api.2notasudi.com.br/api/v1/dlq/evolution/enqueue \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $CARTORIO_API_KEY" \
  -d '{
    "payload": {"message_id":"abc","scrubbed_text":"oi"},
    "actor_id": "sistema",
    "next_retry_at": "2026-06-25T00:00:00Z"
  }'
```

### Admin (5)

```bash
# Pausar bot (HITL universal)
curl -X POST https://api.2notasudi.com.br/api/v1/admin/agent/pause \
  -H "X-API-Key: $CARTORIO_API_KEY" \
  -d '{"reason":"manutencao","duration_minutes":30}'
```

### Integrations (2)
- POST `/integrations/opencode/test`
- POST `/integrations/evolution/test`

### Audit (2)

```bash
# Verificar integridade hash chain
curl -s https://api.2notasudi.com.br/api/v1/audit/verify \
  -H "X-API-Key: $CARTORIO_API_KEY"
# {"ok":true,"last_valid_position":12453,"chain_length":12453}
```

---

## MCP Server (4 tools)

Exposto via `/mcp` (protocolo 2025-03-26):

| Tool | Descrição |
|---|---|
| `criar_protocolo` | Cria protocolo DRAFT (HITL) |
| `consultar_protocolo` | Busca por número ou ID |
| `calcular_emolumento` | Calcula valor MG 2026 |
| `consultar_audit` | Busca log auditoria (DPO) |

---

## WebSocket (1)

```javascript
const ws = new WebSocket('wss://api.2notasudi.com.br/api/v1/ws/atendimentos');
ws.onmessage = (e) => JSON.parse(e.data);
```

---

## Response shapes (RFC 7807)

```json
{
  "type": "https://api.2notasudi.com.br/errors/lgpd-blocked",
  "title": "LGPD Block",
  "status": 422,
  "detail": "Cliente nao concedeu consentimento",
  "request_id": "uuid-...",
  "timestamp": "2026-06-24T13:23:45Z"
}
```

---

## LGPD nos responses

**NUNCA** retornamos PII puro. Sempre:
- `cpf_hash` (SHA256+salt) em vez de CPF
- `***.***.***-**` em logs
- `consent_granted: false` bloqueia resposta

---

Modified by ZCode/Mavis + Gustavo Almeida — 2026-06-24
