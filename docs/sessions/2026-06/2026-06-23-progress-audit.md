# SESSION AUDIT — 2026-06-23 (sessão atual ZCode/Mavis)

> **Fonte da verdade:** este doc NÃO é plano, NÃO é spec. É **fotografia do estado do projeto** comparada ao briefing (chat) do Gustavo. Serve pra (a) você não repetir o mesmo briefing amanhã, (b) a próxima sessão continuar sem perder contexto, (c) matar a fantasia de "100 tasks / 7 squads / reescrever tudo".

**Data:** 2026-06-23
**Sessão:** atual (chat aberto com `/init` malformado, depois análise)
**Branch:** `master`, 18 commits, clean tree, v0.5.0 tagged (`cce5061`)

---

## 1. O que existe NO REPO (verificado, não no briefing)

### Backend FastAPI
- `backend/app/main.py` v0.5.0 + 18 endpoints v1
- `backend/app/services/` — 12 services: audit, chatwoot_handoff, emolumento, evolution_ingest, pii, protocolo, rate_limit, redis_bus, stale_detector, websocket_manager, + 2
- `backend/app/models/webhook_event.py` (idempotência)
- `backend/app/integrations/opencode_go.py` + `fallback.py`
- `backend/app/mcp_server.py` (5 servers, 164 tools)
- **186 tests passing, 93% coverage** (gate 90% hit no Sprint 2)

### Infraestrutura
- `infra/n8n-workflows/` — **18 JSONs**:
  - 00-error-handler, 01-consulta-emolumento (3 versões), 02-criar-protocolo, 03-handoff-human, 04-boas-vindas-lgpd, 04-consulta-protocolo, 05-agendamento, 06-2-via-protocolo, 07-pesquisa-evolucao, 08-audit-verify-diario, 09-backup-status, 10-faq-bot, 11-monitor-cartorio (14 nodes), 12-chatbot-llm-end-to-end, 22-mcp-server, 23-cron-stale-detector
- `infra/openclaw/` — persona CartorioBot (IDENTITY/SOUL/USER/TOOLS) + skill `cartorio-saudacoes.md` v1
- `infra/backup/cartorio-backup.sh` VPS-side (128 linhas, /usr/local/bin)
- Traefik + LetsEncrypt ativos

### VPS / Swarm runtime (verificado 18:50 BRT 2026-06-23)
- 23 containers Swarm rodando
- 5/6 domínios verdes: api, whatsapp, easypanel, agent, supbase, flow (chatwoot DNS missing)
- API `cartorio_api` rolling v0.4.5, healthcheck OK
- N8N `cartorio_n8n` 16 workflows ativos
- Chatwoot UP mas em restart loop (B1 — ADR-015)
- Evolution API 2.3.7 UP, número NÃO conectado (decisão consciente)
- OpenClaw Gateway Tailscale UP, sem LLM key
- Supabase UP (P0 incident resolvido 14:48 BRT — ADR `ADR-013-supabase-password-mismatch.md`)
- Redis UP, redis_bus.py funcional
- DB `cartorio`: 5 tabelas backend + 90 N8N core (isolamento ADR-010)

### ADRs (16 total)
010 (DB isolation), 011 (backup), 012 (API MCP), 013 (mount watchdog), 015 (Chatwoot loop), 016 (OpenClaw overflow) + 10 outros.

### Docs
- CHANGELOG v0.5.0
- ENV_PRODUCTION.md (13 seções)
- RUNBOOK_VPS.md
- PENDENCIAS_SUI_2026-06-23.md (8 itens UI)
- BENCHMARK_CARTORIO_2026-06-23.md
- PROSPECCAO_MERCADO.md + leads/cartorios-br-top30.md
- 12 roteiros LGPD-safe aprovados CEO (5 WhatsApp + 3 email + 3 LinkedIn + README)
- LGPD/RIPD + consent + privacy-policy
- superpowers/specs: sprint-0-diagnostico, sprint-2-design
- superpowers/plans: cartorio-sprint-2 (12k), sprint-2-plan (45k, 11 tasks TDD)

---

## 2. O que o briefing PEDIU e que NÃO existe no repo (gap real)

### Crítico: NÃO existe no repo
- **Nenhum arquivo `SUPER_ARQUIVO_CARTORIO_2NOTAS.md`** (busca exaustiva: 0 matches). O briefing referenciou 73k chars / 2.261 linhas que nunca foram commitadas. O que existe é `docs/SUPER_PLANO_v0.6.0.md` (12k) e `docs/SUPER_PLAN.md` (13k).
- **Nenhuma skill/plugin ZCode ↔ MiniMax** instalada. Comunicação documentada em `docs/COMMUNICATION_ARCHITECTURE.md` mas sem código.
- **Nenhum bot Telegram** implementado.
- **Nenhum `alembic/` ou pasta de migrations**.
- **Nenhum `.github/workflows/`** (sem CI/CD).
- **Nenhum `n8n-nodes-chatwoot` em uso** (instalado, não usado).
- **Nenhum `n8n-nodes-pdfkit` em uso**.
- **Nenhum `n8n-nodes-mcp` em uso**.

### Workflows N8N com problema
- **#22 MCP Server Tools**: `"active": false` no JSON. Não vai disparar.
- **#23 Cron Stale Detector 5min**: `"active": false` no JSON. Código deployado, mas inativo no N8N.
- **#07 Pesquisa Satisfação**: sem credencial Evolution no N8N (SUI #2).

### Pendências SUI — só Gustavo fecha via UI (~80 min)
1. DNS `chatwoot.2notasudi.com.br` — Easypanel UI (10min)
2. Credencial Evolution API no N8N (5min)
3. Agent Bot Chatwoot "Cartório Assistant" — UI 5 cliques (30min)
4. Regenerar Easypanel API key (2min)
5. OpenClaw LLM key (2min, depende L1)
6. Decisão DNS typo `supbase` → `supabase` (15min)

### Bugs P0 abertos (ADRs prontos, fix aplicável)
- **B1 Chatwoot restart loop** — ADR-015 RCA (OOM), aplicar `docker service update --limit-memory 1G` (5min, SUI SSH)
- **B2 OpenClaw context overflow** — ADR-016, threshold 50 msgs + TTL 24h + `curl /compact` (5min, SUI OpenClaw UI)

### LGPD / Compliance (não bloqueia dev, bloqueia prod real)
- L1 DPA OpenCode-Go/MiniMax (2-4 semanas jurídica)
- L2 Confirmar modelo LLM definitivo (briefing `deepseek-v4-flash`, repo `deepseek-v4-pro/flash`)
- L3 Encryption at-rest Postgres (LGPD art. 46, ~2h dev)
- L4 Provisionar OpenClaw LLM key (depende L1)
- E2.T1-T9 (RIPD, DPO, política privacidade, direito esquecimento endpoint, retenção 5y, logs art. 37, pen-test, WAF Cloudflare)

### Débitos backend pré-merge (Sprint 1)
- LGPDBlockedResponse copy jurídica defensável
- Coluna `cliente.motivo_encerramento` ENUM + migration Alembic
- `RequestContextMiddleware` (IP/UA/canal no audit)
- Cross-review `cartorio-lgpd` (gate 24h)
- `.env` real com CARTORIO_API_KEY (já tem em .env.example)
- Endpoint `GET /emolumento/calcular` polish + OpenAPI
- PII scrubbing regex-only latência < 5ms pré-LLM
- Teste E2E webhook Evolution → resposta WhatsApp com PII zero

### Hardening / Segurança
- LiteLLM removido mas tem dead references em docs
- Credenciais expostas no chat que precisam rotação: OpenCode-Go sk-, N8N MCP HTTP JWT, N8N public API JWT, OpenClaw Gateway Token/Password, EasyPanel API key (marcada MORTA), Redis default, Supabase DB

### Backlog E2-E5 (semanas 7-12+)
- E2 Compliance 9 tasks
- E3 Multi-canal (Telegram, web, e-mail, LiteLLM HA, LLM local Llama 3.1 8B)
- E4 Premium (gov.br/ICP-Brasil, PDF carimbo, HITL isenção, relatório auditoria, SLA dashboards)
- E5 Pós-12 sem (CARTIS MG, mobile RN, white-label, BI, JEF)

---

## 3. O que ZCode/Mavis PODE fazer agora (sem credenciais)

ZCode **não tem** e **não vai fingir ter**:
- ❌ Acesso SSH ou SSH-Tailscale à VPS 100.99.172.84
- ❌ API key do Easypanel (187.77.236.77:3000)
- ❌ API key do Hostinger
- ❌ API keys dos JWTs (N8N, MCP) — tem eles documentados no repo mas NUNCA vai usar sem autorização explícita
- ❌ Acesso ao painel Chatwoot
- ❌ Acesso ao painel Evolution API
- ❌ Acesso ao painel OpenClaw
- ❌ Acesso ao painel Supabase

ZCode **tem** e **pode usar agora**:
- ✅ Read/Write no repo local `/Users/gustavoalmeida/projetos/Cartorio`
- ✅ Git na branch `master` (já autorizado pelo histórico de 18 commits)
- ✅ `Bash` pra rodar comandos locais (pytest, ruff, git, alembic se vier a existir)
- ✅ Tailscale CLI se instalada localmente (a verificar)
- ✅ Skills ZCode instaladas localmente (brainstorming, writing-plans, etc.)

---

## 4. Rota recomendada (sem inflar backlog)

### Caminho A — SUI-first (~80min Gustavo + ~10min ZCode)
1. Gustavo fecha os 6 SUI listados em §2 (80min UI)
2. ZCode aplica B1+B2 via SSH **quando Gustavo autorizar e der acesso** (10min)
3. ZCode regenera `.env.example` com CARTORIO_API_KEY novo, Gustavo cola no `.env` real do Easypanel
4. Gustavo roda smoke test E2E
5. Commit `v0.5.1` em `master`
6. Sprint 3 começa com cred rotation, encryption at-rest, CI/CD

### Caminho B — Code-first (ZCode faz o que dá, Gustavo faz SUI em paralelo)
1. ZCode commita débitos pré-merge que não precisam de VPS (LGPDBlockedResponse copy, RequestContextMiddleware, PII regex perf)
2. ZCode reativa workflows #22 e #23 (corrige `"active": true` no JSON)
3. ZCode ativa MCP Client node em workflow #12 (não precisa de credencial, só de node instalado)
4. Gustavo faz SUI em paralelo
5. Sprint 3 idem

### Caminho C — Checkpoint-resume (sem fazer nada agora)
1. ZCode só grava este doc + cria SPEC de Sprint 3 enxuto (~15-20 tasks reais, não 100)
2. Próxima sessão começa do `master` v0.5.0 sem perda de contexto
3. Gustavo dispara SUI quando tiver tempo

---

## 5. Anti-itens confirmados (do Sprint 0 spec §5, repetindo pra cimentar)

- ❌ NÃO criar 7 subagent squads do zero (já existem 3: cartorio-dev, cartorio-n8n, cartorio-lgpd, todos com problema de registro)
- ❌ NÃO inventar 700/100/30 tasks
- ❌ NÃO reescrever API do zero
- ❌ NÃO reescrever N8N workflows do zero
- ❌ NÃO reescrever OpenClaw persona
- ❌ NÃO criar 7 subdomínios novos
- ❌ NÃO reconsolidar DB (já feito, ADR-010)
- ❌ NÃO fingir VPS/Easypanel access
- ❌ NÃO ecoar credenciais em chat/logs
- ❌ NÃO bloquear Gustavo em loops de briefing
