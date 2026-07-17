# Lesson 191 — G7 Wave 19: PII inventory + OpenAPI + handoff + redlock (2026-07-16)
Type: project + reference

## Contexto

CONTINUE loop. Master avançou com MiniMax (`d9690a3` badge, `48637b6` lesson G6
16-18). Grok Wave 19 sem tocar badge.

## 4 slots

| Slot | Task | Entrega |
|------|------|---------|
| A1 lgpd | G7.02.T3 | `scripts/pii_pre_llm_inventory.py` — 8/8 sites WORK |
| A2 dev | G7.01.T1 | `openapi.baseline.json` 126 paths updated + --check green |
| A3 n8n | G7.05.T3 | `docs/CHATWOOT_HANDOFF_G7.md` (prod HOLD SUI) |
| A4 dev | G7.07.T4 | redlock peer skip `dms-loop` test |

## PII pre-LLM sites (canonical)

chat_pipeline · cartorio_agent · opencode_go · openclaw · opencode_generic ·
antigravity · output_safety · telegram

## Validação

```
pii_pre_llm_inventory --strict → WORK
openapi_snapshot --check → WORK
pytest wave19+18 → 9 passed
```

## Coord

Grok uncommitted waves 13-19; MiniMax on master. Commit G7 when other agent idle.

**Modified by Gustavo Almeida — G7 Wave 19**
