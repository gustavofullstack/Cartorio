# CONTRACTS

Contratos de dados entre componentes (2026-07-20).

## Contratos HTTP (API v1)

- Erros: RFC 7807 problem details (`app/middleware/problem_details.py`) — `type`, `title`, `status`, `detail`, `instance`.
- Versão: header `X-API-Version`; `/api/v2/` alpha com sunset 2027-12-31.
- Auth: `X-API-Key` (3-tier rate limit) + JWT para roles (DPO).
- Nunca retornar ORM direto — sempre Pydantic v2 response models.

## Schemas de mensagem (canais)

- **Telegram update**: aceito somente com `secret_token` válido; payload normalizado internamente (`chat_id`, `user_id`, `text`, `update_id`).
- **Evolution webhook**: parser aceita formato legado root-level `message` **e** aninhado `data.message` (ambos em prod).
- **Resposta interna**: `{ response_sent, scheduled, channel, masked_meta }` — nunca PII.

## Schemas de persistência (SQLAlchemy 2.0 typed)

- `cliente`, `conversa`, `protocolo` (nasce `DRAFT`), `documento`, `emolumento`, `agendamento`, `atendimento`.
- `audit_log` (campos: hash anterior, hash atual, HMAC, actor, ação, payload scrubado).
- `webhook_event` (dedupe), `outbox_message` (DLQ: attempts, next_retry, last_error).

## Contratos LLM

- Request: `{ messages, model, timeout: 45s, payload_mode: minimal|full }` por provider.
- Response normalizada: `{ text, provider, slot, latency_ms, attempts }`.
- Schemas detalhados por entidade em `contracts/*_SCHEMA.md` (message, task, event, tool_call, error).
