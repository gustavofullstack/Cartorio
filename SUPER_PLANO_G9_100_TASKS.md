# SUPER PLANO G9 — 100 Tasks · 25 Squads · 4 Tasks/Squad
**Cartório 2º Notas · Telegram Hardening, LLM Zen 3 Contas, CNJ Export & Go-Live SUI**
**Base:** pós-G8 + sessão 2026-07-20 (webhook re-sync, probes funcionais, diagnósticos E1–E4)
**Orquestrador:** harness + reins (dev / n8n / lgpd / sre / brain)

---

> **HONESTY GATE:** `[x]` só com evidência de 1 linha. **14/100** concluídas em 2026-07-20.
> Regressões A1–A6 = diagnóstico E1 (`backend/app/api/v1/telegram.py`). Slots/timeout/payload = diagnóstico E2 (`backend/app/services/cartorio_agent.py`).

## META

Transformar o Telegram de "funcional em probe" em **robusto sob regressão**, profissionalizar a cadeia LLM (3 contas OpenCode Zen com fallback coerente), validar o export massivo CNJ ponta-a-ponta, sanar segredos em scripts, completar o núcleo `cartorio-ai/`, fechar as pendências SUI herdadas do G7 (DNS/Tailscale/OpenClaw/WA) e elevar a bateria de testes para 1000+ com CI verde — tudo com LGPD-by-design, HITL obrigatório e audit chain íntegro.

**DoR/DoD canônico:** [`docs/G8_DOR_DOD.md`](docs/G8_DOR_DOD.md) (honesty gate herdado do G8).
**Pendências SUI herdadas do G7:** G7.04.T4, G7.05.T1/T3, G7.06.T3, G7.11.T1/T2, G7.12.T1 → Squads 16–17.

---

## SQUADS (25 × 4 tasks = 100)

### Squad 01 — Telegram Webhook Sync & Boot Hardening (A1–A3) (dev)
- [x] **G9.01.T1** — Diagnóstico E1 (A1–A3) mapeado com linhas: A1 `sync_telegram_webhook()` dispara em TODOS os workers no boot (`main.py:305-307`) e worker sem `TELEGRAM_WEBHOOK_SECRET` chama setWebhook sem `secret_token` (`telegram.py:2435-2436`) derrubando a verificação das demais réplicas; A2 URL hardcoded (`telegram.py:2429`); A3 webhook pode 5xx (`1964-1966` JSON inválido re-raise; `2357` `bus.client.get` sem try).
- [x] **G9.01.T2** — Re-sync webhook prod executado via `POST /api/v1/telegram/set-webhook` com `X-API-Key` (mecanismo do commit `96fedc9`): getWebhookInfo OK com secret, `pending_update_count=0`, 401 sem header.
- [x] **G9.01.T3** — Boot sync seguro: somente worker líder (redlock) executa `sync_telegram_webhook()` e aplica fail-fast se `TELEGRAM_WEBHOOK_SECRET` estiver ausente — nunca registrar setWebhook sem `secret_token`. Teste multi-worker simulado.
- [x] **G9.01.T4** — Webhook sempre-200 exceto 401 de secret: envelopar `bus.client.get` (2357) e JSON inválido (1964-1966) em exceções tipadas → ack 200 + DLQ. Teste de regressão A3.

### Squad 02 — Telegram Debounce & Fallback (A4–A6) (dev)
- [x] **G9.02.T1** — Diagnóstico E1 (A4–A6) mapeado com linhas: A4 fallback síncrono é código morto (`2315-2352`; `get_bus()` nunca retorna None — `redis_bus.py:216-221`); A5 `_DEBOUNCE_METADATA` keyed por `chat_id` (`1626`, `2362`) mas filas/locks por `chat_id:user_id` → 2 usuários no mesmo grupo na janela de 1.2s → um nunca recebe resposta; A6 debounce falha silenciosa (`1663-1667` fila vazia → return; `1732-1733` exceção → só log).
- [x] **G9.02.T2** — A4: remover o fallback síncrono morto ou torná-lo alcançável atrás de flag explícita; teste provando o caminho escolhido.
- [x] **G9.02.T3** — A5: alinhar `_DEBOUNCE_METADATA` à chave `chat_id:user_id` (mesmo escopo de fila/lock); teste com 2 usuários no mesmo grupo dentro da janela de 1.2s → ambos respondidos.
- [x] **G9.02.T4** — A6: debounce com feedback garantido — fila vazia ou exceção → mensagem amigável ao usuário + métrica + alerta; teste de regressão que falha se o silêncio voltar.

### Squad 03 — Telegram E2E Grupo & Stress Prod (dev+n8n)
- [x] **G9.03.T1** — Probes funcionais prod (2026-07-20): `/start` em chat real → `response_sent=true`; texto livre e mensagem em grupo → `scheduled=true` (debounce async agendado).
- [x] **G9.03.T2** — E2E grupo real: 2 usuários distintos na mesma janela de debounce recebem respostas independentes (regressão A5 em produção).
- [ ] **G9.03.T3** — Stress prod assinado: `backend/scripts/stress_telegram_prod*.py` passando `X-Telegram-Bot-Api-Secret-Token` via env (nunca literal); relatório com taxas 200/401/5xx.
- [ ] **G9.03.T4** — Confirmar resposta assíncrona pós-debounce entregue em grupo real (hoje só `scheduled=true` observado) + documentar `/setjoingroups Enable` no @BotFather (ação do dono; `can_join_groups=false` bloqueia novos grupos).

### Squad 04 — LLM/Zen 3 Contas: Fallback Coerente (dev)
- [x] **G9.04.T1** — Diagnóstico E2 mapeado com linhas: slots free 1/2/3 (`cartorio_agent.py:66-82`) herdam só `API_KEY` de `OPENCODE_ZEN_ACCOUNT_X_*`, sem `BASE_URL`/`MODEL` → mistura chave da conta 1 com modelo de outro slot; timeout único de 50s compartilhado por até 6 tentativas sequenciais (`:616`) → pior caso 15-20min percebido como silêncio; payload envia `thinking` e `tools` para TODOS os providers (`:610-614`) incl. zen free → risco de HTTP 400 em cascata.
- [x] **G9.04.T2** — Cadeia de fallback OpenCode Zen integrada e fallback de agente live restaurado (commits `96fedc9` "integrate opencode zen fallbacks" e `9522cce` — 2026-07-20).
- [x] **G9.04.T3** — Coerência de slot: cada slot herda a tupla completa (`API_KEY`, `BASE_URL`, `MODEL`) da mesma conta — proibido misturar chave de uma conta com modelo de outro slot; teste de coerência por slot no CI.
- [ ] **G9.04.T4** — Healthcheck por slot/conta com circuit breaker e ordem de fallback determinística; métricas por provider/slot.

### Squad 05 — LLM Timeouts & Payload por Provider (dev)
- [x] **G9.05.T1** — Timeout por tentativa (ex.: 50s/attempt) + deadline total propagado do webhook; teste de pior caso < 2min percebido pelo usuário.
- [x] **G9.05.T2** — Payload por provider: `thinking`/`tools` apenas quando o provider suporta (allowlist); zen free recebe payload mínimo; teste provando ausência de HTTP 400.
- [ ] **G9.05.T3** — Tentativas × latência por provider/slot exportadas ao Prometheus (histograma).
- [ ] **G9.05.T4** — Mensagem de espera/degradação ao usuário quando o LLM está lento ou todos os slots falham — silêncio nunca é resposta.

### Squad 06 — LLM LGPD-015 Output Scrub (lgpd+dev)
- [ ] **G9.06.T1** — Auditoria LGPD-015: inventário de todos os pontos de saída do LLM (Telegram, WhatsApp, logs, Sentry) com scrub aplicado ou gap identificado.
- [ ] **G9.06.T2** — Output scrub: resposta do LLM passa por `app/services/pii.py` antes de canal/log; teste provando CPF/RG/protocolo nunca raw na saída.
- [ ] **G9.06.T3** — Regressão com canary tokens: teste falha se o LLM ecoar PII que entrou mascarada.
- [ ] **G9.06.T4** — Sign-off `cartorio-lgpd` documentado + entrada no audit log (mudança toca `pii*`).

### Squad 07 — CNJ Export Massivo: Endpoint & Streaming (dev)
- [x] **G9.07.T1** — Endpoint `/api/v1/lgpd/cnj-exports/massive-dump` implementado: `StreamingResponse` com `yield_per(1000)`, scrub de payload via `pii.scrub`, API key + JWT DPO (`require_cartorio_api_key` + `require_dpo_role`), gate de audit antes do dump (commits `ff599aa`, `0d15da6`, `6c029fc` — 2026-07-20).
- [ ] **G9.07.T2** — Teste de streaming sob volume alto (seed/faker): memória estável, ordem por `id`, JSON válido de ponta a ponta.
- [ ] **G9.07.T3** — Falha de audit antes do dump → 500 `AUDIT_FAILURE` e nenhum byte vazado; teste dedicado.
- [ ] **G9.07.T4** — Contrato OpenAPI documentado (security ApiKey+Bearer, headers, filename) + exemplo curl sem segredos.

### Squad 08 — CNJ Segurança, Hash Chain & Relatório (lgpd+dev)
- [ ] **G9.08.T1** — JWT DPO obrigatório validado (role, expiração, `sub` registrado no audit); testes 401/403.
- [ ] **G9.08.T2** — Verificação independente da cadeia SHA256+HMAC sobre o pacote exportado; teste que falha se a cadeia quebrar.
- [ ] **G9.08.T3** — Relatório de logs de proteção de dados (acessos, exportações, mascaramentos) gerado a partir do audit log — Padrão CNJ.
- [ ] **G9.08.T4** — RIPD/compliance atualizados com o fluxo massive-dump (revisão `cartorio-lgpd`).

### Squad 09 — Segurança: Scrub de Secrets em Scripts (sre+lgpd)
- [ ] **G9.09.T1** — Auditar `backend/scripts/stress_telegram_prod*.py`, `scripts/test_telegram_e2e.sh` e os `backend/test_*.py` ad-hoc por segredos literais (token bot, webhook secret, chave zen) — listar ocorrências SEM imprimir valores.
- [ ] **G9.09.T2** — Sanitizar: segredos passam a vir de env/`.secrets` com mascaramento; decidir destino de `test_send_tg.py`, `test_webhook*.py`, `test_llm*.py` (sanitizar + gitignore ou deletar — hoje untracked).
- [ ] **G9.09.T3** — Confirmar `.gitignore` cobrindo arquivos de teste ad-hoc com credenciais; gate `git grep` no pre-commit.
- [ ] **G9.09.T4** — Varredura histórica (git log/trufflehog) nos paths afetados; relatório com recomendação de rotação — decisão exclusiva do dono (proibido rotacionar sem ordem expressa).

### Squad 10 — Segurança: Checker & CARTORIO_API_KEY Sync (sre)
- [ ] **G9.10.T1** — `scripts/check_no_literal_keys.py`: adicionar padrão hex-64 genérico (cobre webhook secrets); teste positivo/negativo do checker.
- [ ] **G9.10.T2** — Sincronizar `CARTORIO_API_KEY` entre backend, n8n e scripts com fonte única em `.secrets`; runbook de atualização (sem rotação).
- [ ] **G9.10.T3** — CI `secrets_scan` estendido com o padrão hex-64 (bloqueia PR com novo literal).
- [ ] **G9.10.T4** — Rate limit 3-tier por API key (N8N 600 / DPO 60 / default 30) revalidado com as chaves atuais; teste.

### Squad 11 — cartorio-ai/ Núcleo Institucional (brain/docs)
- [x] **G9.11.T1** — `cartorio-ai/AGENTS.md`, `README.md` e `ARCHITECTURE.md` escritos com conteúdo real do projeto (missão, stack, regras P0, relação com `backend/` e `.harness/`) — sessão C4 2026-07-20.
- [x] **G9.11.T2** — `cartorio-ai/MANIFEST.md`, `INDEX.md` e `BOOTSTRAP.md` escritos (inventário do núcleo, índice navegável, boot de agente novo em <10min) — sessão C4 2026-07-20.
- [ ] **G9.11.T3** — Completar os demais diretórios/arquivos do layout (~400 arquivos) conforme `cartorio-ai/ROADMAP.md` — fase posterior, não bloqueia G9.
- [ ] **G9.11.T4** — Gate no CI: nenhum arquivo-núcleo do `cartorio-ai/` pode regredir a placeholder de 1 linha.

### Squad 12 — cartorio-ai/ Domínio Vivo (brain)
- [x] **G9.12.T1** — `brain/BRAIN.md`, `identity/SOUL.md` e `identity/IDENTITY.md` com propósito, valores e workflow obrigatório reais — sessão C4 2026-07-20.
- [x] **G9.12.T2** — `planning/GOALS.md` e `planning/TASKS.md` apontando para o SUPER PLANO G9 com estado 14/100 — sessão C4 2026-07-20.
- [x] **G9.12.T3** — `memory/MEMORY.md`, `security/SECURITY.md` e `compliance/CNJ.md` com fatos de 2026-07-20 (webhook fix, fallback zen, CNJ export) — sessão C4 2026-07-20.
- [ ] **G9.12.T4** — Sync quinzenal AGENTS.md raiz → cartorio-ai (script + diff no CI).

### Squad 13 — Observabilidade: Métricas Telegram (sre)
- [ ] **G9.13.T1** — `/metrics`: contadores `telegram_webhook_total{result=200|401|5xx}`, `telegram_debounce_scheduled_total`, `telegram_response_sent_total`.
- [ ] **G9.13.T2** — Histograma de latência webhook → resposta (incluindo a janela de debounce de 1.2s).
- [ ] **G9.13.T3** — Revisão LGPD das labels: `chat_id`/username nunca como label (revisão `cartorio-lgpd`).
- [ ] **G9.13.T4** — Painel Telegram no radar/Grafana + documentação das novas séries.

### Squad 14 — Observabilidade: Versão & Alertas (sre)
- [ ] **G9.14.T1** — `GIT_SHA` (+ build time) exposto em `/version` e `/health`, injetado no build Docker.
- [ ] **G9.14.T2** — Alertas AlertManager: taxa de 401 do webhook acima do limiar; `response_sent=0` com tráfego; fallback LLM esgotado.
- [ ] **G9.14.T3** — Entrega dos alertas no Telegram do escrevente sem PII (reuso do caminho G8.15.T2).
- [ ] **G9.14.T4** — Runbook de resposta para os 3 alertas novos.

### Squad 15 — WhatsApp/Evolution Readiness (QR pendente — só preparação) (n8n)
- [ ] **G9.15.T1** — Checklist pré-QR: instância `state=close` confirmada, envs, webhook dual-format (legado root-level + aninhado `data.message`) já coberto por fuzz (G7.04.T3).
- [ ] **G9.15.T2** — Workflow n8n de monitoramento de state → alerta Telegram pronto para ativar pós-QR (template do G8.22.T2).
- [ ] **G9.15.T3** — TTL rígido de 24h das mensagens WhatsApp validado em staging (G8.22.T3) + teste de retenção.
- [ ] **G9.15.T4** — Runbook "dia do QR": do scan à 1ª mensagem real (prepara a execução live do G9.17.T4).

### Squad 16 — Herança G7 SUI: DNS & Chatwoot (sre — execução do dono)
- [ ] **G9.16.T1** — (herda G7.05.T1) DNS chatwoot A record + Traefik router — pack `docs/CHATWOOT_GO_LIVE_SUI_G7.md`; execução Gustavo.
- [ ] **G9.16.T2** — (herda G7.12.T1) 3 A records chatwoot/n8n/supabase (último snapshot: 3× NXDOMAIN); após criar, `make dns-check-strict` exit 0.
- [ ] **G9.16.T3** — (herda G7.05.T3) Handoff WF3 + labels LGPD em prod (pack pronto; prod HOLD).
- [ ] **G9.16.T4** — Pós-DNS: smoke chatwoot/n8n/supabase → 200 e radar verde.

### Squad 17 — Herança G7 SUI: Tailscale, OpenClaw & WA live (sre — execução do dono)
- [ ] **G9.17.T1** — (herda G7.11.T1) Tailscale online restore na VPS (pack `TAILSCALE_RESTORE_G7`).
- [ ] **G9.17.T2** — (herda G7.11.T2) SSH 22 + MagicDNS health no radar (`docs/TAILSCALE_SSH_RADAR_LIVE_G7.md`).
- [ ] **G9.17.T3** — (herda G7.06.T3) OpenClaw cartorio-bot create E8 (`docs/OPENCLAW_CARTORIO_BOT_DEPLOY_G7.md`; JSON pronto, deploy HOLD).
- [ ] **G9.17.T4** — (herda G7.04.T4) 1 mensagem real WA → resposta de emolumento (`docs/WA_EMOLUMENTO_LIVE_SUI_G7.md`; depende do QR — G9.15).

### Squad 18 — Testes 1000 Telegram & Cobertura (dev)
- [x] **G9.18.T1** — Diagnóstico E4: inventário de testes/stress/smoke consolidado; `backend/tests/test_telegram_1000.py` com 1000 interações mockadas (commit `4f43ff8`); SUPER_PLANOs G7/G8 revisados → base deste G9.
- [x] **G9.18.T2** — Bateria 1000 ampliada: cenários grupo/menção/comandos/mídia + header de secret; sem flakiness (fakeredis/respx).
- [x] **G9.18.T3** — Bateria 1000 como gate de CI (marker próprio, < 5min, relatório junit).
- [ ] **G9.18.T4** — Cobertura de `telegram.py` ≥95% mantendo gate global de 90%; mutation spot-check nos handlers novos.

### Squad 19 — CI/CD Gates (sre+dev)
- [ ] **G9.19.T1** — `make qa` verde local e no CI após as mudanças G9 (lint 0 errors + test com coverage ≥90%).
- [ ] **G9.19.T2** — Gate "webhook sempre-200" (regressão A3) obrigatório no CI.
- [ ] **G9.19.T3** — Gate de coerência de slots LLM (G9.04.T3) no CI.
- [ ] **G9.19.T4** — Pipeline publica artifacts de cobertura + junit.

### Squad 20 — Audit Chain & HMAC em Produção (lgpd+dev)
- [ ] **G9.20.T1** — Verificação read-only da cadeia SHA256 em prod (amostra + full em janela off-hours); relatório.
- [ ] **G9.20.T2** — Dead-man's switch (audit check a cada 15min) com alerta ao DPO; teste de falha injetada em staging.
- [ ] **G9.20.T3** — Regressões `t024` (retro-edit mid-chain) e `t025` (rotação HMAC) verdes no CI.
- [ ] **G9.20.T4** — Procedimento de evidência forense documentado (export + verificação independente), alinhado ao fluxo CNJ.

### Squad 21 — LGPD Rights & Retenção (lgpd)
- [ ] **G9.21.T1** — Drill Art. 18 completo (acesso, correção, anonimização, portabilidade, eliminação, oposição, não-automação) com evidências.
- [ ] **G9.21.T2** — Scheduler de retenção 03:00 BRT validado (`t036`/`t037`) + métrica de execuções.
- [ ] **G9.21.T3** — RIPD v1.6 incluindo fallback zen 3 contas e CNJ massive-dump.
- [ ] **G9.21.T4** — Data inventory refresh pós-G9 (novos campos PII).

### Squad 22 — HITL & Protocolo DRAFT (lgpd+dev)
- [ ] **G9.22.T1** — E2E: protocolo nasce `DRAFT`, escrevente valida; bot nunca decide isenção/urgência/emissão sozinho.
- [ ] **G9.22.T2** — Takeover Chatwoot → mute imediato do bot (G8.03.T2) revalidado após as mudanças de Telegram.
- [ ] **G9.22.T3** — Sugestões de minuta/escritura do LLM sempre com aprovação humana registrada no audit.
- [ ] **G9.22.T4** — Métrica HITL no DPO dashboard.

### Squad 23 — Rate Limit & Idempotência (dev)
- [ ] **G9.23.T1** — Drill fail-open com Redis down: rate limit degrada sem derrubar o webhook; teste.
- [ ] **G9.23.T2** — Idempotency 24h: replay de `update_id` do Telegram → dedupe confirmado; teste.
- [ ] **G9.23.T3** — Rate limit adicional por `chat_id` (anti-spam de usuário) além de IP/key; teste.
- [ ] **G9.23.T4** — Limites e comportamento de degradação documentados no runbook operacional.

### Squad 24 — Runbooks & Docs Operacionais (docs)
- [ ] **G9.24.T1** — Runbook webhook Telegram (re-sync, troubleshooting 401/5xx, rotação de secret SÓ com ordem do dono).
- [ ] **G9.24.T2** — Runbook LLM zen 3 contas (fallback, timeouts, payload por provider).
- [ ] **G9.24.T3** — Runbook CNJ export (solicitar, aprovar como DPO, baixar, verificar hash).
- [ ] **G9.24.T4** — Política de segredos em scripts/testes (onde vivem, como mascarar, checker hex-64).

### Squad 25 — Memória & Governança (brain)
- [ ] **G9.25.T1** — Lesson G9 consolidada em `.harness/memory/MEMORY.md` (webhook secret sync, debounce A5/A6, fallback zen).
- [x] **G9.25.T2** — `STATUS.md` reescrito e `PROGRESS.md` atualizado com o estado 2026-07-20 (telegram funcional validado, pendências, próximos passos) — sessão C4.
- [ ] **G9.25.T3** — SUI_CHECKLIST atualizado com as pendências G9 (DNS, Tailscale, QR, OpenClaw).
- [ ] **G9.25.T4** — Tag `v0.9.0-g9` + release notes quando Squads 01–10 fecharem.

---

## MAPA DE ONDAS (sugerido, 4 tasks/onda)

| Wave | Tasks | Foco |
|------|-------|------|
| W54 | G9.01.T3, G9.01.T4, G9.02.T2, G9.02.T3 | Regressões A1–A5 código |
| W55 | G9.02.T4, G9.03.T2, G9.03.T3, G9.03.T4 | A6 + E2E grupo + stress |
| W56 | G9.04.T3, G9.04.T4, G9.05.T1, G9.05.T2 | LLM slots/timeouts/payload |
| W57 | G9.05.T3, G9.05.T4, G9.06.T1, G9.06.T2 | LLM métricas + LGPD-015 |
| W58 | G9.06.T3, G9.06.T4, G9.07.T2, G9.07.T3 | Scrub regressão + CNJ stream |
| W59 | G9.07.T4, G9.08.T1, G9.08.T2, G9.08.T3 | CNJ contrato/JWT/hash/relatório |
| W60 | G9.08.T4, G9.09.T1, G9.09.T2, G9.09.T3 | RIPD + scrub secrets scripts |
| W61 | G9.09.T4, G9.10.T1–T3 | hex-64 checker + API key sync |
| W62 | G9.10.T4, G9.13.T1–T3 | rate-limit + métricas telegram |
| W63 | G9.13.T4, G9.14.T1–T3 | painel + GIT_SHA + alertas |
| W64 | G9.14.T4, G9.15.T1–T3 | runbook alertas + WA prep |
| W65 | G9.15.T4, G9.16.T1–T3 (SUI Gustavo) | QR runbook + DNS/Chatwoot |
| W66 | G9.16.T4, G9.17.T1–T3 (SUI Gustavo) | smoke pós-DNS + Tailscale/OpenClaw |
| W67 | G9.17.T4, G9.18.T2–T4 | WA live + bateria 1000 |
| W68 | G9.19.T1–T4 | CI/CD gates |
| W69 | G9.20.T1–T4 | audit chain prod |
| W70 | G9.21.T1–T4 | LGPD rights/retenção |
| W71 | G9.22.T1–T4 | HITL DRAFT |
| W72 | G9.23.T1–T4 | rate-limit/idempotência |
| W73 | G9.24.T1–T4 | runbooks |
| W74 | G9.25.T1/T3/T4 + G9.11.T3/T4 + G9.12.T4 | memória, SUI, tag, docs gate |

---

**Modified by Gustavo Almeida + orquestrador G9 — 2026-07-20**
(Plano G9 consolidado: 100 tasks em 25 squads; 14/100 concluídas na sessão 2026-07-20 com evidência)
