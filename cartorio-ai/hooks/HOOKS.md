# HOOKS

Hooks de ciclo de vida do atendimento e da engenharia (2026-07-20).

## Hooks de mensagem (backend)

| Hook | Ponto | Comportamento |
|---|---|---|
| `PRE_RESPONSE` | Antes do LLM | Scrub PII camada 2 (pre-LLM) — `pii.py` |
| `POST_RESPONSE` | Após LLM | Scrub PII camada 3 (output) + métricas de latência |
| `ON_CUSTOMER_MESSAGE` | Webhook recebido | Idempotência (SETNX 24h) → ack 200 imediato → processamento async |
| `ON_ESCALATION` | `/humano` ou baixa confiança | Handoff Chatwoot, mute do bot, registro audit |
| `ON_ERROR` | Exceção tipada | RFC 7807 problem details + DLQ se falha de entrega |

## Hooks de engenharia (repo)

- `pre-commit`: `make pre-commit` (lint + fast test) + `check_no_literal_keys.py`.
- `pre-push`: mypy strict (0 errors) + bateria completa com coverage.
- `.pre-commit-config.yaml` é a fonte; hooks locais em `.hooks/`.

## Hooks de infra (lifespan FastAPI)

1. Startup: OTel → DB smoke → `create_all` → audit startup check.
2. Scheduled: dead-man's-switch audit (15min) + retenção LGPD (03:00 BRT diário).
3. Boot Telegram: somente worker líder (redlock) faz `sync_telegram_webhook()`; fail-fast se `TELEGRAM_WEBHOOK_SECRET` ausente (commit `d642e0e`).
4. Shutdown: flush de outbox, fechamento de pools, deregistro limpo.

## Segurança

- Hooks nunca logam PII (filtro `log_masker.py` aplicado em todos os handlers).
- Falha em hook de segurança = fail-closed (ver `guardrails/FAIL_CLOSED.md`).
