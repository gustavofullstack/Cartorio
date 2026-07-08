# coding-vps-orchestrator (MCP server)

MCP server (`fastmcp` stdio JSON-RPC) que expoe as 100 tools do orchestrator
`scripts/coding_vps_mcp_orchestrator.py` para clientes MCP (TRAE, Antigravity,
Claude Code, Cursor, Aider, etc.).

## TL;DR

```bash
# Validar que o server sobe
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
  /Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py mcp
# Deve mostrar: "MCP orchestrator: 100/100 tools registered"
```

## Manifesto & Configs

| Arquivo | Para que serve |
|---|---|
| `scripts/mcp_manifest.json` | Manifesto canonico (100 tools, 2 resources, MCP-protocol JSON Schema) |
| `scripts/mcp.json` | Manifesto de identidade do server (name, version, transport, deps) |
| `scripts/mcp_config.trae.json` | Config para colar no TRAE/Antigravity workspace |
| `scripts/mcp_config.claude_desktop.json` | Config para `~/Library/Application Support/Claude/claude_desktop_config.json` |
| `scripts/mcp_config.cursor.json` | Config para `~/.cursor/mcp.json` |
| `scripts/install_mcp_clients.sh` | Instala/desinstala o server em todos os clientes |
| `scripts/MCP_USAGE.md` | Este arquivo |

## Install automatic (Claude Desktop + Cursor + TRAE)

```bash
bash /Users/gustavoalmeida/projetos/Cartorio/scripts/install_mcp_clients.sh install
bash /Users/gustavoalmeida/projetos/Cartorio/scripts/install_mcp_clients.sh status   # checa
bash /Users/gustavoalmeida/projetos/Cartorio/scripts/install_mcp_clients.sh uninstall
```

## Install manual (1 cliente)

### TRAE / Antigravity

`~/.trae/mcp.json` (ou na raiz do projeto em `.trae/mcp.json`):
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
        "SSH_TAILSCALE_HOST": "100.99.172.84",
        "LITELLM_API_KEY": "sk-local-litellm-2026"
      }
    }
  }
}
```

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "coding-vps-orchestrator": {
      "command": "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3",
      "args": ["/Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py", "mcp"],
      "env": {"SSH_PRIVATE_KEY": "/Users/gustavoalmeida/.ssh/id_ed25519_cartorio"}
    }
  }
}
```

### Cursor

`~/.cursor/mcp.json` (mesma estrutura).

## Protocolo MCP (JSON-RPC 2.0 stdio)

O server expoe **2 metodos**:

### `initialize` (handshake)
```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"TRAE","version":"1.0"}}}
```
Resposta vem com `serverInfo={"name":"coding-vps-orchestrator"}` e capability `tools`.

### `tools/list`
```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```
Retorna 100 tools. Cada tool tem:
```json
{
  "name": "chat_minimax",
  "description": "Chat with MiniMax-M3 XMax Thinking via LiteLLM proxy",
  "inputSchema": {
    "type":"object",
    "properties": {
      "prompt":{"type":"string","description":"prompt"},
      "max_tokens":{"type":"integer","description":"max tokens"},
      "model":{"type":"string","description":"model"}
    },
    "required":["prompt"]
  }
}
```

### `tools/call`
```json
{
  "jsonrpc":"2.0","id":3,
  "method":"tools/call",
  "params":{
    "name":"chat_minimax",
    "arguments":{"prompt":"PING-OK-21","max_tokens":120,"model":"MiniMax-M3"}
  }
}
```
Resposta (formato `content[]`):
```json
{
  "result":{
    "content":[{"type":"text","text":"{\"reply\":\"PONG\",\"elapsed_s\":0.42,\"total_tokens\":37}"}],
    "isError":false
  }
}
```

### `resources/read` (bonus)
```json
{"jsonrpc":"2.0","id":4,"method":"resources/read","params":{"uri":"manifest://tools"}}
```
Devolve manifesto completo com tool/args/category/description.

URIs disponiveis:
- `manifest://tools` — JSON com 100 tools
- `manifest://categories` — JSON `{"llm":11,"status":8,...}`

## Categorias de tools (15)

| Categoria | qtd | Exemplos |
|---|---:|---|
| llm         | 11 | `chat_minimax`, `list_models`, `chat_<agente>` (9 coding agents) |
| status      |  8 | `list_services`, `docker_stats`, `swarm_info`, `node_list` |
| docker      |  6 | `service_logs`, `restart_service`, `scale_service`, `env_set` |
| easypanel   |  4 | `ep_login`, `ep_list_projects`, `ep_deploy` |
| db          | 10 | `postgres_query`, `redis_ping`, `clickhouse_query`, `minio_list` |
| workflow    |  4 | `temporal_list_workflows`, `langflow_run`, `paperclip_list_tasks` |
| code-review |  6 | `gerrit_list_changes`, `sonarqube_issues`, `sourcegraph_search` |
| websocket   |  6 | `centrifugo_publish`, `mirotalk_create_room`, `filepizza_create` |
| webhook     |  4 | `request_basket_create`, `webhook_send` |
| rag         |  5 | `langflow_list_flows`, `anythingllm_query`, `langfuse_traces` |
| search      |  4 | `firecrawl_scrape`, `crwal4ai_scrape`, `flaresolverr_solve` |
| dev         |  6 | `goclaw_list_agents`, `boltdiy_create`, `opencode_run` |
| monitoring  |  8 | `prometheus_query`, `sentry_list_issues`, `status_page_get` |
| networking  |  3 | `traefik_*`, `caddy_*`, `n8n_*` |
| utility     | 15 | `exec_in_container`, `file_read`, `swarm_service_create`, `port_scan` |

## Curl-like (modo HTTP debug)

Se preferir testar via HTTP, o script expoe tambem em modo FastAPI:

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
  /Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py http &
curl http://localhost:8100/                      # GET / -> server info
curl http://localhost:8100/tools                 # GET /tools -> list of all tools
curl -X POST http://localhost:8100/call/chat_minimax \
     -H 'Content-Type: application/json' \
     -d '{"prompt":"PING-OK-21"}'
curl http://localhost:8100/openapi.json          # OpenAPI 3.1 spec
```

## Requisitos de runtime

| Item | Valor |
|---|---|
| Python | 3.14 (tambem funciona 3.11+) |
| fastmcp | >= 3.4.2 |
| SSH key | `~/.ssh/id_ed25519_cartorio` (Tailscale) |
| VPS target | `100.99.172.84` (coding-vps_apenas_para_auxilio) |
| Network | Tailscale VPN ativo |

## Bug fix aplicado (2026-07-08)

| Antes | Depois |
|---|---|
| Script travava em `mcp` mode com `ValueError: Functions with **kwargs are not supported as tools` (FastMCP 3.x rejeita `**_` na assinatura). | Removido `**_` do wrapper `make_handler` em `_register_llm`; agora todos os 9 `chat_<agente>` tools sao registrados. Adicionados 2 `@mcp.resource` (`manifest://tools`, `manifest://categories`). |
| Sem `@mcp.tool()` declarados — confianca no dynamic registration. | `@mcp.tool(name, description)` explicito + try/except com log de falhas. |

Validacao:
```bash
$ timeout 5 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
    scripts/coding_vps_mcp_orchestrator.py mcp
MCP orchestrator: 100/100 tools registered
... INFO Starting MCP server 'coding-vps-orchestrator' with transport 'stdio'
```

## Stack relacionada

- Tailscale SSH → VPS Hostinger `100.99.172.84`
- 89 servicos Docker Swarm em `coding-vps_apenas_para_auxilio_*`
- LiteLLM proxy `:4000` com `MiniMax-M3 XMax Thinking`
- 9 coding agents: crew-ai, goose, hermes, kilo-org_kilocode, langgraph,
  openchamber, openclaw, opencode, openhands
