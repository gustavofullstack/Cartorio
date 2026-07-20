# MODEL_REGISTRY

Registro de modelos e providers LLM (estado 2026-07-20, commit `bc9823c`).

## Providers OpenCode Zen — 3 contas integradas

| Slot | Env prefix | Papel |
|---|---|---|
| `opencode_zen_account_1` | `OPENCODE_ZEN_ACCOUNT_1_*` | Conta zen primária (default) |
| `opencode_zen_account_2` | `OPENCODE_ZEN_ACCOUNT_2_*` | Conta zen secundária |
| `opencode_zen_account_3` | `OPENCODE_ZEN_ACCOUNT_3_*` | Conta zen terciária |
| `opencode_free_1..3` | `OPENCODE_FREE_1..3_*` | Slots free (fallback) |
| `opencode_go` | `OPENCODE_GO_*` | Zen Go (`api.opencode.ai/zen/go/v1`) — usado em testes |

**Coerência de slot (P0):** cada slot herda a tupla completa `API_KEY` + `BASE_URL` + `MODEL` da **mesma** conta. Proibido misturar chave de uma conta com modelo de outro slot (teste de coerência no CI).

## Fallback chain (`LLM_FALLBACK_CHAIN`)

`zen_account_1 → zen_account_2 → zen_account_3 → free_1 → free_2 → free_3 → opencode_go → openrouter → groq → mistral → google_ai_studio → openclaw → cache`

- Ordem determinística; **circuit breaker** por slot: slot com falhas consecutivas é pulado na janela de cooldown (saúde por slot + métricas por provider).
- **Timeout global 45s** por tentativa; deadline total propagado do webhook (pior caso percebido < 2min).
- **Payload por provider**: `thinking`/`tools` só quando suportado (allowlist); zen free recebe payload mínimo — evita HTTP 400 em cascata.

## Regras

- `LLM_DEFAULT_PROVIDER=opencode_zen_account_1` em prod; testes forçam `opencode_go` (`tests/conftest.py`).
- PII mascarada antes de **qualquer** provider externo (`pii.py`).
- Custos, latência e limites de contexto em `models/COSTS.md`, `models/LATENCY.md`, `models/CONTEXT_LIMITS.md`.
