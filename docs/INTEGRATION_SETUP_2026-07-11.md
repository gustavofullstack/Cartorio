# OpenCode × MiniMax Coding Plan × cmux.app — Integration Setup

**Data:** 2026-07-11
**Audit completo:** Gustavo Almeida
**Modified by Gustavo Almeida**

## Visão geral

Este documento descreve a integração completa entre:

- **OpenCode CLI 1.17.18** (`~/.hermes/node/bin/opencode`) — IDE/agent runner
- **MiniMax.io Coding Plan** — provedor LLM primário (modelo `MiniMax-M3` XMax Thinking)
- **opencode-go (zen)** — provedor secundário free tier com 11+ modelos
- **cmux.app 0.64.17** (libghostty) — terminal-agentic cockpit
- **MacBook Pro M4 · 16GB · macOS 26.x**

Antes deste audit, o setup tinha **3 problemas críticos** que causavam `404 Page not found` em qualquer chamada `opencode run --model opencode-go/minimax-m3`. Todas foram corrigidas.

---

## 🔴 Problemas encontrados (e soluções)

### 1. `opencode.json` global estava vazio (apenas plugin)

**Sintoma:** Apenas o `plugin: ["./plugins/cmux-session.js"]` estava em `~/.config/opencode/opencode.json`. Toda a configuração real vivia em `~/.config/opencode/opencode.jsonc`.

**Problema:** O OpenCode 1.17 lê **AMBOS** `.json` e `.jsonc` no mesmo escopo (deep-merge). Mas o `.jsonc` antigo tinha `provider.opencode-go` apontando para o endpoint errado (`https://api.minimax.io/v1`), o que **sobrescrevia** qualquer config do `.json`.

**Solução:**
- Reescrito `~/.config/opencode/opencode.json` consolidado (15.9KB, 19 top-level keys)
- Removido `~/.config/opencode/opencode.jsonc` (renomeado para `.OLD.bak.*`)
- Backup em `~/.config/opencode/opencode.json.bak.20260711-204955`

### 2. `baseURL` do provider `opencode-go` estava errado

**Sintoma:** `404 Page not found` ao chamar `opencode run --model opencode-go/minimax-m3`.

**Causa raiz:** O `opencode.jsonc` antigo configurava:
```json
"opencode-go": {
  "options": {
    "baseURL": "https://api.minimax.io/v1",  // ❌ endpoint errado
    "apiKey": "{env:MINIMAX_API_KEY}"        // ❌ key errada (sk-cp-* vs sk-j03K...)
  }
}
```

**Endpoint real (descoberto via `strings` no binário opencode.exe):**
```
//opencode.ai/zen/go/v1
//opencode.ai/zen/v1
//opencode.ai/go
```

**Endpoint correto:** `https://opencode.ai/zen/go/v1`
**API key correta:** `$OPENCODE_GO_API_KEY` (sk-***REDACTED-PURGED-2026-07-28***)

**Validação:**
```bash
curl -sS https://opencode.ai/zen/go/v1/models -H "Authorization: Bearer $OPENCODE_GO_API_KEY"
# {"object":"list","data":[{"id":"minimax-m3",...}]}
```

### 3. Skills duplicadas (24 nomes × 2 paths)

**Sintoma:** Warnings `duplicate skill name` em todas as sessões.

**Causa:** `~/.agents/skills` é **symlink** → `~/.config/opencode/skills`. O `.jsonc` antigo listava ambos em `skills.paths`.

**Solução:**
- Mantido apenas `~/.config/opencode/skills/` em `skills.paths`
- Removida referência redundante `~/.agents/skills`
- Backup: `~/.config/opencode/skills.bak.20260711/`

---

## 📁 Arquivos modificados

| Arquivo | Antes | Depois | Notas |
|---|---|---|---|
| `~/.config/opencode/opencode.json` | 104 bytes (só plugin) | **15.9KB · 19 keys** | Schema-compliant, JSONC com comentários |
| `~/.config/opencode/opencode.jsonc` | 3.2KB (config errada) | `.OLD.bak.20260711-205309` | Removido para evitar conflito |
| `~/.config/opencode/skills/` | 24 dirs duplicadas | 24 dirs (1 cópia) | Symlink ~/.agents/skills aponta aqui |
| `/Users/gustavoalmeida/projetos/Cartorio/opencode.json` | inexistente | **3.7KB** | Override local do projeto |

---

## 🔧 Arquitetura de providers

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenCode CLI 1.17.18                     │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   opencode-go          anthropic            google            xai
   (zen, free)          (MiniMax plan)       (Antigravity)     (xAI OAuth)
        │                   │                   │                │
        ▼                   ▼                   ▼                ▼
opencode.ai/zen/go/v1   127.0.0.1:4000     generativelanguage   api.x.ai/v1
                        (proxy launchd)     .googleapis.com
        │                   │
        │                   ▼
        │             api.minimax.io/anthropic
        │             (Claude + MiniMax-M3)
        ▼
   11 modelos free:
   - minimax-m3 (XMax Thinking)
   - minimax-m2.7 (Highspeed)
   - kimi-k2.7-code, kimi-k2.6
   - glm-5.1, glm-5.2
   - qwen3.7-max, qwen3.6-plus
   - deepseek-v4-pro
   - mimo-v2.5-pro
```

### Tabela de providers

| Provider | baseURL | Auth | Modelos principais | Custo |
|---|---|---|---|---|
| `opencode-go` | `https://opencode.ai/zen/go/v1` | `$OPENCODE_GO_API_KEY` | minimax-m3, kimi-k2.7-code, deepseek-v4-pro | **free** |
| `anthropic` | `$ANTHROPIC_BASE_URL` (= `127.0.0.1:4000`) | `$ANTHROPIC_API_KEY` (= proxy bypass) | claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5 | MiniMax plan |
| `google` | (default) | `$GOOGLE_GENERATIVE_AI_API_KEY` | gemini-2.5-pro, gemini-2.5-flash | Free tier |
| `xai` | `https://api.x.ai/v1` | `$XAI_API_KEY` | grok-4.5, grok-4.20-multi-agent | xAI |

### Tabela de modelos default

| Slot | Provider/Model | Por quê |
|---|---|---|
| `model` | `opencode-go/minimax-m3` | MiniMax-M3 XMax Thinking, 1M ctx, free via zen |
| `small_model` | `opencode-go/minimax-m2.7` | Faster, ideal para title generation |

---

## 🤖 Agents custom

### `build` (primary built-in, override parcial)

**⚠️ IMPORTANTE:** O OpenCode 1.17 define o agent `build` como **BUILT-IN NATIVO** (marcado com `"native": true` no `debug agent build`). O `model` default é fixo em `google/gemini-3.1-pro-preview` e **não pode ser overriden via config inline**.

**Workaround aplicado (Cartório):** Criar agent `cartorio` como `primary` + `default_agent: cartorio`.

```yaml
# /Users/gustavoalmeida/projetos/Cartorio/opencode.json
default_agent: cartorio
agent:
  cartorio:
    mode: primary
    model: opencode-go/minimax-m3
    description: Primary agent do Cartório bot
    prompt: "Você trabalha no Cartório bot. Stack: FastAPI + SQLAlchemy 2.0..."
```

Resultado: `opencode run` no diretório Cartório usa `cartorio` agent com MiniMax-M3 (não o built-in Gemini).

### `cartorio-dev` (subagent)

```yaml
mode: subagent
model: opencode-go/minimax-m3
description: Backend FastAPI / SQLAlchemy / audit chain / PII scrubbing / emolumento MG
prompt: "Você é cartorio-dev: engenheiro backend especializado no Cartório bot..."
```

### `cartorio-lgpd` (subagent)

```yaml
mode: subagent
model: opencode-go/minimax-m3
description: LGPD / RIPD / retenção / política privacidade / direito esquecimento
prompt: "Você é cartorio-lgpd: DPO + advogado de privacidade. NUNCA permita PII bruta..."
```

### `cartorio-n8n` (subagent)

```yaml
mode: subagent
model: opencode-go/minimax-m2.7
description: Workflows n8n / Evolution API / OpenClaw / multi-canal / deploy Easypanel
prompt: "Você é cartorio-n8n: engenheiro de workflows..."
```

---

## ⚡ Slash commands custom

| Command | Agent | Função |
|---|---|---|
| `/health` | build | Smoke-test todos os providers em paralelo |
| `/audit` | cartorio-dev | Valida audit chain SHA256 + HMAC |
| `/pii-check` | cartorio-lgpd | PII scrubbing tests + 3 camadas |
| `/deploy-status` | cartorio-n8n | Status api.2notasudi.com.br, flow, supbase |
| `/cartorio-test` | cartorio-dev | `pytest --cov=app --cov-fail-under=90` |
| `/cartorio-audit` | cartorio-dev | Valida audit chain |
| `/cartorio-pii` | cartorio-lgpd | Valida PII 3 camadas |
| `/cartorio-deploy` | cartorio-n8n | Status produção |
| `/cartorio-lint` | cartorio-dev | ruff + mypy backend |

---

## 🔌 MCP servers

| MCP | Tipo | URL | Status |
|---|---|---|---|
| `context7` | remote | `https://mcp.context7.com/mcp` | ✅ enabled |
| `github-grep` | remote | `https://mcp.grep.app` | ✅ enabled |
| `openwork-browser` | remote | `http://127.0.0.1:64883/mcp` | ⏸ disabled |
| `chrome-bridge` | remote | `http://127.0.0.1:43110/mcp` | ⏸ disabled |
| `cartorio` | local | `uv run --project backend python -m mcp_server` | ⏸ disabled (precisa backend rodando) |

---

## 🖥️ cmux.app integration

**Versão:** 0.64.17 (build 97, commit 9ed29d81a)
**Terminal:** libghostty (embarcado em `/Applications/cmux.app/Contents/Resources/bin/ghostty`)

### Comandos úteis

```bash
cmux <path>                          # Abre diretório em nova workspace
cmux omo [opencode-args...]          # Invoca OpenCode CLI
cmux omx [omx-args...]               # Invoca OMX
cmux claude-teams [claude-args...]   # Invoca Claude Code
cmux codex-teams [codex-args...]     # Invoca Codex
cmux reload-config                   # Recarrega ~/.config/cmux/cmux.json + Ghostty
cmux config doctor                   # Valida cmux.json
cmux settings path                   # Path do settings atual
```

### Plugin OpenCode↔cmux

```json
"plugin": [
  "./plugins/cmux-session.js",  // Session lifecycle bridge (100 max sessions)
  "./plugins/cmux-feed.js"      // Feed/TUI integration (20KB)
]
```

**Importante:** Os 2 plugins ficam em `~/.config/opencode/plugins/` e são gerenciados pelo próprio cmux (`cmux hooks opencode install`). Não editar manualmente.

### Ghostty config

Path: `~/.config/ghostty/config` (controla transparência, blur, font, theme, keybinds).

```bash
cmux reload-config   # Recarrega ambos ghostty + cmux.json in-place
```

---

## 🛡️ Permissões

### Global (`~/.config/opencode/opencode.json`)

```json
"permission": {
  "edit": "allow",
  "bash": "allow",
  "external_directory": "allow",
  "webfetch": "allow",
  "doom_loop": "ask"
}
```

### Cartório local (`./opencode.json`)

```json
"permission": {
  "edit": "allow",
  "bash": {
    "git *": "allow",
    "uv *": "allow",
    "pytest*": "allow",
    "ruff*": "allow",
    "mypy*": "allow",
    "rm *": "ask",
    "curl *": "allow",
    "ssh *": "ask",
    "*": "allow"
  },
  "external_directory": {
    "~/MEMORY.md": "deny",                      // ← proteção memória
    "~/.zcode/secrets/**": "deny",              // ← proteção secrets
    "~/projetos/*/.git/**": "allow",
    "*": "allow"
  },
  "webfetch": "allow",
  "doom_loop": "ask"
}
```

---

## 📊 Compaction & tool output

```json
"compaction": {
  "auto": true,
  "prune": true,
  "tail_turns": 6,
  "preserve_recent_tokens": 20000,
  "reserved": 8192
},
"tool_output": {
  "max_lines": 3000,
  "max_bytes": 81920
}
```

**Justificativa:** M3 tem 1M context window, então `preserve_recent_tokens: 20000` mantém os últimos ~20k tokens verbatim durante compaction, enquanto `tail_turns: 6` preserva 6 turnos completos do usuário.

---

## 🧪 Validação E2E (2026-07-11)

```bash
$ opencode run --model opencode-go/minimax-m3 "Diga apenas: pong m3 ok"
> build · minimax-m3
pong m3 ok

$ opencode run --model opencode-go/kimi-k2.7-code "Diga apenas: pong kimi ok"
> build · kimi-k2.7-code
pong kimi ok

$ opencode run --model opencode-go/deepseek-v4-pro "Diga apenas: pong deepseek ok"
> build · deepseek-v4-pro
pong deepseek ok
```

**3/3 modelos responded.** ✅

---

## 🚀 Comandos rápidos

```bash
# Test rápido
~/.hermes/node/bin/opencode run --model opencode-go/minimax-m3 "ping"

# Debug config
~/.hermes/node/bin/opencode debug config

# Stats
~/.hermes/node/bin/opencode stats

# Validar skills (sem duplicatas)
~/.hermes/node/bin/opencode debug skill | head -50

# Restart proxy cache (se hit_rate=0)
launchctl kickstart -k gui/$(id -u)/com.gustavoalmeida.minimax-proxy
curl -sS http://127.0.0.1:4000/health | head -c 200

# Tail logs
tail -f /tmp/minimax-proxy.log
```

---

## 📚 Referências

- **OpenCode schema**: <https://opencode.ai/config.json>
- **MiniMax.io Coding Plan**: <https://api.minimax.io/v1> (auth Bearer)
- **opencode-go (zen)**: <https://opencode.ai/zen/go/v1> (auth Bearer)
- **Vault**: `~/.zcode/secrets/api-keys-vault.env` (chmod 600, nunca commitar)
- **MEMORY.md**: `~/MEMORY.md` (append-only)
- **AGENT-STACK-MAP.md**: `~/.zcode/docs/AGENT-STACK-MAP.md` (canonical map)
- **Skills canônicas**: `/Users/gustavoalmeida/projetos/Cartorio/.agents/skills/`

---

## 🧠 Lessons Learned (2026-07-11)

1. **OpenCode lê `.json` E `.jsonc`** no mesmo escopo, e o **`.jsonc` é processado POR ÚLTIMO**, sobrescrevendo o `.json`. Ter ambos é receita para confusão — manter apenas um.
2. **`provider.{name}.options.apiKey` no config sobrescreve `~/.local/share/opencode/auth.json`**. Se você quer usar a key do auth.json, NÃO defina `options.apiKey` no provider.
3. **O provider `opencode-go` é servido em `https://opencode.ai/zen/go/v1`**, não em `api.minimax.io` nem `api.opencode.ai`. Endereços errados = 404 silencioso.
4. **`~/.agents/skills/` é symlink** → `~/.config/opencode/skills/`. Listar ambos em `skills.paths` causa warning "duplicate skill name" mas funciona (apenas ruído).
5. **OpenCode 1.17 é binário Go compilado (bun-bundle)** — strings revelam endpoints hardcoded. Use `strings ./opencode.exe | grep opencode` para descobrir URLs internas.
6. **`opencode debug config`** é a ferramenta canônica para ver a config resolvida após merge. Use sempre após editar.
7. **JSONC é aceito** (allowComments, allowTrailingCommas) mas o `python3 -m json.tool` NÃO aceita. Use `python3 -c "import json,re; json.loads(re.sub(...))"` para validar.
8. **Built-in agents (`build`, `plan`, `general`, `explore`) têm `native: true`** e seus campos `model` são fixos. Para usar outro modelo, crie um agent custom (`mode: primary`) e defina `default_agent` no config.
9. **`~/.agents/skills/` é symlink → `~/.config/opencode/skills/`** no MacBook do Gustavo. Não listar ambos em `skills.paths` para evitar warnings.
10. **Proxy LiteLLM local (127.0.0.1:4000) só conhece modelos MiniMax.** Anthropic `claude-haiku-4-5` retorna `400 unknown model` — o proxy re-escreve silenciosamente para `MiniMax-M3` apenas no endpoint `/v1/messages` (Anthropic format), mas retorna 400 em `/v1/chat/completions`.

---

**Modified by Gustavo Almeida** — audit, fix, document, save.