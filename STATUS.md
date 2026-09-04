# STATUS — Cartório OS (live)

## 2026-09-04 22:20 BRT — RESTAURAÇÃO TOTAL HOSTINGER & SANEAMENTO OPERACIONAL (v0.6.1 LIVE + RADAR GREEN + QR WHATSAPP)

**Estado:** `HOSTINGER_PROD_100_ONLINE` | Radar `GREEN` | Backend `v0.6.1` | WhatsApp `QR_GENERATED` (aguardando scan)

**Ações Executadas e Evidências Reais:**
1. **Deploy v0.6.1 na VPS Hostinger**:
   - Easypanel acionado com o ambiente unificado e canônico (`cartorio_system-api`).
   - Commit `cc25ee62` em produção.
   - Endpoint `https://api.2notasudi.com.br/health` respondendo 200 OK com `{"status":"ok","service":"cartorio-backend","version":"0.6.1"}`.
   - PR #247 (regras da serventia e correção de preços de emolumentos) ativo em produção.
2. **Radar de Saúde 100% Verde**:
   - `https://api.2notasudi.com.br/api/v1/health/radar` retorna `status: "green"` com todos os serviços ativos (database, redis, n8n, evolution, supabase) online e serviços descomissionados (openclaw, chatwoot) devidamente isolados sem falso alarme.
3. **Saneamento de Loops Zumbis no Swarm**:
   - Serviços legados `cartorio_api` e `vps_whoami` escalados para 0 réplicas. Cessado o loop contínuo de rejeição.
4. **P0 Canal Mudo WhatsApp (Evolution API)**:
   - Identificada e eliminada a causa raiz: chaves antigas de sessão Baileys no Redis causavam conflito `401 device_removed`, mantendo o status em falso-open e canal mudo há 18 dias.
   - Tabela e Redis higienizados com backup preservado.
   - Novo QR Code gerado em tempo real com sucesso para pareamento do número oficial (+55 34 9195-2444).

---

## 2026-09-04 — Auditoria Operacional Hostinger VPS (187.77.236.77 / Tailscale 100.99.172.84) **LIVE PASS**

**Estado:** `HOSTINGER_PROD_ONLINE` | WhatsApp `OPEN` | DB 1ms | Redis 3ms | MiniMax-M3 200 OK | FastMCP 200 OK

**Diagnóstico & Evidência Real:**
- **VPS Hostinger**: Uptime de 40 dias ininterruptos, Tailscale ativo (`100.99.172.84`).
- **Traefik 3.6.7**: SSL ativo e respondendo em 4 subdomínios canônicos (`api`, `flow`, `whatsapp`, `easypanel.2notasudi.com.br`).
- **Postgres 17 (pgvector)**: 27 tabelas notariais íntegras, migration Alembic no `0032`, latência 1ms.
- **Redis 8.8**: Cache operacional, latência 3ms.
- **Evolution API (WhatsApp)**: Instância `cartorio-agent` pareada, sessão `OPEN`, `session_connected: true`.
- **Hermes Agent (Lark)**: Conexão ativa via WebSocket, FastMCP server autenticado sob `/mcp/` com Bearer JWT.
- **MiniMax M3 LLM**: Endpoint `/v1/models` responde HTTP 200 com a chave operacional.
- **Saneamento de Radar**: Refatoradas sondas de `health_radar` e `health_integracoes` para não gerarem falso alarme com serviços aposentados (`chatwoot`/`openclaw` desligados em 27/07) e adicionado header Bearer na checagem de modelos LLM.
- **Identificado Serviço Zumbi**: `cartorio_api` (0/1 réplicas) no Swarm em loop de rejeição contínuo tentando baixar imagem inexistente (`easypanel/cartorio/api:latest`) enquanto `cartorio_system-api` é o container ativo.

---

## 2026-08-18 — INCIDENT 194 (Telegram LGPD Poll + atendimento parado) **P0 estabilização**

**Estado:** `IN_PRODUCTION` (aguardando smoke real pós-deploy, critérios de aceite ainda em validação)

**Diagnóstico:**
- `issue #194` reportado como LGPD gate quebrando pipeline (`SIM`/`Nao` textual sem avanço).
- Causa raiz parcial confirmada: consentimento LGPD passava pelo caminho de texto, mas o fluxo não aguardava retorno persistido da escolha do usuário e `poll_answer` nem sempre era recebido em produção.
- Causa raiz operacional adicional: `sync_telegram_webhook` não incluía `poll_answer` em `allowed_updates`, com risco de perder respostas de enquete.

**Correções aplicadas (arquivo único):**
- `backend/app/api/v1/telegram.py`
  - Envio de consentimento via enquete Telegram em `sendPoll` com apenas `Sim`/`Nao`.
  - Mapeamento `poll_id → conv_key` em Redis com TTL (`lgpd_poll`).
- `backend/app/api/v1/telegram.py`
  - Tratamento de `poll_answer` em `telegram_webhook` para gravar/limpar consentimento e avançar estado sem depender de texto.
- `backend/app/api/v1/telegram.py`
  - `sync_telegram_webhook` atualiza `allowed_updates` para incluir `poll_answer`.
- `backend/tests/test_telegram_regressions_g9.py`
  - Regressão garante `poll_answer` em `allowed_updates` do `setWebhook`.
- `backend/tests/test_telegram_webhook.py`
  - Regressão mínima para respostas `poll_answer` (`Sim`/`Nao`).

**Evidência técnica (rodadas de validação):**
- Root cause: `sim` textual não era caminho primário, retorno de estado não persistia antes do poll e webhook podia ignorar `poll_answer`.
- Arquivos alterados: `backend/app/api/v1/telegram.py`, `backend/tests/test_telegram_webhook.py`, `backend/tests/test_telegram_regressions_g9.py`.
- Testes executados: regressões G9 (`test_sync_webhook_sends_secret_and_env_url`) + novos cenários de `poll_answer` via `telegram_webhook`.
- Comportamento esperado: 
  - `/start` sem consentimento abre aviso + enquete.
  - Clique em `Sim`/`Nao` define consentimento persistido e remove prompt.
  - Chat segue para atendimento normal sem novo “bloqueio LGPD”.
- Prevenção de regressão: teste de integração G9 em `allowed_updates`, regressão de `poll_answer` no handler.
- Deploy: VPS Agent Cartório / Tailscale (sem alteração de ambiente).
- Smoke real prevista: `LGPD -> PASS`, `sim -> PASS`, `pergunta -> resposta`, `segunda pergunta -> resposta`.
- Backlog operacional: investigar conversas históricas sem resposta após bloqueio e reprocessar apenas itens confirmados.

---

> **Atualização 2026-07-28 (IMENSAGER QA consolidado — Sessão B local):**
> **Status:** `IMESSAGE_QA_AMARELO` — 3 P0-candidates NOVOS + tz root cause | `PAINEL_DADOS_LIVE`
>
> **Sessão 2026-07-28 (B) — deliverables:**
> - **QA harness local reproduzível**: DB `cartorio_qa` (PG16 UTC) + backend :8001 isolado; genesis→42 audit chain **intact (score 1.000)** pós-tráfego+burst.
> - **ROOT CAUSE definitivo do "audit chain 152/152 broken" local**: **TimeZone artifact** (coluna naive + ORM tz-aware + GUC local BRT → shift −3h no storage → recompute diverge). Prova: recompute +3h = match. **NÃO era rotação HMAC** (refina FA2). Prod intacto (33/33). Lesson 285.
> - **25 casos live HTTP** contra backend QA: inbound 8/8 correto (200/400 RFC7807), PII zero eco em resposta+log, rate limit 30/min tier exato (30×200+40×429), latência offline P50≈50ms, RSS 18.6MB.
> - **3 P0-candidates novos**: **FB1/FB2** HITL offline não escala "isenção"/"urgência"/"escritura" (classificador offline só escala com palavras explícitas — escalation de ato jurídico é LLM-only); **FB5** scrubber NÃO mascara RG formato MG (`MG-12.345.678`, `SSP MG`, bare c/ contexto); **FB10** Art. 18 LGPD indisponível no canal iMessage (`bot_lgpd.py` Literal só telegram/whatsapp → 422).
> - **2 gaps LGPD menores**: FB9 `lgpd_dsar.py` não montado + mock; FB8 webhook ingest não audita. FB3 falso positivo HITL por substring "escrevente".
> - **Gates verdes**: ruff 0 + mypy 0 (229 arquivos) + secrets 0 violações + 206 testes focados + suite completa `make test-fast`.
> - **P0 IDENTITY_HERMES_LEAK permanece ABERTO** (N≥30 não rodado). Relatório completo: `.harness/memory/TEST_IMENSAGER_2026-07-28.md`.
>
> **P0 blockers humanos (inalterados):** B1 LGPD sign-off 0028 · B2 WhatsApp QR · B3 secrets rotation · B5 Felipe confirmação iPhone. **Novos p/ backlog dev:** FB1/FB2 (keyword gate HITL offline), FB5 (regex RG), FB9/FB10 (LGPD imessage).

---

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

> **Atualização 2026-07-28 (IMENSAGER QA parcial — sanity + audit verdes, fases live bloqueadas):**
> **Status:** `IMENSAGER_QA_PARTIAL_YELLOW` | P0 IDENTITY_HERMES_LEAK **aberto** (N≥30 não rodado)
>
> **Sessão 2026-07-28 — validação imensager (prompt v2.0):**
> - **Fase 1 sanity ✅**: prod health/ready/radar 200 (<100ms); Photon :8793 LISTEN + 401 fail-closed; suites pietra/imessage **86 passed, 1 skipped**; retry envelope **15/15**.
> - **Fase 5 audit ✅**: prod `verify_full_chain` = **33/33 intact** (container `cartorio_system-api`). Dev local 0% é esperado (rotação HMAC em dev) — não é tampering.
> - **Achado F3**: `cartorio_hermes` VPS com models `deepseek-v4-flash-free`/`nemotron-3-ultra-free` (não minimax) — hipótese contribuinte do identity leak. SOUL.md OK (PIETRA canônica, 131 linhas).
> - **Bloqueadas (aguardam Gustavo)**: Fases 2, 3, 4-live, 6 (HITL), 7-live, 8, 9 + N≥30 do P0 — requerem envio de iMessages reais.
> - Relatório completo: `.harness/memory/TEST_IMENSAGER_2026-07-28.md`.

---

# STATUS — Cartório OS (live)

> **Atualização 2026-07-27 23:14 BRT (B4 RESOLVED — MCP endpoint público funcional):**
> **Status:** `STAGE_7_EMOLUMENTOS_REAL_PASS` + **P0_IDENTITY_LEAK_DEFENSE_IN_PLACE** + **MCP_ENDPOINT_RESOLVED (B4)** | `PAINEL_DADOS_LIVE`
>
> **Sessão 2026-07-27 — B4 deliverables:**
> - **B4 RESOLVED**: `MCP_SERVER_ENABLED=true` deployado no serviço **`cartorio_system-api`** (não `cartorio_api`) — é o system-api que serve `api.2notasudi.com.br` via Traefik. `MCP_SERVER_ENABLED=false` era o bug real (404 no `/mcp` público). Fix aplicado via `docker service update --env-add`.
> - **MCP round-trip validado**: `tools/list` retorna **16 tools** e `cartorio_calcular_emolumento` retorna **R$156,40** (procuração) via endpoint público.
> - **Config Mac Hermes revertida** para `https://api.2notasudi.com.br/mcp` (agora funcional).
> - **P0 blockers humanos remanescentes**: B1 (LGPD sign-off), B2 (WhatsApp QR), B3 (secrets rotation), B5 (Felipe confirmação visual no iPhone).

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

---

# STATUS — Sessão ZCode/Kimi K3 (paralela, 04:00 BRT)

> **Status:** Bot Lark v6 construído e rodando localmente. Hermes stub crash corrigido.
> **Sem deploy Lark** (depende de Gustavo criar app no Developer Console).

**Sessão 2026-07-28 (ZCode) — deliverables:**

- **Lark bot standalone v6** (`scripts/lark_bot_v6.py`): plugado em PIETRA VPS
  (`api.2notasudi.com.br/api/v1/pietra/chat/completions`), persona canônica, PII scrub,
  identity guard via backend. 6 versões iteradas em ~3h.
- **OCR + LGPD scrub**: tesseract 5.5.2 extrai texto, scrubber mascara CPF/RG/TEL/EMAIL/CARTÃO
  ANTES de mandar pro LLM. Validado: `CPF 123.456.789-00` → `123.***.***-**`.
- **Detector de tipo documento**: 9 tipos (CPF, RG, CNH, PROCURAÇÃO, ESCRITURA, CONTRATO,
  RECEITA, FATURA, PROTOCOLO). PIETRA recebe `[DOC DETECTADO: TIPO]` no contexto.
- **Memória PIETRA VPS**: cada chat vinculado a "telefone proxy" (chat_id limpo + prefixo +55),
  persiste no Postgres do cartório.
- **Comandos admin** (owner only via `LARK_OWNER_OPEN_ID`): `!stats`, `!doc`, `!bot stop`,
  `!bot restart`, `!broadcast <msg>`.
- **Endpoint `/test-image` standalone** pra OCR fora do Lark.
- **LaunchAgent** `ai.zcode.lark-bot.plist` (port 8083, v6, pillow + OCR).
- **Bot v6 rodando AGORA**: PID 77420, valida `/health` retorna `{"bot":"v6 ok","pietra_ok":true,"ocr_available":true}`.
- **Hermes stub fix** (Lesson 285): `/Applications/Hermes.app` era instalador stub (11MB)
  referenciando path de ISO-build inexistente → SIGABRT diário. Backup em `~/.hermes_backup/`
  + symlink pro app funcional. Crash reports velhos limpos.
- **3 lessons salvas**: 283 (P0 VPS identity leak Camada 3), 284 (bot standalone > TRAE SOLO shell),
  285 (Hermes stub vs functional).

**Pendências (dependem Gustavo no Mac):**

1. Subir cloudflared tunnel (`cloudflared tunnel --url http://localhost:8083`).
2. Preencher `scripts/.env.lark` com App ID/Secret/Token do Developer Console.
3. Adicionar bot como **admin** no grupo GG (Settings → Members).
4. Configurar `LARK_OWNER_OPEN_ID` no `.env.lark`.
5. Rodar `scripts/vps_fix_cartorio_hermes_F3.sh` no VPS (Lesson 283 → fecha P0 identity leak).
6. Liberar Full Disk Access do OpenClaw no macOS System Settings (4+ dias crashloop).

**Artefatos pra revisar:**

- `docs/sessions/2026-07/SESSION_2026-07-28_INDEX.md` — consolidado completo
- `docs/sessions/2026-07/CHECKLIST_VOLTA_MAC_2026-07-28.md` — passo-a-passo ordenado
- `scripts/lark_bot_v6.py` — código principal
- `scripts/LARK_BOT_V3_RUNBOOK.md` — runbook atualizado v6

**Não-feitos (decisão consciente):**

- git commit (Gustavo revisa antes).
- LLM vision nativa (PIETRA VPS só aceita `content:string`, não `image_url`).
- Deletar `~/Library/LaunchAgents/ai.hermes.gateway.plist` legacy (mencionado).

_Modified by Gustavo Almeida — sessão ZCode/Kimi K3 04:00 BRT._
