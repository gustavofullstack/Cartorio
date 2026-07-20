# INTEGRATIONS

Integrações externas do ecossistema (estado 2026-07-20).

## Matriz de integrações

| Sistema | Papel | Estado | Gotcha crítico |
|---|---|---|---|
| Telegram Bot API | Canal ativo | ✅ validado 2026-07-20 | Webhook exige `secret_token`; resposta sempre 200 exceto 401 |
| Evolution API 2.3.7 | Gateway WhatsApp | ⏸ `state=close` (QR pendente) | Webhook chega em 2 formatos: root `message` **e** `data.message` — parser aceita ambos |
| n8n | Workflow engine | ✅ 1/1 | `/mcp-server/http` retorna 401 silencioso se auth header errado |
| Chatwoot 4.x | CRM/handoff humano | ✅ 1/1 | Exige extensão **pgvector** no Postgres — sem ela crashloop |
| OpenClaw 0.4.x | Gateway de agente | ✅ 1/1 | `/v1/chat` via WS; HTTP 404 conhecido em schema errado |
| Supabase (Postgres 17 + pgvector) | Banco central | ✅ 1/1 | Alembic gerencia schema; GRANTs no `public` são causa comum de CrashLoop |
| Redis 8 | Cache/idempotência/rate limit | ✅ 1/1 | Fail-open: se cair, rate limit degrada sem derrubar webhook |
| Traefik | Edge proxy + SSL | ✅ 1/1 | 6 domínios com cert LE |
| LiteLLM | Proxy LLM | ✅ 1/1 | Fallback chain atrás do cartorio_agent |

## Padrões transversais

- Idempotência de webhooks: Redis SETNX por `update_id`/evento, TTL 24h.
- DLQ (`outbox_message`): 3 tentativas com backoff exponencial 1m/5m/15m.
- Timeouts: LLM 45s/tentativa; HTTP externos com retry + backoff (`integrations/RETRIES.md`).
- Segredos: somente via env/`.secrets` — nunca literal em código (checker `check_no_literal_keys.py`).
