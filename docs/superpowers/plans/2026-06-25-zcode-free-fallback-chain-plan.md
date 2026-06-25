# ZCode Free-Provider Fallback Chain — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provisionar os 4 provedores LLM free (`opencode-free`, `openrouter-free`, `groq-free`, `mistral-free`) como **rota alternativa** dentro do ZCode.app, criar uma skill de roteamento por criticidade, mapear skills/plugins aplicáveis, validar override de subagent, e persistir aprendizados — **sem mexer no projeto Cartorio** e **sem patchar o binário ZCode**.

**Architecture:** Configuração declarativa via JSON (`~/.zcode/v2/config.json`, `~/.zcode/cli/config.json`, `~/.zcode/subagents/*.json`) + nova skill user-level `zcode-fallback` que ensina o agente principal a rotear tarefas entre providers conforme criticidade (Modo A pago / Modo B free chain / Modo C override experimental). Memória em 2 níveis (global + projeto).

**Tech Stack:** ZCode.app v3.1.5 (Electron), Node.js, JSON config, Bash para testes de log, Markdown para docs/skills, Git para versionamento.

---

## File Structure

| Path | Tipo | Responsabilidade |
|---|---|---|
| `~/.zcode/cli/config.json` | modify | Trocar `"model"` para o provider correto do coding plan (somente se usuário confirmar quota ativa) |
| `~/.zcode/subagents/redesim-helper-agent.json` | modify (temporário) | Alvo do teste controlado de override de model |
| `~/.zcode/skills/zcode-fallback/SKILL.md` | create | Skill principal — ensina roteamento por criticidade |
| `~/.zcode/skills/zcode-fallback/references/provider-registry.md` | create | Tabela canônica de providers+models+ratelimits |
| `~/.zcode/skills/zcode-fallback/references/subagent-routing.md` | create | Como (não) confiar em override de model em subagent |
| `~/.zcode/memory/MEMORY.md` | create | Memória cross-session sobre ZCode |
| `.brain/memory/2026-06-25.md` | modify | Adicionar timeline desta sessão |
| `.brain/docs/skills-applicability-2026-06-25.md` | create | Mapa de skills aplicáveis (49 entradas) |
| `.brain/docs/audit-zcode-config-2026-06-25.md` | create | Relatório de auditoria inicial (read-only, não-destrutivo) |

---

## Fase 0 — Pré-flight e auditoria (read-only)

### Task 0.1: Sanity check do ambiente

**Files:** nenhum (somente leitura)

- [ ] **Step 1: Verificar que ZCode está instalado**

```bash
ls -la /Applications/ZCode.app/Contents/Info.plist
plutil -p /Applications/ZCode.app/Contents/Info.plist | grep -E "CFBundleShortVersionString|CFBundleVersion"
```
Expected: v3.1.5 e build ≥ 1966.

- [ ] **Step 2: Confirmar que os 4 provedores free estão enabled**

```bash
jq -r 'to_entries[] | select(.value.enabled==true) | "\(.key) \(.value.name) \(.value.options.baseURL)"' \
  ~/.zcode/v2/config.json
```
Expected output contém 7 linhas, incluindo as 4 com UUIDs:
- `15568793-...` → opencode-free
- `a84a18da-...` → openrouter-free
- `4ff49ce7-...` → groq-free
- `04873a4d-...` → mistral-free

- [ ] **Step 3: Verificar modelo default atual**

```bash
jq -r '.model' ~/.zcode/cli/config.json
```
Expected: `"default-minimax/minimax-m3"` (o default atual, que aponta para opencode.ai/zen/go).

- [ ] **Step 4: Backup da config atual**

```bash
cp ~/.zcode/cli/config.json ~/.zcode/cli/config.json.bak.$(date +%Y%m%d-%H%M%S)
cp ~/.zcode/v2/config.json ~/.zcode/v2/config.json.bak.$(date +%Y%m%d-%H%M%S)
ls -la ~/.zcode/cli/config.json.bak.* ~/.zcode/v2/config.json.bak.*
```
Expected: 2 arquivos `.bak.<timestamp>` criados.

- [ ] **Step 5: Commit (sem mudanças, marca início da fase)**

```bash
cd /Users/gustavoalmeida/projetos/Cartorio
git checkout -b feat/zcode-fallback-chain
echo "# ZCode Fallback Chain — sessão iniciada $(date +%Y-%m-%d)" > /tmp/zcode-session-start.md
```

### Task 0.2: Relatório de auditoria (read-only)

**Files:**
- Create: `.brain/docs/audit-zcode-config-2026-06-25.md`

- [ ] **Step 1: Escrever relatório de auditoria**

Criar `.brain/docs/audit-zcode-config-2026-06-25.md` com este conteúdo exato:

```markdown
# Auditoria ZCode — 2026-06-25

## Ambiente
- **ZCode.app**: /Applications/ZCode.app (v3.1.5, build 1966)
- **Plataforma**: macOS Darwin 25.5.0 arm64
- **Working dir**: /Users/gustavoalmeida/projetos/Cartorio
- **Git branch**: feat/zcode-fallback-chain (criada nesta sessão)

## Providers ativos (enabled em v2/config.json)
| ID | Nome | Kind | baseURL |
|---|---|---|---|
| default-minimax | opencode-go | anthropic | https://opencode.ai/zen/go |
| c997ca58-cfda-4c2f-8550-69830972bad7 | minimax-coding-plan | anthropic | https://api.minimax.io/anthropic |
| a78c8877-8acd-42db-a21e-e1a4f38e57d3 | kimi | openai-compatible | https://api.kimi.com/coding/v1 |
| 15568793-5414-4c84-b794-ba4572e0412e | opencode-free | openai-compatible | https://opencode.ai/zen/v1 |
| a84a18da-ac47-43d1-a250-2bfdf49cf4a3 | openrouter-free | openai-compatible | https://openrouter.ai/api/v1 |
| 4ff49ce7-9523-462f-89c2-2ba8b55042d8 | groq-free | openai-compatible | https://api.groq.com/openai/v1 |
| 04873a4d-dba3-43c1-9840-22d9eb7ada4b | mistral-free | openai-compatible | https://api.mistral.ai/v1 |

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

## Skills top-level (33 em ~/.zcode/skills/)
[preencher a partir de `ls -la ~/.zcode/skills/`]

## Plugins oficiais ativos (3 enabled, 2 disabled)
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
```

- [ ] **Step 2: Preencher a seção "Skills top-level" com a listagem real**

```bash
ls -1 ~/.zcode/skills/ | tee /tmp/zcode-skills-list.txt
# copiar saída e colar na seção "Skills top-level" do audit doc
```

- [ ] **Step 3: Commit**

```bash
git add .brain/docs/audit-zcode-config-2026-06-25.md
git -c user.name='Cartorio CI' -c user.email='ci@cartorio.local' \
  commit -m "docs(audit): ZCode config snapshot 2026-06-25"
```

---

## Fase 1 — Memória global cross-session

### Task 1.1: Criar ~/.zcode/memory/MEMORY.md

**Files:**
- Create: `~/.zcode/memory/MEMORY.md`

- [ ] **Step 1: Criar arquivo com seções iniciais**

```bash
mkdir -p ~/.zcode/memory
cat > ~/.zcode/memory/MEMORY.md <<'EOF'
# ZCode Memory — Cross-Session Lessons

> Lições duradouras sobre o ambiente ZCode.app. Atualizar quando descobrir algo novo que sobreviva à sessão atual.

---

## Provider configuration

### 2026-06-25 — Bug: default-minimax ≠ minimax-coding-plan
- O provider ID `default-minimax` em `~/.zcode/v2/config.json` aponta para `https://opencode.ai/zen/go`, **NÃO** para `https://api.minimax.io/anthropic`.
- O coding plan real (MiniMax IO) está no UUID `c997ca58-cfda-4c2f-8550-69830972bad7` (`minimax-coding-plan`), mas hoje está **não-selecionado** como default.
- Implicação: se o usuário tem quota MiniMax IO mas o app está em `default-minimax/minimax-m3`, o app está usando proxy opencode-go (não-official, sem garantia de SLA).
- **Lição**: ao diagnosticar custos, sempre cruzar `cli/config.json:model` com `v2/config.json:providers[name=default-minimax].options.baseURL`.

### 2026-06-25 — Free tiers disponíveis e suas armadilhas
| Provider | Modelos | Rate limit (aprox.) | Tool support |
|---|---|---|---|
| opencode-free | deepseek-v4-flash-free, mimo-v2.5-free, nemotron-3-ultra-free, north-mini-code-free | Generoso (1M ctx) | Incerto |
| openrouter-free | nvidia/nemotron-3-ultra-550b-a55b:free, poolside/laguna-m.1:free, cohere/north-mini-code:free | ~20 req/min | Incerto |
| groq-free | groq/compound, openai/gpt-oss-120b | ~30 req/min | Incerto |
| mistral-free | devstral-small-latest, mistral-large-latest, devstral-latest | Limitado | Incerto |

- **Lição**: free tiers são kind `openai-compatible` (chat/completions). Apps que dependem de tool-use estilo Anthropic (`tool_choice: "any"`, `parallel_tool_calls: true`) podem quebrar.

---

## Subagent model override

### 2026-06-25 — Campo `model` em ~/.zcode/subagents/*.json é display label
- 12 arquivos de subagent customizado usam campo `model` com strings tipo `"kimi-k2.6"` e `"Gemini 3.5 Flash (High)"`.
- Nenhuma dessas strings bate com `providerId/modelId` em `v2/config.json`.
- Bundle do app (`app.asar`) ofuscado impede confirmar 100% como a string é resolvida.
- Log de 2026-06-25 mostra subagents rodando em providers diferentes do parent, mas inconclusivo se é por override do JSON ou por mudança de model no parent no meio da sessão.
- **Lição**: NÃO contar com override de model em subagent como mecanismo de routing na v1. Fazer routing na camada do agente principal.

---

## Workarounds para reduzir cota MiniMax IO

### 2026-06-25 — Skill `zcode-fallback` (criada nesta sessão)
- Local: `~/.zcode/skills/zcode-fallback/SKILL.md`
- Estratégia: classificar tarefa por criticidade e rotear para provider adequado (Modo A/B/C do spec).

EOF
ls -la ~/.zcode/memory/MEMORY.md
```

- [ ] **Step 2: Verificar tamanho**

```bash
wc -l ~/.zcode/memory/MEMORY.md
```
Expected: ≥ 50 linhas.

### Task 1.2: Adicionar entradas em .brain/memory/2026-06-25.md

**Files:**
- Modify: `.brain/memory/2026-06-25.md`

- [ ] **Step 1: Anexar timeline desta sessão**

Ler o arquivo atual primeiro:
```bash
cat /Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-06-25.md
```

Depois anexar (substituir `HH:MM` pela hora atual `date +%H:%M`):
```bash
TS=$(date +%H:%M)
cat >> /Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-06-25.md <<EOF

[$TS] docs(specs): spec ZCode fallback chain aprovado, commit b0edc8f
[$TS] feat(audit): auditoria ZCode config (.brain/docs/audit-zcode-config-2026-06-25.md)
[$TS] feat(memory): ~/.zcode/memory/MEMORY.md criado com 3 lições iniciais
EOF
tail -10 /Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-06-25.md
```

- [ ] **Step 2: Commit**

```bash
git add .brain/memory/2026-06-25.md
git -c user.name='Cartorio CI' -c user.email='ci@cartorio.local' \
  commit -m "chore(memory): timeline ZCode fallback chain session 2026-06-25"
```

---

## Fase 2 — Skill `zcode-fallback`

### Task 2.1: Criar SKILL.md principal

**Files:**
- Create: `~/.zcode/skills/zcode-fallback/SKILL.md`

- [ ] **Step 1: Criar diretório**

```bash
mkdir -p ~/.zcode/skills/zcode-fallback/references
```

- [ ] **Step 2: Escrever SKILL.md**

Criar `~/.zcode/skills/zcode-fallback/SKILL.md` com este conteúdo exato:

````markdown
---
name: zcode-fallback
description: Use when you need to choose which ZCode provider/model to use for a task — guides routing between paid (minimax-coding-plan) and free tiers (opencode/openrouter/groq/mistral-free) based on task criticality, with explicit fallback chain.
---

# ZCode Provider Routing

This skill teaches the main agent how to choose a ZCode provider/model based on **task criticality**, to reduce consumption of the paid MiniMax IO coding plan.

## Routing Decision

For every task, classify into one of three modes **before** invoking subagents or executing heavy operations.

| Mode | When | Provider chain | Cost |
|---|---|---|---|
| **A — Paid** | Critical: destructive edits, architecture decisions, long reasoning, sensitive data (LGPD/PII) | `minimax-coding-plan/minimax-m3` | Quota MiniMax IO |
| **B — Free chain** | Exploratory: reading files, grep, classification, summarization, docstring generation, simple refactors | `groq-free/openai/gpt-oss-120b` → `mistral-free/devstral-small-latest` → `openrouter-free/cohere/north-mini-code:free` → `opencode-free/north-mini-code-free` | Free |
| **C — Override experimental** | Isolated sub-task where override risk is acceptable | Edit `~/.zcode/subagents/<name>.json` field `model` to `providerId/modelId`, dispatch via Agent tool, **revert immediately** | Free if works; quota if doesn't |

## Decision Heuristics

Ask these questions in order:

1. **Does the task touch production data or destructive operations?**
   - YES → Mode A (paid)
   - NO → continue

2. **Does the task require multi-step reasoning or generate code that will be committed?**
   - YES (large refactor, new module, API design) → Mode A
   - NO (read, classify, summarize) → Mode B

3. **Is the task isolated enough that a subagent override is worth trying?**
   - YES (single self-contained question, low blast radius) → Mode C
   - NO → Mode B

## How to switch provider

### Switch the default for the whole session (Mode A)
- GUI: Settings → Model Provider → pick `minimax-coding-plan` → `minimax-m3`
- CLI (advanced, app must be closed): edit `~/.zcode/cli/config.json`, set `"model": "c997ca58-cfda-4c2f-8550-69830972bad7/minimax-m3"`

### Use Mode B (free chain) without changing default
- The agent runs in the **current** default provider for the main thread.
- For sub-tasks, dispatch via `Agent` tool with `subagent_type: "general-purpose"` or `Explore`.
- The subagent will inherit the parent provider — **which may not be free**.
- **To actually get free routing**, the parent session must already be in a free provider.

### Use Mode C (override) — experimental
See `references/subagent-routing.md` for the controlled test procedure.

## Provider Registry

For the canonical table of providers, models, rate limits, and tool support, see:
- `references/provider-registry.md`

## When NOT to use this skill

- If the task requires the strongest available model regardless of cost (e.g., novel algorithm design, complex debugging in unfamiliar code). Just use Mode A.
- If quota MiniMax IO is unknown or depleted. Ask the user first.
- If tool-use is critical (function calling, parallel tools). Free tiers may not support it well.

## Validation

After applying this skill, verify by checking:
1. Log file: `tail ~/.zcode/cli/log/zcode-$(date +%Y-%m-%d).jsonl | grep model.network.completed`
2. Confirm `providerId` and `modelId` match what you intended.
3. If subagent was used: confirm `querySource: "subagent"` event also matches.

## Anti-patterns

- ❌ Switching provider mid-task without recording the switch in memory
- ❌ Using Mode B for tasks that need guaranteed tool support
- ❌ Using Mode C without snapshot+revert (risk of leftover override)
- ❌ Assuming the `model` field in `~/.zcode/subagents/*.json` is honored (it's display-only until proven otherwise)
````

- [ ] **Step 3: Verificar criação**

```bash
wc -l ~/.zcode/skills/zcode-fallback/SKILL.md
head -5 ~/.zcode/skills/zcode-fallback/SKILL.md
```
Expected: ~120 linhas, primeiras linhas são o frontmatter YAML.

### Task 2.2: Criar provider-registry.md

**Files:**
- Create: `~/.zcode/skills/zcode-fallback/references/provider-registry.md`

- [ ] **Step 1: Escrever registry canônico**

Criar `~/.zcode/skills/zcode-fallback/references/provider-registry.md` com:

````markdown
# Provider Registry — ZCode v3.1.5

> Última atualização: 2026-06-25. Atualizar manualmente quando providers mudarem.

## Active providers (enabled em ~/.zcode/v2/config.json)

### Pago
| Provider ID | Nome | Kind | baseURL | Models | Notas |
|---|---|---|---|---|---|
| `c997ca58-cfda-4c2f-8550-69830972bad7` | minimax-coding-plan | anthropic | `https://api.minimax.io/anthropic` | `minimax-m3` | Coding plan MiniMax IO. **Usar para tarefas críticas.** |

### Proxy opencode-go
| Provider ID | Nome | Kind | baseURL | Models | Notas |
|---|---|---|---|---|---|
| `default-minimax` | opencode-go | anthropic | `https://opencode.ai/zen/go` | `minimax-m3` | Default atual. **NÃO é o coding plan MiniMax IO**, apesar do nome enganoso. |

### OpenAI-compatible (free)
| Provider ID | Nome | Kind | baseURL | Models | Context | Notas |
|---|---|---|---|---|---|---|
| `15568793-5414-4c84-b794-ba4572e0412e` | opencode-free | openai-compatible | `https://opencode.ai/zen/v1` | `deepseek-v4-flash-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`, `north-mini-code-free` | 1M (256K p/ `north`) | 4 modelos, generoso em contexto |
| `a84a18da-ac47-43d1-a250-2bfdf49cf4a3` | openrouter-free | openai-compatible | `https://openrouter.ai/api/v1` | `nvidia/nemotron-3-ultra-550b-a55b:free`, `poolside/laguna-m.1:free`, `cohere/north-mini-code:free` | 1M / 262K / 256K | Rate limit ~20 req/min |
| `4ff49ce7-9523-462f-89c2-2ba8b55042d8` | groq-free | openai-compatible | `https://api.groq.com/openai/v1` | `groq/compound`, `openai/gpt-oss-120b` | 131.1K | Rate limit ~30 req/min. **Mais rápido.** |
| `04873a4d-dba3-43c1-9840-22d9eb7ada4b` | mistral-free | openai-compatible | `https://api.mistral.ai/v1` | `devstral-small-latest`, `mistral-large-latest`, `devstral-latest` | 256K | Devstral é bom p/ código. |

### OpenAI-compatible (pago alternativo)
| Provider ID | Nome | Kind | baseURL | Models | Notas |
|---|---|---|---|---|---|
| `a78c8877-8acd-42db-a21e-e1a4f38e57d3` | kimi | openai-compatible | `https://api.kimi.com/coding/v1` | `kimi-k2.7` | **Nota**: subagents JSONs referenciam `kimi-k2.6` (provavelmente display label desatualizado) |

## Free-tier fallback chain (Modo B)

Ordem recomendada para minimizar latência e maximizar qualidade:

1. **`groq-free/openai/gpt-oss-120b`** — mais rápido, contexto OK para tarefas curtas
2. **`mistral-free/devstral-small-latest`** — bom para tarefas com código
3. **`openrouter-free/cohere/north-mini-code:free`** — backup com contexto grande
4. **`opencode-free/north-mini-code-free`** — último recurso

## Como descobrir providers novos

```bash
# Listar todos os providers enabled:
jq -r 'to_entries[] | select(.value.enabled==true) | "\(.key) \(.value.name)"' \
  ~/.zcode/v2/config.json

# Listar modelos de um provider específico:
jq -r '.<uuid>.models | keys[]' ~/.zcode/v2/config.json
```

## Como testar conectividade de um provider

```bash
curl -sS -X POST "https://api.groq.com/openai/v1/chat/completions" \
  -H "Authorization: Bearer $(jq -r '.["4ff49ce7-9523-462f-89c2-2ba8b55042d8"].options.apiKey' ~/.zcode/v2/config.json)" \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-oss-120b","messages":[{"role":"user","content":"ping"}],"max_tokens":10}'
```
Substituir o UUID e a URL conforme o provider alvo.
````

- [ ] **Step 2: Verificar**

```bash
wc -l ~/.zcode/skills/zcode-fallback/references/provider-registry.md
```

### Task 2.3: Criar subagent-routing.md

**Files:**
- Create: `~/.zcode/skills/zcode-fallback/references/subagent-routing.md`

- [ ] **Step 1: Escrever guia de override experimental**

Criar `~/.zcode/skills/zcode-fallback/references/subagent-routing.md` com:

````markdown
# Subagent Model Override — Modo C (experimental)

> **AVISO**: este modo é **experimental**. Há evidência forte de que o campo `model` em `~/.zcode/subagents/*.json` é uma string de display, não um identificador honrado. Use apenas com snapshot + revert.

## Background

Hoje (2026-06-25), os 12 subagents custom em `~/.zcode/subagents/*.json` declaram campo `model` com valores que **não batem** com nenhum `providerId/modelId` em `~/.zcode/v2/config.json`:

- `"kimi-k2.6"` (10 arquivos) — provider `kimi` tem `kimi-k2.7`, não `kimi-k2.6`
- `"Gemini 3.5 Flash (High)"` (2 arquivos) — Gemini não está em lugar nenhum

O bundle do ZCode.app (`app.asar`) está ofuscado, então não dá para confirmar 100% como a string é resolvida. **Hipótese mais provável**: display label, não override.

## Controlled Test Procedure

**Pré-condições**:
- Sessão ZCode aberta em `c997ca58-cfda-.../minimax-m3` (parent atual) **OU** em qualquer provider pago.
- Subagent alvo: `redesim-helper-agent.json` (baixo risco, isolado).

**Passo a passo**:

```bash
# 1. Snapshot
cp ~/.zcode/subagents/redesim-helper-agent.json \
   /tmp/redesim-helper-agent.json.bak

# 2. Editar campo model para string providerId/modelId válida
#    (groq-free/openai/gpt-oss-120b — confirmado disponível)
jq '.model = "4ff49ce7-9523-462f-89c2-2ba8b55042d8/openai/gpt-oss-120b"' \
   ~/.zcode/subagents/redesim-helper-agent.json > /tmp/r.json && \
   mv /tmp/r.json ~/.zcode/subagents/redesim-helper-agent.json

# 3. (Opcional) Restart do ZCode para invalidar cache in-memory
#    Caso não faça restart, o teste pode pegar cache stale.

# 4. Despachar subagent (na sessão atual)
#    Ex: "Use o redesim-helper-agent para listar os endpoints da API X."

# 5. Observar log em tempo real
tail -f ~/.zcode/cli/log/zcode-$(date +%Y-%m-%d).jsonl | \
  grep -E '"querySource":"subagent"' | head -10

# 6. Verificar se o providerId mudou
grep '"model.network.completed"' ~/.zcode/cli/log/zcode-$(date +%Y-%m-%d).jsonl | \
  jq -r 'select(.context.querySource=="subagent") | "\(.context.providerId) \(.context.modelId)"' | tail -5
```

## Critérios de resultado

| Resultado | providerId observado | modelId observado | Interpretação |
|---|---|---|---|
| Override funciona | `4ff49ce7-...` (groq-free) | `openai/gpt-oss-120b` | **Sucesso** — campo `model` é honrado |
| Override NÃO funciona | `c997ca58-...` (minimax) | `minimax-m3` | Display-only — não confiar |

## Revert (SEMPRE executar)

```bash
# Reverter imediatamente após o teste
cp /tmp/redesim-helper-agent.json.bak \
   ~/.zcode/subagents/redesim-helper-agent.json
diff /tmp/redesim-helper-agent.json.bak \
     ~/.zcode/subagents/redesim-helper-agent.json
# (diff deve ser vazio)
```

## Riscos

- **Cache stale**: app pode ter o JSON em memória; editar e despachar imediatamente pode não refletir.
- **Quota do parent**: se o subagent falhar e cair no parent, pode gastar quota paga.
- **Tool calls incompatíveis**: se o subagent usa tools estilo Anthropic, free tier pode quebrar.
- **Persistência**: alteração fica até o próximo revert manual.

## Workaround alternativo (recomendado)

Em vez de override por JSON, **dispatch via Agent tool** com `subagent_type` apontando para um subagent existente (sem mexer no JSON). O subagent herda o provider do parent — então, para routing, **troque o parent antes de despachar**:

1. GUI Settings → Model Provider → `groq-free` → `openai/gpt-oss-120b`
2. Despachar subagent → ele herda groq-free
3. Voltar o parent para o provider original

Esse workaround é mais confiável que override por JSON.
````

- [ ] **Step 2: Verificar**

```bash
ls -la ~/.zcode/skills/zcode-fallback/
ls -la ~/.zcode/skills/zcode-fallback/references/
```

Expected: 3 arquivos (SKILL.md, references/provider-registry.md, references/subagent-routing.md).

### Task 2.4: Validar que a skill carrega

**Files:** nenhum

- [ ] **Step 1: Reiniciar o ZCode**

Fechar e abrir o app `/Applications/ZCode.app`. (Não tem CLI; tem que ser pela GUI ou via `killall ZCode && open /Applications/ZCode.app`.)

- [ ] **Step 2: Verificar que a skill aparece**

Numa nova sessão, perguntar ao agente:
> "Quais skills você tem disponíveis para roteamento de provider?"

Resposta esperada: a skill `zcode-fallback` deve estar listada.

- [ ] **Step 3: Confirmar que as referências linkam corretamente**

Peder ao agente:
> "Use a skill `zcode-fallback` e me diga o que está em `references/provider-registry.md`"

Resposta esperada: o agente deve conseguir ler a referência e citar conteúdo dela.

- [ ] **Step 4: Commit (registro, não código)**

```bash
cd /Users/gustavoalmeida/projetos/Cartorio
TS=$(date +%H:%M)
cat >> .brain/memory/2026-06-25.md <<EOF
[$TS] feat(skill): zcode-fallback criada (SKILL.md + 2 referências)
EOF
git add .brain/memory/2026-06-25.md
git -c user.name='Cartorio CI' -c user.email='ci@cartorio.local' \
  commit -m "chore(memory): log skill zcode-fallback criada"
```

---

## Fase 3 — Mapa de skills aplicáveis

### Task 3.1: Inventário completo de skills

**Files:**
- Modify: `.brain/docs/audit-zcode-config-2026-06-25.md`

- [ ] **Step 1: Coletar inventário**

```bash
# Skills top-level
ls -1 ~/.zcode/skills/ > /tmp/skills-toplevel.txt
wc -l /tmp/skills-toplevel.txt

# Skills em plugins oficiais (enabled)
find ~/.zcode/cli/plugins/cache/zcode-plugins-official -name "SKILL.md" \
  -path "*superpowers*/*" -o -name "SKILL.md" -path "*android-emulator*/*" \
  -o -name "SKILL.md" -path "*ios-simulator*/*" \
  -o -name "SKILL.md" -path "*document-skills*/*" \
  -o -name "SKILL.md" -path "*skill-creator*/*" 2>/dev/null > /tmp/skills-plugin.txt
wc -l /tmp/skills-plugin.txt
```

- [ ] **Step 2: Atualizar audit doc com inventário**

Acrescentar ao final de `.brain/docs/audit-zcode-config-2026-06-25.md`:

```bash
cat >> /Users/gustavoalmeida/projetos/Cartorio/.brain/docs/audit-zcode-config-2026-06-25.md <<EOF

## Skills inventory (snapshot 2026-06-25)
- Top-level: $(wc -l < /tmp/skills-toplevel.txt) entries (ver /tmp/skills-toplevel.txt)
- Em plugins: $(wc -l < /tmp/skills-plugin.txt) entries (ver /tmp/skills-plugin.txt)
EOF
```

### Task 3.2: Tabela de aplicabilidade

**Files:**
- Create: `.brain/docs/skills-applicability-2026-06-25.md`

- [ ] **Step 1: Escrever tabela**

Criar `.brain/docs/skills-applicability-2026-06-25.md`:

````markdown
# Skills Applicability Map — 2026-06-25

> Decisão por skill: **A** = aplicável agora (uso imediato nesta sessão), **N** = não aplicável, **D** = adiar (próximo sub-projeto).

## Top-level skills (~33)

| Skill | Flag | Justificativa |
|---|---|---|
| `zcode-fallback` (recém-criada) | **A** | Routing de provider — usada imediatamente |
| `brainstorming` | **A** | Em uso nesta sessão |
| `writing-plans` | **A** | Em uso nesta sessão |
| `using-superpowers` | **A** | Em uso nesta sessão |
| `verification-before-completion` | **A** | Verificar resultados antes de declarar done |
| `systematic-debugging` | **A** | Quando bater bug no ZCode/MiniMax |
| `test-driven-development` | **N** | ZCode é config JSON, não código |
| `dispatching-parallel-agents` | **A** | Despachar subagents para free tier |
| `subagent-driven-development` | **A** | Estrutura de execução do plano |
| `executing-plans` | **A** | Modo alternativo de execução |
| `using-git-worktrees` | **N** | Trabalho no repo Cartorio, não em branch isolada crítica |
| `finishing-a-development-branch` | **N** | Não estamos finalizando branch |
| `requesting-code-review` | **N** | Não temos reviewer externo |
| `receiving-code-review` | **N** | Não temos reviewer externo |
| `skill-creator` | **A** | Usamos para criar `zcode-fallback` |
| `skill-installer` | **N** | Sem necessidade agora |
| `plugin-creator` | **D** | Próximo sub-projeto (se criar plugin ZCode) |
| `up-agent-corporation` | **D** | C-levels — para trabalho estratégico no Cartorio |
| `cfo-agent`, `chro-agent`, `cio-agent`, `cmo-agent`, `coo-agent`, `cpo-agent`, `cro-agent`, `cso-agent`, `cto-agent`, `ceo-agent` | **D** | C-levels — para estratégia corporativa no Cartorio |
| `prompt-cartorio` | **A** | Provavelmente útil para contexto do Cartorio |
| `redesim-helper` | **A** | Útil p/ tarefas Redesim no Cartorio |
| `browser-automation` | **A** | MCP Chrome já disponível |
| `frontend-design` | **D** | Quando mexer em UI do Cartorio |
| `paperclip*` (5 variantes) | **N** | Não relacionado ao ZCode |
| `terminal-bench-loop` | **N** | Benchmarking, não pertinente |
| `migrate-to-codex`, `kimi-webbridge`, `openai-docs`, `imagegen`, `algorithmic-art`, `brand-guidelines`, `diagnose-why-work-stopped` | **N** | Skills de outros runtimes |
| `para-memory-files` | **A** | Formato de memória (`.brain/`) |
| `restore-legacy-sessions` (plugin) | **N** | Recuperação de sessões |

## Skills em plugins (superpowers, ~14)

Todas as 14 do superpowers já marcadas acima (brainstorming, writing-plans, etc.).

## MCP servers ativos

| MCP | Flag | Uso |
|---|---|---|
| `android-emulator` | **A** | Já disponível, usar para debug Android do Cartorio |
| `ios-simulator` | **A** | Já disponível, usar para debug iOS do Cartorio |
| `chrome-bridge` (user-level) | **A** | Browser automation |
| `udiapods-api` (user-level) | **D** | Específico do UdiaPods |

## Resumo
- **Aplicáveis agora**: ~14 skills + 3 MCPs
- **Adiar**: ~12 skills (C-levels, frontend, plugin creator)
- **Não aplicáveis**: ~15 skills (TDD/code-review/legacy)
EOF

- [ ] **Step 2: Commit**

```bash
git add .brain/docs/skills-applicability-2026-06-25.md .brain/docs/audit-zcode-config-2026-06-25.md
git -c user.name='Cartorio CI' -c user.email='ci@cartorio.local' \
  commit -m "docs(skills): applicability map 2026-06-25"
```

---

## Fase 4 — Validação empírica do override (Modo C)

### Task 4.1: Executar teste controlado

**Files:**
- Modify (temporário): `~/.zcode/subagents/redesim-helper-agent.json`

- [ ] **Step 1: Confirmar pré-condições**

```bash
# Parent deve estar em provider pago (não free)
jq -r '.model' ~/.zcode/cli/config.json
# Esperado: "default-minimax/minimax-m3" (pago via opencode-go)

# Backup
cp ~/.zcode/subagents/redesim-helper-agent.json \
   /tmp/redesim-helper-agent.json.bak.$(date +%Y%m%d-%H%M%S)
ls -la /tmp/redesim-helper-agent.json.bak.*
```

- [ ] **Step 2: Aplicar override**

```bash
# Editar campo model
jq '.model = "4ff49ce7-9523-462f-89c2-2ba8b55042d8/openai/gpt-oss-120b"' \
   ~/.zcode/subagents/redesim-helper-agent.json > /tmp/r.json
mv /tmp/r.json ~/.zcode/subagents/redesim-helper-agent.json

# Verificar
jq '.model' ~/.zcode/subagents/redesim-helper-agent.json
```
Expected: `"4ff49ce7-9523-462f-89c2-2ba8b55042d8/openai/gpt-oss-120b"`.

- [ ] **Step 3: Despachar subagent**

Numa nova mensagem nesta sessão, pedir:
> "Use o `redesim-helper-agent` para me listar as 5 primeiras linhas do arquivo `/etc/hosts`."

OU, se preferir, abrir nova sessão ZCode para isolar.

- [ ] **Step 4: Observar log**

```bash
tail -100 ~/.zcode/cli/log/zcode-$(date +%Y-%m-%d).jsonl | \
  jq -r 'select(.event=="model.network.completed") | "\(.context.querySource) \(.context.providerId) \(.context.modelId) \(.context.baseURL)"' | tail -10
```

- [ ] **Step 5: Classificar resultado**

| providerId observado | Resultado |
|---|---|
| `4ff49ce7-9523-462f-89c2-2ba8b55042d8` | ✅ Override funciona |
| `c997ca58-cfda-4c2f-8550-69830972bad7` | ❌ Display-only (parent herda) |
| `default-minimax` | ❌ Display-only (parent via opencode-go) |

### Task 4.2: Reverter e documentar

- [ ] **Step 1: Reverter (sempre)**

```bash
cp /tmp/redesim-helper-agent.json.bak.* ~/.zcode/subagents/redesim-helper-agent.json
# (pegar o .bak mais recente)
diff /tmp/redesim-helper-agent.json.bak.* ~/.zcode/subagents/redesim-helper-agent.json
# Esperado: diff vazio
jq '.model' ~/.zcode/subagents/redesim-helper-agent.json
# Esperado: "kimi-k2.6" (estado original)
```

- [ ] **Step 2: Documentar resultado em MEMORY.md**

Adicionar seção em `~/.zcode/memory/MEMORY.md`:

```bash
cat >> ~/.zcode/memory/MEMORY.md <<'EOF'

### 2026-06-25 — Teste empírico de override de subagent
- Subagent testado: `redesim-helper-agent.json`
- Mudança: campo `model` para `4ff49ce7-9523-462f-89c2-2ba8b55042d8/openai/gpt-oss-120b` (groq-free)
- Parent provider: `default-minimax/minimax-m3` (opencode-go)
- **Resultado**: [PREENCHER APÓS TESTE — ✅ funciona ou ❌ display-only]
- providerId observado: [PREENCHER]
- modelId observado: [PREENCHER]

EOF
```

- [ ] **Step 3: Commit timeline**

```bash
TS=$(date +%H:%M)
cat >> /Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-06-25.md <<EOF

[$TS] test(override): subagent model override testado, resultado: [PREENCHER]
EOF
git add .brain/memory/2026-06-25.md
git -c user.name='Cartorio CI' -c user.email='ci@cartorio.local' \
  commit -m "test(override): documented empirical subagent model override result"
```

---

## Fase 5 — Reconfiguração do default (CONDICIONAL)

> ⚠️ **Esta fase só executa se o usuário confirmar quota MiniMax IO ativa.**

### Task 5.1: Trocar default para coding plan real

**Files:**
- Modify: `~/.zcode/cli/config.json`

- [ ] **Step 1: Confirmar quota com usuário**

Perguntar: "Você tem quota MiniMax IO ativa hoje? (S/N)"

Se **NÃO**: pular esta fase e manter `default-minimax/minimax-m3`.
Se **SIM**: continuar.

- [ ] **Step 2: Backup adicional**

```bash
cp ~/.zcode/cli/config.json ~/.zcode/cli/config.json.bak.pre-default-switch
```

- [ ] **Step 3: Trocar model**

```bash
jq '.model = "c997ca58-cfda-4c2f-8550-69830972bad7/minimax-m3"' \
   ~/.zcode/cli/config.json > /tmp/cli-config.json.new
mv /tmp/cli-config.json.new ~/.zcode/cli/config.json
jq -r '.model' ~/.zcode/cli/config.json
```
Expected: `"c997ca58-cfda-4c2f-8550-69830972bad7/minimax-m3"`.

- [ ] **Step 4: Fechar ZCode e reabrir**

```bash
killall ZCode 2>/dev/null
sleep 2
open /Applications/ZCode.app
```

- [ ] **Step 5: Verificar que nova sessão usa o provider correto**

Numa nova sessão, fazer uma pergunta trivial e observar o log:
```bash
tail -50 ~/.zcode/cli/log/zcode-$(date +%Y-%m-%d).jsonl | \
  jq -r 'select(.event=="model.network.completed") | "\(.context.providerId) \(.context.modelId) \(.context.baseURL)"' | tail -3
```
Expected: `c997ca58-...` `minimax-m3` `https://api.minimax.io/anthropic`.

- [ ] **Step 6: Rollback se quebrou**

Se a sessão não responde ou dá erro de auth:
```bash
killall ZCode 2>/dev/null
cp ~/.zcode/cli/config.json.bak.pre-default-switch ~/.zcode/cli/config.json
open /Applications/ZCode.app
```

- [ ] **Step 7: Commit timeline**

```bash
TS=$(date +%H:%M)
cat >> /Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-06-25.md <<EOF

[$TS] chore(config): default trocado para minimax-coding-plan (ou revertido)
EOF
git add .brain/memory/2026-06-25.md
git -c user.name='Cartorio CI' -c user.email='ci@cartorio.local' \
  commit -m "chore(config): ZCode default model switched to coding plan"
```

---

## Fase 6 — Cleanup e fechamento

### Task 6.1: Branch e PR (ou merge direto)

- [ ] **Step 1: Verificar estado do repo**

```bash
cd /Users/gustavoalmeida/projetos/Cartorio
git status
git log --oneline -10
```

- [ ] **Step 2: Decidir destino**

- Se tudo OK e usuário confirmar: `git checkout master && git merge feat/zcode-fallback-chain --no-ff -m "merge: ZCode free-fallback chain spec + plan"`
- Caso contrário: deixar na branch para revisão.

- [ ] **Step 3: Push (se houver remote)**

```bash
git remote -v
# Se houver remote:
# git push origin feat/zcode-fallback-chain
# ou criar PR:
# gh pr create --base master --head feat/zcode-fallback-chain --title "ZCode free-fallback chain" --body "..."
```

### Task 6.2: Memória final

- [ ] **Step 1: Adicionar lições aprendidas em MEMORY.md**

```bash
cat >> ~/.zcode/memory/MEMORY.md <<'EOF'

### 2026-06-25 — Workflow para criar skill no ZCode
- Path: `~/.zcode/skills/<skill-name>/SKILL.md`
- Frontmatter YAML: `name` e `description` obrigatórios
- Subdir `references/` carregado automaticamente
- Não precisa reiniciar app para criar a skill, mas precisa reiniciar para carregá-la em nova sessão

### 2026-06-25 — Backup antes de mexer em config do ZCode
- Sempre `cp ~/.zcode/cli/config.json ~/.zcode/cli/config.json.bak.<timestamp>`
- E `cp ~/.zcode/v2/config.json ~/.zcode/v2/config.json.bak.<timestamp>`
- Sem undo nativo no app.
EOF
```

- [ ] **Step 2: Commit final**

```bash
TS=$(date +%H:%M)
cat >> /Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-06-25.md <<EOF

[$TS] chore(close): ZCode fallback chain plan executado, fase 0-4 completas
EOF
git add .brain/memory/2026-06-25.md
git -c user.name='Cartorio CI' -c user.email='ci@cartorio.local' \
  commit -m "chore(close): ZCode fallback chain session wrap-up"
```

---

## Critérios de aceitação (final)

| # | Critério | Como verificar |
|---|---|---|
| 1 | Default correto do coding plan **OU** decisão consciente de manter o errado, documentada | `jq -r '.model' ~/.zcode/cli/config.json` + log em `.brain/memory/` |
| 2 | Skill `zcode-fallback` existe e carrega | `ls ~/.zcode/skills/zcode-fallback/SKILL.md` + reload do app |
| 3 | `~/.zcode/memory/MEMORY.md` tem ≥ 3 entradas | `grep -c '^### ' ~/.zcode/memory/MEMORY.md` ≥ 3 |
| 4 | `.brain/docs/skills-applicability-2026-06-25.md` lista ~49 skills | `wc -l` razoável, todas com flag A/N/D |
| 5 | Nenhuma quebra na sessão | Próxima chamada LLM no log funciona |
| 6 | Teste de override documentado (✅ ou ❌) | Seção em `MEMORY.md` preenchida |
| 7 | Branch `feat/zcode-fallback-chain` mergeada em master | `git log master --oneline -5` mostra commits |

## Self-review do plano

- **Spec coverage**: §3-9 do spec mapeados para Fases 0-6. Cobertura completa.
- **Placeholder scan**: sem TBDs no código. "PREENCHER APÓS TESTE" marcado claramente onde o usuário precisa completar empíricamente.
- **Type consistency**: UUIDs dos providers são usados consistentemente (`c997ca58-...`, `4ff49ce7-...`, etc.).
- **Riscos**: cobertos em §6 do spec e reiterados nos passos de revert em cada fase destrutiva.
