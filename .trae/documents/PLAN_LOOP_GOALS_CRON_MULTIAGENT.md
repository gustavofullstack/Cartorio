# Plano — Loop Contínuo + Goals + Cron + Multi-Agent Orchestration

**Data**: 2026-07-03
**Owner**: Mavis (orquestrador único Minimax-M3)
**Modo**: YOLO (autonomia total, sem pedir permissão por ciclo)
**Rein-alvo**: cartorio-dev / cartorio-n8n / cartorio-lgpd sob `.harness/agent.md`

---

## 1. Resumo

Ativar um **loop contínuo autônomo** que orquestra o time multi-agent do projeto Cartório, sem interrupção, sem prompt de permissão, com:

- **Goals vivas** rastreáveis em arquivo único
- **Meta única** declarada: "100% production-ready + WhatsApp conectado"
- **Objetivos parciais** derivados do `PLAN_100_TASKS_LOOP.md` e `paperclip-board/board.json`
- **Progresso** auto-salvo em `PROGRESS.md` (append-only)
- **Cron de heartbeat** via launchd (macOS Gustavo) + crontab (VPS Linux) — cada agente roda enquanto Gustavo dorme

Resultado esperado: o sistema **continua de onde parou** mesmo após Gustavo sumir/desconectar/dormir, respeitando gates de qualidade (mypy/ruff/pytest) e boundaries LGPD.

---

## 2. Estado Atual (Phase 1 — Exploration)

### 2.1 O que JÁ EXISTE (não recriar)

| Componente | Path | Função |
|------------|------|--------|
| Orquestrador | `.harness/agent.md` | Roteamento dev/n8n/lgpd |
| 5 sub-agents | `.harness/agents/01-analyze-agent.sh` ... `05-memory-agent.sh` | Ciclo analyze→test→fix→doc→memory |
| Loop cron | `.harness/loop-engineer/goal-loop-cron.sh` | Dispara 01-analyze + 02-test, decide next_step |
| Installer launchd | `.harness/loop-engineer/crons/install-launchd.sh` | Cria `~/Library/LaunchAgents/com.cartorio.goal-loop.plist` (4h cycle) |
| Installer crontab | `.harness/loop-engineer/crons/install-crontab.sh` | Cria entry no crontab Linux (4h) |
| Intensive launchd | `.harness/loop-engineer/crons/install-intensive-launchd.sh` | 30min cycle |
| Plan gigante | `.harness/PLAN_100_TASKS_LOOP.md` | 100 tasks, squads S0/A/B/C/D/E/H/J |
| Loop objective | `.harness/crons/LOOP_OBJECTIVE.md` | Goal atual + completion criteria |
| Paperclip board | `.harness/paperclip-board/board.json` + `.md` | 5 goals G1-G5, 11 tasks |
| Progress | `PROGRESS.md` | Append-only log timestamped |
| Memory | `.harness/memory/MEMORY.md` (61 KB) | Cross-rein lessons, index por data |
| Task banks | `.harness/task-bank.json`, `task-bank-turn50.json`, `task-bank-100-melhorias.json` | Bancos de tasks com criteria |
| Validators | `.harness/validators/validate-minimax.sh` (PASS), `validate-zcode.sh`, `validate-zed.sh` | Spec pra sessão externa |

### 2.2 Gaps detectados

1. **launchd NÃO está instalado**: `~/Library/LaunchAgents/com.cartorio.goal-loop.plist` ainda não foi criado (board mostra MEM-1 P0 pendente)
2. **Falta arquivo canônico `GOALS.md`** na raiz: hoje goals vivem em `paperclip-board/board.json` (5 metas) e `LOOP_OBJECTIVE.md` (10 critérios) — estão espalhados
3. **Sem heartbeat cron de progresso**: PROGRESS.md só é atualizado manualmente em `/goal`; loop-cron escreve em `/tmp/cartorio-loop-*.json` mas não atualiza PROGRESS.md
4. **Sem auto-chain entre cycles**: quando loop termina, próximo cycle não sabe retomar do ponto exato
5. **Skills inexistentes (`paperclip-converting-plans-to-tasks`, `parallel-m3-orchestration`, `m3-ultra`, `m27-fast`, etc.)**: usuário listou 17 nomes de skills, mas só `yolo` e `goal` existem no conjunto real → o plano abaixo **mapeia cada intenção para o conjunto real** sem criar skills falsas

### 2.3 Constraints inegociáveis (do AGENTS.md)

- ✅ Audit log tamper-evident (SHA256 + HMAC) — qualquer alteração retroativa quebra chain
- ✅ PII scrubbing 3 camadas — CPF/RG nunca sai raw
- ✅ HITL obrigatório — bot NUNCA decide sozinho em isenção, urgência, emissão
- ✅ mypy 0 + ruff 0 + pytest >= 90% coverage — gates rígidos
- ✅ Mudança em `audit`/`pii` exige review do `cartorio-lgpd`
- ✅ Conventional Commits terminando com `Modified by Gustavo Almeida`
- ✅ SUDO + Root + Admin do Gustavo — YOLO mode = continuar sem perguntar

---

## 3. Decisões do Plano

### D1. Modo YOLO ativo
Decisão: este plano ativa YOLO por default. Não pedir permissão por ciclo. Pular etapas de confirmação. Prosseguir mesmo se Gustavo dormir 15-30s.

### D2. Single source of truth de GOALS
Decisão: criar **`GOALS.md` na raiz** (formato `letra → objetivo → status → % → evidência`) espelhado de `paperclip-board/board.json`. Demais arquivos referenciam este. Mantém compatibilidade com skill `goal`.

### D3. Cron cadence
Decisão: **2 cadences** rodando em paralelo:
- `com.cartorio.goal-loop.plist` (4h) — analysis + tests + decisão
- `com.cartorio.intensive.plist` (30min) — só health checks + progress append

### D4. Auto-chain entre cycles
Decisão: cada cycle escreve `state/cycle-<N>.json` com `next_step`, `carry_over_tasks`, `blockers`. Próximo cycle lê o último e retoma.

### D5. Mapping de skills inexistentes → reais

| Pedido | Real equivalente |
|--------|------------------|
| `init` | `brainstorming` (se aplicável) — senão, primeira execução direta |
| `paperclip-converting-plans-to-tasks` | ação direta: ler `.harness/paperclip-board/board.json` + gerar próximo task |
| `yolo` | ✅ existe — invocar |
| `goal` | ✅ existe — invocar |
| `context` | ler `cartorio-context.md` em `.harness/memory/` |
| `memory-files` | `notion-knowledge-capture` ou escrita direta em `.harness/memory/` |
| `para-memory-files` | organização por pastas (Projects/Areas/Resources/Archive) dentro de `.harness/memory/` |
| `orchestrate-protocol` | leitura literal de `.harness/agent.md` (já tem decision tree) |
| `parallel-m3-orchestration` | usar `Task` tool com múltiplos subagentes em paralelo |
| `ceo-assistant` | já existe como `.harness/reins/cartorio-n8n` no escopo comercial |
| `security-review` | `security-best-practices` skill (quando aplicável) |
| `review` | `executing-plans` (checkpoint review) |
| `loop` | `yolo` + loop-engineer cron |
| `m3-ultra` / `m27-fast` | modelo subjacente — não controlável |
| `dispatch-parallel` | `Task` tool em paralelo |

### D6. Auto-chain de agents (já existente, manter)
`01-analyze → 02-test → 03-fix (se FAIL) → 04-document → 05-memory → PROGRESS.md auto-update`

---

## 4. Mudanças Propostas

### 4.1 Criar `GOALS.md` na raiz (canônico)

**Arquivo**: `/Users/gustavoalmeida/projetos/Cartorio/GOALS.md`

**Formato** (alinhado com skill `goal`):
```markdown
# GOALS — Cartório 2º Notas · 2026-07-03

| Letra | Objetivo | Status | % | Evidência |
|-------|----------|--------|---|-----------|
| A | API + audit chain + PII production-grade | ✅ done | 100% | 1648 pytest passed, mypy 0 |
| B | Telegram bot live + Chatwoot inbox | ✅ done | 100% | lesson 137, 9 E2E tests |
| C | LGPD compliance 100% | ✅ done | 95% | squad D 100% + DPA DeepSeek |
| D | WhatsApp Evolution API conectado | 🟡 blocked | 30% | SUI Gustavo QR scan |
| E | Loop engineer auto-reactivação | 🟡 in_progress | 60% | 5 agents + cron scripts criados |
| F | Docs sincronizadas turn 50+ | 🟡 in_progress | 80% | PROMPT.json/MD divergence |
| G | Multi-provider fallback validado | 🟡 in_progress | 50% | openclaw 3 providers |
```

**Evidência será linkada a**: PROGRESS.md entries, git commit hashes, lesson IDs em MEMORY.md.

### 4.2 Criar `state/` directory + cycle state machine

**Diretório**: `/Users/gustavoalmeida/projetos/Cartorio/.harness/loop-engineer/state/`

**Arquivos por cycle**:
- `cycle-NNN.json` — output completo de cada loop
- `last.json` — symlink ou cópia do mais recente

**Schema**:
```json
{
  "cycle": 137,
  "ts": "2026-07-03T20:30:00-03:00",
  "phase": "analyze|test|fix|document|memory",
  "next_step": "string",
  "carry_over_tasks": ["T9", "DEP-1"],
  "blockers": ["SUI1-DNS-Cloudflare"],
  "gates": {"mypy": 0, "ruff": 0, "pytest": "1648 passed"},
  "evidence": "commit_hash|lesson_id|test_id"
}
```

### 4.3 Modificar `goal-loop-cron.sh` para escrever em `state/`

**Arquivo**: `/Users/gustavoalmeida/projetos/Cartorio/.harness/loop-engineer/goal-loop-cron.sh`

**Mudança** (mínima — append-only, sem mexer no core):
```bash
# Após gerar $OUT, também escrever em state/
STATE_DIR="$PROJECT/.harness/loop-engineer/state"
mkdir -p "$STATE_DIR"
CYCLE_NUM=$(ls "$STATE_DIR"/cycle-*.json 2>/dev/null | wc -l | tr -d ' ')
NEXT=$((CYCLE_NUM + 1))
cp "$OUT" "$STATE_DIR/cycle-$(printf '%04d' $NEXT).json"
cp "$OUT" "$STATE_DIR/last.json"

# Atualizar PROGRESS.md (append-only)
PROGRESS="$PROJECT/PROGRESS.md"
echo -e "\n## $(date '+%Y-%m-%d %H:%M') — LOOP cycle #$NEXT\n" >> "$PROGRESS"
echo '```json' >> "$PROGRESS"
cat "$STATE_DIR/last.json" >> "$PROGRESS"
echo '```' >> "$PROGRESS"
```

### 4.4 Ativar launchd (instalar plist)

**Comando** (executar uma vez):
```bash
bash /Users/gustavoalmeida/projetos/Cartorio/.harness/loop-engineer/crons/install-launchd.sh
bash /Users/gustavoalmeida/projetos/Cartorio/.harness/loop-engineer/crons/install-intensive-launchd.sh
```

**Validação**:
```bash
launchctl list | grep cartorio
# esperado:
# PID	Status	Label
# -	0	com.cartorio.goal-loop
# -	0	com.cartorio.intensive
```

### 4.5 Criar wrapper `loop-continue.sh` (retomada de sessão)

**Arquivo**: `/Users/gustavoalmeida/projetos/Cartorio/.harness/loop-engineer/loop-continue.sh`

**Propósito**: quando uma nova sessão inicia (Gustavo volta após dormir), o agent lê `state/last.json` e retoma o `carry_over_tasks` automaticamente. Mapeia a skill `loop` para este script.

**Schema**:
```bash
#!/usr/bin/env bash
# Lê último cycle e imprime próximos passos
LAST="$PROJECT/.harness/loop-engineer/state/last.json"
cat "$LAST" | jq '.carry_over_tasks[]' 2>/dev/null
```

### 4.6 Mapping de skills → ações reais

**Documento**: `/Users/gustavoalmeida/projetos/Cartorio/.harness/loop-engineer/SKILLS-MAP.md`

Lista cada skill pedida pelo Gustavo + mapping para skill real ou ação direta.

---

## 5. Arquivos a Criar / Modificar

| Ação | Path | Por quê |
|------|------|---------|
| CRIAR | `/Users/gustavoalmeida/projetos/Cartorio/GOALS.md` | Single source of truth de metas |
| CRIAR | `/Users/gustavoalmeida/projetos/Cartorio/.harness/loop-engineer/state/` dir | Cycle state machine |
| MODIFICAR | `/Users/gustavoalmeida/projetos/Cartorio/.harness/loop-engineer/goal-loop-cron.sh` | Append state + PROGRESS |
| EXECUTAR | `bash .harness/loop-engineer/crons/install-launchd.sh` | Ativar cron macOS |
| EXECUTAR | `bash .harness/loop-engineer/crons/install-intensive-launchd.sh` | Ativar cron 30min |
| CRIAR | `/Users/gustavoalmeida/projetos/Cartorio/.harness/loop-engineer/loop-continue.sh` | Retomada de sessão |
| CRIAR | `/Users/gustavoalmeida/projetos/Cartorio/.harness/loop-engineer/SKILLS-MAP.md` | Mapping pedido→real |
| SINCRONIZAR | `/Users/gustavoalmeida/projetos/Cartorio/.harness/paperclip-board/board.json` | Atualizar status goals A-G |
| ATUALIZAR | `/Users/gustavoalmeida/projetos/Cartorio/.harness/memory/MEMORY.md` | Lesson 139: loop engineer ativado |

---

## 6. Workflow Obrigatório (do AGENTS.md)

Sequência de execução (sem pular etapas):

```
analisar  → done (Phase 1 exploração)
testar    → próximo: verificar pyproject.toml deps (fakeredis, pytest-asyncio)
corrigir  → aplicar mudanças 4.1-4.6
melhorar  → refactor goal-loop-cron.sh se necessário
otimizar  → validar que cron não trava processos longos
documentar → atualizar PROGRESS.md + MEMORY.md (Lesson 139)
comentar   → Conventional Commits
salvar na memória → Lesson 139 + SKILLS-MAP.md
```

---

## 7. Verificação (Stop When)

- [ ] `GOALS.md` existe na raiz com 7 metas A-G
- [ ] `state/last.json` existe e tem schema válido
- [ ] `goal-loop-cron.sh` escreve em state/ E em PROGRESS.md (testado com run manual)
- [ ] `launchctl list | grep cartorio` retorna 2 entries (goal-loop + intensive)
- [ ] `PROGRESS.md` tem nova entrada com cycle #N timestamped
- [ ] `MEMORY.md` tem Lesson 139 indexada
- [ ] `paperclip-board/board.json` goals G1-G5 mapeados para A-G no GOALS.md
- [ ] `SKILLS-MAP.md` mapeia as 17 skills pedidas → reais
- [ ] Gustavo (root session) não precisou aprovar nada mid-execution (YOLO)

---

## 8. Próximas Ações Após Aprovação

1. Criar `GOALS.md` na raiz
2. Criar `state/` directory
3. Modificar `goal-loop-cron.sh` (append state + PROGRESS)
4. Executar `install-launchd.sh` + `install-intensive-launchd.sh`
5. Criar `loop-continue.sh` + `SKILLS-MAP.md`
6. Sincronizar `paperclip-board/board.json`
7. Atualizar `MEMORY.md` (Lesson 139)
8. Atualizar `PROGRESS.md` (cycle 138)
9. Validar `launchctl list | grep cartorio` = 2 entries
10. Commit Conventional Commits + push

Modified by Gustavo Almeida (via plan Mavis)