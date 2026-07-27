# STATUS — Cartório OS (live)

> **Atualização 2026-07-26 22:15Z (Stage 6 — VAIO Recovery & Real Agent Arena):**  
> **Status:** `STAGE_6_VAIO_RECOVERY_PENDING` | `FREEZE_ACTIVE` (Congelamento de Features Ativo)  
> **Diagnóstico de Conectividade do VAIO (Track B):**  
> - `agent-os` (`100.116.49.17`): **`HOST_OFFLINE`** (Offline no Tailscale há ~6h; ICMP/SSH port 22 timeout).  
> - `triqhub` (`100.110.127.44`): **`TAILSCALE_ONLINE_BUT_SSH_EXEC_DENIED`** (Online no Tailscale; SSH responde porta 22 via Tailscale SSH, mas rejeita exec não-interativa com `tailscale: failed to look up local user`).  
> - `vps-cartorio` (`100.99.172.84`): **`CONNECTED`** (`uid=0 root` via SSH).  
> - `macbook-pro-gus` (`100.83.180.16`): **`CONNECTED`** (Modo estrito: UI/Cliente Apenas).  
> **Blindagem & Classificação Mantidas:**  
> - **Bugs P0 Corrigidos:** `BUG_INTERNAL_AGENT_CONTROL_UI_LEAK` (guardrails.ts - 36 TS tests PASS) & `T2_FEE_MCP_EVIDENCE_GATE` (imessage_felipe_classify.py - 13 Python tests PASS).  
> - **Qualidade Total:** `make qa` **PASSED** (6.070 testes backend Python PASS | 92.44% cobertura).  
> - **Baseline do VAIO:** Documentado em `docs/testing/VAIO_RUNTIME_BASELINE.json`.  
> Fonte: `docs/RUNTIME_INVENTORY.json` e `docs/testing/VAIO_RUNTIME_BASELINE.json`.

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
