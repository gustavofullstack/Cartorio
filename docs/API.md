# API — Cartório Chatbot

> Documentação completa dos endpoints HTTP do backend FastAPI.
> Base URL prod: `https://api.2notasudi.com.br`
> OpenAPI/Swagger: `https://api.2notasudi.com.br/docs`
> ReDoc: `https://api.2notasudi.com.br/redoc`
> Versão: 0.5.4 (master @ b370895)

## Auth

Todos os endpoints `/api/v1/*` exigem header `X-API-Key: <CARTORIO_API_KEY>` (exceto webhooks Evolution/Chatwoot que usam HMAC).

Webhooks (Evolution + Chatwoot) usam header `X-Signature: <hmac_sha256(body, AUDIT_HMAC_KEY)>`.

Endpoints `/admin/*` + `/audit/*` exigem role DPO/escrevente (validado por `X-API-Key` no allowlist).

## Tags + Endpoints (31 total)

### Meta (4 endpoints — sem auth)

| Método | Path | Summary |
|---|---|---|
| GET | `/health` | Health check (FastAPI) |
| GET | `/ready` | Readiness (deps UP) |
| GET | `/` | Root info |
| GET | `/mcp-servers` | Lista MCP servers disponíveis |

### Emolumento (1)

| Método | Path | Summary |
|---|---|---|
| GET | `/api/v1/emolumento/calcular` | Calcula emolumento + adicionais (5% folha, 50% urgencia). Snapshot tabela oficial MG 2026. |

### Protocolo (3)

| Método | Path | Summary |
|---|---|---|
| GET | `/api/v1/protocolo/{numero}` | Consulta protocolo por número |
| POST | `/api/v1/protocolo` | Criar protocolo (HITL DRAFT obrigatório) |
| GET | `/api/v1/protocolo/recentes-concluidos` | Lista concluídos últimos N min (N8N #25) |

### Webhook (2)

| Método | Path | Summary |
|---|---|---|
| POST | `/api/v1/webhook/evolution` | Webhook WhatsApp (Evolution API) — HMAC + idempotency |
| POST | `/api/v1/webhook/chatwoot` | Webhook Chatwoot (handoff) — HMAC + idempotency |

### Audit (3) — DPO/escrevente

| Método | Path | Summary |
|---|---|---|
| POST | `/api/v1/audit/verify` | Verificar integridade hash chain SHA256+HMAC |
| GET | `/api/v1/audit/logs` | Lista audit logs paginados (LGPD art. 37) |
| GET | `/api/v1/audit/logs/{log_id}` | Busca 1 entry por ID |

### Health (2)

| Método | Path | Summary |
|---|---|---|
| GET | `/api/v1/health/radar` | Health radar multi-serviço (API+N8N+EVO+CW+OCL+SUP+RED) |
| GET | `/api/v1/health/backup` | Status do backup diário (N8N #09) |

### Agendamento (1)

| Método | Path | Summary |
|---|---|---|
| GET | `/api/v1/agendamento/disponibilidade` | Consultar slots livres (N8N #05) |

### Documento (2)

| Método | Path | Summary |
|---|---|---|
| POST | `/api/v1/documento/segunda-via` | Emitir segunda via PDF (N8N #06) |
| POST | `/api/v1/documento/upload` | Upload PDF assinado com hash SHA256 |

### Atendimento (6)

| Método | Path | Summary |
|---|---|---|
| GET | `/api/v1/atendimentos/ultimas-24h` | Lista concluídos últimas 24h (N8N #07) |
| POST | `/api/v1/atendimento/{id}/pesquisa-enviada` | Marcar pesquisa NPS enviada |
| POST | `/api/v1/atendimento` | Criar atendimento (handoff Chatwoot ou webhook externo) |
| POST | `/api/v1/atendimento/{id}/concluir` | Concluir atendimento (registra timestamp) |
| GET | `/api/v1/atendimento/{session_id}/historico` | Histórico (Redis + Supabase) |
| GET | `/api/v1/atendimento/list-active` | Lista sessões ativas (últimas N horas) |

### CRON (1)

| Método | Path | Summary |
|---|---|---|
| POST | `/api/v1/cron/stale-detector` | Marca atendimentos parados como stale (N8N #23) |

### Cliente (2)

| Método | Path | Summary |
|---|---|---|
| DELETE | `/api/v1/cliente/{id}` | Direito ao esquecimento (LGPD art. 18 VI) |
| GET | `/api/v1/cliente/{id}/historico` | Histórico completo (timeline LGPD) |

### Admin (1)

| Método | Path | Summary |
|---|---|---|
| POST | `/api/v1/admin/retencao/run` | Job retenção LGPD (5y COM / até-revogação SEM) |

### Dev (1)

| Método | Path | Summary |
|---|---|---|
| GET | `/api/v1/postman` | Exporta coleção Postman v2.1.0 |

### Metrics (1)

| Método | Path | Summary |
|---|---|---|
| GET | `/api/v1/metrics/prometheus` | Metrics em formato Prometheus |

### Integrações (2)

| Método | Path | Summary |
|---|---|---|
| POST | `/api/v1/integrations/opencode/test` | Smoke test OpenCode-Go LLM provider |
| GET | `/api/v1/integrations/agent/health` | Health do OpenClaw gateway |

## WebSocket (1)

| Método | Path | Summary |
|---|---|---|
| WS | `/ws/atendimentos` | Real-time dashboard (broadcaster Redis pub/sub channel `cartorio:atendimentos`) |

## Schemas principais (Pydantic v2)

- `EmolumentoCalculo` (input): tipo, folhas, urgente, isencao
- `ProtocoloResponse` (output): numero, cliente_id, ato, valor_snapshot, status, created_at
- `AuditLog` (output): id, action, actor, payload_hash, prev_hash, hmac, timestamp
- `Atendimento` (output): id, cliente_id, canal, instance_name, session_id, status, last_msg_at
- `Cliente` (output): id, cpf_hash, nome, consent_at, consent_ip, retencao_5y

## Validações e LGPD

- **PII scrub**: input passa por `pii.scrub()` ANTES de LLM call. Output também passa (3 sites: opencode_go.py:390, router.py:553, integrations.py:190).
- **Audit log**: toda mutação grava `audit_log` (append-only + SHA256 chain + HMAC).
- **Consentimento**: armazenado `consent_at`, `consent_ip`, `consent_user_agent`, `consent_canal`.
- **Retenção**: 5y cliente COM protocolo (Provimento 74 CNJ + LGPD art. 7 II) / até-revogação cliente SEM (LGPD art. 7 I).
- **IP**: armazenado completo 2y, exibido truncado /24 (LGPD art. 5 I).
- **Webhook idempotency**: Redis SETNX com TTL 5min, rejeita replay.
- **Dead-letter queue**: Redis para webhooks falhados, retry 3x exp backoff.

## Erros (códigos)

| Código | Significado |
|---|---|
| 200 | OK |
| 400 | Validation error (Pydantic) |
| 401 | Missing/invalid X-API-Key |
| 403 | Role insuficiente (DPO/escrevente only) |
| 404 | Recurso não encontrado |
| 409 | Conflict (protocolo duplicado, consent já revogado) |
| 422 | LGPD blocked (PII sem consent) |
| 429 | Rate limit (60 req/min/IP) |
| 500 | Internal error (audit log obrigatório) |
| 502 | Dependência upstream down (N8N/EVO/CW) |

## Variáveis de ambiente principais (`.env`)

```
DATABASE_URL=postgresql+psycopg://supabase_admin:$PG_PWD@db:5432/cartorio
REDIS_URL=redis://default:$REDIS_PWD@cartorio_redis:6379/0
AUDIT_HMAC_KEY=<openssl rand hex 32>
CARTORIO_API_KEY=<openssl rand hex 32>  # mesmo valor no N8N
EVOLUTION_API_KEY=<token Evolution>
OPENCLAW_API_KEY=<token OpenClaw>
N8N_WEBHOOK_SECRET=<hmac N8N>
OPENCODE_GO_API_KEY=<sk-...>
```

## Workflows N8N que chamam esta API

- WF #01: `/webhook/consulta-emolumento` → `GET /emolumento/calcular`
- WF #02: `/webhook/criar-protocolo` → `POST /protocolo`
- WF #03: `/webhook/handoff-human` → cria atendimento + aciona Chatwoot
- WF #04: `/webhook/boas-vindas` → LGPD consent capture
- WF #07: pesquisa satisfação (NPS) → `POST /atendimento/{id}/pesquisa-enviada`
- WF #08: audit verify diário 06:00 → `POST /audit/verify`
- WF #09: backup monitor 04:00 → `GET /health/backup`
- WF #22: audit verify 6h
- WF #23: stale detector → `POST /cron/stale-detector`
- WF #25: metrics collector → `GET /metrics/prometheus`

## MCP Server

A API expõe um MCP server em `/mcp/mcp` (FastMCP 3.x, 14 tools). Tools disponíveis:
- calcular_emolumento
- criar_protocolo
- buscar_protocolo
- criar_agendamento
- listar_horarios
- gerar_segunda_via
- enviar_pesquisa
- consultar_cpf_hash
- criar_handoff
- validar_consent
- upload_storage
- enviar_whatsapp
- criar_chatwoot_contact
- audit_verify

## Status

- **Master HEAD**: b370895 (mega plano de melhoria - 100 tasks)
- **Testes**: 382 passed, 92.22% coverage
- **Lint**: ruff 0 erros
- **Typecheck**: mypy 0 erros
- **OpenAPI auto-gerado**: /docs + /redoc

Modified by Mavis (Pietra root mvs_410a1b1266d64830b9dfa31973fdd9fe — 2026-06-24 10:30 BRT)