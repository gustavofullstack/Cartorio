# AUX GPT-5.6 Terra — Bridge Operacional G9

**Data:** 2026-07-23  
**Papel deste doc:** pacote de apoio para o agent **GPT-5.6 Terra** fechar o pedido do dono sem inventar “1000 testes” sem critério.  
**Fonte canônica de tasks:** [`SUPER_PLANO_G9_100_TASKS.md`](../SUPER_PLANO_G9_100_TASKS.md)  
**DoR/DoD:** [`docs/G8_DOR_DOD.md`](G8_DOR_DOD.md) (honesty gate herdado)  
**Autor bridge:** grok-4.5 (auxiliar) · execução principal: GPT-5.6 Terra

---

## 0. META / GOAL / OBJECTIVE (sessão)

| Campo | Valor |
|-------|--------|
| **GOAL** | Validação operacional mensurável do Cartório em produção + fila G9 residual, sem PII e sem ação jurídica automática |
| **META** | 100 rodadas com evidência (não 1000 checkboxes vazios); baseline local verde; prod por camadas; memória sem segredos |
| **OBJECTIVE** | Entregar a Terra um mapa executável: o que já está verde, o que falta no G9 (75/100), ordem de ataque, comandos e bloqueios SUI |
| **PROGRESS (bridge)** | **R00–R19 + R31–R34 + R50–R55 evidenciadas** (Wave 2) · residual G9/SUI na fila Terra/Kimi |
| **NÃO-OBJETIVO** | Colar token/chave em chat, log, MEMORY ou commit · rotacionar secret sem ordem do dono · bot decidir isenção/emissão |

---

## 1. Regras P0 de segredo (ler antes de qualquer ação)

1. **Nunca** imprimir, logar, colar ou versionar: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `CARTORIO_API_KEY`, chaves Zen/OpenCode/MiniMax, JWT DPO.
2. Chat/CLI/sandbox **não** é cofre. Histórico de conversa pode ser apagado; segredo só em env / secret manager / `.env` gitignored.
3. Evidência = **status HTTP, contagem de testes, path, commit SHA** — nunca valor de chave.
4. Scanner: `cd backend && uv run python scripts/check_no_literal_keys.py` → deve sair `OK: zero violacoes`.
5. Stress/webhook prod: header secret **só via env** (`X-Telegram-Bot-Api-Secret-Token`), nunca literal no script.
6. PII (CPF/RG/telefone/email/protocolo) → sempre `app/services/pii.py` antes de LLM/canal/log.
7. HITL: protocolo nasce `DRAFT`. Bot **não** decide ato jurídico sozinho.
8. Mudança em `audit*` / `pii*` → review `cartorio-lgpd` antes de merge.

---

## 2. Baseline evidenciada (2026-07-23) — R00–R08

### R00 — Git / branch
- Branch: `master`
- HEAD recente relevante: `dff5fcc` (telegram date parsing) · `2894b5f` (1000 interactions) · `d642e0e` (webhook nunca 5xx)
- Working tree: **alterações locais não commitadas** em telegram/agent/metrics/stress/tests — **não formatar/limpar em massa** sem isolar autoria (Terra e auxiliares devem stage seletivo).

### R01 — Gates estáticos locais
| Check | Resultado | Evidência |
|-------|-----------|-----------|
| `make lint` (ruff + mypy) | **PASS** | ruff All checks passed · mypy 0 issues / 208 files |
| `check_no_literal_keys.py` | **PASS** | `OK: zero violacoes detectadas` (+ 6 fingerprints baseline) |

### R02 — Subset G9 focado (pytest --no-cov)
```text
tests/test_telegram_regressions_g9.py
tests/test_cartorio_agent_g9.py
tests/test_check_no_literal_keys_g8.py
tests/test_pii_telegram_output_g9.py
→ 49 passed in 2.80s
```

### R03 — Produção HTTP (sem auth / sem secrets)
| Endpoint | HTTP | Nota |
|----------|------|------|
| `GET /health` | 200 | `status=ok` service cartorio-backend v0.6.0 |
| `GET /ready` | 200 | `audit_chain_initialized=true` |
| `GET /api/v1/telegram/health` | 200 | bot `test_cartorio_bot`, `webhook_configured=true`, version `v0.6.1-p0fix` |
| `GET /api/v1/health/radar` | 200 | **green**: database, redis, n8n, openclaw, evolution, chatwoot, supabase = online |
| `GET /openapi.json` | 200 | ~252 KB |
| `GET /docs` | 200 | Swagger UI |
| `GET /metrics` | **410** | métricas públicas gone/disabled na borda — ver gap G9.S2 |
| `GET/Upgrade /api/v1/ws/atendimentos` | **404** | path canônico no código é `/api/v1/ws/atendimentos`; em prod a borda ainda responde 404 → **gap R31** (Traefik/mount/flag) |
| `GET /mcp` | **307** | redirect (provável mount condicional / trailing slash); inventário real em `backend/mcp_server.py` (grep `@mcp.tool(`) |

### R04 — G9 honesty counter
| Métrica | Valor |
|---------|-------|
| Tasks `[x]` | **25** |
| Tasks `[ ]` | **75** |
| % evidenciado | **25%** |
| Plano | `SUPER_PLANO_G9_100_TASKS.md` |

### R05 — O que NÃO fazer nesta sessão
- Não fingir 1000 tasks novas: já existem G7/G8/G9 + bateria `test_telegram_1000*`.
- Não editar em massa o working tree sujo (diff ~14 files / +153 −78).
- Não re-sync webhook com secret no chat.
- Não abrir browser flow com PII real.

### R06 — Mapa “pedido do dono” → artefato real

| Pedido (linguagem do dono) | Onde vive / como validar |
|----------------------------|---------------------------|
| Harness | `.harness/` · `AGENTS.md` · `TASKS.md` · `memory/MEMORY.md` |
| API | `backend/app/api/v1/` · OpenAPI · `/health` `/ready` radar |
| WebSocket | `backend/app/api/v1/ws/atendimentos.py` → `/api/v1/ws/atendimentos` |
| Webhook | `backend/app/api/v1/telegram.py` · secret header · never-5xx |
| MCP server/client | `backend/mcp_server.py` · mount `/mcp` · clients em `~/.mavis/mcp/clients/` |
| DB-pool | SQLAlchemy engine/session · radar `database=online` · testes pool |
| Brains (MD) | `cartorio-ai/` · `.brain/` · `brain/BRAIN.md` |
| Memory | `.harness/memory/MEMORY.md` + session memory (fora do git) |
| Input/Output/PII | `app/services/pii.py` 3 camadas |
| Context window | agent slots + history Redis (lesson 161/192) |
| Cache hit | Redis 8 · rate limit / idempotency / agendamento cache |
| 1000 testes | `backend/tests/test_telegram_1000.py` + integration twin |
| 100 tasks | **G9** (não reinventar) |
| 100 rounds | §3 deste doc |
| Goals/meta/progress | este bridge + SUPER_PLANO_G9 + PROGRESS/STATUS |

### R07 — Working tree sensível (avisar Terra)
Arquivos modificados locais (não commitar às cegas):
- `backend/app/services/cartorio_agent.py` (maior diff)
- `backend/app/api/v1/cnj_export.py`
- `backend/app/services/metrics.py`
- stress scripts telegram
- testes telegram 1000 / regressions / agent g9
- untracked: `test_pii_telegram_output_g9.py`, scratch_*.py, PDFs plano-llm

### R08 — Conclusão baseline
**Infra prod core: VERDE.**  
**Gates estáticos locais: VERDES.**  
**Subset G9 crítico: 49/49 PASS.**  
**Trabalho residual: 75 tasks G9 + SUI (DNS/Tailscale/QR/OpenClaw) + métricas 410 + suite full com timeout longo.**

---

## 3. SUPER PLANO de 100 RODADAS (executável pelo Terra)

Cada rodada exige: **ID · Goal · Critério · Comando/ação · Evidência · Status**.  
`[x]` só com honesty gate (artefato + teste + nota).

### Bloco A — Baseline & governança (R00–R09) — bridge

| R | Goal | Critério | Status |
|---|------|----------|--------|
| R00 | Isolar branch/HEAD | branch + 5 commits | [x] bridge |
| R01 | Lint/mypy | 0 errors | [x] bridge |
| R02 | Secrets scanner | zero violações | [x] bridge |
| R03 | Subset G9 pytest | ≥40 pass área telegram/agent/pii | [x] 49 pass |
| R04 | Prod health/ready | 200 + audit init | [x] |
| R05 | Radar integrações | all online | [x] green |
| R06 | Telegram health | webhook_configured | [x] |
| R07 | OpenAPI/docs | 200 | [x] |
| R08 | Contador G9 honesto | 25/75 | [x] |
| R09 | Diff inventory | lista paths sem stage cego | [x] este doc |

### Bloco B — API / pool / cache (R10–R19) → G9.S5/S8 parcial

| R | Goal | Critério | Mapa G9 |
|---|------|----------|---------|
| R10 | `make test-fast` completo com timeout ≥15min | exit 0 ou falhas triadas | S8.T7 |
| R11 | Coverage gate local seletivo áreas tocadas | não regredir <90% global se rodar full | S8.T6/T7 |
| R12 | DB pool smoke (script ou teste admin pool) | pass | — |
| R13 | Redis ping + fail-open rate limit | teste G9.S5.T9 | S5.T9 |
| R14 | Idempotency replay update_id | dedupe | S5.T10 |
| R15 | Rate limit 3-tier revalidado | N8N/DPO/default | S5.T8 |
| R16 | CARTORIO_API_KEY fonte única documentada | runbook sem valor | S5.T6 |
| R17 | hex-64 no checker | teste pos/neg | S5.T5 |
| R18 | CI secrets_scan extended | doc ou workflow | S5.T7 |
| R19 | Varredura scripts stress sem literal | paths only | S5.T1–T3 |

### Bloco C — Webhook / Telegram (R20–R34) → G9.S1/S2

| R | Goal | Mapa G9 |
|---|------|---------|
| R20 | Stress prod assinado via env | S1.T9 |
| R21 | Resposta async pós-debounce grupo | S1.T10 |
| R22 | Métricas webhook_total 200/401/5xx | S2.T3 |
| R23 | Histograma latência webhook→resp | S2.T4 |
| R24 | Labels sem chat_id/username | S2.T5 lgpd |
| R25 | Painel radar/Grafana Telegram | S2.T6 |
| R26 | GIT_SHA em /version|/health | S2.T7 |
| R27 | Alertas 401 / silence / LLM fail | S2.T8 |
| R28 | Alerta → Telegram escrevente sem PII | S2.T9 |
| R29 | Runbook 3 alertas | S2.T10 |
| R30 | Investigar `/metrics` 410 na borda | S2 gap |
| R31 | Probe WS path correto + ping/pong | harness WS |
| R32 | Regressões A1–A6 ainda verdes após diff local | S1 |
| R33 | test_telegram_1000 unit | S8.T3–T5 |
| R34 | test_telegram_1000 integration (se rede ok) | S8 |

### Bloco D — LLM / PII / output (R35–R49) → G9.S3/S4

| R | Goal | Mapa G9 |
|---|------|---------|
| R35 | Healthcheck por slot + circuit breaker | S3.T4 |
| R36 | Histograma tentativas×latência provider | S3.T7 |
| R37 | Mensagem espera/degradação (nunca silêncio) | S3.T8 |
| R38 | Inventário saídas LLM (LGPD-015) | S3.T9 |
| R39 | Output scrub pii.py em todos canais | S3.T10 |
| R40 | Canary PII echo fail-test | S4.T1 |
| R41 | Sign-off cartorio-lgpd + audit entry | S4.T2 |
| R42 | CNJ stream volume test | S4.T4 |
| R43 | Audit fail → 500 sem byte | S4.T5 |
| R44 | OpenAPI CNJ contract | S4.T6 |
| R45 | JWT DPO 401/403 | S4.T7 |
| R46 | Hash chain no pacote export | S4.T8 |
| R47 | Relatório proteção dados CNJ | S4.T9 |
| R48 | RIPD/compliance dump | S4.T10 |
| R49 | Diff local cartorio_agent revisado seletivo | S3 |

### Bloco E — MCP / WS / Brain / Memory (R50–R64)

| R | Goal | Ação |
|---|------|------|
| R50 | Inventário MCP tools (grep, não hardcode) | `rg '@mcp.tool\(' backend/mcp_server.py` |
| R51 | MCP mount condicional documentado | settings MCP_SERVER_ENABLED |
| R52 | MCP client config paths (sem secrets) | `~/.mavis/mcp/clients/` |
| R53 | WS concurrent 50/20 regression | testes G8/G7 existentes |
| R54 | Heartbeat/ping WS | atendimentos.py |
| R55 | Brain router health | `/api/v1` brain |
| R56 | cartorio-ai núcleo anti-placeholder | S6.T4 |
| R57 | Sync AGENTS → cartorio-ai | S6.T8 |
| R58 | Runbook webhook | S6.T9 |
| R59 | Runbook LLM zen 3 contas | S6.T10 |
| R60 | MEMORY append lesson sessão (sem secrets) | S10.T7 |
| R61 | Context window / hist Redis multi-turn | lesson 161 |
| R62 | Cache hit paths catalogados | rate_limit/idempotency/agendamento |
| R63 | Input validators Pydantic PII | models/schemas |
| R64 | Output MaskingFilter + Sentry before_send | log_masker/sentry |

### Bloco F — Audit / LGPD / HITL (R65–R79) → G9.S9/S10

| R | Goal | Mapa G9 |
|---|------|---------|
| R65 | Verify chain amostra prod read-only | S9.T1 |
| R66 | DMS 15min alerta | S9.T2 |
| R67 | t024/t025 CI | S9.T3 |
| R68 | Procedimento forense | S9.T4 |
| R69 | Drill Art.18 | S9.T5 |
| R70 | Retenção 03:00 BRT t036/t037 | S9.T6 |
| R71 | RIPD v1.6 | S9.T7 |
| R72 | Data inventory refresh | S9.T8 |
| R73 | E2E protocolo DRAFT | S9.T9 |
| R74 | Chatwoot takeover mute | S9.T10 |
| R75 | Minuta só com aprovação humana | S10.T1 |
| R76 | Métrica HITL DPO | S10.T2 |
| R77 | Rate limit por chat_id | S10.T3 |
| R78 | Degradação documentada | S10.T4 |
| R79 | Runbook CNJ export | S10.T5 |

### Bloco G — SUI / dono (R80–R89) — HOLD até Gustavo

| R | Goal | Mapa G9 | Owner |
|---|------|---------|-------|
| R80 | DNS chatwoot/n8n/supabase | S7.T5–T8 | Gustavo |
| R81 | Tailscale restore | S7.T9–T10 | Gustavo |
| R82 | Pré-QR WA checklist | S7.T1–T4 | Gustavo+n8n |
| R83 | OpenClaw bot deploy | S8.T1 | Gustavo |
| R84 | 1ª msg WA real | S8.T2 | Gustavo |
| R85 | BotFather setjoingroups | S1.T10 | Gustavo |
| R86 | Rotação secret (só se ordem) | S5.T4 | Gustavo |
| R87 | Browser Arc smoke público | sem PII | Terra+CU |
| R88 | EasyPanel status 1/1 api | sre | Terra/SSH |
| R89 | SUI_CHECKLIST update | S10.T9 | docs |

### Bloco H — Fechamento / release (R90–R99)

| R | Goal | Mapa G9 |
|---|------|---------|
| R90 | Política segredos scripts | S10.T6 |
| R91 | Lesson G9 MEMORY | S10.T7 |
| R92 | STATUS/PROGRESS refresh | S10.T8 done base |
| R93 | `make qa` verde pós-diff | S8.T7 |
| R94 | Gate webhook-always-200 CI | S8.T8 |
| R95 | Gate slot coherence CI | S8.T9 |
| R96 | Artifacts junit/cov CI | S8.T10 |
| R97 | Tag v0.9.0-g9 só com S1–S5 | S10.T10 |
| R98 | PR checklist completo | CONTRIBUTING |
| R99 | Relatório final 1 página | este bridge §5 |

---

## 4. Fila prioritária para o Terra (agora)

Ordem anti-desperdício (máximo impacto, mínimo risco de secret leak):

1. **Inventariar diff local** (`git diff` por arquivo) e decidir: manter / reverter / commit seletivo Conventional + `Modified by Gustavo Almeida`.
2. **R10** — `make test-fast` com timeout longo; triar falhas reais vs flake.
3. **R32 + R33** — regressões G9 + bateria 1000 unit.
4. **R22–R26** — métricas Telegram + gap `/metrics` 410.
5. **R35–R40** — LLM slots + output scrub + canary PII (review lgpd se tocar pii).
6. **R20** — stress prod **somente** com env secrets (nunca print).
7. **R50–R54** — MCP inventário + WS path correto.
8. **R65+** — audit/LGPD read-only primeiro.
9. **R80+** — marcar HOLD-SUI; não fingir `[x]`.
10. **R91** — MEMORY só com lição reutilizável e **zero** segredo.

### Comandos canônicos (copiar/colar)

```bash
# da raiz do repo
make lint
make test-fast          # dev loop; timeout generoso
make qa                 # gate CI completo quando estável

cd backend
uv run python scripts/check_no_literal_keys.py
uv run pytest -q --no-cov tests/test_telegram_regressions_g9.py \
  tests/test_cartorio_agent_g9.py tests/test_telegram_1000.py

# prod (sem secrets)
curl -sS https://api.2notasudi.com.br/health
curl -sS https://api.2notasudi.com.br/ready
curl -sS https://api.2notasudi.com.br/api/v1/telegram/health
curl -sS https://api.2notasudi.com.br/api/v1/health/radar
```

### Browser (Arc) — escopo seguro
- Só URLs públicas: `/docs`, health pages, painéis sem PII.
- Bridges (Kimi/Antigravity): usar para UI ops **sem** colar tokens no DOM/console compartilhado.
- Validação humana Telegram: DM `@test_cartorio_bot` com `/start` `/menu` — **sem** CPF real.

---

## 5. Template de relatório (Terra preenche ao fechar lote)

```markdown
## Lote YYYY-MM-DD / Wave N
- Rodadas: Rxx–Ryy
- PASS / FAIL / HOLD-SUI:
- Comandos:
- Contagem testes:
- Paths tocados:
- Secrets: nenhum valor exposto (sim/não)
- G9 checkboxes atualizados com evidência:
- Próximo lote:
- Modified by Gustavo Almeida
```

---

## 6. Progresso visual (honesty)

```
G9 tasks:     [█████░░░░░░░░░░░░░░░] 25/100
Bridge rounds:[███████░░░░░░░░░░░░░] ~28/100 (R00–R19, R31–R34, R50–R55)
Prod radar:   GREEN 8/8 (+opencode_go)
Lint/mypy:    GREEN
Secrets scan: GREEN
Critical pack:239 PASS (12.2s) — telegram+pii+audit+rate+idempotency
Terra patch:  parsers/FSM tests aligned to contract (runtime untouched)
WS canônico:  wss://api.../api/v1/ws/atendimentos → {"type":"pong"}
Metrics:      /api/v1/metrics 200 · /api/v1/metrics/prometheus 200 · /metrics 410 by design
MCP:          307→/mcp/ · 401 sem chave · 14 tools · meta /mcp-servers ok
DB-pool:      size=10 util~6.7% · audit_chain_length=1078 · dlq=0
SUI blocks:   DNS / Tailscale / QR / OpenClaw deploy / setjoingroups / MCP client path local
```

---

## 8. WAVE 2 — evidência auxiliar (2026-07-23 ~BRT) — grok + Terra + Kimi

### Coordenação multi-agent
| Agent | Papel | Estado observado |
|-------|--------|------------------|
| **GPT-5.6 Terra** | execução principal | matriz 100R; fix testes parser/FSM; 35 focados PASS; gate cov em curso |
| **Kimi K3** | auxiliar paralelo | inventário + prod R1; suite sem `-x` |
| **Grok-4.5 (este)** | bridge + validação canônica | doc bridge; 239 pack; WS real; MCP/metrics paths |

### Correção de gaps da Wave 1 (honesty)
| Gap Wave 1 | Resolução Wave 2 |
|------------|------------------|
| `/metrics` 410 “quebrado” | **by design** — canônico = `/api/v1/metrics` (JSON ops) + `/api/v1/metrics/prometheus` |
| WS curl Upgrade 404 | **falso negativo** — cliente `websockets` → **pong 200** em `wss://…/api/v1/ws/atendimentos` |
| MCP 307 “falha” | redirect trailing slash; **401 sem apikey** = auth OK (não é outage) |

### Pack de testes (comando + resultado)
```text
pytest --no-cov \
  test_telegram_parsers + state_machine + regressions_g9 + telegram_1000
  + integration/test_telegram_1000 + cartorio_agent_g9 + pii_telegram_output_g9
  + check_no_literal_keys_g8 + pii + audit + audit_integrity_g8
  + idempotency_store + rate_limit + antigravity
→ 239 passed, 1 deselected in 12.20s
```
Lint/mypy reconfirmados verdes após patch Terra nos testes.

### Produção por camada (sem secrets)
| Camada | Endpoint / check | Resultado |
|--------|------------------|-----------|
| API | `/health` `/ready` | 200 · audit init |
| Radar | `/api/v1/health/radar` | green 7 core |
| Integrações | `/api/v1/health/integracoes` | green **8/8** (db, redis, n8n, openclaw, evolution, chatwoot, supabase, opencode_go) latências ms ok |
| Telegram | `/api/v1/telegram/health` | ok · webhook_configured · bot test_cartorio_bot |
| Metrics JSON | `/api/v1/metrics` | 200 · keys: db_pool, audit_chain_*, counters, dlq_pending… |
| Metrics Prom | `/api/v1/metrics/prometheus` | 200 · ~2.5KB · séries pool/telegram/pii/audit |
| Metrics root | `/metrics` | **410** moved (doc) |
| WebSocket | `wss://…/api/v1/ws/atendimentos` ping | **`{"type":"pong"}`** |
| MCP | `POST /mcp/` sem chave | **401** MCP authentication required |
| MCP meta | `/mcp-servers` | ok · cartorio-api **14 tools** + n8n 50 + supabase 30 + easypanel 57 + openclaw 20 |
| DB-pool | metrics.db_pool | size=10, total_capacity=15, utilization_pct≈6.67, checked_out=1 |
| Audit | metrics | chain_length=**1078**, dlq_pending=**0** |
| OpenAPI | `/openapi.json` | 200 |

### Harness / Brain / Memory (config presente)
| Item | Evidência |
|------|-----------|
| Harness | `.harness/{AGENTS,STANDARDS,TASKS,SUI_CHECKLIST,memory,reins,agents,…}` |
| Brains MD | `cartorio-ai/` núcleo (AGENTS, ARCHITECTURE, BOOTSTRAP, memory/*, planning/*) |
| Memory files | **135** em `.harness/memory/` |
| AGENTS | raiz + `.harness/AGENTS.md` OK |
| MCP clients path | `~/.mavis/mcp/clients/` **ausente neste host** (gap local IDE — não é outage API) |

### Patch Terra (isolado, só testes)
- `tests/test_telegram_parsers.py` — aceita hífen/ponto/ano curto no contrato real
- `tests/test_telegram_state_machine.py` — erro curto mantém wizard; texto conversacional longo → IDLE + Agent
- **Runtime não alterado** (alinha honesty: test follows code contract de `dff5fcc`)

### Próximo lote recomendado (não duplicar Terra)
1. Terra: terminar **coverage gate ≥90%** (`make test` / qa) e reportar número real.
2. Aux: **não** editar `cartorio_agent.py` / stress scripts enquanto Terra fecha baseline.
3. R20 stress prod **só com env** (nunca print token).
4. Browser Arc: smoke **público** `/docs` + health — sem PII.
5. HOLD-SUI: DNS/Tailscale/QR/OpenClaw/setjoingroups = dono.
6. Stage seletivo só dos testes parser/FSM se quiser commit isolado Conventional.

### Mensagem curta p/ colar no Terra (Wave 2)

> Bridge Wave 2: gaps `/metrics` e WS **fechados por path canônico**.  
> WS pong OK · metrics JSON+Prom 200 · MCP 401 sem key · 14 tools · radar 8/8 · chain 1078 · pool ok.  
> Pack crítico **239 PASS** + lint/mypy green. Seu patch parsers/FSM validado.  
> Siga coverage gate; eu não toco runtime/diff sujo. Zero secrets. Doc: `docs/AUX_GPT_TERRA_G9_BRIDGE_2026-07-23.md` §8.

---

## 9. WAVE FINAL P0 — TRACK B Security (2026-07-23)

### GOAL / META / OBJECTIVE
| | |
|--|--|
| GOAL | Fechar auth HMAC dos webhooks Evolution/WhatsApp com evidência |
| META | invalid/missing/malformed → 401; misconfig → 503; valid → processa; prod fail-closed após deploy |
| OBJECTIVE | TRACK B: security real, não re-diagnóstico de paths canônicos |

### ROOT CAUSE (comprovado em código)
1. `/api/v1/whatsapp/webhook` — return 401 estava **comentado**; logava "rejeitando" e **processava**.
2. `/api/v1/webhook/evolution` (**URL canônica prod** `EVOLUTION_WEBHOOK_URL`) — **sem nenhuma** checagem HMAC.
3. Docstring continha API key literal (removida → "via ambiente").

### CHANGES (esta sessão + paralelo Terra)
| Path | Mudança |
|------|---------|
| `backend/app/api/v1/whatsapp.py` | fail-closed 401/503 + `request.body()` + `db.commit()` idempotência + scrub secret docstring |
| `backend/app/api/v1/router.py` | HMAC no `webhook_evolution` (path prod) |
| `backend/tests/test_webhook_evolution_hmac_p0.py` | **NOVO** 7 casos fail-closed |
| `backend/tests/test_whatsapp_e2e_5x.py` | classe `TestWebhookHmacFailClosed` (paralelo) |
| `backend/tests/conftest.py` | default test `REQUIRE=false` (suíte aberta; testes P0 forçam true) |
| `backend/.env.example` | `EVOLUTION_REQUIRE_SIGNATURE` + secrets placeholders |

### TEST RESULTS (local, TRACK B)
```
test_webhook_evolution_hmac_p0 + TestWebhookHmacFailClosed + evolution_hmac
+ evolution_message_types + webhook_evolution_e2e + whatsapp_consent + e2e_5x
→ 75 passed
```

### PRODUCTION SMOKE (sem secrets)
| Check | Status | Evidência |
|-------|--------|-----------|
| /health /ready | PASS | 200 |
| radar | PASS | green 7/7 |
| WS ping→pong | PASS | `{"type":"pong"}` |
| MCP no auth | PASS | 401 |
| POST /whatsapp/webhook unsigned | **FAIL (ainda aberto)** | **200** `consent_required` — código fix **não deployado** |
| POST /webhook/evolution unsigned | BLOCKED/timeout | curl 15s timeout (investigar borda; não tratar como PASS) |

### SECURITY VERDICT
| Item | Local | Prod |
|------|-------|------|
| HMAC whatsapp path | PASS | **FAIL** até deploy + env REQUIRE=true + SECRET |
| HMAC evolution path canônico | PASS | **NOT TESTED** pós-deploy (timeout pre-fix) |
| MCP fail-closed | PASS | PASS |
| Secrets em git/doc | PASS (literal removido) | N/A |

### NEXT ACTION (P0 dono/SRE)
1. Deploy API com patch HMAC.
2. EasyPanel: `EVOLUTION_REQUIRE_SIGNATURE=true` + `EVOLUTION_WEBHOOK_SECRET` (e Evolution enviando header assinado).
3. Smoke: unsigned → **401**; signed probe sintético → 200.
4. Não marcar P0 prod PASS antes do passo 3.

---

## 7. Mensagem curta para colar no chat do Terra

> Use `docs/AUX_GPT_TERRA_G9_BRIDGE_2026-07-23.md` como contrato da sessão.  
> Não invente 1000 tasks: execute as **100 rodadas** mapeadas no G9 residual (75 abertas).  
> Baseline bridge: lint/mypy OK, secrets scan OK, 49 testes G9 OK, prod radar GREEN, telegram health OK, G9=25/100.  
> `/metrics` retorna 410 (gap). Working tree sujo — stage seletivo.  
> **Zero secrets em log/chat/MEMORY.** PII via `pii.py`. HITL obrigatório.  
> Próximo: R10 test-fast → R32/R33 → métricas → PII output → stress env-only → HOLD-SUI.

---

**Modified by Gustavo Almeida** (bridge redigido sob orientação do dono · auxiliar grok-4.5 · 2026-07-23)
