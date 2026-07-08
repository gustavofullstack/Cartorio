---
name: coding-vps-orchestrator
description: Como usar o MCP orchestrator local + remoto (coding-vps_apenas_para_auxilio) com 100+ tools / 15 categorias. CLI, MCP stdio, HTTP server, e registro no TRAE.
type: agent
created: 2026-07-08
squad: 3
---

# coding-vps-orchestrator

Skill que ensina **qualquer agente LLM** (TRAE IDE, TRAE SOLO.APP, Antigravity, Claude Desktop) a consumir o **MCP orchestrator** rodando em `localhost:8100` (HTTP) ou via `stdio` (MCP nativo).

## Quando usar

- Você precisa **listar serviços**, **restartar container**, **ler logs** ou **deployar** um agent no VPS `100.99.172.84`.
- Você quer **conversar com um LLM agent** (claude, gpt, gemini, minimax, opencode) sem sair do MCP.
- Você precisa de **métricas Prometheus**, **issues Sentry** ou **dashboards Grafana**.
- Você quer **rodar workflows Temporal** ou **scrape Firecrawl** sem instalar nada localmente.

## Formas de consumo (3 modos)

### Modo 1 — CLI (mais simples)

```bash
cd /Users/gustavoalmeida/projetos/Cartorio

# Listar todos os 100+ tools em 15 categorias
python3 scripts/coding_vps_mcp_orchestrator.py list

# Chamar uma tool (CLI posiciona args)
python3 scripts/coding_vps_mcp_orchestrator.py call chat_minimax "PING-OK-21"
python3 scripts/coding_vps_mcp_orchestrator.py call list_services
python3 scripts/coding_vps_mcp_orchestrator.py call restart_service openclaw
python3 scripts/coding_vps_mcp_orchestrator.py call firecrawl_scrape https://example.com
```

### Modo 2 — HTTP server (recomendado para TRAE)

```bash
# Sobe HTTP server em localhost:8100
uvicorn scripts.coding_vps_mcp_orchestrator:http_app --port 8100 --host 0.0.0.0
```

Endpoints:
- `GET  http://localhost:8100/` → metadata + contagem de tools
- `GET  http://localhost:8100/tools` → lista pública
- `POST http://localhost:8100/call/{tool_name}` → executa tool, body = `{"arg1": "val1", ...}`

Exemplo:
```bash
curl -X POST http://localhost:8100/call/chat_minimax \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Liste os serviços Docker ativos"}'
```

### Modo 3 — MCP stdio (nativo TRAE/Claude Desktop)

```bash
python3 scripts/coding_vps_mcp_orchestrator.py mcp
```

Adicione ao `~/.claude/mcp_servers.json` ou `.trae/mcp-servers/coding-vps.json` (já presente no repo).

## Categorias e tools mais usadas

| Categoria | Tools destaque | Uso típico |
|---|---|---|
| LLM (17) | `chat_minimax`, `chat_with_claude`, `chat_with_gpt`, `list_models` | Chamar LLMs via LiteLLM proxy |
| STATUS (8) | `list_services`, `health_check_all`, `docker_stats`, `swarm_info` | Visão geral do VPS |
| DOCKER (6) | `service_logs`, `restart_service`, `scale_service`, `deploy_image` | Operação Docker Swarm |
| DB (10) | `postgres_query`, `redis_ping`, `redis_get/set` | CRUD Postgres/Redis/Clickhouse/Mongo |
| MONITORING (8) | `prometheus_query`, `sentry_list_issues`, `grafana_dashboards` | Observabilidade |
| NETWORKING (3) | `tailscale_status`, `tailscale_ping`, `tailscale_list_devices` | Tailscale mesh |
| UTILITY (15) | `file_read`, `file_write`, `exec_in_container`, `port_scan` | Operação VPS genérica |

Lista completa: `python3 scripts/coding_vps_mcp_orchestrator.py list` ou ver [coding-vps-21/SKILL.md](../coding-vps-21/SKILL.md).

## Pré-requisitos

1. **SSH key**: `~/.ssh/id_ed25519_cartorio` configurada e autorizada no VPS.
2. **Conectividade Tailscale**: `tailscale ping 100.99.172.84` deve funcionar.
3. **Python 3.11+** com `fastmcp`, `fastapi`, `uvicorn` instalados (no `backend/pyproject.toml`).

## Variáveis de ambiente

| Var | Default | Descrição |
|---|---|---|
| `SSH_PRIVATE_KEY` | `~/.ssh/id_ed25519_cartorio` | Caminho da chave SSH |
| `SSH_TAILSCALE_HOST` | `100.99.172.84` | Host Tailscale do VPS |
| `LITELLM_API_KEY` | `e39dss0k1baohuqkprjv` | Master key do LiteLLM proxy |
| `EASYPANEL_URL` | `http://100.99.172.84:3000` | URL do EasyPanel |

## Troubleshooting

- **`fastmcp not installed`** → `pip install fastmcp` (ou `uv add fastmcp` no backend).
- **`SSH timeout`** → checar `ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 "echo OK"`.
- **`tool not found`** → rodar `list` para ver nomes exatos (são case-sensitive).
- **HTTP 502 no `chat_minimax`** → LiteLLM proxy fora do ar, rodar `restart_service litellm-app`.

## Integração TRAE/Antigravity

Ver `docs/integrations/TRAE-coding-vps.md` para setup completo do MCP server no TRAE IDE / SOLO.APP.
