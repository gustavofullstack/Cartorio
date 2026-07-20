# EVALS

Avaliação e baterias de teste (estado 2026-07-20).

## Resultados vigentes

| Bateria | Resultado | Evidência |
|---|---|---|
| pytest full (1000 interações Telegram + suíte) | **1000 PASS** | sessão 2026-07-20, `backend/tests/test_telegram_1000.py` |
| E2E Telegram (`tests/smoke/`) | **18/20** | 2 falhas residuais documentadas (stress prod assinado + async grupo) |
| Probes prod | `/start` → `response_sent=true`, webhook secret OK, `pending=0` | 2026-07-20, bot `@test_cartorio_bot` |
| Coverage | gate `--cov-fail-under=90` | `pyproject.toml`, CI |

Relatório consolidado: `cartorio-ai/docs/TEST-REPORT.md`.

## Suites por área

- **Telegram**: 20 cenários E2E (`docs/GUIA_TESTES_TELEGRAM.md`); regressões A1–A6 (webhook 5xx, sync secret, debounce `chat_id:user_id`, feedback garantido).
- **Emolumento**: nominal + bordas (isenção, urgência, faixa, mínimo, teto) — markers `t043`/`t044`/`t045`.
- **Audit**: regressão `t024` (retro-edit mid-chain) e `t025` (rotação HMAC) — falham se a cadeia regredir.
- **Retenção LGPD**: `t036`/`t037` (scheduler 03:00 BRT).
- **PII**: canary tokens — falha se LLM ecoar PII mascarada.

## Infra de teste

- `fakeredis` para Redis; `respx` para HTTP externo; `pytest-asyncio` auto.
- `tests/conftest.py` força `LLM_DEFAULT_PROVIDER=opencode_go` — zero chamada real a LLM.
- Markers `smoke`/`integration`/`e2e` excluídos por default; E2E exige `uv sync --extra e2e` (Playwright).

## Gates

- CI: ruff 0 + mypy 0 + coverage ≥ 90% + bateria 1000 verde.
- Critérios de aceite por squad no `SUPER_PLANO_G9_100_TASKS.md`.
