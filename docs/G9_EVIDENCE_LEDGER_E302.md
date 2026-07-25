# G9 Evidence Ledger — E3.02 (2026-07-25)

> **Regra:** DONE exige commit + teste/evidência inline no SUPER_PLANO. PARTIAL não conta.
> BLOCKED_HUMAN fica fora da contagem técnica. Não herda estimativas de agentes (36/40/70).
> Fonte: parse direto de `SUPER_PLANO_G9_100_TASKS.md` + reconciliação de swarm E3.01.

## Resultado verificado

| Classe | Qtd | Nota |
|--------|-----|------|
| **DONE (verificado)** | **41** | checkbox + evidência inline (commit/teste) |
| TODO técnico | 43 | escopo Etapa 3 e posteriores |
| BLOCKED_HUMAN | 16 | fora da contagem técnica |
| **percent_verified** | **41/100** | DONE/100 |

## Por squad

| Squad | DONE | TODO | BLOCKED_HUMAN |
|-------|------|------|---------------|
| S1 Telegram webhook/boot/stress | 8 | 1 (T9 stress prod) | 1 (T10 BotFather/grupo real) |
| S2 Telegram E2E/métricas/alertas | 2 | 8 | 0 |
| S3 LLM Zen/timeouts/scrub | **10** | 0 | 0 |
| S4 CNJ export/LGPD | 6 | 3 (T1 canary, T9 relatório, T10 RIPD) | 1 (T2 sign-off DPO) |
| S5 Segredos/checker/rate limit | 6 | 3 (T2/T6/T7) | 1 (T4 rotação dono) |
| S6 cartorio-ai/runbooks | 5 | 5 | 0 |
| S7 WhatsApp/DNS/Tailscale (SUI) | 0 | 0 | **10 (tudo Gustavo)** |
| S8 OpenClaw/WA live/1000/CI | 3 | 5 | 2 (T1 deploy HOLD, T2 QR) |
| S9 Audit chain/LGPD rights/HITL | 0 | 9 | 1 (T1 verify prod) |
| S10 HITL cont./degradação/runbooks | 1 | 9 | 0 |

## Divergências corrigidas (honesty gate)

- Header do plano dizia "40/100" → real pós-reconcile: **41** (S4.T4 tickado com evidência de 10 testes, commit `29951526`).
- STATUS.md dizia 37 → atualizado no commit `29951526` (37+S4.T4); ledger E3.02 é a fonte canônica a partir de agora.
- Baseline "5819 passed / 92.07%" é **pré-Etapa 2** — substituído obrigatoriamente pela FULL QA E3.11.
- Drift de working tree eliminado em E3.01: 3 commits atômicos (`29951526` S4.T4, `73989420` trusted proxy+DPO tier+scanner lint, `ae60ea69` chaos matrix offline).

## TODO técnico em execução nesta etapa (lanes)

- Lane A (security): S5.T2/T6/T7 + gates XFF/registry (E3.03/E3.04/E3.05)
- Lane B (observability): S2.T3/T4/T5/T8/T9/T10 + métricas/alertas E3.06
- Lane C (data/gates): S4.T1/T9/T10 + MCP/WS formal (E3.08/E3.10)

## BLOCKED_HUMAN explícito (não entra no denominador técnico)

1. **S7 inteiro (10):** QR WhatsApp, DNS chatwoot/n8n/supabase, Tailscale VPS, handoff WF3 — dono Gustavo.
2. **S4.T2:** sign-off LGPD/DPO (ADR-030 + LGPD_REVIEW_AUDIT_0028).
3. **S5.T4:** varredura histórica → decisão de rotação do dono.
4. **S8.T1:** deploy OpenClaw HOLD (aprovação). **S8.T2:** 1ª msg WA real (depende QR).
5. **S9.T1:** verify audit chain prod (pós-deploy 0028).
6. **S1.T10:** @BotFather `/setjoingroups` + confirmação grupo real.

_Modified by Gustavo Almeida — orquestrador Etapa 3, 2026-07-25._
