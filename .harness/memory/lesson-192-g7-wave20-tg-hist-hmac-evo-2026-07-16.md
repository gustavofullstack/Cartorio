# Lesson 192 — G7 Wave 20: TG hist + HMAC drill + Evolution checklist (2026-07-16)
Type: project + reference

## Contexto

CONTINUE loop 4 agents. MiniMax em master (G6 SLO/consent/metrics). Grok W20.

## 4 slots

| Slot | Task | Entrega |
|------|------|---------|
| A1 | G7.03.T4 | tests `_hist_get/_hist_append` + catalog 1-msg + CPF scrub in hist |
| A2 | G7.02.T4 | `docs/AUDIT_HMAC_ROTATION_DRILL_G7.md` — dual-key gap explícito |
| A3 | G7.04.T1/T2 | `docs/EVOLUTION_DATABASE_URL_QR_CHECKLIST_G7.md` |
| A4 | G7.24.T4 | `docs/SUPER_STATUS.html` banner G7 |

## Telegram Redis namespaces (ref)

| Key | TTL | Uso |
|-----|-----|-----|
| `tg:hist:{id}` | 7200 | multi-turn user/bot (scrubbed) |
| `tg:state:{id}` | 3600 | FSM |
| `tg:idem:{update}` | — | webhook dedupe |
| `tg:queue:{id}` | 10 | debounce queue |
| `tg:lock:{id}` | — | processing lock |

## Validação

```
pytest test_g7_wave20_integration → 6 passed
```

## Coord

Grok uncommitted 13–20; MiniMax master moving. Commit when idle.

**Modified by Gustavo Almeida — G7 Wave 20**
