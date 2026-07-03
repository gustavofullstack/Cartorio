# SKILLS-MAP — Mapeamento Skills Pedidas → Skills/ações Reais

**Data**: 2026-07-03
**Lesson**: 139
**Contexto**: Gustavo listou 17 nomes de skills; o conjunto real da plataforma Minimax-M3 contém apenas algumas dessas + skills nativas Trae. Este arquivo mapeia cada intenção para o que REALMENTE existe.

---

## SKILLS PEDIDAS vs REAIS

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

## SKILLS TRAE NATIVAS MAIS ÚTEIS (referência)

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
| `api` | Interagir com FastAPI do Cartório |
| `chatwoot` | Interagir com Chatwoot CRM |
| `easypanel` | Easypanel via REST — deploy, services, env vars |
| `hostinger` | VPS Hostinger via SSH/Tailscale/API |
| `n8n` | N8N Workflow Engine API REST + MCP |
| `supabase` | Supabase self-hosted REST + Auth + Storage + Realtime |
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

## REGRA DE OURO

> **Quando Gustavo listar skills, sempre mapear antes de executar.**
> Não criar skills falsas. Se não existe, fazer a ação via script direto ou tool nativa.

Modified by Gustavo Almeida (via plan Mavis)