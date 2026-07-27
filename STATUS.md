# STATUS — Cartório OS (live)

> **Atualização 2026-07-26 21:08Z (Stage 5 — Real iMessage Arena Reclassification & Bug Fixes):**  
> **Status:** `ARENA_HARNESS_PASS / REAL_TRANSPORT_NOT_CERTIFIED`  
> **Reclassificação Honesta baseada em Evidência Visual:**  
> - **Cartório DM**: `🟢 OPERATIONAL` (Respondeu emolumentos R$ 8,46 e menu).  
> - **Grupo (`CARTORIO GRUPO TEST`)**: `🔴 NO_RESPONSE` (Nenhuma IA respondeu às mensagens do grupo).  
> - **Runtimes dos Testers:** `Kimi` (`AUTH_FAILED`), `Grok` (`GATEWAY_DOWN`), `Codex` (`GATEWAY_DOWN`), `AGY` (`CONNECTION_REFUSED Errno 61`), `Antigravity` (`UNVERIFIED`).  
> - **Reinvindicações Anteriores ("6/6 Online / 1.000 Turnos Reais")**: **REVERTIDAS** (Trata-se do simulador do harness offline, não de transporte iMessage real).  
> **Bugs Críticos Corrigidos nesta Sessão:**  
> 1. `BUG_INTERNAL_AGENT_CONTROL_UI_LEAK` (P0): `stripInternalAgentControlLeaks` adicionado ao `guardrails.ts` para eliminar vazamento de comandos como `↳ Redirected current run`, `Self-improvement review` e `/new` no chat do cliente. (36/36 testes TS PASS).  
> 2. `T2_FEE_MCP_EVIDENCE_GATE` (P0): `imessage_felipe_classify.py` agora exige chamada real à ferramenta FastMCP `cartorio_calcular_emolumento` para aprovar valores numéricos de emolumentos.  
> **Diretiva de Arquitetura (Stage 5 - VAIO Arch Migration):**  
> - **MacBook**: Apenas UI/Cliente (Messages.app, OpenChamber UI, SSH/Tailscale).  
> - **VAIO Arch Agent OS**: Hospedará todos os 6 runtimes Hermes, conexões Spectrum Cloud, logs isolados e orquestradores.  
> **Complemento (runtime photon, esta sessão):** leak de UX interna também contido na fonte — `display.platforms.photon.*` (tool_progress/interim/busy_ack off) + `HERMES_GATEWAY_BUSY_ACK_ENABLED=false` + guard de slash no `plugins/platforms/photon/adapter.py` (7 testes em `test_photon_client_safe_ux.py`); gateway cartorio restartado (PID 98842, photon connected). **T2 re-prova pendente**: SOUL.md #3 já exige `cartorio_calcular_emolumento`, falta turno real confirmando a tool call. Gate Felipe: falta confirmação visual no aparelho dele.
> Fonte: `docs/RUNTIME_INVENTORY.json` e `services/spectrum-gateway/src/guardrails.ts`.

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
