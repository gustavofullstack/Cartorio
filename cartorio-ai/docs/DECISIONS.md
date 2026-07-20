# DECISIONS — ADRs recentes

Registro de decisões arquiteturais (2026-07-20). Formato: contexto → decisão → consequência.

## ADR-2026-07-20-01 — Webhook Telegram nunca-5xx

- **Contexto**: webhook podia retornar 5xx (JSON inválido re-raise; `bus.client.get` sem try) → Telegram faz retry storm e marca endpoint como falho.
- **Decisão**: envelope em exceções tipadas → sempre ack 200 + DLQ; único 401 possível = `secret_token` inválido/ausente.
- **Consequência**: commit `d642e0e`; regressão A3 coberta por teste; pending=0 confirmado em prod.

## ADR-2026-07-20-02 — Sync de webhook com secret obrigatório

- **Contexto**: todo worker no boot chamava `setWebhook`; worker sem `TELEGRAM_WEBHOOK_SECRET` registrava sem `secret_token`, derrubando a verificação das réplicas.
- **Decisão**: somente worker líder (redlock) sincroniza; fail-fast se secret ausente; URL sem hardcode.
- **Consequência**: boot seguro multi-worker; re-sync prod validado via `POST /api/v1/telegram/set-webhook`.

## ADR-2026-07-20-03 — Debounce keyed por conversa (`chat_id:user_id`)

- **Contexto**: `_DEBOUNCE_METADATA` por `chat_id`, mas filas/locks por `chat_id:user_id` → 2 usuários no mesmo grupo na janela de 1.2s → um nunca recebia resposta; falhas eram silenciosas.
- **Decisão**: alinhar metadata à chave `chat_id:user_id`; fila vazia/exceção → mensagem amigável + métrica.
- **Consequência**: regressão A5/A6 com testes; E2E grupo real validado (2 usuários respondidos).

## ADR-2026-07-20-04 — Slots zen coerentes + timeout 45s + payload por provider

- **Contexto**: slots free herdavam só `API_KEY` (mistura chave↔modelo entre contas); timeout único de 50s × 6 tentativas → até 15-20min de silêncio; `thinking`/`tools` enviados a todos os providers → HTTP 400 em cascata.
- **Decisão**: cada slot herda tupla completa (`API_KEY`,`BASE_URL`,`MODEL`) da mesma conta; timeout global 45s/tentativa com deadline total; payload por allowlist de provider; circuit breaker por slot com fallback determinístico.
- **Consequência**: commit `bc9823c`; teste de coerência de slot no CI; pior caso percebido < 2min.

## ADR-2026-07-20-05 — CNJ massive-dump streaming com gate de audit

- **Decisão**: `/api/v1/lgpd/cnj-exports/massive-dump` com `StreamingResponse` + `yield_per(1000)`, scrub `pii`, API key + JWT DPO, e falha de audit antes do dump ⇒ 500 `AUDIT_FAILURE` sem vazar byte.
- **Consequência**: commits `ff599aa`/`0d15da6`/`6c029fc`; contrato OpenAPI pendente (S4).
