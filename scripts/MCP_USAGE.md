# coding-vps-orchestrator (MCP server)

MCP server (`fastmcp` stdio JSON-RPC) que expoe as **62 tools** do orchestrator
`scripts/coding_vps_mcp_orchestrator.py` para clientes MCP (TRAE, TRAE SOLO,
Antigravity, Claude Code, Cursor, Aider, etc.).

> **Estado real 2026-07-08 (Squad 5):** 62 tools / 13 categorias.
> Claims antigos de 100/92/85 tools estão desatualizados (dedupe Squad 10 + aliases).

## TL;DR

```bash
# Contagem real
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
  /Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py list
# Esperado: "MCP orchestrator: 62 tools in 13 categories"

# Smoke
bash /Users/gustavoalmeida/projetos/Cartorio/scripts/validate_coding_vps_tools_60.sh
```

## Manifesto & Configs

| Arquivo | Para que serve |
|---|---|
| `scripts/mcp.json` | Identidade do server (version, transport, categories) |
| `scripts/mcp_manifest.json` | Manifesto estendido (pode estar stale vs CLI — confiar no `list`) |
| `scripts/mcp_config.trae.json` | Template TRAE / TRAE SOLO |
| `scripts/mcp_config.antigravity.json` | Template Antigravity |
| `scripts/mcp_config.claude_desktop.json` | Template Claude Desktop |
| `scripts/mcp_config.cursor.json` | Template Cursor (`~/.cursor/mcp.json`) |
| `scripts/install_mcp_clients.sh` | Instala/desinstala em todos os clients |
| `scripts/validate_coding_vps_tools_60.sh` | Smoke-test exit≠0 |
| `docs/platforms/coding-vps/INTEGRATION_TRAE_ANTIGRAVITY.md` | JSON exatos + HTTP mode |
| `scripts/MCP_USAGE.md` | Este arquivo |

**Secrets:** configs versionados **não** incluem `LITELLM_API_KEY`. Export no shell
do client ou use `~/.mavis/secrets/coding-vps-global.env` (chmod 600).

## Install automatic

```bash
bash /Users/gustavoalmeida/projetos/Cartorio/scripts/install_mcp_clients.sh install
bash /Users/gustavoalmeida/projetos/Cartorio/scripts/install_mcp_clients.sh status
bash /Users/gustavoalmeida/projetos/Cartorio/scripts/install_mcp_clients.sh uninstall
```

Targets: Claude Desktop, Cursor, `~/.trae/mcp.json`, `~/.antigravity/mcp.json`,
`.trae/mcp-servers/coding-vps.json`.

## Install manual (stdio)

### TRAE / TRAE SOLO / Antigravity / Cursor / Claude

Mesmo bloco (paths absolutos no Mac Gustavo):

```json
{
  "mcpServers": {
    "coding-vps-orchestrator": {
      "command": "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3",
      "args": [
        "/Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py",
        "mcp"
      ],
      "env": {
        "SSH_PRIVATE_KEY": "/Users/gustavoalmeida/.ssh/id_ed25519_cartorio",
        "SSH_TAILSCALE_HOST": "100.99.172.84"
      }
    }
  }
}
```

Paths de destino:

| Client | Path |
|--------|------|
| TRAE | `~/.trae/mcp.json` + `.trae/mcp-servers/coding-vps.json` |
| TRAE SOLO | mesmo `~/.trae/mcp.json` ou Preferences → MCP |
| Antigravity | `~/.antigravity/mcp.json` |
| Cursor | `~/.cursor/mcp.json` |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |

## Protocolo MCP (JSON-RPC 2.0 stdio)

### `initialize`
```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"TRAE","version":"1.0"}}}
```

### `tools/list`
```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```
Retorna **62** tools (não 100).

### `tools/call`
```json
{
  "jsonrpc":"2.0","id":3,
  "method":"tools/call",
  "params":{
    "name":"chat_minimax",
    "arguments":{"prompt":"PING-OK-62","max_tokens":120,"model":"MiniMax-M3"}
  }
}
```

### `resources/read` (se registrado)
- `manifest://tools`
- `manifest://categories`

## Categorias (13) — 62 tools

| Categoria | qtd | Exemplos |
|---|---:|---|
| llm | 3 | `chat_minimax`, `chat_with_agent`, `list_models` |
| status | 10 | `list_services`, `health_check_service`, `health_check_all`, … |
| docker | 6 | `service_logs`, `restart_service`, `scale_service`, … |
| easypanel | 4 | `ep_login`, `ep_list_*`, `ep_deploy` |
| db | 7 | `postgres_*`, `redis_cmd`, `redis_ping`, `redis_get/set/keys` |
| workflow | 3 | `temporal_*`, `langflow_run` |
| code-review | 2 | `sonarqube_*` |
| websocket | 4 | `centrifugo_*`, `mirotalk_create_room` |
| webhook | 1 | `webhook_send` |
| rag | 3 | `langflow_list_flows`, `anythingllm_query`, `langfuse_traces` |
| dev | 1 | `opencode_run` |
| networking | 1 | `tailscale_status` |
| utility | 17 | `exec_in_container`, `service_http_*`, files, swarm, secrets, `openapi_spec` |

## Curl-like (modo HTTP debug)

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
  /Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py http &
curl http://localhost:8100/
curl http://localhost:8100/tools
curl -X POST http://localhost:8100/call/list_services \
     -H 'Content-Type: application/json' -d '{"stack":"all"}'
```

## Requisitos de runtime

| Item | Valor |
|---|---|
| Python | 3.11+ (3.14 Frameworks no Mac) |
| fastmcp | >= 3.4.2 |
| SSH key | `~/.ssh/id_ed25519_cartorio` |
| VPS | `100.99.172.84` |
| Network | Tailscale |

## Histórico de contagem

| Data | Tools | Evento |
|------|------:|--------|
| pré-Squad 10 | 100 | catálogo inflado + stubs |
| Squad 10 | 60 | dedupe final |
| Squad 5 | **62** | `redis_ping` + `health_check_all` |

## Stack relacionada

- Tailscale SSH → Hostinger `100.99.172.84`
- ~89 serviços Docker Swarm `coding-vps*`
- LiteLLM proxy com MiniMax-M3 XMax Thinking
- Agents: crew-ai, goose, hermes, kilo, langgraph, openchamber, openclaw, opencode, openhands
  (via `chat_with_agent`, não 9 tools separadas)

**Modified by Gustavo Almeida**
