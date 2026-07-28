# STATUS — Cartório OS (live)

> **Atualização 2026-07-27 22:40 BRT (Stage 7 — Defesa-em-profundidade Identity Leak + Hipótese MCP):**
> **Status:** `STAGE_7_EMOLUMENTOS_REAL_PASS` + **P0_IDENTITY_LEAK_DEFENSE_IN_PLACE** + **MCP_ENDPOINT_HYPOTHESIS_CONFIRMED** | `PAINEL_DADOS_LIVE`
>
> **Sessão 2026-07-27 — deliverables:**
> - **P0 IDENTITY_HERMES_LEAK defense-in-depth**: novo módulo `backend/app/services/pietra_identity_guard.py` (195 linhas) com 17 padrões regex cobrindo variantes canônicas ("Sou o Hermes", "Sou a Hermes-2"), standalone ("Hermes continua online"), e bypass (Hérmes via NFD+strip Mn, SOU O HERMES via IGNORECASE). 3 ações: PASS / SUBSTITUTE / HARD_STOP. Stub Prometheus interno thread-safe. 39 regression tests PASSED (1 skipped edge case).
> - **Hipótese MCP T2 FAIL_FUNCTIONAL CONFIRMADA**: `~/.hermes/profiles/cartorio/config.yaml:335` aponta para `https://api.2notasudi.com.br/mcp` que retorna **HTTP 404**. Caminho funcional real é `http://localhost:8000/mcp` (interno). Fix = 1 linha de config no Mac, não de código.
> - **Working tree dirty resolvido**: commit `f3d86f10` consolidou 4 arquivos (`AGENTS.md`, `.brain/memory/2026-07-27.md`, `prompts/IMENSAGER_VALIDATION_PROMPT.md`, `prompts/IMENSAGER_P0_IDENTITY_LEAK_INVESTIGATION.md`, `SUPER_GOAL.md`). Commit `fce886f7` adicionou feature identity guard.
> - **Lesson 282** adicionada a `.harness/memory/MEMORY.md`: defesa-em-profundidade + hipótese MCP + topologia reconciliada (backend VPS, iMessage local).
> - **Quality gates verdes**: ruff 0 errors, mypy 0 errors (229 source files), secrets scanner 0 violações, `make test-fast` 6230 passed, `pytest test_pietra_identity_guard.py` 39 passed, `pytest test_retry_envelope_3x20s.py` 15 passed.
> - **Paste accumulation consolidada**: paste #1 (220428) e paste #2 (221544) continham 3 cópias do mesmo super-prompt IMENSAGER + JSON de estado. Paste #2 trouxe investigação focada do P0 + hipótese MCP únicas (primeiras 358 linhas); restante era duplicata. Consolidado em 2 arquivos `prompts/*.md` no repo.
> - **Topologia reconciliada**: backend (cartorio_api, MCP, audit, PII, retry envelope) = VPS Hostinger (187.77.236.77). iMessage/Photon sidecar + Hermes runtime = Mac local do Gustavo (`ai.hermes.gateway-cartorio`, port 8793). Coexistência legítima — Messages.app é dependência de macOS.
>
> **Gate oficial do canal iMessage:** `IMESSAGE_REQUIRES_FIX` (3/10 Hermes em N=10)
>
> **P0 blockers humanos (inalterados):**
> - **B1** Audit 0028 + legacy sign-off LGPD → `cartorio-lgpd`
> - **B2** WhatsApp QR → Gustavo (cell +16282649335)
> - **B3** Secrets rotation → Gustavo (NUNCA sob pressão)
> - **B4** Fix config MCP endpoint no Mac (1 linha) → Gustavo
> - **B5** Felipe confirmação visual no próprio iPhone → Felipe

---

# STATUS — Cartório OS (live)

> **Atualização 2026-07-26 22:33Z (Stage 7 — Real Price Collection, AI Extraction & Data Dashboard):**  
> **Status:** `STAGE_7_EMOLUMENTOS_REAL_PASS` | `PAINEL_DADOS_LIVE`  
> **Mapeamento Notarial Real — 2º Serviço Notarial de Uberlândia (Tabelionato Djalma):**  
> - **Preços & Tabelas Reais:** Tabela oficial MG 2026 / TJMG com cálculo de Emolumento, TFJ (15%), RECOMPE (6%) e ISSQN (5% Uberlândia) implementada em `emolumento_real_djalma.py`.  
> - **Motor de Extração IA + LGPD:** Sanitização PII 3-camadas + NLP parser em `ai_data_extractor.py`.  
> - **Painel de Dados:** Dashboard em `app/static/dashboard.html` disponível via `/dashboard`.  
> - **Ferramentas MCP & APIs:** `cartorio_extrair_e_calcular_real` exposta em FastMCP + 3 endpoints REST `/api/v1/emolumentos/real/*`.  
> - **Qualidade Total:** `8/8` testes unitários e de integração PASSED | `ruff check` 0 erros.  
> Fonte: `PROGRESS.md` e `docs/PRONTIDAO_VPS_AGENT_AI_20260727.md`.


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
