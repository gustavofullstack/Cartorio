# cartorio-ai · planning/GOALS.md

## Meta ativa — SUPER PLANO G9 (2026-07-20 →)

Transformar o Telegram de "funcional em probe" em **robusto sob regressão**, profissionalizar a
cadeia LLM (3 contas OpenCode Zen), validar o export massivo CNJ ponta-a-ponta, sanar segredos em
scripts, completar o núcleo `cartorio-ai/` ✅, fechar pendências SUI do G7 (DNS/Tailscale/OpenClaw/WA)
e elevar testes para 1000+ com CI verde.

Plano canônico: `../../SUPER_PLANO_G9_100_TASKS.md` (100 tasks / 25 squads). Estado: **14/100**.

## Objetivos mensuráveis

| # | Objetivo | Medição | Squad |
|---|---|---|---|
| O1 | Webhook Telegram sem regressão A1–A6 | testes de regressão verdes + stress prod assinado | 01–03 |
| O2 | Fallback LLM coerente (slot=conta completa) | gate de coerência no CI; zero HTTP 400 zen free | 04–05 |
| O3 | LGPD-015 output scrub em 100% das saídas LLM | inventário + canary tokens | 06 |
| O4 | CNJ massive-dump validado ponta-a-ponta | streaming + JWT DPO + hash chain + relatório | 07–08 |
| O5 | Zero segredos literais em scripts/testes | checker hex-64 + CI secrets_scan | 09–10 |
| O6 | Núcleo cartorio-ai completo | 15 arquivos reais ✅ (2026-07-20) | 11–12 |
| O7 | Observabilidade: métricas telegram + GIT_SHA | séries no /metrics + alertas | 13–14 |
| O8 | Pendências SUI G7 fechadas (dono) | DNS ok, Tailscale online, QR, OpenClaw E8, WA live | 15–17 |
| O9 | Bateria 1000 telegram no CI + qa verde | junit + coverage ≥90% | 18–19 |
| O10 | Audit/LGPD/HITL intactos | t024/t025/t036/t037 verdes | 20–23 |

## Definition of Done (herdado do honesty gate)

Task `[x]` = código + teste que falha se regredir + evidência de 1 linha no plano + memória atualizada.
Ver `../../docs/G8_DOR_DOD.md`.
