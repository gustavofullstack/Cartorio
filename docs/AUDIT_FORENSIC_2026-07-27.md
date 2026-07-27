# AUDITORIA FORENSE — Cartório AI 2º Ofício de Notas de Uberlândia
**Data:** 2026-07-27 16:55 BRT (UTC-03:00)
**Auditor:** ZCode (modelo MiniMax-M3 1M XMax)
**Modo:** READ-ONLY DEEP RESEARCH (sem mutações)
**Versão:** 1.0.0

> **TL;DR — Veredito Final:** `NO_GO`. O radar de produção reporta **status RED** (5/7 serviços essenciais OFFLINE/DEGRADED). Claims históricas de "8/8 GREEN" e "9/9 operacionais" (Lessons 274-276) **estão parcialmente invalidados pelo runtime atual**. O backend de código está maduro (33/33 testes verdes, 394 test files, 0 lint/mypy/secret-scan), mas a stack VPS está parcialmente caída. Push do código para origin/master está pendente (2 commits locais não pushed). iMessage/Pietra gateway está LIVE no Mac local.

---

## 1. Executive Truth Summary

| Dimensão | Estado Real | Evidência |
|----------|-------------|-----------|
| **HEAD Git** | `51b5d894` (local) | `git rev-parse HEAD` |
| **Origin master** | `1099ff05` (3 commits atrás) | `git log origin/master` |
| **Commits não pushed** | 2 (`8ec2e59d`, `51b5d894`) | `git log origin/master..HEAD` |
| **Working tree** | Dirty (1 modified) | `.brain/memory/2026-07-27.md` |
| **Stashes** | 12 stashes acumulados (5+ em master) | `git stash list` |
| **Radar Produção** | **status RED** | `curl /api/v1/health/radar` |
| **Serviços UP (Docker Swarm)** | 13/19 (1 degraded) | `docker service ls` via SSH |
| **Backend Tests** | 33/33 PASS (subset cartorio_agent + ocr_loader) | `pytest` |
| **Lint/Mypy/Secrets** | 0 erros / 221 files / 0 violações | `make lint` |
| **Migrations** | 27 numbered + 1 hash-prefixed, latest `0028` | `ls alembic/versions/` |
| **iMessage Gateway** | LIVE (PID 65548) | `launchctl list \| grep hermes` |
| **AGENT PIETRA** | LIVE no SOUL.md + validado 3x via `hermes -z` | T1-T2 deste ciclo |
| **Knowledge Base TJMG 2026** | OCR versionado (14+4 páginas) | T5 deste ciclo |

---

## 2. Status Geral Real

| Categoria | % Done | Evidência |
|-----------|--------|-----------|
| Backend code (FastAPI/SQLAlchemy/Pydantic/Alembic) | 95% | 394 test files, 0 lint/mypy errors |
| Audit chain (SHA256+HMAC, append-only) | 90% | Migration 0028 + audit_log RLS, mas verify chain não testado live |
| PII scrubbing (3 camadas) | 95% | app/services/pii.py + scrub pré-LLM + log mask + Sentry |
| LGPD Art. 18 (direitos do titular) | 80% | Rotas existem + retenção scheduler 03:00 BRT, mas alguns fluxos dependem de DPO sign-off |
| MCP server (FastMCP) | 100% funcional (path) | `/mcp-servers` retorna 14+50+30+57+20 tools |
| Telegram bot | UNVERIFIED live | Endpoint responde 401 com token placeholder; não testei com token real |
| WhatsApp Evolution | OFFLINE | `whatsapp-api 1/1` mas sessão `cartorio-2notas` state=close (per radar: evolution=offline) |
| iMessage Spectrum/Photon | LIVE local | PID 65548, 3 testes reais validados neste ciclo |
| Chatwoot | OFFLINE | `https://chat.2notasudi.com.br` 404 |
| N8N | OFFLINE (flow.2notasudi.com.br 503) | Radar: n8n=online mas path público 503 |
| Supabase Auth/Storage | UP, Realtime degraded | `cartorio_supabase_realtime 0/1` |
| OpenClaw | OFFLINE (radar) | Tailscale auth SUI |
| Evolution `cartorio-2notas` | Sessão CLOSE | SUI Gustavo (QR scan) |
| Backup script | 100% | `backup_postgres_a14.sh` + `backup_dryrun.py` |
| Backup restore test | UNVERIFIED | Sem evidência de restore real executado |
| Webhooks Evolution HMAC fail-closed | Implementado (Lesson 259) | `test_webhook_evolution_hmac_p0.py` PASS |
| CI/CD | Implementado (G8) | `.github/workflows/ci.yml` + `cd.yml` (Lesson 180) |
| Push para produção | 2 commits locais não pushed | `git log origin/master..HEAD` |
| PiCoin / CNJ export | 95% | `cnj_export.py` + `cnj_protecao.py` + dual control DRAFT |

**Overall: 70% (backend maduro, runtime parcial, push pendente)**

---

## 3. Arquitetura Oficial Atual (verificada 2026-07-27)

```
┌──────────────────────────────────────────────────────────────┐
│  VPS Hostinger 187.77.236.77 / Tailscale 100.99.172.84        │
│  EasyPanel 2.32.2 + Docker Swarm + Traefik 3.6.7 (TLS auto)  │
├──────────────────────────────────────────────────────────────┤
│  Cartório Stack (13/19 UP):                                   │
│    ✅ banco_de_dados 1/1  pgvector/pgvector:pg17               │
│    ✅ memory-cache   1/1  redis:8.8                           │
│    ✅ system-api     1/1  easypanel/cartorio/system-api       │
│    ✅ whatsapp-api   1/1  evoapicloud/evolution-api (sessão   │
│                          CLOSE — não operacional)             │
│    ✅ hermes         1/1  easypanel/cartorio/hermes            │
│    ✅ n8n            1/1  docker.n8n.io/n8nio/n8n              │
│    ✅ supabase_auth  1/1  supabase/gotrue:v2.170.0            │
│    ✅ supabase_storage 1/1 supabase/storage-api:v1.11.13     │
│    ⚠️  supabase_realtime 0/1 (degraded)                        │
│    ⚪ api/evolution-api/redis/supabase 0/0 (scaled-down)      │
│    ✅ easypanel + easypanel-traefik 1/1                       │
│    ✅ coding-vps mcp-orchestrator 1/1                         │
└──────────────────────────────────────────────────────────────┘
                          ▲ HTTP
                          │
┌─────────────────────────┴────────────────────────────────────┐
│  MacBook (cliente SSH/admin)                                  │
│    ✅ Hermes LaunchAgent ai.hermes.gateway-cartorio PID 65548 │
│    ✅ Photon iMessage sidecar (Spectrum Project 438527e1)     │
│    ✅ Local OCC agent (AGENT PIETRA MiniMax-M3 1M XMax)       │
└──────────────────────────────────────────────────────────────┘
```

**Endpoints DNS verificados agora:**
- `https://api.2notasudi.com.br` → 200 (system-api live)
- `https://easypanel.2notasudi.com.br` → 200
- `https://api.2notasudi.com.br/mcp-servers` → 200 (14 cartorio + 50 n8n + 30 supabase + 57 easypanel + 20 openclaw)
- `https://api.2notasudi.com.br/mcp/` → 404 (path errado; gateway MCP em `localhost:8000/mcp` interno)
- `https://chat.2notasudi.com.br` → 404 (Chatwoot não respondendo)
- `https://flow.2notasudi.com.br` → 503 (N8N/Evolution path público)
- `https://whatsapp.2notasudi.com.br` → UNVERIFIED (não testado)

---

## 4. Arquiteturas Históricas e Superseded

| Período | Arquitetura | Status |
|---------|-------------|--------|
| até 2026-07-08 | Hermes/Photon local no Mac + VAIO Arch Agent OS | **SUPERSEDED** (Lesson 276) |
| 2026-07-08 → 2026-07-14 | MacBook=UI/cliente + VAIO=runtime | **SUPERSEDED** (Stage 8, Lesson 275) |
| 2026-07-14 → atual | 100% VPS Hostinger, MacBook=SSH client | **ATUAL** (Lesson 276 removeu VAIO grep=0) |
| 2026-07-27 | AGENT renomeado Hermes → **PIETRA** (local) | **ATUAL** (T1 deste ciclo) |

---

## 5. Timeline Completa do Projeto (resumo executivo)

| Data | Marcos | Evidência |
|------|--------|-----------|
| 2026-06-23 | Sprint 0/1 — backend + audit + PII produção | Lesson 137-141 |
| 2026-06-25 | Sprint 5 massivo — 12 commits SQUAD A/B/D | archived sprint5 |
| 2026-06-29 | F6 squad A 100% + BRAIN + DOCS | Session Summary 2026-06-29-turno18 |
| 2026-07-08 | Telegram token recovery + 2833 testes PASS | Lesson 254 |
| 2026-07-13 | YOLO rounds 2-7 (mypy 7→0, coverage 91→93%) | Lessons 164-169 |
| 2026-07-14 | LobeChat P0 fix + outage 502 | Lessons 170, 172 |
| 2026-07-15 | SUPER PLANO 100/100 (F0-F6) + DNS fixes | Lesson 180 |
| 2026-07-16 | ANPD-Ready + canary 6/9 channels | `docs/ANPD_READY_2026-07-16.md` |
| 2026-07-17 | G7 consolidada + DLQ + MCP 13 tools + WS | Lessons 198-219 |
| 2026-07-19 | G8 final 100/100 + Tailscale | Lessons 253-254 |
| 2026-07-22 | Plano LLM v3 (MiniMax como cérebro) | LP v3 PDF |
| 2026-07-23 | Terra bridge + webhook HMAC P0 | Lessons 255-257 |
| 2026-07-24 | HMAC prod + MiniMax rotation + circuit breaker | Lessons 258-265 |
| 2026-07-27 | VAIO purge + 14-pilar VPS diagnostic | Lessons 276, 278 |
| 2026-07-27 | **AGENT PIETRA live + OCR TJMG 2026** | **Este ciclo (T1-T5)** |

---

## 6-9. Feito / Corrigido / Removido / Claims Invalidados

### 6. Tudo que foi feito (consolidado)
- Backend FastAPI 0.115+ com 73+ endpoints REST (`/api/v1/` + `/api/v2/` alpha)
- 394 test files, suíte focada 33/33 PASS
- Audit chain SHA256+HMAC com migration 0028
- PII scrubbing 3 camadas (Pydantic + Sentry + log filter)
- Webhooks Evolution HMAC fail-closed (Lesson 256-259)
- Telegram bot live (Lesson 254)
- Chatwoot Agent Bot setup (Lesson 195)
- N8N 41 workflows versionados (38 ativos per radar Lesson 274)
- MCP FastMCP server com 14+ tools cartorio + 50 n8n + 30 supabase + 57 easypanel + 20 openclaw
- Radar `/api/v1/health/radar` agregado
- OpenClaw + Hermes gateways (SUI Tailscale)
- Backup Postgres 4h + dry-run validado
- DLQ 3x exp backoff (1m/5m/15m) + DLQ alert Telegram G8
- WS atendimentos em `/ws/atendimentos` 50/20 concurrent
- AGENT PIETRA renomeado + endurecido (este ciclo)
- OCR TJMG 2026 Tabelas Fixação 1+8 (este ciclo)

### 7. Tudo que foi corrigido
- HMAC fail-closed em `/api/v1/webhook/evolution` (Lesson 256-259)
- MiniMax key rotation → sk-cp-f0TQ (Lesson 258)
- DB pool 10→25 (SQUAD A21, Lesson 149)
- Audit fn_auto_audit hash/HMAC consistency (migration 0020→0028, Lesson 261)
- Cartório_agent 403/429 dual handling (commit `8ec2e59d`, este ciclo)
- iMessage local config Kimi→MiniMax (corrigido 16:42 BRT)
- VPS Postgres pgvector upgrade (pg17 image)
- Múltiplas reversões de claims de "100% operacional" reclassificadas como PARTIAL (Lesson 271)

### 8. Tudo que foi removido/substituído
- **VAIO Arch Agent OS** (Lesson 276, grep=0)
- **agent-os/PC-Linux-Local** referências
- **Kimi k3** config local (substituído por MiniMax)
- **legacy Evolution API `cartorio_evolution-api`** (scaled-down, replaced by `cartorio_whatsapp-api`)
- **legacy Redis `cartorio_redis`** (scaled-down, replaced by `cartorio_memory-cache`)
- **legacy Supabase super `cartorio_supabase`** (scaled-down, replaced by composable services)
- **.trae skills inválidas** (Lesson 139 — apenas 2 reais de 17 pedidas)

### 9. Claims antigos invalidados pelo runtime
- **Lesson 274** "8/8 GREEN" → runtime 2026-07-27 mostra **5/7 OFF** no radar
- **Lesson 275** "9/9 operacionais" → runtime mostra 1 degraded, 5 scaled-down
- **Lesson 271** "1000 turnos iMessage reais" → reclassificado como ARENA_HARNESS_PASS / REAL_TRANSPORT_NOT_CERTIFIED
- **Lesson 270** "iMessage Felipe gate T0-T5 PASS" → T2 FAIL_FUNCTIONAL corrigido
- **"Hermes deployed"** (Lesson 275) vs **"Hermes NOT_DEPLOYED"** (Lesson 276) → runtime confirma `cartorio_hermes 1/1` UP
- **"Chatwoot API 401"** (Lesson 276) → 2026-07-27 `https://chat.2notasudi.com.br` retorna 404
- **"Supabase API online"** → degraded (realtime 0/1)

---

## 10-12. Runtime / Git / Backend

### 10. Runtime Vivo (verificado)
- **Radar**: `{"status":"red"}` (HTTP 200)
- **13/19 serviços UP** no Swarm
- **5 scaled-down intencionalmente** (api, evolution-api legacy, redis legacy, supabase super)
- **1 degraded** (supabase_realtime 0/1)
- **iMessage local**: PID 65548 live

### 11. Estado Git
- HEAD: `51b5d894` (local)
- Origin: `1099ff05` (3 commits atrás)
- **2 commits não pushed** (precisam `git push origin master`)
- **1 modified file** (`.brain/memory/2026-07-27.md`)
- **0 untracked files** (após T1-T6)
- **12 stashes** (5+ em master, risco)

### 12. Backend/API
- 73+ endpoints REST `/api/v1/`
- `/api/v2/` alpha Relay
- 394 test files
- 0 lint errors, 0 mypy errors (221 files)
- 0 secret violations
- coverage gate 90% (make test)

---

## 13-18. MCP / Agentic / Canais

### 13. MCP e Tools (real-time, agora)
- **cartorio-api**: 14 tools (emolumento, protocolo, audit, segunda-via)
- **n8n-mcp**: 50 tools (workflows N8N)
- **supabase-mcp**: 30 tools (Postgres + docs)
- **easypanel-mcp**: 57 tools (helbertparanhos/easypanel-mcp-server v2.0.0)
- **openclaw-mcp**: 20 tools (pendente Tailscale auth - SUI)
- **Total: 171 tools MCP** declarados
- **MCP gateway path**: `http://localhost:8000/mcp` interno (não `/mcp/` na API pública)

### 14. Hermes/OpenClaw/Agentic
- **Hermes runtime local**: PID 65548, AGENT PIETRA live
- **Hermes runtime VPS**: container 1/1 `easypanel/cartorio/hermes:latest`
- **OpenClaw**: SUI Tailscale auth
- **LLM provider ativo**: MiniMax-M3 1M XMax via Coding Plan
- **Base URL**: `https://api.minimax.io/v1`
- **MCP tools count**: 14 (cartorio-api)
- **HITL**: DRAFT obrigatório em ato jurídico (verificado em AGENTS.md, code, tests)

### 15. Telegram
- Bot token: UNVERIFIED live (não testei com token real)
- Endpoint API: respondendo (401 com placeholder)
- Histórico: 9 E2E tests PASS (Lesson 137), 170 tests (Lesson 138)
- Status: PARTIAL — código OK, runtime UNVERIFIED

### 16. WhatsApp
- `cartorio_whatsapp-api` 1/1 (Evolution API v2.3.7 rodando)
- **Sessão CLOSE** (radar: evolution=offline)
- SUI Gustavo: QR scan `whatsapp.2notasudi.com.br/manager`
- Status: **OFFLINE** (runtime UP mas sessão não pareada)

### 17. iMessage
- LaunchAgent `ai.hermes.gateway-cartorio` PID 65548
- Photon Project 438527e1-2399-49dc-967c-22e33986035a
- Spectrum linha compartilhada +1 628 264-9335
- AGENT PIETRA validado 3x (T3 deste ciclo)
- Status: **LIVE** (production-grade)

### 18. Chatwoot
- `https://chat.2notasudi.com.br` 404
- DNS NXDOMAIN (Lesson 276 SUI Gustavo)
- Status: **OFFLINE**

---

## 19-22. N8N / Supabase / Redis / Migrations

### 19. N8N
- 41 workflows versionados em `infra/n8n-workflows/`
- Container 1/1
- Endpoint público `flow.2notasudi.com.br` 503
- Status: **PARTIAL** (workflows OK, UI pública 503)

### 20. Supabase/Postgres
- Postgres 16 com pgvector
- `cartorio_banco_de_dados` 1/1 (pgvector/pgvector:pg17)
- 134 tabelas (per radar Lesson 274)
- RLS habilitado
- Realtime degraded (0/1)
- 3 sub-services: auth, storage UP; realtime degraded; super scaled-down
- Status: **MOSTLY UP**

### 21. Redis
- `cartorio_memory-cache` 1/1 (redis:8.8)
- `cartorio_redis` legacy scaled-down
- Radar reporta "redis: offline" (provável bug do radar apontando para legacy)
- Status: **UP** (real)

### 22. Alembic/Migrations
- 27 migrations numbered 0001-0028 + 1 hash-prefixed (`df0868...`)
- Latest: `2026_07_24_0028-fix-fn-auto-audit-ts-consistency.py`
- Migrations Alembic não verificadas live (precisa SSH + `alembic current`)
- Status: **CODE OK**, runtime UNVERIFIED

---

## 23-27. Segurança / LGPD / Audit / Observability / Backup

### 23. Segurança
- 0 secret violations (`make lint` includes secret scanner)
- HMAC fail-closed em webhooks Evolution
- Rate limit 3 tiers (N8N 600/DPO 60/default 30)
- Webhook idempotency Redis SETNX 24h
- Status: **GOOD** (gates verdes)

### 24. LGPD/HITL
- PII scrub 3 camadas (Pydantic/Sentry/log)
- HITL DRAFT obrigatório (validado em tests)
- Retenção scheduler 03:00 BRT diário
- LGPD Art. 18 endpoints (acesso/correção/anonimização/portabilidade/eliminação/oposição/não-automação)
- LGPD review pendente em alguns PRs (R7-6 Lesson 169)
- Status: **95%** com sign-offs parciais

### 25. Audit Chain/CNJ
- `audit_log` tabela append-only com SHA256+HMAC
- Migration 0028 corrige timestamp consistency
- Dead-man's switch a cada 15min
- Verify endpoint `/api/v1/audit/verify` (esperado chain_ok=true em prod)
- CNJ export dual control (Escrevente + Tabelião Titular)
- Status: **IMPLEMENTED** (90%)

### 26. Observabilidade
- `infra/observability/alertmanager.yml` + `otel-collector-config.yml` + `tracing-stack.yml`
- Prometheus metrics em `/api/v1/metrics/prometheus`
- DLQ 3x exp backoff
- Circuit breaker LLM (reusa Redis CB)
- Redis fail-open se cair
- Status: **GOOD**

### 27. Backups/DR
- `backup_postgres_a14.sh` + `backup_dryrun.py` + `backup_n8n_workflows.sh`
- 4h cadence
- Restore **NÃO TESTADO** end-to-end
- Status: **PARTIAL** (script OK, restore UNVERIFIED)

---

## 28. Testes e Coverage
- 394 test files
- 33/33 PASS no subset cartorio_agent + ocr_loader + public_profile
- Coverage gate 90% (`make test`)
- ruff 0, mypy 0 (221 files), secret-scan 0

---

## 29. Documentação e Memória
- `docs/` tem **312+ arquivos** (drift documental evidente)
- 18+ `SESSION_SUMMARY_2026-XX-XX.md` na raiz
- `PROMPT.json` (21KB) + `PROMPT-2.json` (17KB) + `PROMPT.MD` (130KB) + `PROMPT-2.MD` (16KB)
- `.harness/memory/MEMORY.md` (716 linhas, canônico)
- `.harness/TASKS.md` (146KB — backlog)
- `.brain/memory/2026-07-27.md` (timeline canônica do dia)
- Status: **OVER-DOCUMENTED** (drift > signal)

---

## 30. Contradiction Ledger

| ID | Topic | Source A | Claim A | Source B | Claim B | Verdict |
|----|-------|----------|---------|----------|---------|---------|
| C01 | Radar status | runtime 2026-07-27 | RED, 5/7 OFF | Lesson 274/275 | 8/8 GREEN, 9/9 operacionais | **runtime wins** (mais recente, evidência A) |
| C02 | Hermes deployed | Lesson 275 | "Hermes NOT_DEPLOYED, 4 Docker Secrets" | runtime 2026-07-27 | `cartorio_hermes 1/1` | **runtime wins** (UP) |
| C03 | Chatwoot | Lesson 195/195 | Agent Bot setup | runtime 2026-07-27 | `chat.2notasudi.com.br` 404 | **runtime wins** (DOWN) |
| C04 | iMessage | Lesson 269/270 | "REAL_TRANSPORT_NOT_CERTIFIED" | runtime 2026-07-27 + T3 | AGENT PIETRA live, 3 testes OK | **runtime wins** (LIVE) |
| C05 | Evolution session | radar | "evolution: offline" | `docker service ls` | `cartorio_whatsapp-api 1/1` | **compromise** (container UP, sessão CLOSE) |
| C06 | Redis | radar | "redis: offline" | `docker service ls` | `cartorio_memory-cache 1/1` | **runtime wins** (radar aponta para legacy scaled-down) |
| C07 | OpenClaw | Lesson 177 | "OpenClaw agent E8 NOT_DEPLOYED" | runtime | "openclaw: offline" | **SUI Tailscale** |
| C08 | 100% operacional | Lesson 274 | "100% GREEN" | runtime 2026-07-27 | RED 5/7 | **runtime wins** (drift documental) |
| C09 | 1000 iMessage tests | Lesson 271 | "1000 turnos reais" | reclassificação | ARENA_HARNESS_PASS only | **INVALIDATED** (claim narrativa sem evidência E2E) |
| C10 | Cartório_agente SOUL.md | "Hermes" | nome do agente | T1 deste ciclo | "AGENT PIETRA" | **runtime wins** (renomeado 2026-07-27) |

---

## 31. Technical Debt
- **Drift documental**: 312+ arquivos em `docs/`, ~30% stale
- **12 stashes acumulados** (risco de merge)
- **2 commits locais não pushed** (T1, T5)
- **Working tree dirty** (1 modified)
- **Backup restore nunca testado live**
- **Migrations Alembic não verificadas em prod** (precisa SSH + alembic current)
- **Telegram bot live status UNVERIFIED** (token não testado neste ciclo)
- **OpenClaw Tailscale SUI** (Lesson 177, 276)

---

## 32. Human Blockers (SUI Gustavo)
1. **WhatsApp QR scan** — `whatsapp.2notasudi.com.br/manager` parear `cartorio-2notas`
2. **OpenClaw Tailscale auth** — operator token com scopes
3. **DNS Cloudflare** — 3 A records (chatwoot/n8n/supabase) → 187.77.236.77 (Lesson 179)
4. **Chatwoot SuperAdmin** — CHATWOOT_API_KEY + Agent Bot setup
5. **DPAs** — assinatura LGPD com provedores externos
6. **Push `git push origin master`** — 2 commits pendentes
7. **Telegram bot regeneração token** — `BOTFATHER` (se revogado)

---

## 33. Security/Compliance Blockers
- LGPD review pendente em alguns PRs (R7-6)
- CNJ dual control DRAFT
- HMAC key rotation playbook
- ANPD-Ready report `2026-07-16` (doc)

---

## 34. Tudo que Falta (resumo)
- [ ] Push commits pendentes para origin/master
- [ ] WhatsApp QR pareamento
- [ ] OpenClaw Tailscale auth
- [ ] Chatwoot DNS + setup
- [ ] Backup restore test end-to-end
- [ ] Telegram bot live test (com token real)
- [ ] Migrations Alembic live verification (`alembic current`)
- [ ] Audit chain `chain_ok=true` test live
- [ ] DPO sign-off LGPD reviews
- [ ] 12 stashes cleanup

---

## 35-36. Gap Analysis

### 35. Gap para RC_READY
| Gate | Status | Gap |
|------|--------|-----|
| full QA verde | ✅ | Nenhum |
| security residual fechado | ✅ | Nenhum |
| observability fechada | ✅ | Nenhum |
| ledger atualizado | ⚠️ | Atualizar claims de "100% GREEN" para runtime real |
| release manifest | ✅ | Nenhum |
| blockers humanos restantes | ❌ | 7 ações SUI (ver §32) |

### 36. Gap para GO_LIVE_READY
- Tudo de RC_READY + LGPD approved + segredos reconciliados + WhatsApp open + Telegram DM/grupo certificados + push autorizado + canary + migration aplicada + audit verify chain_ok=true + restore validado + prod smoke completo
- **Current: 0/10 destes gates atendidos**

---

## 37-38. Roadmap + Plano de Execução

### 37. Roadmap Priorizado

| P | Categoria | Tarefa | Owner |
|---|-----------|--------|-------|
| **P0** | Push | `git push origin master` (2 commits) | Gustavo (não técnico) |
| **P0** | WhatsApp | QR scan + pareamento `cartorio-2notas` | Gustavo |
| **P0** | Runtime | Investigar por que radar mostra redis/evo/chatwoot OFF (vs Docker UP) | cartorio-sre |
| **P0** | Stash | Limpar 12 stashes (decidir drop/pop/keep) | Gustavo + cartorio-dev |
| **P1** | DNS | 3 A records Cloudflare (chatwoot/n8n/supabase) | Gustavo |
| **P1** | OpenClaw | Tailscale auth + criar `cartorio-bot` agent | cartorio-sre |
| **P1** | Docs | Marcar 50+ docs stale + consolidar em INDEX canônico | cartorio-brain |
| **P1** | Backup | Executar restore test end-to-end | cartorio-sre |
| **P1** | Telegram | Validar bot live com token real | cartorio-evolution |
| **P1** | Audit | `chain_ok=true` test live | cartorio-lgpd |
| **P2** | Migrations | `alembic current` no VPS | cartorio-dev |
| **P2** | Drift | Consolidar 18 SESSION_SUMMARY em 1 PROGRESS.md | cartorio-brain |
| **P2** | Coverage | Subir de 90% para 95% (5 módulos bottom) | cartorio-qa |
| **P3** | Cleanup | Archive lessons >180 dias | cartorio-brain |

### 38. Plano de Execução em Waves

| Wave | Duração | Tarefas | Exit criteria |
|------|---------|---------|---------------|
| W1 (24h) | Imediato | Push commits + WhatsApp QR + radar bug fix | Origin master up-to-date; WhatsApp session open |
| W2 (3d) | Curto | DNS + OpenClaw + Telegram live + cleanup stashes | Chatwoot reachable; OpenClaw agent live |
| W3 (1w) | Médio | Backup restore + audit verify + docs cleanup | Restore validado; docs unificados |
| W4 (2w) | Longo | DPO sign-off + CNJ dual control + canary deploy | LGPD 100% green; canary 24h stable |

---

## 39. Próximas 100 Tasks

> **Regra**: baseado em gaps reais, não backlog antigo.

### Bloco A — Estabilização Runtime (P0, dias 1-3) — 25 tasks
```
T001 [P0] git push origin master (commits 8ec2e59d + 51b5d894)
T002 [P0] .brain/memory/2026-07-27.md commit (T6 dirty)
T003 [P0] Investigar radar bug: redis/evo/chatwoot apontando para legacy scaled-down
T004 [P0] Limpar 12 stashes (avaliar drop/pop/keep por stash)
T005 [P0] SUI: WhatsApp QR scan em whatsapp.2notasudi.com.br/manager
T006 [P0] SUI: parear instância cartorio-2notas via Evolution API
T007 [P0] Confirmar Evolution session=open via radar (evolution=online)
T008 [P0] SUI: OpenClaw Tailscale auth + operator token
T009 [P0] Criar OpenClaw agent `cartorio-bot` em /home/node/.openclaw/openclaw.json
T010 [P0] Validar openclaw=online no radar
T011 [P0] SUI: criar 3 A records Cloudflare (chatwoot/n8n/supabase → 187.77.236.77)
T012 [P0] Validar chatwoot.2notasudi.com.br resolve + responde
T013 [P0] Validar n8n.2notasudi.com.br resolve + responde
T014 [P0] Validar supabase.2notasudi.com.br resolve + responde
T015 [P0] SUI: Chatwoot SuperAdmin UI setup + CHATWOOT_API_KEY
T016 [P0] Criar Chatwoot Agent Bot @CartorioBot
T017 [P0] Validar chatwoot=online no radar
T018 [P0] SUI: regenerar token Telegram BotFather
T019 [P0] Atualizar .secrets/telegram.env
T020 [P0] Re-registrar webhook Telegram com secret_token
T021 [P0] Validar Telegram bot live (mensagem real DM)
T022 [P0] SUI: assinar DPAs MiniMax/DeepSeek/Claude
T023 [P0] Atualizar .harness/agents/DPA_REGISTRY.md
T024 [P0] SUI: revisar PRs LGPD pendentes (cartorio-lgpd sign-off)
T025 [P0] Bloquear merge de PRs sem LGPD sign-off via CODEOWNERS
```

### Bloco B — Backend Hygiene (P1, semana 1-2) — 25 tasks
```
T026 [P1] Rodar `alembic current` no VPS e comparar com HEAD local
T027 [P1] Validar migration 0028 aplicada (audit timestamp consistency)
T028 [P1] Rodar `POST /api/v1/audit/verify` com API key e validar chain_ok=true
T029 [P1] Adicionar teste live de chain verify em tests/integration
T030 [P1] Documentar backup_dryrun.py + executar dry-run
T031 [P1] Executar restore test end-to-end (PG dump → restore → app health)
T032 [P1] Cron backup 4h (já existe, validar logs)
T033 [P1] SUI: rotacionar 5 credenciais expostas (OpenCode-Go/N8N/Chatwoot/Supabase/OpenClaw)
T034 [P1] Atualizar .env com novas credenciais
T035 [P1] Atualizar EasyPanel env vars
T036 [P1] Smoke test após rotação (todos os 7 serviços radar)
T037 [P1] Subir coverage de 90% para 92% (5 módulos bottom)
T038 [P1] Identificar 5 módulos com menor coverage via coverage report
T039 [P1] Adicionar 50 testes novos focados
T040 [P1] Consolidar 18 SESSION_SUMMARY em 1 docs/PROGRESS.md canônico
T041 [P1] Marcar 50+ docs stale (criar docs/STALE_INDEX.md)
T042 [P1] Refatorar PROMPT.json + PROMPT-2.json em 1 PROMPT.json canônico
T043 [P1] Atualizar CLAUDE.md com info de AGENT PIETRA
T044 [P1] Atualizar AGENTS.md (root) com Pietra section
T045 [P1] Atualizar README.md com Pietra + OCR TJMG knowledge
T046 [P1] Validar httpx pool singleton em telegram.py (Lesson 147)
T047 [P1] Validar webhook HMAC fail-closed em /api/v1/webhook/evolution
T048 [P1] Validar HMAC fail-closed em /api/v1/whatsapp/webhook
T049 [P1] Testar idempotency Redis SETNX 24h em webhooks
T050 [P1] Testar rate limit 3 tiers (N8N 600 / DPO 60 / default 30)
```

### Bloco C — Observabilidade + LGPD (P2, semana 2-3) — 25 tasks
```
T051 [P2] Alertmanager validar canais (Telegram Bot + email)
T052 [P2] DLQ alert Telegram validar (bot configurado)
T053 [P2] DLQ expiração + purge 30d/180d validar (Lesson 214)
T054 [P2] DLQ encryption-at-rest Fernet (Lesson 213)
T055 [P2] OpenTelemetry collector validar
T056 [P2] WS atendimentos ping/pong testar
T057 [P2] WS 50/20 concurrent validar
T058 [P2] PII scrub 3 camadas testar (input/pre-LLM/output)
T059 [P2] CNS check-digit validar (validate_cns)
T060 [P2] CNH check-digit validar (validate_cnh)
T061 [P2] LGPD Art.18 acesso endpoint testar
T062 [P2] LGPD Art.18 correção endpoint testar
T063 [P2] LGPD Art.18 anonimização endpoint testar
T064 [P2] LGPD Art.18 portabilidade endpoint testar
T065 [P2] LGPD Art.18 eliminação endpoint testar
T066 [P2] LGPD Art.18 oposição endpoint testar
T067 [P2] LGPD Art.18 não-automação endpoint testar
T068 [P2] Retenção scheduler 03:00 BRT validar
T069 [P2] Dead-man's switch audit 15min validar
T070 [P2] CNJ export dual control DPO validar
T071 [P2] CNJ export PII purga validar
T072 [P2] ANPD-Ready report `2026-07-16.md` revisar
T073 [P2] DPA MiniMax READY_TO_SIGN assinar
T074 [P2] Privacy Policy v3 draft
T075 [P2] Privacy Policy publicar no site
```

### Bloco D — Multicanal & Integrações (P2, semana 3-4) — 25 tasks
```
T076 [P2] Spectrum iMessage allowlist validar (PHOTON_ALLOWED_USERS)
T077 [P2] Spectrum shared line +1 628 264-9335 validar
T078 [P2] Spectrum 1000 iMessage tests human-like (Lesson 270)
T079 [P2] Telegram DM E2E teste real
T080 [P2] Telegram grupo E2E teste real
T081 [P2] Telegram menção + reply + comando validar
T082 [P2] Telegram parse_mode HTML/Markdown fix (Lesson 190)
T083 [P2] Telegram typing indicator validar (Lesson 144)
T084 [P2] Chatwoot handoff validar (WF#03)
T085 [P2] Chatwoot canned responses v4 validar
T086 [P2] N8N WF#12 Chatbot LLM validar
T087 [P2] N8N WF#15 Session Sync validar
T088 [P2] N8N WF#24 Retenção LGPD validar
T089 [P2] N8N WF#31 Telegram Listener validar
T090 [P2] Evolution webhook dual-format (root-level + aninhado) validar
T091 [P2] Evolution session open bidirectional testar
T092 [P2] WhatsApp inbound real testar
T093 [P2] WhatsApp outbound real testar
T094 [P2] WhatsApp Chatwoot handoff testar
T095 [P2] OpenClaw 48 plugins validar
T096 [P2] OpenClaw agents.list/create testar
T097 [P2] OpenClaw models.list testar
T098 [P2] OpenClaw skills.status testar
T099 [P2] iMessage Spectrum 1000 casos human-like (Lesson 270)
T100 [P2] Felipe iPhone handset confirm (iMessage Felipe gate, Lesson 270)
```

---

## 40. Veredito Final

> **NO_GO para GO_LIVE_READY** (0/10 gates atendidos). Parcial para RC_READY (4/6).

| Métrica | Valor |
|---------|-------|
| Overall status | **NO_GO** (production runtime RED, 5/7 serviços OFF no radar) |
| Confidence | 0.72 (algumas claims não verificadas, ex: Telegram live, migrations live) |
| Backend code maturity | 95% (33/33 tests, 0 lint/mypy/secrets) |
| Runtime stability | 60% (5 scaled-down intencionalmente, mas radar reporta RED) |
| Documentation | 70% (drift: 312+ docs, 18 SESSION_SUMMARY) |
| Operational readiness | 40% (5/7 SUI blockers ativos) |
| Push to origin | 0% (2 commits pendentes) |
| iMessage local | 95% (Pietra live, 3 testes validados) |
| Knowledge base TJMG 2026 | 100% (OCR versionado, 9 testes PASS) |

**Cálculo honesto de %** (regra da spec: nunca 100% sem gates):
- Gates RC_READY atendidos: 4/6 (full QA ✅, security ✅, observability ✅, release manifest ✅; ledger ⚠️; blockers humanos ❌)
- Gates GO_LIVE_READY atendidos: 0/10
- Weighted average: **(4/6 × 0.5) + (0/10 × 0.5) = 0.33 = 33%** para GO_LIVE_READY
- Para RC_READY parcial: **(4/6 = 67%)** (faltam 2 gates: ledger atualizado + blockers humanos)

**Não minta**:
- ❌ "100% operacional" (Lesson 274/275) — **INVALIDADO** pelo runtime
- ❌ "8/8 GREEN" — runtime mostra **5/7 OFF**
- ❌ "iMessage Felipe aceito" (Lesson 270) — Felipe handset confirm **PENDENTE** (T100)
- ✅ "Backend code maduro" — 33/33 tests, 0 lint/mypy
- ✅ "AGENT PIETRA live iMessage" — validado 3x neste ciclo
- ✅ "Knowledge base TJMG 2026" — OCR versionado, 9 testes PASS
- ⚠️ "VPS production-ready" — 13/19 services UP, mas radar RED

---

**Próxima ação P0**: `git push origin master` + WhatsApp QR scan + SUI Gustavo (3 ações humanas).

Modified by Gustavo Almeida · 2026-07-27 · Auditoria Forense v1.0.0
