# Lesson 189 — G7 Wave 17: dual-format WA + WS50 + Postman + Tailscale (2026-07-16)
Type: project + reference

## Contexto

CONTINUE loop 4 agents. SUI ainda bloqueia radar green. Wave 17 fechou
integração **parser + contratos + orquestração**.

## 4 slots

| Slot | Task | Entrega |
|------|------|---------|
| A1 n8n/dev | G7.04.T3 | `parse_evolution_payload` dual-format root+nested + Hypothesis 40 ex |
| A2 dev | G7.01.T4 | WS ConnectionManager 50 clients mock broadcast |
| A3 dev | G7.17.T1/T2/T4 | `postman_export.py` X-API-Key, 128 items local, no double prefix; swagger persistAuthorization assert |
| A4 sre | G7.11.T3 + G7.16.T4 | Tailscale offline fallback runbook + `scripts/g7_orchestrator.py` |

## Bugfix

`parse_evolution_payload` **só lia nested `data.*`**. AGENTS.md exige root-level
legado também. Root path nunca normalizava → drop silencioso de msgs Evolution
antigas. Fix: dual extract key/message + `extra.format` nested|root.

## Postman

- `--from-app` gera 126 paths / 128 items (local HEAD)
- Auth apikey `X-API-Key` (não bearer genérico)
- base_url origin-only → zero `/api/v1/api/v1/`

## Orquestrador

```bash
python3 scripts/g7_orchestrator.py status   # 27% after W17
python3 scripts/g7_orchestrator.py next     # 4 tasks next wave
make g7-status
```

## Validação

```
pytest test_g7_wave17 + hmac + whatsapp_adapter → green
```

## Prod

Inalterado (SUI).

**Modified by Gustavo Almeida — G7 Wave 17**
