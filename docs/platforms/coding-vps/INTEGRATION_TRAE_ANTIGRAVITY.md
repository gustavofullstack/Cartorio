# Integração TRAE / TRAE SOLO / Antigravity / Claude Desktop / Cursor

> **Squad 5 — 2026-07-08**. Fonte de verdade para registrar o MCP orchestrator
> `scripts/coding_vps_mcp_orchestrator.py` (modo `mcp` = stdio JSON-RPC).
>
> **Estado real (validado via CLI Squad 5):** **62 tools / 13 categorias**.
> Services: `health_check_all stack=all` → **26/80 up** (54 down/scale=0).
> Claims “51/89” ou “100 tools” são **stale** (Squad 10 deduped 100→60;
> Squad 5 registrou `redis_ping` + `health_check_all` → 62).

---

## Pré-requisitos

| Item | Valor |
|------|-------|
| Python | 3.11+ (repo usa 3.14 Frameworks em macOS) |
| Script | `/Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py` |
| Modo MCP | `mcp` (stdio) — args finais: `["…/coding_vps_mcp_orchestrator.py", "mcp"]` |
| SSH key | `~/.ssh/id_ed25519_cartorio` (`SSH_PRIVATE_KEY`) |
| Host | `100.99.172.84` (`SSH_TAILSCALE_HOST`) |
| VPN | Tailscale ativo |
| Optional | `LITELLM_API_KEY` — **não commitar**. Preferir env do client ou `~/.mavis/secrets/coding-vps-global.env` |

### Install one-shot (todos os clients)

```bash
bash /Users/gustavoalmeida/projetos/Cartorio/scripts/install_mcp_clients.sh install
bash /Users/gustavoalmeida/projetos/Cartorio/scripts/install_mcp_clients.sh status
bash /Users/gustavoalmeida/projetos/Cartorio/scripts/validate_coding_vps_tools_60.sh
```

### Validar sem client

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
  /Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py list
# Esperado: "MCP orchestrator: 62 tools in 13 categories"
```

---

## 1. TRAE.APP (IDE — MCP stdio)

**Arquivos de referência no repo:**
- `scripts/mcp_config.trae.json`
- `.trae/mcp-servers/coding-vps.json` (auto-detect do projeto)

### UI

1. TRAE → Settings → MCP Servers → Add Server  
2. Name: `coding-vps-orchestrator`  
3. Colar o JSON abaixo  
4. Restart TRAE  

### JSON exato (stdio)

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
      },
      "description": "coding-vps-orchestrator: 62 tools / 13 categories via MCP stdio"
    }
  }
}
```

**Path local do user:** `~/.trae/mcp.json`  
**Path do projeto:** `.trae/mcp-servers/coding-vps.json`

Se o LiteLLM exigir key no client, adicione em `env` **somente localmente** (não no git):

```json
"LITELLM_API_KEY": "${LITELLM_API_KEY}"
```

(valores literais de key **não** devem ser commitados; o orchestrator aceita env do processo.)

---

## 2. TRAE SOLO.APP

TRAE SOLO usa o mesmo formato MCP stdio **ou** HTTP se o app preferir URL.

### A) Stdio (recomendado)

Mesmo JSON do TRAE.APP → Preferences → MCP → Add Server.

**Path típico:** `~/.trae/mcp.json` (compartilhado com TRAE IDE) ou Preferences UI.

### B) HTTP (alternativa)

```bash
cd /Users/gustavoalmeida/projetos/Cartorio
MCP_HTTP_PORT=8100 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
  scripts/coding_vps_mcp_orchestrator.py http
```

Endpoints:

| Method | URL | Uso |
|--------|-----|-----|
| GET | `http://localhost:8100/` | metadata / tool count |
| GET | `http://localhost:8100/tools` | lista tools |
| POST | `http://localhost:8100/call/{tool_name}` | body JSON com args |
| GET | `http://localhost:8100/openapi.json` | OpenAPI 3.1 |

SOLO.APP → Settings → Tools → Custom MCP / HTTP URL: `http://localhost:8100`

---

## 3. Antigravity.APP

**Arquivo de referência:** `scripts/mcp_config.antigravity.json`  
**Path local:** `~/.antigravity/mcp.json`

### JSON exato (stdio)

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
      },
      "description": "coding-vps-orchestrator: 62 tools / 13 categories via MCP stdio"
    }
  }
}
```

### HTTP streamable (se o client Antigravity exigir URL)

1. Subir: `python3 scripts/coding_vps_mcp_orchestrator.py http`  
2. Settings → Integrations → MCP → URL `http://localhost:8100` (ou `/mcp` se o client exigir path)

---

## 4. Claude Desktop

**Arquivo de referência:** `scripts/mcp_config.claude_desktop.json`  
**Path macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

### JSON exato

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

Restart Claude Desktop após editar.

---

## 5. Cursor

**Arquivo de referência:** `scripts/mcp_config.cursor.json`  
**Path:** `~/.cursor/mcp.json`

### JSON exato

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

Cursor → Settings → MCP → refresh / restart.

---

## 6. Catálogo real (62 tools / 13 categorias)

| Categoria | Qtd | Tools |
|-----------|----:|-------|
| LLM | 3 | `chat_minimax`, `chat_with_agent`, `list_models` |
| STATUS | 10 | `list_services`, `health_check_service`, `health_check_all`, `service_info`, `service_tasks`, `docker_stats`, `swarm_info`, `node_list`, `network_list`, `volume_list` |
| DOCKER | 6 | `service_logs`, `restart_service`, `scale_service`, `deploy_image`, `env_get`, `env_set` |
| EASYPANEL | 4 | `ep_login`, `ep_list_projects`, `ep_list_services`, `ep_deploy` |
| DB | 7 | `postgres_query`, `postgres_list_tables`, `redis_cmd`, `redis_ping`, `redis_get`, `redis_set`, `redis_keys` |
| WORKFLOW | 3 | `temporal_list_workflows`, `temporal_describe`, `langflow_run` |
| CODE-REVIEW | 2 | `sonarqube_projects`, `sonarqube_issues` |
| WEBSOCKET | 4 | `centrifugo_publish`, `centrifugo_channels`, `centrifugo_history`, `mirotalk_create_room` |
| WEBHOOK | 1 | `webhook_send` |
| RAG | 3 | `langflow_list_flows`, `anythingllm_query`, `langfuse_traces` |
| DEV | 1 | `opencode_run` |
| NETWORKING | 1 | `tailscale_status` |
| UTILITY | 17 | `exec_in_container`, `service_http_*`, volumes, images, swarm create/remove, files, port_scan, secrets, `openapi_spec` |

**Aliases Squad 5:**
- `redis_ping` — thin wrapper sobre `_redis_cmd(..., "ping")` (já existia; agora registrado)
- `health_check_all` — bulk summary via `list_services` (sem TCP por serviço)

---

## 7. Exemplos rápidos (CLI)

```bash
PY=/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
ORCH=/Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py

$PY $ORCH call list_services stack=all
$PY $ORCH call health_check_all stack=main
$PY $ORCH call redis_ping redis_service=langfuse-redis
$PY $ORCH call chat_minimax prompt="PING-OK-62" max_tokens=30
$PY $ORCH call openapi_spec
```

---

## 8. Troubleshooting

| Sintoma | Causa | Fix |
|---------|-------|-----|
| `fastmcp not installed` | dep ausente | `pip install 'fastmcp>=3.4.2'` no Python do `command` |
| Client lista 0 tools | path Python errado | usar o bin Frameworks 3.14 absoluto |
| SSH timeout | Tailscale off / key | `tailscale status`; `ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84` |
| Docs dizem 100 tools | stale docs | confiar no `list` CLI (62) |
| `LITELLM_API_KEY invalid` | key não no env | export local ou secrets file; **não** colar key em JSON versionado |
| Redis `NOAUTH` | password no container | `redis_ping` / `redis_cmd` usam `$REDIS_PASSWORD` via redis-cli |

---

## 9. Referências

| Path | Conteúdo |
|------|----------|
| `scripts/coding_vps_mcp_orchestrator.py` | implementação (62 tools) |
| `scripts/MCP_USAGE.md` | protocolo MCP / install |
| `scripts/mcp_config.*.json` | templates por client |
| `scripts/install_mcp_clients.sh` | install/status/uninstall |
| `scripts/validate_coding_vps_tools_60.sh` | smoke test (exit ≠ 0 se falhar) |
| `.agents/skills/coding-vps-tools-100/SKILL.md` | skill + status real |
| `docs/platforms/coding-vps/MEMORY_2026-07-08.md` | lesson da integração |

**Modified by Gustavo Almeida**
