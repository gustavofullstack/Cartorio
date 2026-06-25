# API Endpoints Catalog — Cartório 2º Notas

> Auto-generated from FastAPI OpenAPI spec
> Last updated: 2026-06-25

## Base URL

```
PRODUCTION: https://api.2notasudi.com.br
LOCAL:      http://localhost:8000
```

## Authentication

All endpoints require `X-API-Key` header unless noted.

---

## Health & Monitoring

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Basic health check |
| GET | `/api/v1/health/radar` | Yes | All services status |
| GET | `/api/v1/health/integracoes` | Yes | Integration details |
| GET | `/api/v1/health/backup` | Yes | Backup status |

---

## API v1 — Core Endpoints

### Clientes

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/cliente` | Yes | List clients |
| GET | `/api/v1/cliente/{id}` | Yes | Get client by ID |
| POST | `/api/v1/cliente` | Yes | Create client |
| PATCH | `/api/v1/cliente/{id}` | Yes | Update client (LGPD art. 18 III) |

### Protocolos

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/protocolos` | Yes | List protocols |
| POST | `/api/v1/protocolos` | Yes | Create protocol (LGPD) |
| GET | `/api/v1/protocolos/{id}` | Yes | Get protocol by ID |

### Emolumentos

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/emolumentos` | Yes | List emoluments MG 2026 |
| GET | `/api/v1/emolumentos/{id}` | Yes | Get emolument by ID |

### Agendamentos

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/agendamento/disponibilidade` | Yes | Available slots |
| POST | `/api/v1/agendamento` | Yes | Create appointment |
| GET | `/api/v1/agendamento/pendentes` | Yes | Pending appointments (N8N) |
| GET | `/api/v1/agendamento/proximos` | Yes | Upcoming 24h (N8N) |

### Documentos

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/documento/segunda-via` | Yes | Generate second copy |

---

## API v1 — Webhooks (Inbound)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/webhook/chatwoot` | HMAC | Receive Chatwoot handoff |
| POST | `/api/v1/webhook/evolution` | HMAC | Receive Evolution events |

---

## API v1 — LGPD Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/lgpd/{cpf}/historico` | Yes | Client history (art. 18 IV) |
| PATCH | `/api/v1/cliente/{id}` | Yes | Right to correction (art. 18 III) |
| POST | `/api/v1/lgpd/{cpf}/anonimizar` | Yes | Anonymize data (art. 18 VI) |
| POST | `/api/v1/lgpd/{cpf}/portabilidade` | Yes | Data portability (art. 18 V) |
| GET | `/api/v1/lgpd/{cpf}/portabilidade/download` | Yes | Download portable data |
| POST | `/api/v1/lgpd/{cpf}/oposicao` | Yes | Oppose processing (art. 18 IX) |
| POST | `/api/v1/lgpd/{cpf}/optout` | Yes | Opt-out marketing |

---

## API v1 — Brain/Memory

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/brain/tasks` | Yes | List tasks |
| GET | `/api/v1/brain/lessons` | Yes | List lessons |
| POST | `/api/v1/brain/lesson` | Yes | Create lesson |
| POST | `/api/v1/brain/sync` | Yes | Force brain sync |
| GET | `/api/v1/brain/loop-state` | Yes | Current loop state |

---

## API v1 — Admin

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/admin/slow-queries` | Yes | Slow query log |
| POST | `/api/v1/admin/audit/check-now` | Yes | Trigger audit check |

---

## API v1 — Integrations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/integrations/status` | Yes | Integration status |
| POST | `/api/v1/integrations/n8n/error` | HMAC | N8N error handler |

---

## API v2 (Alpha — Sunset 2027-12-31)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v2/info` | No | API v2 metadata |
| GET | `/api/v2/clientes` | Yes | Client list (cursor pagination) |
| GET | `/api/v2/protocolos` | Yes | Protocol list (cursor pagination) |
| GET | `/api/v2/emolumento` | Yes | Emolument list |

---

## MCP Servers

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/mcp-servers` | No | List MCP servers |
| POST | `/mcp` | No | MCP server endpoint (164 tools) |

---

## OpenAPI Spec

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/openapi.json` | No | OpenAPI 3.1 spec |
| GET | `/docs` | No | Swagger UI |
| GET | `/redoc` | No | ReDoc UI |

---

## Total: 58 endpoints (v1) + 4 endpoints (v2) = 62 endpoints

**Auth**: Most endpoints require `X-API-Key` header
**LGPD**: PII scrubbed before logging, audit trail on all mutations
**Rate Limiting**: Redis-based, fail-open if Redis offline
