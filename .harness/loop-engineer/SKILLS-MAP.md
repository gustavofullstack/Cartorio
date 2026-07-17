# SKILLS-MAP — Mapeamento Skills Pedidas → Skills/ações Reais

**Data sync**: 2026-07-17 (G7.15.T4 Wave 25)  
**Origem histórica**: 2026-07-03 · Lesson 139  
**Smoke**: `docs/SKILLS_SMOKE_G7.md` · `python3 scripts/skills_smoke.py`  
**Catálogo agent**: `.agents/skills/INDEX.md`

> **Lesson**: Gustavo listou 17 nomes de skills; o conjunto real da plataforma Minimax-M3
> contém apenas algumas dessas + skills nativas Trae. Este arquivo mapeia cada intenção
> para o que REALMENTE existe — e, desde G7.15, lista o inventário versionado em
> `.agents/skills/`.

---

## 0. INVENTÁRIO REAL — `.agents/skills/` (G7.15.T4)

Skills **versionadas no repo** (cada uma com `SKILL.md` não-vazio). Smoke core = 6 primeiras.

| # | Skill | Path | Categoria | Purpose (1ª linha) |
|---|-------|------|-----------|--------------------|
| 1 | `api` | [`.agents/skills/api/SKILL.md`](../../.agents/skills/api/SKILL.md) | INTEGRATION | FastAPI REST + WebSocket + MCP cartório |
| 2 | `chatwoot` | [`.agents/skills/chatwoot/SKILL.md`](../../.agents/skills/chatwoot/SKILL.md) | INTEGRATION | Chatwoot CRM API + handoff humano |
| 3 | `n8n` | [`.agents/skills/n8n/SKILL.md`](../../.agents/skills/n8n/SKILL.md) | WORKFLOW | N8N REST + webhooks + MCP tools |
| 4 | `supabase` | [`.agents/skills/supabase/SKILL.md`](../../.agents/skills/supabase/SKILL.md) | DATABASE | Supabase self-hosted REST/Auth/Storage |
| 5 | `easypanel` | [`.agents/skills/easypanel/SKILL.md`](../../.agents/skills/easypanel/SKILL.md) | INFRA | Easypanel deploy / Swarm / env |
| 6 | `hostinger` | [`.agents/skills/hostinger/SKILL.md`](../../.agents/skills/hostinger/SKILL.md) | INFRA / NET | VPS SSH + Tailscale + Docker Swarm |
| 7 | `minimax-m3` | [`.agents/skills/minimax-m3/SKILL.md`](../../.agents/skills/minimax-m3/SKILL.md) | LLM | MiniMax-M3 XMax Thinking via LiteLLM |
| 8 | `coding-vps-21` | [`.agents/skills/coding-vps-21/SKILL.md`](../../.agents/skills/coding-vps-21/SKILL.md) | AGENT | Ativar 21+ coding agents MiniMax |
| 9 | `coding-vps-tools-100` | [`.agents/skills/coding-vps-tools-100/SKILL.md`](../../.agents/skills/coding-vps-tools-100/SKILL.md) | INFRA | Catálogo real ~62 tools MCP (nome histórico 100) |
| 10 | `coding-vps-orchestrator` | [`.agents/skills/coding-vps-orchestrator/SKILL.md`](../../.agents/skills/coding-vps-orchestrator/SKILL.md) | AGENT | MCP orchestrator CLI / HTTP / stdio |
| 11 | `coding-vps-deploy` | [`.agents/skills/coding-vps-deploy/SKILL.md`](../../.agents/skills/coding-vps-deploy/SKILL.md) | INFRA | Deploy agents Docker no coding-vps |
| 12 | `coding-vps-monitor` | [`.agents/skills/coding-vps-monitor/SKILL.md`](../../.agents/skills/coding-vps-monitor/SKILL.md) | MONITORING | Health / stats / Prometheus no VPS |

**Total**: 12 skills com `SKILL.md` (smoke core 6/6 — ver `docs/SKILLS_SMOKE_G7.md`).

### Smoke rápido

```bash
python3 scripts/skills_smoke.py          # exit 0 se core 6/6
python3 scripts/skills_smoke.py --all    # + extended inventory
python3 scripts/skills_smoke.py --json
```

### Skill → rein harness

| Skill | Rein principal |
|-------|----------------|
| `api` | cartorio-dev |
| `chatwoot`, `n8n` | cartorio-n8n |
| `supabase` | cartorio-data / cartorio-dev |
| `easypanel`, `hostinger` | cartorio-sre |
| `minimax-m3`, coding-vps-* | cartorio-dev (+ coding-vps ops) |

---

## 1. SKILLS PEDIDAS vs REAIS (histórico Lesson 139)

| # | Skill pedida | Existe? | Equivalente real | Como executar |
|---|--------------|---------|------------------|---------------|
| 1 | `init` | ❌ | primeira execução direta OU `brainstorming` (skill Trae) | Iniciar task sem preâmbulo |
| 2 | `paperclip-converting-plans-to-tasks` | ❌ | ação direta + `.harness/paperclip-board/board.json` | Ler board.json → gerar próximo task |
| 3 | `yolo` | ✅ EXISTE | — | Skill Trae nativa — invocar |
| 4 | `goal` | ✅ EXISTE | — | Skill Trae nativa — invocar |
| 5 | `context` | ❌ | ler `.harness/memory/cartorio-context.md` direto | Read tool no arquivo |
| 6 | `memory-files` | ❌ | `notion-knowledge-capture` (Trae) OU escrita direta em `.harness/memory/` | Write tool + naming convention |
| 7 | `para-memory-files` | ❌ | organizar `.harness/memory/` por pastas (Projects/Areas/Resources/Archive) | mkdir + mover arquivos |
| 8 | `orchestrate-protocol` | ❌ | ler `.harness/agent.md` direto (decision tree) | Read tool |
| 9 | `parallel-m3-orchestration` | ❌ | `Task` tool com múltiplos subagentes em paralelo | run 3-5 Task calls em uma mensagem |
| 10 | `ceo-assistant` | ❌ | já existe como escopo `.harness/reins/cartorio-n8n` (comercial) | Read agent.md do rein |
| 11 | `security-review` | ❌ | `security-best-practices` (Trae) | Skill Trae — invocar quando aplicável |
| 12 | `review` | ❌ | `executing-plans` (Trae) — review checkpoint | Skill Trae — invocar |
| 13 | `loop` | ❌ | `yolo` + `.harness/loop-engineer/goal-loop-cron.sh` + `loop-continue.sh` | bash scripts |
| 14 | `m3-ultra` | ❌ | modelo subjacente — não controlável pelo usuário | n/a |
| 15 | `m27-fast` | ❌ | modelo subjacente — não controlável pelo usuário | n/a |
| 16 | `dispatch-parallel` | ❌ | `Task` tool em paralelo | múltiplos run_mcp / Task calls simultâneos |
| 17 | `ceo-assistant` (dup) | ❌ | mesma linha 10 | mesma |

---

## 2. SKILLS TRAE NATIVAS MAIS ÚTEIS (referência)

| Skill Trae | Quando usar |
|------------|-------------|
| `yolo` | Full autonomy, 100-task plano, "OK then execute" preference |
| `goal` | Acompanhar A→Z goals em `~/GOALS.md` com formato letra → objetivo → status → % → evidência |
| `brainstorming` | Antes de criar feature / componente / modificar comportamento |
| `executing-plans` | Quando tem plan escrito para executar com checkpoints |
| `writing-plans` | Quando tem spec/requirements para multi-step task |
| `test-driven-development` | Implementar feature/bugfix, ANTES de escrever código |
| `security-best-practices` | Apenas quando user pedir security review (python/js/go) |
| `web-design-guidelines` | Review UI code for Web Interface Guidelines compliance |
| `notion-knowledge-capture` | Transformar conversa em documentação Notion |
| `notion-research-documentation` | Pesquisar Notion workspace + criar páginas |
| `obsidian-cli` | Interagir com Obsidian vault via CLI |
| `mcp-builder` | Criar MCP servers Python (FastMCP) ou Node (MCP SDK) |
| `defuddle` | Extrair markdown limpo de páginas web |
| `agent-browser` | Browser automation CLI para AI agents |
| `electron` | Automate Electron desktop apps via CDP |
| `gsap` | GSAP animation reference |
| `hyperframes` | Create video compositions em HyperFrames HTML |
| `hyperframes-cli` | HyperFrames dev loop |
| `hyperframes-media` | Asset preprocessing (TTS, transcription, remove bg) |
| `redis-development` | Redis performance + best practices |
| `chart-visualization` | Visualizar dados — 26 chart types |
| `data-analysis` | Excel/CSV → stats, pivot, SQL queries |
| `consulting-analysis` | Professional research reports (market analysis, etc.) |
| `report-generator` | Video analysis report (Markdown) |
| `hook-analyzer` | Análise dos primeiros 3s de vídeo |
| `theme-factory` | Toolkit de styling para artifacts |
| `webapp-testing` | Interagir/testar web apps via Playwright |
| `web-dev` | Criar websites/web apps/web-based games do zero |
| `frontend-design` | Frontend interfaces production-grade |
| `frontend-skill` | Landing pages, demos, apps — image-led hierarchy |
| `skill-creator` | Criar SKILLs (MANDATORY) |
| `shadcn` | shadcn/ui components |
| `api` | → **repo** `.agents/skills/api/` (FastAPI Cartório) |
| `chatwoot` | → **repo** `.agents/skills/chatwoot/` |
| `easypanel` | → **repo** `.agents/skills/easypanel/` |
| `hostinger` | → **repo** `.agents/skills/hostinger/` |
| `n8n` | → **repo** `.agents/skills/n8n/` |
| `supabase` | → **repo** `.agents/skills/supabase/` |
| `internal-comms` | Status reports, leadership updates, FAQs |
| `doc-coauthoring` | Co-author documentation estruturada |
| `local-computer-use` | Windows computer use (Intel Local) |
| `screenshot` | Desktop/system screenshot |
| `web-artifacts-builder` | Multi-component HTML artifacts com React + Tailwind + shadcn/ui |
| `canvas-design` | Visual art em .png/.pdf |
| `algorithmic-art` | p5.js generative art |
| `byted-seedream-image-generate` | Gerar imagens via Seedream |
| `byted-seedance-video-generate` | Gerar vídeos via Seedance |
| `slides` | Criar .pptx com PptxGenJS |
| `json-canvas` | JSON Canvas files (.canvas) para Obsidian |
| `obsidian-bases` | Obsidian Bases (.base files) |
| `obsidian-markdown` | Obsidian Flavored Markdown |
| `dogfood` | QA / exploratory test / bug hunt |
| `vercel-composition-patterns` | React composition patterns |
| `vercel-react-best-practices` | React/Next.js performance |
| `vercel-react-native-skills` | React Native + Expo best practices |

---

## 3. REGRA DE OURO

> **Quando Gustavo listar skills, sempre mapear antes de executar.**  
> Não criar skills falsas. Se não existe, fazer a ação via script direto ou tool nativa.  
> Fonte de verdade versionada: `.agents/skills/` + este mapa + `INDEX.md`.  
> Smoke gate: `python3 scripts/skills_smoke.py` (core 6).

---

**Modified by Gustavo Almeida — G7.15.T4 Wave 25 (2026-07-17)**  
*Histórico Lesson 139 preservado (seções 1–2); inventário real adicionado na seção 0.*
