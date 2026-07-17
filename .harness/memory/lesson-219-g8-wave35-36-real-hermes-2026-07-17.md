# Lesson 219 — G8 Wave 35/36 REAL (Hermes) — 2026-07-17

## Contexto
Continue do G8 honesty-reset (13/100). PROGRESS tinha ticks fake S05–S25. Esta wave entrega **código + testes** sem tick fraudulento.

## Tasks evidenciadas (+7 → 20/100)

| ID | Artefato | Tests |
|----|----------|-------|
| G8.01.T1 | `ws_concurrency.py` MockWS 100+ | `test_ws_concurrency_g8.py` |
| G8.01.T3 | `ws_heartbeat.py` + `/ws/atendimentos` | `test_ws_heartbeat_g8.py` |
| G8.02.T1 | `dialog_history.py` token budget + telegram wire | `test_dialog_history_g8.py` |
| G8.02.T4 | 10 cenários sessão longa | `test_telegram_long_session_g8.py` |
| G8.03.T2 | `bot_mute.py` HITL Redis + chatwoot_handoff + chat_pipeline | `test_bot_mute_g8.py` |
| G8.05.T3 | `redis_doc_keys.py` HMAC CPF/CNPJ | `test_redis_doc_keys_g8.py` |
| G8.07.T4 | `mcp_radar_status.py` no radar expanded | `test_mcp_radar_status_g8.py` |

## Validação
```bash
cd backend && unset PYTHONPATH && .venv312/bin/python -m pytest \
  tests/test_ws_heartbeat_g8.py tests/test_ws_concurrency_g8.py \
  tests/test_dialog_history_g8.py tests/test_bot_mute_g8.py \
  tests/test_mcp_radar_status_g8.py tests/test_redis_doc_keys_g8.py \
  tests/test_telegram_long_session_g8.py --no-cov -q
# 47 passed
```

## Lições
1. **Nunca confiar em PROGRESS de orquestrador sem commit** — Lesson 216 reforçada.
2. **Conflito multi-agent em mesmo arquivo**: subagents + orchestrator overwrite → sempre re-ler antes de write; preferir API unificada (ws_heartbeat).
3. **PYTHONPATH Hermes venv** quebra pydantic_core do backend — `unset PYTHONPATH` + `.venv312/bin/python`.
4. **StatusLabel** tipado: estender Literal em vez de string solta (`hitl_muted`).

## Próximo
Wave 37: G8.03.T1 deepen schemas, G8.02.T3 debounce, G8.05.T4 stress idempotency, G8.09 Tailscale probes (docs/scripts se SUI).

Modified by Gustavo Almeida
