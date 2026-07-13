---
name: mac-perf-optim-agent-servers-2026-07-12
description: Zed.app com 320% CPU e 5.4GB RAM por agent_servers duplicados; 5 desabilitados recuperaram 5GB RAM e zeraram 60% CPU
type: project
date: 2026-07-12
priority: P1
status: closed
---

# Lesson 163 — Mac perf: Zed.app agent_servers duplicados

## Sintomas (Gustavo reportou)
1. Mac travado — fan barulhento, mouse lag
2. Activity Monitor: `zed` consumindo 320% CPU, 5.4 GB RAM
3. 36 processos filhos do Zed (`pgrep -P $(pgrep zed) | wc -l`)
4. RAM total 16 GB → 15 GB usados, swapouts 158k (transbordando)
5. Load Avg 7.67 / 9.49 / 11.24 em 10 cores (saturado)

## Causa raiz
`~/.config/zed/settings.json` tinha **6 agent_servers** registrados:

```json
"agent_servers": {
  "gemini":      { "type": "registry" },
  "goose":       { "type": "registry" },
  "opencode":    { "default_config_options": {...}, ... },
  "grok-build":  { "type": "registry" },
  "cursor":      { "type": "registry" },
  "claude-acp":  { "default_config_options": {...}, ... }
}
```

Cada `agent_server` registrado spawna **child processes**:
- 1× `npm exec @agentclientprotocol/claude-agent-acp`
- 1× `node claude-agent-acp`
- 1× `claude-agent-sdk` (CLI da Anthropic)
- N× `npm exec hostinger-*-mcp` (MCP servers configurados)
- N× `node hostinger-*-mcp` (processo real do MCP)

No caso do Gustavo:
- 2 sessões claude-acp simultâneas (PIDs 66482, 85691)
- Cada uma com 7 MCPs Hostinger (hosting, domains, dns, billing, reach, vps, ecommerce)
- = 14 processos Node + 14 wrappers npm + 2 SDKs = **~36 processos filhos**
- Apenas 1 agent_server estava em uso real (`claude-acp` na conversa atual)

## Fix LIVE (2026-07-12)

### 1. Backup
```bash
cp ~/.config/zed/settings.json ~/.config/zed/settings.json.pre-optim-2026-07-12.bak
```

### 2. Editar settings.json
Mover 5 agent_servers não usados para `_disabled_2026-07-12` (preserva config):
```json
"agent_servers": { "claude-acp": { ... } },
"_disabled_2026-07-12": {
  "_comment": "Disabled 2026-07-12 to reduce Zed CPU/RAM. Restore from .pre-optim-2026-07-12.bak",
  "gemini":   { "type": "registry" },
  "goose":    { "type": "registry" },
  "opencode": { ... },
  "grok-build": { "type": "registry" },
  "cursor":    { "type": "registry" }
}
```

⚠️ Cuidado: JSON5 (Zed aceita `// comments` e trailing commas), mas validar com:
```bash
python3 -c "
import re, json
c = open(path).read()
print(json.loads(re.sub(r'^\s*//.*$', '', c, flags=re.M)))
"
```

### 3. LaunchAgents redundantes — `launchctl unload`:
```bash
# Bridges de IA não usados (manter anthropic-bridge + minimax-proxy)
launchctl unload ~/Library/LaunchAgents/com.gustavoalmeida.opencode-bridge.plist
launchctl unload ~/Library/LaunchAgents/com.gustavoalmeida.codex-bridge.plist
launchctl unload ~/Library/LaunchAgents/com.gustavoalmeida.grok-bridge.plist
launchctl unload ~/Library/LaunchAgents/com.gustavoalmeida.trae-bridge.daemons.plist
launchctl unload ~/Library/LaunchAgents/com.gustavoalmeida.trae-work-server.plist

# RAM optimizers conflitantes (manter zcode.ram-deep-optimizer)
launchctl unload ~/Library/LaunchAgents/com.zcode.ram-purge-aggressive.plist
launchctl unload ~/Library/LaunchAgents/com.superapp.ram-optimizer.plist

# PostgreSQL duplicado
launchctl unload ~/Library/LaunchAgents/homebrew.mxcl.postgresql@15.plist
```

## Resultado (métricas)

| Métrica | ANTES | DEPOIS | Δ |
|---|---|---|---|
| **Zed RSS** | 6,170 MB | 1,136 MB | **−82% (−5.0 GB)** |
| **Zed %CPU** | 261% | 105% | **−60%** |
| **Filhos do Zed** | ~36 | 3 | **−92%** |
| **LaunchAgents 3rd** | 37 | 30 | **−19%** |

Sistema recuperou **5 GB de RAM** sem reiniciar o Zed. O Zed detectou os agent_servers removidos e matou os processos órfãos automaticamente.

## Padrão a aplicar em outros projetos

1. **Sempre auditar `agent_servers` / `extensions` / `plugins`** antes de reclamar de CPU/RAM
2. **LaunchAgents duplicados** (mesmo propósito) competem por recursos
3. **Tools de "RAM optimizer"** múltiplos = overhead cumulativo, manter UM
4. **`launchctl unload` é reversível** (`launchctl load` restaura) — preferir sobre `rm`
5. **Backup antes** de editar JSON de configuração crítica (`.bak` com data)

## How to apply

Quando qualquer IDE/editor mostrar >100% CPU ou >2GB RAM:
1. `ps -A -o pid,ppid,pcpu,pmem,rss,command | awk '$2==<PID>'` → listar filhos
2. Procurar por `agent_servers`, `extensions`, `mcp`, `lsp`, `language_servers` na config
3. Desabilitar **só os que NÃO estão em uso**, mover para `_disabled_<DATE>`
4. Medir antes/depois com `ps -p <PID> -o rss,pcpu`
5. Documentar em `.harness/memory/lesson-NN-<topic>-<date>.md`

Modified by Gustavo Almeida