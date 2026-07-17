# Lesson 188 — G7 Wave 16: HMAC rotation PREV + CI gates + agility (2026-07-16)
Type: project + reference

## Contexto

CONTINUE loop super plano 100 tasks / 4 agents. SUI Gustavo ainda bloqueia
radar green; Wave 16 avançou **código + CI + governance** sem SSH.

## 4 slots

| Slot | Task | Entrega |
|------|------|---------|
| A1 cartorio-security/dev | G7.10.T3 | `EVOLUTION_WEBHOOK_SECRET_PREV` zero-downtime + tests + `docs/WEBHOOK_HMAC_ROTATION_G7.md` |
| A2 cartorio-sre/dev | G7.22.T1 + T4 | CI: bare-exception + secrets_scan + g7_super_validator (HOLD prod allowed) |
| A3 brain/scrum | G7.16.T2/T3 + G7.23.T1/T2 | TASKS.md epic G7 · paperclip board · `docs/G7_DOR_DOD.md` |
| A4 cartorio-dev | G7.21.T4 + G7.17.T3 | `scripts/check_no_bare_exception.py` · API_ENDPOINTS_CATALOG patch |

## Código crítico

`validate_evolution_signature` agora aceita **current OR previous** secret.
Se só PREV setado (current empty), **não** cai em dev mode aberto — exige sig.

## Validação

```
pytest test_evolution_hmac + test_g7_wave15 → 14 passed
check_no_bare_exception → WORK (0 hits)
g7_super_validator → HOLD (radar+dns) + bare_exception WORK
```

## Prod

Sem mudança: radar red partial; expanded 404; DNS NXDOMAIN.

## Progresso G7

~18/100 tasks · waves 13–16 agent-done · W17 = SUI-first

**Modified by Gustavo Almeida + Pietra — 2026-07-16**
