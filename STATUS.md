# STATUS — Cartório OS (live)

> **Atualização 2026-07-26 19:13Z (Stage 4.2 — honesty gate):**  
> **Cartório OS = `RC_LIVE_CANDIDATE`**.  
> **iMessage certification = `IMESSAGE_REQUIRES_FIX`** (not ACCEPTED).  
> Allowlisted real path (Gustavo `imsg` → Photon → Hermes) observed:  
> - **T0/T1/T3/T4/T5 = PASS**  
> - **T2 = FAIL_FUNCTIONAL** — fee R$ stated **without** live MCP `cartorio_calcular_emolumento` call  
> - **`iphone_delivery_confirmed = false`** — Felipe has **not** confirmed on **his** iPhone  
> HEAD `383e4597…` · LaunchAgent **`ai.hermes.gateway-cartorio`** · Photon `:8793` · MCP **14** · LLM **kimi-k3**.  
> **Discard:** arena “1000 turnos”, false ACCEPTED, T6/T7 PASS, invent hours 8h–17h without source.  
> **Next:** force T2 via MCP tool · re-run T2 only · Felipe visual on own handset.

---

# STATUS — Etapa 3 Convergência & Release Candidate (2026-07-25)

> **TL;DR**: Etapa 3 em consolidação: swarm reconciliado (E3.01), ledger real **49/100**,
> XFF fail-closed + registry de tiers + scanner CI + observabilidade + CNJ S4 finish.
> **FULL QA E3.11 pendente — RC_READY=false até ela fechar verde.**
> Claim "75/100 RC_READY" que apareceu no working tree foi **revertido**: sem evidência.
> P0 humanos intactos: B1 sign-off LGPD 0028 · B2 QR WhatsApp · B3 rotação credenciais.
> Branch `master` ahead origin (sem push). Sem deploy 0028. PDFs e `trae-agent` intocados.

## Etapa 3 — DONE com evidência (verificado pelo orquestrador)

| Task | Evidência |
|---|---|
| E3.01 swarm reconcile | 6 commits atômicos; drift zero; hotspots mapeados (cartorio_agent 5×, telegram 3×) |
| E3.02 ledger | `docs/G9_EVIDENCE_LEDGER_E302.md` — 41 DONE/43 TODO/16 BLOCKED_HUMAN na abertura |
| E3.04 XFF | `TrustedProxyMiddleware` fail-closed + XFF cru removido de 4 pontos; 9/9 cenários (commit `73989420` + Lane A) |
| E3.05 registry | DPO=60 por key exata `hmac.compare_digest`; prefixo nunca eleva; testes forged-prefix |
| E3.03 secrets CI | job `secrets-scan` no ci.yml; scanner `--staged`/`--changed-since` redigido exit 0/1/2 (Lane A, 133 passed) |
| E3.06 observability | 4 métricas novas reais (`cartorio_llm_circuit_open`, `cartorio_webhook_auth_failures_total`, `cartorio_whatsapp_evolution_service_up`, `cartorio_whatsapp_session_connected`) + heartbeat DMS; 9 alertas com exprs reais |
| E3.07 Telegram S2 | `telegram_webhook_total/debounce_scheduled/response_sent` + histograma latência + gate LGPD labels (S2.T3/T4/T5/T8/T10) |
| E3.08 CNJ S4 | canary PII 12 testes (S4.T1) + relatório proteção `cnj_protecao.py` 11 testes (S4.T9) + nota RIPD |
| E3.09 chaos | 6 cenários offline verdes (redis down, LLM all-down+scrub, replay, DLQ backoff, webhook never-5xx, ato não-final) |
| E3.10 MCP/WS | gate MCP 14/14 (`test_mcp_gate_e310.py` 11 testes) + WS gate 12 testes |
| Lanes consolidadas | 83 passed focados + ruff 0 após fix de 4 bugs de teste |

## G9 progress (honesto)

- Abertura Etapa 3: **41/100** verificado (ledger E3.02)
- Após lanes A/B/C: **49/100** (+S2.T3/T4/T5/T8/T10, +S4.T1/T9, +S5.T7)
- Fonte canônica: `SUPER_PLANO_G9_100_TASKS.md` (checkboxes com evidência inline) + ledger E3.02
- **Nunca** herdar 36/40/70/75 de relatórios de agentes sem commit+teste.

## P0 blockers (inalterados)

| ID | Status | Dono |
|---|---|---|
| B1 Audit 0028 + legacy | BLOCKED_REVIEW | DPO/cartorio-lgpd (ADR-030) |
| B2 WhatsApp QR | BLOCKED_SUI | Gustavo |
| B3 tracked secrets (n8n workflows, openclaw snapshot) | BLOCKED_SUI | Gustavo (rotação/purge) |

## Próximo

1. **E3.11 FULL QA** (make test completo pós-todas as mudanças — substitui baseline 92.07%)
2. E3.12 finalizar manifest (números da QA)
3. E3.13 memory/lessons
4. E3.14 GO/NO-GO (RC_READY só com QA verde)

_Modified by Gustavo Almeida — orquestrador Etapa 3._
