# Lesson 193 — G7 Wave 21: TG webhook + smoke + LobeChat secret scrub (2026-07-16)
Type: project + reference

## Contexto

CONTINUE Wave 21. Achado crítico de segurança no import LobeChat.

## Security fix

`infra/lobechat/agent_cartorio_import.json` continha `apiKey` literal
(`@Techno…`). Substituído por placeholder `${OPENCLAW_GATEWAY_TOKEN_OR_PASSWORD}`.

**Ação Gustavo:** se essa senha era real e pública no git history, **rotacionar**
no OpenClaw/LobeChat e não reutilizar.

## 4 slots

| Slot | Task | Entrega |
|------|------|---------|
| A1 | G7.03.T1 | runbook + `scripts/telegram_set_webhook.py` (mask token) |
| A2 | G7.03.T2 | `scripts/smoke_inventory.py` → **26 tests / 4 files** |
| A3 | G7.06.T2 | secret scrub + `docs/LOBCHAT_OPENCLAW_IMPORT_G7.md` |
| A4 | G7.02.T1 | `docs/MUTMUT_REPORT_G7_WAVE21.md` PARTIAL |

## Smoke gap

Meta “20 cenários Telegram” ainda não coberta só por `tests/smoke/` (foco
infra/WA/RIPD). Inventory deixa gap explícito para waves futuras.

## Validação

```
pytest test_g7_wave21 → 5 passed
smoke_inventory → WORK 26 tests
```

**Modified by Gustavo Almeida — G7 Wave 21**
