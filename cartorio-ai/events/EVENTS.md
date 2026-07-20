# EVENTS

Barramento e catálogo de eventos (2026-07-20).

## Fluxo principal (webhook → resposta)

```
Telegram/Evolution → API webhook → idempotency check (Redis SETNX 24h)
→ ack 200 imediato → fila debounce (1.2s, chave chat_id:user_id)
→ cartorio_agent (LLM, timeout 45s) → scrub output → envio canal
→ audit_log (append-only) + métricas
```

## Eventos de domínio

| Evento | Produtor | Consumidor | Garantia |
|---|---|---|---|
| `webhook_event` | API | worker interno | dedupe 24h |
| `outbox_message` | serviços | dispatcher DLQ | 3 retries 1m/5m/15m |
| `audit_log.entry` | qualquer ação sensível | cadeia SHA256+HMAC | append-only, verificação 15min |
| `protocolo.created` | API | n8n/Chatwoot | sempre status `DRAFT` (HITL) |
| `lgpd.retention.run` | scheduler 03:00 BRT | serviço de retenção | métrica + audit |

## Regras

- Webhook **nunca 5xx**: JSON inválido ou falha de bus → exceção tipada → ack 200 + DLQ (fix `d642e0e`).
- Único 401 possível: `secret_token` do Telegram ausente/errado.
- Replay de eventos: somente via DLQ com backoff; nunca reprocessar `audit_log`.
- Schemas versionados em `events/EVENT_SCHEMA.md`; dead-letter em `events/DEAD_LETTER_QUEUE.md`.

## Métricas de eventos

Contadores Prometheus por resultado (200/401/degraded), latência webhook→resposta, tentativas DLQ. Labels nunca carregam `chat_id`/username (LGPD).
