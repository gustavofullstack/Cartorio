# Auditoria ZCode — 2026-06-25

## Ambiente
- **ZCode.app**: /Applications/ZCode.app (v3.1.5, build 1966)
- **Plataforma**: macOS Darwin 25.5.0 arm64
- **Working dir**: /Users/gustavoalmeida/projetos/Cartorio
- **Git branch**: master (feat/zcode-fallback-chain merged em commit 1253194)

## Providers cadastrados em v2/config.json (achado da Task 0.1)
| ID | Nome | Kind | baseURL | enabled |
|---|---|---|---|---|
| default-minimax | opencode-go | anthropic | https://opencode.ai/zen/go | **true** |
| c997ca58-cfda-4c2f-8550-69830972bad7 | minimax-coding-plan | anthropic | https://api.minimax.io/anthropic | **true** |
| a78c8877-8acd-42db-a21e-e1a4f38e57d3 | kimi | openai-compatible | https://api.kimi.com/coding/v1 | null |
| 15568793-5414-4c84-b794-ba4572e0412e | opencode-free | openai-compatible | https://opencode.ai/zen/v1 | **null (precisa ativar)** |
| a84a18da-ac47-43d1-a250-2bfdf49cf4a3 | openrouter-free | openai-compatible | https://openrouter.ai/api/v1 | **null (precisa ativar)** |
| 4ff49ce7-9523-462f-89c2-2ba8b55042d8 | groq-free | openai-compatible | https://api.groq.com/openai/v1 | **null (precisa ativar)** |
| 04873a4d-4767-4924-8d47-c25828e7e566 | mistral-free | openai-compatible | https://api.mistral.ai/v1 | **null (precisa ativar)** |

**Achado crítico Task 0.1**: apenas 2 dos 7 providers estão `enabled: true`. Os 4 free (opencode/openrouter/groq/mistral) precisam ser ativados antes de qualquer uso. Ação em Task 0.3.

## Default atual
- `~/.zcode/cli/config.json:89` → `"model": "default-minimax/minimax-m3"`
- Aponta para `opencode.ai/zen/go`, **NÃO** para `api.minimax.io/anthropic` (coding plan real)

## Subagents custom (12 arquivos em ~/.zcode/subagents/)
| Nome | model declarado |
|---|---|
| ceo-agent | "Gemini 3.5 Flash (High)" |
| cto-agent | "Gemini 3.5 Flash (High)" |
| cfo-agent, chro-agent, cio-agent, cmo-agent, coo-agent, cpo-agent, cro-agent, cso-agent, browser-automation-agent, redesim-helper-agent | "kimi-k2.6" |

**Observação:** strings `kimi-k2.6` e `Gemini 3.5 Flash (High)` provavelmente são display labels, não `providerId/modelId` honrados pelo app.

## Skills top-level (33 total)

### Nativas (14 dirs)
- browser-automation
- cfo-agent
- chro-agent
- cio-agent
- cmo-agent
- coo-agent
- cpo-agent
- cro-agent
- cso-agent
- cto-agent
- prompt-cartorio
- redesim-helper
- up-agent-corporation
- using-mavis-cross-session

### Symlinks (19)
- algorithmic-art → /Users/gustavoalmeida/.config/opencode/skills/algorithmic-art
- brand-guidelines → /Users/gustavoalmeida/.config/opencode/skills/brand-guidelines
- diagnose-why-work-stopped → /Users/gustavoalmeida/.claude/skills/diagnose-why-work-stopped
- frontend-design → /Users/gustavoalmeida/.config/opencode/skills/frontend-design
- imagegen → /Users/gustavoalmeida/.codex/skills/.system/imagegen
- kimi-webbridge → /Users/gustavoalmeida/.claude/skills/kimi-webbridge
- migrate-to-codex → /Users/gustavoalmeida/.codex/skills/migrate-to-codex
- openai-docs → /Users/gustavoalmeida/.codex/skills/.system/openai-docs
- paperclip → /Users/gustavoalmeida/.claude/skills/paperclip
- paperclip-converting-plans-to-tasks → /Users/gustavoalmeida/.claude/skills/paperclip-converting-plans-to-tasks
- paperclip-create-agent → /Users/gustavoalmeida/.claude/skills/paperclip-create-agent
- paperclip-create-plugin → /Users/gustavoalmeida/.claude/skills/paperclip-create-plugin
- paperclip-dev → /Users/gustavoalmeida/.claude/skills/paperclip-dev
- para-memory-files → /Users/gustavoalmeida/.claude/skills/para-memory-files
- plugin-creator → /Users/gustavoalmeida/.codex/skills/.system/plugin-creator
- skill-creator → /Users/gustavoalmeida/.codex/skills/.system/skill-creator
- skill-installer → /Users/gustavoalmeida/.codex/skills/.system/skill-installer
- terminal-bench-loop → /Users/gustavoalmeida/.claude/skills/terminal-bench-loop

## Plugins oficiais ativos (4 enabled, 2 disabled)
- enabled: android-emulator, ios-simulator, superpowers, restore-legacy-sessions
- disabled: document-skills, skill-creator

## MCP servers
- Plugin-scoped: android-emulator, ios-simulator (via .mcp.json nos plugins)
- User-level: chrome-bridge, udiapods-api (em ~/.zcode/mcp-servers/)

## Memória
- Global: ~/.zcode/memory/MEMORY.md (vazio)
- Projeto: .brain/memory/2026-06-25.md (1 arquivo, 12:46)
- Estrutura: docs/{chatwoot, evolution-api, n8n, redis, supabase}-quickref.md

## Quota MiniMax IO
[PENDENTE — confirmar com usuário antes de trocar default]

## Backups criados na Task 0.1
- `/Users/gustavoalmeida/.zcode/cli/config.json.bak.20260625-125226`
- `/Users/gustavoalmeida/.zcode/v2/config.json.bak.20260625-125226`
