# Lesson 190 — G7 Wave 18: rate-limit metrics + DLQ + TG plain (2026-07-16)
Type: project + reference

## Contexto

CONTINUE com dual-agent (MiniMax em G6.A.T8 coverage badge). Grok Wave 18
**evitou** `coverage_badge.py` / BADGES para não colidir.

## 4 slots

| Slot | Task | Entrega |
|------|------|---------|
| A1 | G7.07.T3 | `MetricsStore.inc_rate_limit_total` + hooks ddos/sliding/tier |
| A2 | G7.10.T2 | `scripts/dlq_admin_drill.py` valida 60/300/900 |
| A3 | G7.03.T3 | `format_bot_text` strip think/reasoning; sendMessage sem parse_mode |
| A4 | G7.09.T2 + G7.12.T4 | MCP example json + DOMAIN_TYPO G7 ratify |

## Coord multi-agent

- MiniMax: pytest 3009 / mypy 0 / ruff 0 / push f3b0286 / badge task
- Grok: uncommitted G7 stack waves 13–18
- **Serializar commit** ou branch `feat/g7-waves-13-18` antes de push

## Validação

```
pytest wave17+18+hmac → 22 passed
dlq_admin_drill → WORK
```

## Prod

SUI still blocks radar WORK.

**Modified by Gustavo Almeida — G7 Wave 18**
