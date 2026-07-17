# Lesson 187 — G7 Wave 15: integration matrix + catalog/postman/openclaw (2026-07-16)
Type: project + reference

## Contexto

CONTINUE loop: super plano G7 100 tasks, 4 agents/squad. Waves 13–14 já tinham
mutation killers, RIPD 1.4, super validator, SUI checklist. Wave 15 focou
**integração catalogável** (sem SSH/UI Gustavo).

## 4 slots

| Slot | Task | Entrega |
|------|------|---------|
| A1 cartorio-dev | G7.14.T1 | `infra/openclaw/cartorio-bot.openclaw.json` (8 tools HITL, scopes, channels HOLD) |
| A2 cartorio-dev | G7.10.T1 / G7.17 | catalog +12 endpoints (radar expanded, WS, brain, evo health); Postman **47** URLs double-prefix fixed |
| A3 harness | G7.15.T1 | `.agents/skills/INDEX.md` G7 map skill→stack |
| A4 cartorio-sre/dev | G7.07.T1 | `docs/platforms/REDIS_OPS_G7.md` + `docs/INTEGRATION_MATRIX_G7.md` |

## Bugs found & fixed

1. **Postman** `https://api.../api/v1/api/v1/telegram/...` (47 ocorrências) — path array e raw duplicavam `api/v1`. Quebrava try-it-out silencioso.
2. **catalog get_stats** — `total` incluía openclaw mas assert era `v1+v2` only; beta status quebrava `stable+alpha==total`. Corrigido com openclaw + beta counters.
3. **import catalog** — diretório `.brain/api-specs` (hífen) não é package Python; testes backend usam importlib + `sys.modules` register (dataclass precisa do module no sys.modules).

## Validação

```
pytest tests/test_g7_wave15_integration.py → 6 passed
g7_super_validator → HOLD (radar+dns) + WORK openclaw_bot_json + integration_matrix
```

## Prod (sem mudança — SUI)

Radar still red partial; DNS NXDOMAIN 3 hosts; expanded 404 until redeploy.

## Progresso G7

- Antes W15: ~8/100
- Depois W15: **~12–14/100** (T3 partial openclaw deploy still SUI)
- Lessons: 186 + 187

## Próxima wave W16

SUI-assisted: redeploy API expanded, Cloudflare A records, Evolution DATABASE_URL, Telegram token. Agents: only checklists + re-run `make g7-validate` after Gustavo.

**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16**
