# cartorio-ai · planning/TASKS.md

## Fonte canônica

➡️ **`../../SUPER_PLANO_G9_100_TASKS.md`** — 100 tasks (G9.01.T1 … G9.25.T4), 25 squads × 4.
Este arquivo é só a ponte; o estado oficial vive lá (honesty gate: `[x]` só com evidência).

## Snapshot 2026-07-20 — 14/100 concluídas

| Concluída | Evidência |
|---|---|
| G9.01.T1 / G9.02.T1 | Diagnóstico E1: regressões A1–A6 mapeadas com linhas em `telegram.py`/`main.py` |
| G9.01.T2 | Re-sync webhook via `/api/v1/telegram/set-webhook` (commit `96fedc9`); getWebhookInfo OK, pending=0 |
| G9.03.T1 | Probes prod: `/start` → `response_sent=true`; texto/grupo → `scheduled=true` |
| G9.04.T1 | Diagnóstico E2: slots zen herdam só API_KEY; timeout 50s×6; payload thinking/tools p/ todos |
| G9.04.T2 | Fallback zen integrado + agente live restaurado (`96fedc9`, `9522cce`) |
| G9.07.T1 | `/lgpd/cnj-exports/massive-dump` implementado (streaming + JWT DPO + scrub + audit gate) |
| G9.11.T1/T2, G9.12.T1–T3 | Núcleo cartorio-ai (15 arquivos) preenchido — sessão C4 |
| G9.18.T1 | Diagnóstico E4 + `test_telegram_1000.py` (1000 mockadas — `4f43ff8`) |
| G9.25.T2 | STATUS.md + PROGRESS.md atualizados — sessão C4 |

## Próximas waves (ordem sugerida)

1. **W54** — Regressões A1–A5 em código (G9.01.T3/T4, G9.02.T2/T3).
2. **W55** — A6 feedback + E2E grupo + stress prod assinado (G9.02.T4, G9.03.T2–T4).
3. **W56** — LLM slots/timeouts/payload (G9.04.T3/T4, G9.05.T1/T2).

## Herança SUI (execução do dono, packs prontos em `docs/`)

G7.04.T4 → G9.17.T4 · G7.05.T1 → G9.16.T1 · G7.05.T3 → G9.16.T3 · G7.06.T3 → G9.17.T3 ·
G7.11.T1 → G9.17.T1 · G7.11.T2 → G9.17.T2 · G7.12.T1 → G9.16.T2
