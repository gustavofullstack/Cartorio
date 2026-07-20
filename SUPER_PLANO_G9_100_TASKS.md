# SUPER PLANO G9 — 100 Tasks · 10 Squads · 10 Tasks/Squad
**Cartório 2º Notas · Telegram Hardening, LLM Zen 3 Contas, CNJ Export & Go-Live SUI**
**Base:** pós-G8 + sessão 2026-07-20 (webhook re-sync, probes funcionais, diagnósticos E1–E4)
**Orquestrador:** harness + reins (dev / n8n / lgpd / sre / brain)
**Formato:** G9.S1..S10, tasks .T1..T10 (o dono mudou de 25×4 → 10×10 em 2026-07-20)

---

> **HONESTY GATE:** `[x]` só com evidência de 1 linha. **25/100** concluídas em 2026-07-20
> (contador corrigido: arquivo dizia 14, evidência real marca 25).
> IDs antigos (25×4) preservados entre parênteses para rastreio, ex.: `(ex-G9.01.T2)`.
> Regressões A1–A6 = diagnóstico E1 (`backend/app/api/v1/telegram.py`). Slots/timeout/payload = diagnóstico E2 (`backend/app/services/cartorio_agent.py`).

## META

Transformar o Telegram de "funcional em probe" em **robusto sob regressão**, profissionalizar a cadeia LLM (3 contas OpenCode Zen com fallback coerente), validar o export massivo CNJ ponta-a-ponta, sanar segredos em scripts, completar o `cartorio-ai/`, fechar as pendências SUI herdadas do G7 (DNS/Tailscale/OpenClaw/WA) e manter a bateria 1000+ com CI verde — tudo com LGPD-by-design, HITL obrigatório e audit chain íntegro.

**DoR/DoD canônico:** [`docs/G8_DOR_DOD.md`](docs/G8_DOR_DOD.md) (honesty gate herdado do G8).
**Pendências SUI herdadas do G7:** G7.04.T4, G7.05.T1/T3, G7.06.T3, G7.11.T1/T2, G7.12.T1 → Squads S7–S8.

---

## SQUADS (10 × 10 tasks = 100)

### Squad S1 — Telegram Webhook, Boot & Stress (dev)
**Objetivo:** webhook resiliente (nunca-5xx), boot seguro multi-worker, debounce correto e stress prod assinado.
**Risco:** retry storm do Telegram; worker sem secret derruba verificação das réplicas; usuário sem resposta em grupo.
**Comandos:** `make test-one TEST=tests/test_telegram_*.py`; `POST /api/v1/telegram/set-webhook` com `X-API-Key`.
**Rollback:** `git revert d642e0e` + re-sync manual do webhook (runbook S6).
**Evidência:** commits `d642e0e`, HEAD `6967b71`; probes 2026-07-20.
**Aceite:** 8/8 regressões A1–A6 verdes + stress prod com relatório 200/401/5xx + async pós-debounce confirmado em grupo.

- [x] **G9.S1.T1** (ex-G9.01.T1) — Diagnóstico E1 (A1–A3) mapeado com linhas: A1 `sync_telegram_webhook()` dispara em TODOS os workers no boot (`main.py:305-307`) e worker sem `TELEGRAM_WEBHOOK_SECRET` chama setWebhook sem `secret_token` (`telegram.py:2435-2436`); A2 URL hardcoded (`telegram.py:2429`); A3 webhook pode 5xx (`1964-1966` JSON inválido re-raise; `2357` `bus.client.get` sem try).
- [x] **G9.S1.T2** (ex-G9.01.T2) — Re-sync webhook prod executado via `POST /api/v1/telegram/set-webhook` com `X-API-Key` (mecanismo do commit `96fedc9`): getWebhookInfo OK com secret, `pending_update_count=0`, 401 sem header.
- [x] **G9.S1.T3** (ex-G9.01.T3) — Boot sync seguro: somente worker líder (redlock) executa `sync_telegram_webhook()` e aplica fail-fast se `TELEGRAM_WEBHOOK_SECRET` estiver ausente — nunca registrar setWebhook sem `secret_token`. Teste multi-worker simulado.
- [x] **G9.S1.T4** (ex-G9.01.T4) — Webhook sempre-200 exceto 401 de secret: envelopar `bus.client.get` (2357) e JSON inválido (1964-1966) em exceções tipadas → ack 200 + DLQ. Teste de regressão A3.
- [x] **G9.S1.T5** (ex-G9.02.T1) — Diagnóstico E1 (A4–A6) mapeado com linhas: A4 fallback síncrono morto (`2315-2352`; `get_bus()` nunca None — `redis_bus.py:216-221`); A5 `_DEBOUNCE_METADATA` keyed por `chat_id` (`1626`, `2362`) mas filas/locks por `chat_id:user_id`; A6 debounce falha silenciosa (`1663-1667`, `1732-1733`).
- [x] **G9.S1.T6** (ex-G9.02.T2) — A4: remover o fallback síncrono morto ou torná-lo alcançável atrás de flag explícita; teste provando o caminho escolhido.
- [x] **G9.S1.T7** (ex-G9.02.T3) — A5: alinhar `_DEBOUNCE_METADATA` à chave `chat_id:user_id`; teste com 2 usuários no mesmo grupo dentro da janela de 1.2s → ambos respondidos.
- [x] **G9.S1.T8** (ex-G9.02.T4) — A6: debounce com feedback garantido — fila vazia ou exceção → mensagem amigável + métrica + alerta; teste de regressão que falha se o silêncio voltar.
- [ ] **G9.S1.T9** (ex-G9.03.T3) — Stress prod assinado: `backend/scripts/stress_telegram_prod*.py` passando `X-Telegram-Bot-Api-Secret-Token` via env (nunca literal); relatório com taxas 200/401/5xx.
- [ ] **G9.S1.T10** (ex-G9.03.T4) — Confirmar resposta assíncrona pós-debounce entregue em grupo real (hoje só `scheduled=true` observado) + documentar `/setjoingroups Enable` no @BotFather (ação do dono; `can_join_groups=false` bloqueia novos grupos).

### Squad S2 — Telegram E2E, Métricas & Alertas (dev+sre)
**Objetivo:** probes/E2E grupo validados e observabilidade completa do pipeline Telegram.
**Risco:** regressão silenciosa sem métrica; labels com PII violando LGPD.
**Comandos:** `curl localhost:8000/metrics`; bateria `tests/smoke/` (guia `docs/GUIA_TESTES_TELEGRAM.md`).
**Rollback:** desativar alertas novos no AlertManager; métricas são aditivas (sem rollback de dados).
**Evidência:** probes 2026-07-20 (`response_sent=true`, grupo 2 usuários).
**Aceite:** séries webhook/debounce/response no Prometheus, painel no radar, 3 alertas ativos sem PII.

- [x] **G9.S2.T1** (ex-G9.03.T1) — Probes funcionais prod (2026-07-20): `/start` em chat real → `response_sent=true`; texto livre e mensagem em grupo → `scheduled=true` (debounce async agendado).
- [x] **G9.S2.T2** (ex-G9.03.T2) — E2E grupo real: 2 usuários distintos na mesma janela de debounce recebem respostas independentes (regressão A5 em produção).
- [ ] **G9.S2.T3** (ex-G9.13.T1) — `/metrics`: contadores `telegram_webhook_total{result=200|401|5xx}`, `telegram_debounce_scheduled_total`, `telegram_response_sent_total`.
- [ ] **G9.S2.T4** (ex-G9.13.T2) — Histograma de latência webhook → resposta (incluindo a janela de debounce de 1.2s).
- [ ] **G9.S2.T5** (ex-G9.13.T3) — Revisão LGPD das labels: `chat_id`/username nunca como label (revisão `cartorio-lgpd`).
- [ ] **G9.S2.T6** (ex-G9.13.T4) — Painel Telegram no radar/Grafana + documentação das novas séries.
- [ ] **G9.S2.T7** (ex-G9.14.T1) — `GIT_SHA` (+ build time) exposto em `/version` e `/health`, injetado no build Docker.
- [ ] **G9.S2.T8** (ex-G9.14.T2) — Alertas AlertManager: taxa de 401 do webhook acima do limiar; `response_sent=0` com tráfego; fallback LLM esgotado.
- [ ] **G9.S2.T9** (ex-G9.14.T3) — Entrega dos alertas no Telegram do escrevente sem PII (reuso do caminho G8.15.T2).
- [ ] **G9.S2.T10** (ex-G9.14.T4) — Runbook de resposta para os 3 alertas novos.

### Squad S3 — LLM Zen 3 Contas, Timeouts & Scrub Output (dev+lgpd)
**Objetivo:** fallback chain coerente (3 contas zen + free + go), timeout 45s, payload por provider, output scrubbed.
**Risco:** mistura chave↔modelo entre contas; silêncio de 15-20min; HTTP 400 em cascata; PII raw na saída.
**Comandos:** `make test-one TEST=tests/test_cartorio_agent*.py`; healthcheck por slot.
**Rollback:** `git revert bc9823c` (volta chain anterior; secret não rotacionar).
**Evidência:** commit `bc9823c` + teste de coerência de slot no CI.
**Aceite:** pior caso percebido < 2min; zero 400 por payload; canary PII verde; sign-off `cartorio-lgpd`.

- [x] **G9.S3.T1** (ex-G9.04.T1) — Diagnóstico E2 mapeado com linhas: slots free 1/2/3 (`cartorio_agent.py:66-82`) herdam só `API_KEY` de `OPENCODE_ZEN_ACCOUNT_X_*`, sem `BASE_URL`/`MODEL`; timeout único de 50s compartilhado por até 6 tentativas (`:616`); payload envia `thinking`/`tools` para TODOS os providers (`:610-614`) incl. zen free.
- [x] **G9.S3.T2** (ex-G9.04.T2) — Cadeia de fallback OpenCode Zen integrada e fallback de agente live restaurado (commits `96fedc9` e `9522cce` — 2026-07-20).
- [x] **G9.S3.T3** (ex-G9.04.T3) — Coerência de slot: cada slot herda a tupla completa (`API_KEY`, `BASE_URL`, `MODEL`) da mesma conta — proibido misturar; teste de coerência por slot no CI.
- [ ] **G9.S3.T4** (ex-G9.04.T4) — Healthcheck por slot/conta com circuit breaker e ordem de fallback determinística; métricas por provider/slot.
- [x] **G9.S3.T5** (ex-G9.05.T1) — Timeout por tentativa (45s/attempt) + deadline total propagado do webhook; teste de pior caso < 2min percebido pelo usuário.
- [x] **G9.S3.T6** (ex-G9.05.T2) — Payload por provider: `thinking`/`tools` apenas quando o provider suporta (allowlist); zen free recebe payload mínimo; teste provando ausência de HTTP 400.
- [ ] **G9.S3.T7** (ex-G9.05.T3) — Tentativas × latência por provider/slot exportadas ao Prometheus (histograma).
- [ ] **G9.S3.T8** (ex-G9.05.T4) — Mensagem de espera/degradação ao usuário quando o LLM está lento ou todos os slots falham — silêncio nunca é resposta.
- [ ] **G9.S3.T9** (ex-G9.06.T1) — Auditoria LGPD-015: inventário de todos os pontos de saída do LLM (Telegram, WhatsApp, logs, Sentry) com scrub aplicado ou gap identificado.
- [ ] **G9.S3.T10** (ex-G9.06.T2) — Output scrub: resposta do LLM passa por `app/services/pii.py` antes de canal/log; teste provando CPF/RG/protocolo nunca raw na saída.

### Squad S4 — CNJ Export & Segurança LGPD (dev+lgpd)
**Objetivo:** massive-dump CNJ validado ponta-a-ponta com hash chain independente e relatório de proteção.
**Risco:** vazamento de PII em dump; JWT DPO fraco; cadeia quebrada no pacote exportado.
**Comandos:** `curl -H "X-API-Key: ..." -H "Authorization: Bearer ..." /api/v1/lgpd/cnj-exports/massive-dump`.
**Rollback:** desabilitar endpoint via feature flag; pacotes já exportados são imutáveis (hash verificável).
**Evidência:** commits `ff599aa`, `0d15da6`, `6c029fc` (endpoint streaming + gate audit).
**Aceite:** streaming sob volume com memória estável; 500 `AUDIT_FAILURE` sem vazar byte; relatório CNJ gerado.

- [ ] **G9.S4.T1** (ex-G9.06.T3) — Regressão com canary tokens: teste falha se o LLM ecoar PII que entrou mascarada.
- [ ] **G9.S4.T2** (ex-G9.06.T4) — Sign-off `cartorio-lgpd` documentado + entrada no audit log (mudança toca `pii*`).
- [x] **G9.S4.T3** (ex-G9.07.T1) — Endpoint `/api/v1/lgpd/cnj-exports/massive-dump` implementado: `StreamingResponse` com `yield_per(1000)`, scrub de payload via `pii.scrub`, API key + JWT DPO (`require_cartorio_api_key` + `require_dpo_role`), gate de audit antes do dump (commits `ff599aa`, `0d15da6`, `6c029fc` — 2026-07-20).
- [ ] **G9.S4.T4** (ex-G9.07.T2) — Teste de streaming sob volume alto (seed/faker): memória estável, ordem por `id`, JSON válido de ponta a ponta.
- [ ] **G9.S4.T5** (ex-G9.07.T3) — Falha de audit antes do dump → 500 `AUDIT_FAILURE` e nenhum byte vazado; teste dedicado.
- [ ] **G9.S4.T6** (ex-G9.07.T4) — Contrato OpenAPI documentado (security ApiKey+Bearer, headers, filename) + exemplo curl sem segredos.
- [ ] **G9.S4.T7** (ex-G9.08.T1) — JWT DPO obrigatório validado (role, expiração, `sub` registrado no audit); testes 401/403.
- [ ] **G9.S4.T8** (ex-G9.08.T2) — Verificação independente da cadeia SHA256+HMAC sobre o pacote exportado; teste que falha se a cadeia quebrar.
- [ ] **G9.S4.T9** (ex-G9.08.T3) — Relatório de logs de proteção de dados (acessos, exportações, mascaramentos) gerado a partir do audit log — Padrão CNJ.
- [ ] **G9.S4.T10** (ex-G9.08.T4) — RIPD/compliance atualizados com o fluxo massive-dump (revisão `cartorio-lgpd`).

### Squad S5 — Segredos, Checker & Rate Limit (sre)
**Objetivo:** zero segredo literal em scripts/testes, checker hex-64, fonte única para `CARTORIO_API_KEY`, fail-open validado.
**Risco:** token bot/webhook secret vazado em script ad-hoc; chave divergente entre backend/n8n/scripts.
**Comandos:** `python3 scripts/check_no_literal_keys.py`; `git grep -n <padrões>` (sem imprimir valores).
**Rollback:** sanitização é aditiva; deleção de testes ad-hoc registrada no relatório de varredura.
**Evidência:** scrub de secrets em scripts no commit `bc9823c` (chore security).
**Aceite:** checker bloqueia hex-64 no pre-commit/CI; `.gitignore` cobre ad-hoc; drill Redis-down passa.

- [ ] **G9.S5.T1** (ex-G9.09.T1) — Auditar `backend/scripts/stress_telegram_prod*.py`, `scripts/test_telegram_e2e.sh` e os `backend/test_*.py` ad-hoc por segredos literais (token bot, webhook secret, chave zen) — listar ocorrências SEM imprimir valores.
- [ ] **G9.S5.T2** (ex-G9.09.T2) — Sanitizar: segredos passam a vir de env/`.secrets` com mascaramento; decidir destino de `test_send_tg.py`, `test_webhook*.py`, `test_llm*.py` (sanitizar + gitignore ou deletar — hoje untracked).
- [ ] **G9.S5.T3** (ex-G9.09.T3) — Confirmar `.gitignore` cobrindo arquivos de teste ad-hoc com credenciais; gate `git grep` no pre-commit.
- [ ] **G9.S5.T4** (ex-G9.09.T4) — Varredura histórica (git log/trufflehog) nos paths afetados; relatório com recomendação de rotação — decisão exclusiva do dono (proibido rotacionar sem ordem expressa).
- [ ] **G9.S5.T5** (ex-G9.10.T1) — `scripts/check_no_literal_keys.py`: adicionar padrão hex-64 genérico (cobre webhook secrets); teste positivo/negativo do checker.
- [ ] **G9.S5.T6** (ex-G9.10.T2) — Sincronizar `CARTORIO_API_KEY` entre backend, n8n e scripts com fonte única em `.secrets`; runbook de atualização (sem rotação).
- [ ] **G9.S5.T7** (ex-G9.10.T3) — CI `secrets_scan` estendido com o padrão hex-64 (bloqueia PR com novo literal).
- [ ] **G9.S5.T8** (ex-G9.10.T4) — Rate limit 3-tier por API key (N8N 600 / DPO 60 / default 30) revalidado com as chaves atuais; teste.
- [ ] **G9.S5.T9** (ex-G9.23.T1) — Drill fail-open com Redis down: rate limit degrada sem derrubar o webhook; teste.
- [ ] **G9.S5.T10** (ex-G9.23.T2) — Idempotency 24h: replay de `update_id` do Telegram → dedupe confirmado; teste.

### Squad S6 — cartorio-ai & Runbooks (brain/docs)
**Objetivo:** pacote `cartorio-ai/` completo (núcleo + registries) e runbooks operacionais vivos.
**Risco:** placeholder de 1 linha regredindo; runbook divergente da realidade.
**Comandos:** gate CI anti-placeholder; diff quinzenal AGENTS.md → cartorio-ai.
**Rollback:** docs são append-friendly; reverter commit de docs não afeta runtime.
**Evidência:** sessão C4 (núcleo 15 arquivos) + sessão A4 (28 registries/docs) — 2026-07-20.
**Aceite:** 43 arquivos reais no pacote; runbooks webhook/LLM/CNJ/segredos publicados; gate no CI.

- [x] **G9.S6.T1** (ex-G9.11.T1) — `cartorio-ai/AGENTS.md`, `README.md` e `ARCHITECTURE.md` escritos com conteúdo real do projeto (missão, stack, regras P0, relação com `backend/` e `.harness/`) — sessão C4 2026-07-20.
- [x] **G9.S6.T2** (ex-G9.11.T2) — `cartorio-ai/MANIFEST.md`, `INDEX.md` e `BOOTSTRAP.md` escritos (inventário do núcleo, índice navegável, boot de agente novo em <10min) — sessão C4 2026-07-20.
- [ ] **G9.S6.T3** (ex-G9.11.T3) — Completar os demais diretórios/arquivos do layout (~400 arquivos) conforme `cartorio-ai/ROADMAP.md` — fase posterior, não bloqueia G9. (Registries A4 preenchidos 2026-07-20.)
- [ ] **G9.S6.T4** (ex-G9.11.T4) — Gate no CI: nenhum arquivo-núcleo do `cartorio-ai/` pode regredir a placeholder de 1 linha.
- [x] **G9.S6.T5** (ex-G9.12.T1) — `brain/BRAIN.md`, `identity/SOUL.md` e `identity/IDENTITY.md` com propósito, valores e workflow obrigatório reais — sessão C4 2026-07-20.
- [x] **G9.S6.T6** (ex-G9.12.T2) — `planning/GOALS.md` e `planning/TASKS.md` apontando para o SUPER PLANO G9 com estado atual — sessão C4 2026-07-20 (reformatado 10×10 na sessão A4).
- [x] **G9.S6.T7** (ex-G9.12.T3) — `memory/MEMORY.md`, `security/SECURITY.md` e `compliance/CNJ.md` com fatos de 2026-07-20 (webhook fix, fallback zen, CNJ export) — sessão C4 2026-07-20.
- [ ] **G9.S6.T8** (ex-G9.12.T4) — Sync quinzenal AGENTS.md raiz → cartorio-ai (script + diff no CI).
- [ ] **G9.S6.T9** (ex-G9.24.T1) — Runbook webhook Telegram (re-sync, troubleshooting 401/5xx, rotação de secret SÓ com ordem do dono).
- [ ] **G9.S6.T10** (ex-G9.24.T2) — Runbook LLM zen 3 contas (fallback, timeouts, payload por provider).

### Squad S7 — WhatsApp Readiness & SUI DNS/Chatwoot (n8n/sre — execução do dono)
**Objetivo:** tudo pronto para o dia do QR e DNS chatwoot/n8n/supabase resolvendo.
**Risco:** QR expira; NXDOMAIN bloqueia go-live SUI; handoff sem labels LGPD.
**Comandos:** `make dns-check-strict`; packs `docs/CHATWOOT_GO_LIVE_SUI_G7.md`, `docs/WA_EMOLUMENTO_LIVE_SUI_G7.md`.
**Rollback:** DNS removido volta ao estado anterior; workflows ficam desativados até o QR.
**Evidência:** parser dual-format coberto por fuzz (G7.04.T3); snapshot 3× NXDOMAIN.
**Aceite:** checklist pré-QR completo + DNS `exit 0` + smoke pós-DNS 200 nos 3 domínios.

- [ ] **G9.S7.T1** (ex-G9.15.T1) — Checklist pré-QR: instância `state=close` confirmada, envs, webhook dual-format (legado root-level + aninhado `data.message`) já coberto por fuzz (G7.04.T3).
- [ ] **G9.S7.T2** (ex-G9.15.T2) — Workflow n8n de monitoramento de state → alerta Telegram pronto para ativar pós-QR (template do G8.22.T2).
- [ ] **G9.S7.T3** (ex-G9.15.T3) — TTL rígido de 24h das mensagens WhatsApp validado em staging (G8.22.T3) + teste de retenção.
- [ ] **G9.S7.T4** (ex-G9.15.T4) — Runbook "dia do QR": do scan à 1ª mensagem real (prepara a execução live do G9.S8.T2).
- [ ] **G9.S7.T5** (ex-G9.16.T1, herda G7.05.T1) — DNS chatwoot A record + Traefik router — pack `docs/CHATWOOT_GO_LIVE_SUI_G7.md`; execução Gustavo.
- [ ] **G9.S7.T6** (ex-G9.16.T2, herda G7.12.T1) — 3 A records chatwoot/n8n/supabase (último snapshot: 3× NXDOMAIN); após criar, `make dns-check-strict` exit 0.
- [ ] **G9.S7.T7** (ex-G9.16.T3, herda G7.05.T3) — Handoff WF3 + labels LGPD em prod (pack pronto; prod HOLD).
- [ ] **G9.S7.T8** (ex-G9.16.T4) — Pós-DNS: smoke chatwoot/n8n/supabase → 200 e radar verde.
- [ ] **G9.S7.T9** (ex-G9.17.T1, herda G7.11.T1) — Tailscale online restore na VPS (pack `TAILSCALE_RESTORE_G7`).
- [ ] **G9.S7.T10** (ex-G9.17.T2, herda G7.11.T2) — SSH 22 + MagicDNS health no radar (`docs/TAILSCALE_SSH_RADAR_LIVE_G7.md`).

### Squad S8 — OpenClaw, WA Live, Testes 1000 & CI (dev/sre)
**Objetivo:** OpenClaw bot deployado, 1ª mensagem WA real respondida, bateria 1000 como gate e pipeline completo.
**Risco:** flake na bateria; gate lento > 5min; deploy OpenClaw sem revisão.
**Comandos:** `make qa`; `pytest -m "not smoke and not integration and not e2e"`; pack `docs/OPENCLAW_CARTORIO_BOT_DEPLOY_G7.md`.
**Rollback:** desativar gates novos no CI temporariamente; OpenClaw bot permanece HOLD até aprovação.
**Evidência:** `backend/tests/test_telegram_1000.py` (commit `4f43ff8`); bateria 1000 PASS 2026-07-20.
**Aceite:** E8 deployado + WA live 1 msg + coverage telegram.py ≥95% + CI publica junit/cobertura.

- [ ] **G9.S8.T1** (ex-G9.17.T3, herda G7.06.T3) — OpenClaw cartorio-bot create E8 (`docs/OPENCLAW_CARTORIO_BOT_DEPLOY_G7.md`; JSON pronto, deploy HOLD).
- [ ] **G9.S8.T2** (ex-G9.17.T4, herda G7.04.T4) — 1 mensagem real WA → resposta de emolumento (`docs/WA_EMOLUMENTO_LIVE_SUI_G7.md`; depende do QR — S7).
- [x] **G9.S8.T3** (ex-G9.18.T1) — Diagnóstico E4: inventário de testes/stress/smoke consolidado; `backend/tests/test_telegram_1000.py` com 1000 interações mockadas (commit `4f43ff8`); SUPER_PLANOs G7/G8 revisados → base deste G9.
- [x] **G9.S8.T4** (ex-G9.18.T2) — Bateria 1000 ampliada: cenários grupo/menção/comandos/mídia + header de secret; sem flakiness (fakeredis/respx).
- [x] **G9.S8.T5** (ex-G9.18.T3) — Bateria 1000 como gate de CI (marker próprio, < 5min, relatório junit).
- [ ] **G9.S8.T6** (ex-G9.18.T4) — Cobertura de `telegram.py` ≥95% mantendo gate global de 90%; mutation spot-check nos handlers novos.
- [ ] **G9.S8.T7** (ex-G9.19.T1) — `make qa` verde local e no CI após as mudanças G9 (lint 0 errors + test com coverage ≥90%).
- [ ] **G9.S8.T8** (ex-G9.19.T2) — Gate "webhook sempre-200" (regressão A3) obrigatório no CI.
- [ ] **G9.S8.T9** (ex-G9.19.T3) — Gate de coerência de slots LLM (G9.S3.T3) no CI.
- [ ] **G9.S8.T10** (ex-G9.19.T4) — Pipeline publica artifacts de cobertura + junit.

### Squad S9 — Audit Chain, LGPD Rights & HITL (lgpd+dev)
**Objetivo:** cadeia verificada em prod, direitos Art. 18 em drill, protocolo DRAFT→HITL auditado.
**Risco:** cadeia quebrada sem alerta; direito de eliminação falhando; bot decidindo ato jurídico.
**Comandos:** verificação read-only da cadeia (amostra + full off-hours); drill Art. 18 com evidências.
**Rollback:** nenhum rollback de audit (append-only); corrigir forward com nova entrada.
**Evidência:** dead-man's-switch 15min ativo; regressões `t024`/`t025`/`t036`/`t037` verdes.
**Aceite:** relatório de verificação prod + drill completo + métrica HITL no DPO dashboard.

- [ ] **G9.S9.T1** (ex-G9.20.T1) — Verificação read-only da cadeia SHA256 em prod (amostra + full em janela off-hours); relatório.
- [ ] **G9.S9.T2** (ex-G9.20.T2) — Dead-man's switch (audit check a cada 15min) com alerta ao DPO; teste de falha injetada em staging.
- [ ] **G9.S9.T3** (ex-G9.20.T3) — Regressões `t024` (retro-edit mid-chain) e `t025` (rotação HMAC) verdes no CI.
- [ ] **G9.S9.T4** (ex-G9.20.T4) — Procedimento de evidência forense documentado (export + verificação independente), alinhado ao fluxo CNJ.
- [ ] **G9.S9.T5** (ex-G9.21.T1) — Drill Art. 18 completo (acesso, correção, anonimização, portabilidade, eliminação, oposição, não-automação) com evidências.
- [ ] **G9.S9.T6** (ex-G9.21.T2) — Scheduler de retenção 03:00 BRT validado (`t036`/`t037`) + métrica de execuções.
- [ ] **G9.S9.T7** (ex-G9.21.T3) — RIPD v1.6 incluindo fallback zen 3 contas e CNJ massive-dump.
- [ ] **G9.S9.T8** (ex-G9.21.T4) — Data inventory refresh pós-G9 (novos campos PII).
- [ ] **G9.S9.T9** (ex-G9.22.T1) — E2E: protocolo nasce `DRAFT`, escrevente valida; bot nunca decide isenção/urgência/emissão sozinho.
- [ ] **G9.S9.T10** (ex-G9.22.T2) — Takeover Chatwoot → mute imediato do bot (G8.03.T2) revalidado após as mudanças de Telegram.

### Squad S10 — HITL Cont., Degradação, Runbooks Finais & Governança (lgpd/dev/docs/brain)
**Objetivo:** aprovação humana registrada, anti-spam por chat, runbooks CNJ/segredos, memória e release G9.
**Risco:** sugestão de minuta sem aprovação; spam de usuário; lição G9 perdida.
**Comandos:** revisão `cartorio-lgpd`; tag `v0.9.0-g9` quando S1–S5 fecharem.
**Rollback:** docs/memória append-only; tag só após aceite do dono.
**Evidência:** `STATUS.md`/`PROGRESS.md` reescritos 2026-07-20 (sessão C4).
**Aceite:** 4 runbooks publicados + MEMORY.md consolidada + SUI_CHECKLIST atualizado + release notes.

- [ ] **G9.S10.T1** (ex-G9.22.T3) — Sugestões de minuta/escritura do LLM sempre com aprovação humana registrada no audit.
- [ ] **G9.S10.T2** (ex-G9.22.T4) — Métrica HITL no DPO dashboard.
- [ ] **G9.S10.T3** (ex-G9.23.T3) — Rate limit adicional por `chat_id` (anti-spam de usuário) além de IP/key; teste.
- [ ] **G9.S10.T4** (ex-G9.23.T4) — Limites e comportamento de degradação documentados no runbook operacional.
- [ ] **G9.S10.T5** (ex-G9.24.T3) — Runbook CNJ export (solicitar, aprovar como DPO, baixar, verificar hash).
- [ ] **G9.S10.T6** (ex-G9.24.T4) — Política de segredos em scripts/testes (onde vivem, como mascarar, checker hex-64).
- [ ] **G9.S10.T7** (ex-G9.25.T1) — Lesson G9 consolidada em `.harness/memory/MEMORY.md` (webhook secret sync, debounce A5/A6, fallback zen).
- [x] **G9.S10.T8** (ex-G9.25.T2) — `STATUS.md` reescrito e `PROGRESS.md` atualizado com o estado 2026-07-20 (telegram funcional validado, pendências, próximos passos) — sessão C4.
- [ ] **G9.S10.T9** (ex-G9.25.T3) — SUI_CHECKLIST atualizado com as pendências G9 (DNS, Tailscale, QR, OpenClaw).
- [ ] **G9.S10.T10** (ex-G9.25.T4) — Tag `v0.9.0-g9` + release notes quando Squads S1–S5 fecharem.

---

## MAPA DE ONDAS (sugerido)

| Wave | Squads | Foco |
|------|--------|------|
| W54–W56 | S1, S3 | Telegram código + LLM slots/timeouts/payload |
| W57–W59 | S3, S4 | LGPD-015 + CNJ stream/JWT/hash/relatório |
| W60–W61 | S5 | scrub secrets + hex-64 checker + API key sync |
| W62–W63 | S2 | métricas telegram + GIT_SHA + alertas |
| W64–W66 | S7 (Gustavo) | WA prep + DNS/Chatwoot + Tailscale |
| W67–W68 | S8 | OpenClaw/WA live + bateria 1000 + CI gates |
| W69–W71 | S9 | audit chain prod + LGPD rights + HITL |
| W72–W74 | S10, S6 | degradação + runbooks + memória + tag |

---

**Modified by Gustavo Almeida + orquestrador G9 — 2026-07-20**
(Plano G9 reformatado: 10 squads × 10 tasks; 25/100 concluídas na sessão 2026-07-20 com evidência; IDs antigos 25×4 preservados entre parênteses)
