# RECOVERY

Recuperação de falhas (2026-07-20).

## Estratégias por camada

| Falha | Estratégia |
|---|---|
| Webhook Telegram | Sempre 200 (exceto 401 secret); erro interno → ack + DLQ, nunca 5xx |
| LLM slot down | Circuit breaker pula slot → próximo da fallback chain; cache como último recurso |
| Redis down | Rate limit fail-open; idempotência degrada (log + alerta); webhook continua |
| Postgres down | API 503 controlado; healthcheck Swarm reinicia; restore via `operations/RESTORE.md` |
| Envio de mensagem falho | `outbox_message` DLQ: 3 tentativas, backoff 1m/5m/15m, depois dead-letter + alerta |
| Debounce queue vazia/erro | Mensagem amigável ao usuário + métrica (nunca silêncio — regressão A6) |

## Modo degradado

- Sem LLM: respostas de FAQ estáticas + handoff humano sugerido.
- Sem Chatwoot: fila de handoff persistida, alerta ao escrevente por Telegram.
- Sem Evolution: WhatsApp pausado (já é o estado atual — QR pendente).

## Reconciliação de estado

- Idempotência por `update_id` (24h): replay seguro de updates do Telegram.
- `webhook_event` permite auditoria do que entrou vs. o que foi processado.
- State reconciliation detalhada em `recovery/STATE_RECONCILIATION.md`.

## Rollback

- Código: `git revert` + redeploy via EasyPanel; migrations reversíveis (downgrade testado em staging).
- Dados: restore de backup Postgres (dry-run validado 2026-07-16).
- Audit log **nunca** faz rollback — cadeia é append-only por design.
