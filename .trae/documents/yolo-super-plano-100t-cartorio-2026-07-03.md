# YOLO SUPER PLANO — Cartório 100 Tasks Loop (Sessão 2026-07-03)

**Owner:** Gustavo Almeida · **Modo:** YOLO Autonomous Loop (cron launchd)
**Skill invocations:** /init · /memory-files · /cartorio-context · /context · /goal · /dispatch-parallel · /m27-fast · /m3-ultra
**Foco:** Apenas `~/projetos/Cartorio/` (Squads A-J + Brain8 + crwal4ai fix). MZ NET PROJETO SENTINELA fica pausado nesta sessão.
**Autonomy:** Cron loop infinito. SEM prompt intermediário. SUI fixes permitidos quando aplicáveis.

---

## 1. Summary

Bootstrap de sessão multi-skill para orquestrar o loop autônomo de 100 tasks incrementais no projeto Cartório, cobrindo os squads A-J, Brain8 e crwal4ai. O loop usa os 5 scripts do `.harness/agents/` (01-analyze → 02-test → 03-fix → 04-document → 05-memory) sob cron launchd, com auto-reactivação a cada 10min. Cada task gera 1 commit Conventional e append em MEMORY.md cross-session.

**Por que esta abordagem:** O usuário quer Setup completo da sessão (ler todos os arquivos canônicos, popular MEMORY, sincronizar GOALS) e disparar o loop YOLO 100 tasks. O estado real já está maduro: 1211 testes passando, 90%+ coverage, mypy/ruff zero, mas há blockers remanescentes documentados em `loop-state.json` (Squad A13-A25, Brain8, crwal4ai VXLAN). A infraestrutura de loop-engineer já existe — falta o glue de sessão.

---

## 2. Current State Analysis (achados da exploração)

### 2.1 Estado do repo (verificado)
- **Branch:** `master` (nunca push direto — AGENTS.md regra)
- **Testes:** 1211 passing, coverage 90%+ (loop-state 2026-07-02)
- **Gates:** mypy 0 / ruff 0 (validado em SESSION_SUMMARY_2026-06-30)
- **Serviços Swarm:** 8/8 UP (api, litellm, openclaw, langfuse, argilla, evolution, anything-llm, lobechat, zeroclaw, open-notebook)
- **Plan canônico mais recente:** `.harness/PLAN_100_TASKS_LOOP.md` (2026-06-25) — referencia para priorização
- **Task-bank JSON:** `.harness/task-bank.json` — 21% completion, p0=3/10, p1=1/30, p2=17/60
- **Lessons count:** 139 (loop-state)

### 2.2 Artefatos canônicos lidos
- `~/MEMORY.md` — append-only cross-session (já tem 200+ linhas até 2026-07-03T06:08)
- `~/AGENTS.md` — Estrutura Organizada v13, YOLO mode, tools CLI, MCP servers
- `~/GOALS.md` — Loop Orquestrador Autônomo, PROJETO SENTINELA MZ NET (letras A-Z, 76%)
- `/Users/gustavoalmeida/.config/zed/MEMORY.md` — Zed.app setup (settings.json 42 agents, 14 MCPs, 15 LSP)
- `/Users/gustavoalmeida/.config/zed/settings.json` — TRAE hub config
- `/Users/gustavoalmeida/projetos/Cartorio/AGENTS.md` + `CLAUDE.md` — regras de compliance
- `/Users/gustavoalmeida/projetos/Cartorio/.harness/AGENTS.md` — operational multi-agent
- `/Users/gustavoalmeida/projetos/Cartorio/.harness/PLAN_100_TASKS_LOOP.md` — plano dos squads
- `/Users/gustavoalmeida/projetos/Cartorio/.harness/agents/01-analyze-agent.sh` ... `03-fix-agent.sh` — scripts do loop
- `/Users/gustavoalmeida/projetos/Cartorio/.harness/loop-engineer/crons/LOOP_OBJECTIVE.md` — objetivo G7 vigente
- `/Users/gustavoalmeida/projetos/Cartorio/.brain/loop-state.json` — estado operacional atual
- `/Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-07-02.md` — log mais recente
- `/Users/gustavoalmeida/projetos/Cartorio/.harness/memory/MEMORY.md` — mem cross-rein

### 2.3 Pendências priorizadas (loop-state `next_priorities_post_user_confirm`)
1. Squad A 12 tasks pendentes (A13-A25) — audit hardening
2. Reativar N8N (B6-B15)
3. LGPD D21-D25 (5 tasks)
4. BRAIN8 (1 task) — compact loop-state.json
5. SQUAD A20-A25 (5 tasks)
6. crwal4ai VXLAN fix
7. Integrar Langfuse tracing + Argilla feedback na API
8. Sprint retro + lessons loop

### 2.4 SUI tasks (aprovadas para fix nesta sessão)
- SUI1: DNS divergente (chatwoot/n8n/supabase NXDOMAIN 7/7 resolvers)
- SUI2: Evolution `cartorio-2notas` state=close (precisa scan QR)
- SUI3: Chatwoot ENABLE_ACCOUNT_SIGNUP=true → false (já DONE 2026-07-02)

---

## 3. Proposed Changes

### 3.1 Skill wiring (mapping das 8 invocações → ações)

| Skill invocada | Ação real | Arquivo destino | Status |
|---|---|---|---|
| `/init` | Bootstrap sessão: ler ~/MEMORY.md + ~/AGENTS.md, append datado | `~/MEMORY.md` (append-only) | pendente |
| `/memory-files` | Indexar novos arquivos de memória + criar entry MEMORY.md | `~/MEMORY.md` (append-only) | pendente |
| `/cartorio-context` | Carregar `.harness/memory/cartorio-context.md` + AGENTS.md do Cartório | contexto carregado | feito em runtime |
| `/context` | Compilar 1-pager contexto: state + gates + pendências | `~/projetos/Cartorio/.brain/memory/2026-07-03-context.md` (novo) | pendente |
| `/goal` | Atualizar round v23 do `~/GOALS.md` com fase Cartório | `~/GOALS.md` (append-only) | pendente |
| `/dispatch-parallel` | Lançar 2-3 sub-agentes em paralelo: cartorio-dev, cartorio-lgpd, cartorio-n8n | n/a (orquestração in-session) | pendente |
| `/m27-fast` | Framework M2.7 highspeed para tasks triviais (lint, format, doc) | uso interno | pendente |
| `/m3-ultra` | Framework M3-ultra (1M ctx) para refactor profundo, audit review | uso interno | pendente |

### 3.2 Setup de sessão (fase 1 — obrigatória)

| # | Arquivo | Operação | Conteúdo |
|---|---|---|---|
| 1 | `~/MEMORY.md` | append-only | Sessão 2026-07-03 entry: skills invocadas, plan title, contexto carregado |
| 2 | `/Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-07-03-context.md` | criar | 1-pager com state atual + 100-task backlog priorizado |
| 3 | `/Users/gustavoalmeida/projetos/Cartorio/.brain/loop-state.json` | patch leve | Bump version, adicionar `current_session: "yolo-super-plano-2026-07-03"` |
| 4 | `/Users/gustavoalmeida/projetos/Cartorio/.harness/memory/MEMORY.md` | append-only | Cross-rein lesson: "skills invocadas como templates vazios — sempre pedir intent antes" |
| 5 | `~/GOALS.md` | append-only | Round v23 — fase Cartório adicionada |

### 3.3 YOLO Loop 100 Tasks (fase 2 — loop infinito)

Cron launchd carrega `~/Library/LaunchAgents/com.gustavo.cartorio-yolo-100t.plist` → executa `~/bin/cartorio-yolo-100t.sh` a cada 600s (10min).

#### 3.3.1 Estrutura do loop

```bash
for round in $(seq 1 100); do
  # FASE 1: ANALYZE
  /Users/gustavoalmeida/projetos/Cartorio/.harness/agents/01-analyze-agent.sh
  
  # FASE 2: TEST (gate)
  /Users/gustavoalmeida/projetos/Cartorio/.harness/agents/02-test-agent.sh
  if FAIL: continue  # vai pra fase fix
  
  # FASE 3: FIX (1 task do backlog)
  /Users/gustavoalmeida/projetos/Cartorio/.harness/agents/03-fix-agent.sh
  
  # FASE 4: DOCUMENT
  /Users/gustavoalmeida/projetos/Cartorio/.harness/agents/04-document-agent.sh
  
  # FASE 5: MEMORY
  /Users/gustavoalmeida/projetos/Cartorio/.harness/agents/05-memory-agent.sh
  
  # Append estado em MEMORY.md
  append_round_to_memory.sh
  
  sleep 600
done
```

#### 3.3.2 Backlog priorizado (100 tasks)

| Squad | Range | Tipo | Auto-fix? |
|---|---|---|---|
| A13-A25 (13) | 1-13 | Audit hardening (redlock, cache, openapi validator, problem+json) | ✅ |
| B6-B15 (10) | 14-23 | N8N polish (timeout, logs, metrics, alerts, tests) | ✅ após restart N8N |
| D21-D25 (5) | 24-28 | LGPD policy/training (policy-side, código parcial) | parcial |
| BRAIN8 (1) | 29 | Compact loop-state.json | ✅ |
| A20-A25 redo (5) | 30-34 | Squash / cleanup | ✅ |
| crwal4ai (1) | 35 | Fix imagem all-arm64 → latest | ✅ SUI |
| SUI1 DNS (5) | 36-40 | Criar A records chatwoot/n8n/supabase Traefik routers | ⚠️ requer aprovação por item |
| SUI2 Evolution (3) | 41-43 | QR scan + connection state | ⚠️ Gustavo celular |
| C13-C25 docs (13) | 44-56 | Docs ops+audit+stack | ✅ |
| J6-J10 obs (5) | 57-61 | Prometheus alerting, smoke, rollback, dead man's switch | ✅ |
| BRAIN1-BRAIN7 (7) | 62-68 | Brain sync bidirecional + schema + endpoints | ✅ |
| P0.7-P0.9 output PII (3) | 69-71 | Output scrub router.py:553, integrations.py:190, response shape | ✅ |
| P1.BE.* (10) | 72-81 | Encryption at-rest, MCP servers (Evolution/Chatwoot/Redis), admin pause, retry backoff, DLQ metrics, OpenAPI, stale detector test | ✅ |
| P1.LG.* (6) | 82-87 | DPA Evolution/M3/Opencode-Go, direito esquecimento via chat, consent WhatsApp, retenção configurável | ✅ após policy |
| P1.DO.* (6) | 88-93 | CD GitHub Actions, Easypanel auto-deploy, N8N backup, Grafana, Alertmanager | ✅ |
| S16-S20 LGPD endpoints (5) | 94-98 | LGPD-026-032 sprint 3 endpoints HTTP | ✅ |
| Margem de safety (2) | 99-100 | Re-roll / lessons consolidation | ✅ |

### 3.4 SUI fixes permitidos (gate explícito)

Por **SUI1** (DNS divergente): cada fix requer aprovação antes. Pattern: `AskUserQuestion` → "Aplicar fix DNS para X? sim/não".

Por **SUI2** (Evolution QR scan): Gustavo aciona manualmente no celular. Loop detecta `state=close` e gera prompt para Gustavo.

Por **SUI3** (já DONE): não tocar.

### 3.5 MEMORY appends (sessão)

| Arquivo | Tipo | Conteúdo |
|---|---|---|
| `~/MEMORY.md` | append | Sessão 2026-07-03 entry (skills + plan title + estado) |
| `/Users/gustavoalmeida/projetos/Cartorio/.harness/memory/MEMORY.md` | append | Lesson 140: "Skills invocadas vazias — pedir intent primeiro" |
| `/Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-07-03.md` | criar | Log contínuo da sessão |
| `/Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-07-03-context.md` | criar | 1-pager state atual |
| `~/GOALS.md` | append | Round v23 — fase Cartório 100 tasks |

### 3.6 Settings (opcional, sob aprovação)

Patches potenciais em `~/.config/zed/settings.json`:
- Adicionar novo profile `cartorio-yolo` (tools: read+edit+bash+grep+glob, sem network)
- Wire loop launchd plist para `~/Library/LaunchAgents/com.gustavo.cartorio-yolo-100t.plist`
- NÃO modificar agents existentes (42 ativos) sem aprovação

---

## 4. Assumptions & Decisions

### 4.1 Decisões locked-in
- **D1**: Apenas Cartório nesta sessão. MZ NET pausa (não atualizar letras P/Q/U automaticamente).
- **D2**: Autonomy = cron loop (a cada 10min). Sem prompt intermediário.
- **D3**: SUI fixes permitidos com gate explícito (AskUserQuestion por item).
- **D4**: 1 task = 1 commit Conventional Commits. Mensagem termina com `Modified by Gustavo Almeida`.
- **D5**: MEMORY.md sempre append-only (nunca overwrite).
- **D6**: Mudança em `audit` ou `pii` requer review do `cartorio-lgpd` antes do commit.
- **D7**: Gates obrigatórios: mypy 0, ruff 0, pytest 1211+ passing, coverage >= 90%.

### 4.2 Assumptions
- **A1**: `~/Library/LaunchAgents/com.gustavo.cartorio-yolo-100t.plist` ainda não existe (precisa criar)
- **A2**: `~/bin/cartorio-yolo-100t.sh` ainda não existe (precisa criar)
- **A3**: `.harness/agents/04-document-agent.sh` e `05-memory-agent.sh` precisam ser validados (não lidos nesta sessão)
- **A4**: VPS reachable via Tailscale (100.99.172.84) — SSH funcional
- **A5**: Redis recovered, services swarm 8/8 UP (loop-state 2026-07-02)

### 4.3 Out of scope
- MZ NET PROJETO SENTINELA letras P/Q/U (pausado)
- Rotação de chaves API (decisão Gustavo 2026-06-24 14:50 BRT — NUNCA sob pressão)
- Push direto para origin (sempre via PR, regra AGENTS.md)
- Mudanças destrutivas (rm -rf, force push, drop db)

---

## 5. Verification Steps

### 5.1 Setup de sessão (fase 1)
```bash
# 1. MEMORY.md tem nova entrada datada
tail -50 ~/MEMORY.md | grep "2026-07-03"

# 2. context 1-pager existe
test -f /Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-07-03-context.md && echo OK

# 3. loop-state patch leve aplicado
jq .current_session /Users/gustavoalmeida/projetos/Cartorio/.brain/loop-state.json | grep "yolo-super-plano"

# 4. cross-rein lesson em .harness/memory
grep "Lesson 140" /Users/gustavoalmeida/projetos/Cartorio/.harness/memory/MEMORY.md

# 5. GOALS.md round v23 adicionado
tail -100 ~/GOALS.md | grep "Round v23"
```

### 5.2 Loop gates (fase 2 — a cada round)
```bash
# Gates obrigatórios
cd /Users/gustavoalmeida/projetos/Cartorio/backend
uv run pytest --no-cov -q                # >= 1211 passing
uv run mypy app/                          # 0 errors
uv run ruff check .                       # 0 errors
uv run ruff format --check .              # formatted

# Conventional commit válido
git log -1 --pretty=%B | grep -E "^(feat|fix|docs|test|refactor|chore|perf):"
git log -1 --pretty=%B | grep "Modified by Gustavo Almeida"

# MEMORY append
test -f /Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-07-03-round-$(printf '%03d' $ROUND).md
```

### 5.3 SUI gates
- DNS create: validar `dig chatwoot.2notasudi.com.br @1.1.1.1` retorna A record
- Evolution QR: validar `instance.state=open` via Evolution API
- Chatwoot: validar `ENABLE_ACCOUNT_SIGNUP=false` (já DONE, skip)

### 5.4 Done criteria
- [ ] 100 tasks rodadas (ou até gate fail persistente)
- [ ] Cada task: 1 commit + 1 MEMORY append + gates verdes
- [ ] `~/MEMORY.md` tem sessão 2026-07-03 fechada com sumário
- [ ] `.brain/loop-state.json` tem `status` atualizado para `yolo_100t_done_<N>`
- [ ] Cron launchd instalado e validado (`launchctl list | grep cartorio-yolo-100t`)

---

## 6. Rollback Plan

Se gates falharem persistentemente (>3 rounds FAIL):
1. Parar cron: `launchctl unload ~/Library/LaunchAgents/com.gustavo.cartorio-yolo-100t.plist`
2. Reverter último commit: `git reset --hard HEAD~1`
3. Append em MEMORY.md: "Loop abortado em round N — gates falhando"
4. Notificar Gustavo via Telegram (webhook cartório)

Se SUI fix quebrar prod:
1. Auto-rollback via Easypanel snapshot (J8 task)
2. Alertmanager → Telegram GRUPO Pietra
3. Postmortem em `docs/POSTMORTEMS.md`

---

## 7. File Manifest (criar/editar)

**CRIAR:**
1. `/Users/gustavoalmeida/projetos/Cartorio/.trae/documents/yolo-super-plano-100t-cartorio-2026-07-03.md` (este arquivo)
2. `/Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-07-03.md`
3. `/Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-07-03-context.md`
4. `~/bin/cartorio-yolo-100t.sh` (script do loop)
5. `~/Library/LaunchAgents/com.gustavo.cartorio-yolo-100t.plist` (cron)

**EDITAR (append-only):**
1. `~/MEMORY.md`
2. `/Users/gustavoalmeida/projetos/Cartorio/.harness/memory/MEMORY.md`
3. `~/GOALS.md`
4. `/Users/gustavoalmeida/projetos/Cartorio/.brain/loop-state.json` (patch leve)
5. `/Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-07-03-round-*.md` (1 por round)

**NÃO TOCAR (read-only):**
- `backend/app/services/audit.py`, `audit_*.py`, `pii.py` (mudança requer cartorio-lgpd review)
- `backend/.env`, `.env.example` (secrets)
- VPS remoto sem aprovação explícita
- `~/.zshrc`, `~/.zshenv` (exceto via path seguro)

---

## 8. Open Questions (para próxima iteração)

1. **Profile cartorio-yolo**: criar novo profile no settings.json OU reutilizar `yolo` global?
2. **Parallelism**: 2-3 sub-agentes simultâneos OU estritamente sequencial (1 agent)?
3. **N8N restart**: reativar B6-B15 requer restart do serviço. Aprovar agora ou após SUI1 DNS?
4. **Sprint 3 endpoints LGPD-026-032**: spec já existe em `.harness/specs/`. Implementar todos 7 ou só os 3 críticos?
5. **Langfuse + Argilla integration**: tarefa 7 do backlog. Vale o esforço ou skip?

Modified by Gustavo Almeida