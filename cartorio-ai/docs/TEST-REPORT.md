# TEST-REPORT — 2026-07-20

Consolidado histórico das baterias executadas; a execução operacional atual é exclusivamente na VPS do Cartório.

## Resumo

| Bateria | Resultado | Status |
|---|---|---|
| Suíte pytest completa (incl. `test_telegram_1000.py`) | **1000 PASS / 0 fail** | ✅ |
| E2E Telegram (`tests/smoke/`, 20 cenários) | **18/20** | ⚠️ 2 pendências conhecidas |
| Probes funcionais em prod | 3/3 | ✅ |
| Coverage | gate ≥ 90% atendido | ✅ |

## Probes prod (`@test_cartorio_bot`, 2026-07-20)

1. `/start` em chat real → `response_sent=true` ✅
2. Texto livre e mensagem em grupo → `scheduled=true` (debounce async agendado) ✅
3. `getWebhookInfo` → secret registrado, `pending_update_count=0`, 401 sem header ✅

## Pendências E2E (2/20)

- Stress prod assinado (`backend/scripts/stress_telegram_prod*.py` com `X-Telegram-Bot-Api-Secret-Token` via env) — task G9.S1.T9.
- Confirmação de entrega async pós-debounce em grupo real (hoje só `scheduled=true` observado) — G9.S1.T10.

## Regressões cobertas (verdes)

- A1–A3: boot sync líder+secret, URL não-hardcoded, webhook nunca-5xx (commit `d642e0e`).
- A4–A6: fallback morto removido/flag, debounce `chat_id:user_id`, feedback garantido (mesmo commit).
- E2: coerência de slot zen (tupla por conta), timeout 45s, payload por provider (commit `bc9823c`).
- Audit: `t024` (retro-edit), `t025` (rotação HMAC); retenção: `t036`/`t037`; emolumento: `t043`–`t045`.

## Ambiente de execução

- Runner operacional: VPS do Cartório; MacBook apenas cliente SSH.
- Isolamento LLM: `LLM_DEFAULT_PROVIDER=opencode_go` em testes (`tests/conftest.py`) — zero chamada real.
