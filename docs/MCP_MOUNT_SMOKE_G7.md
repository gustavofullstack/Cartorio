# MCP `/mcp` mount smoke — G7.09.T3

**Owner:** `cartorio-dev`  
**Source:** `backend/mcp_server.py`, `backend/app/main.py`  
**Protocol:** MCP 2025-03-26 (FastMCP streamable HTTP)  
**Related:** `docs/platforms/MCP_TOOLS_INVENTORY.md` (G7.09.T1), `scripts/mcp_tools_inventory.py`

---

## 1. Como o mount funciona

### Dois modos

| Modo | Como sobe | URL típica |
|------|-----------|------------|
| **Montado na FastAPI** | `settings.mcp_server_enabled` → `app.mount("/mcp", mcp_app())` | `http://localhost:8000/mcp` |
| **Standalone** | `make -C backend mcp-server` / `uv run python mcp_server.py` | `POST http://localhost:8100/` (ou `MCP_SERVER_PORT`) |

### Wiring em `main.py` (ordem importa)

Quando `MCP_SERVER_ENABLED=true` (Pydantic: `settings.mcp_server_enabled`):

1. Importa `mcp_app` de `backend/mcp_server.py`
2. Cria o sub-app **uma vez**
3. **Mescla lifespan** do MCP no lifespan da FastAPI (`combined_lifespan`)  
   - Sem isso: FastMCP `StreamableHTTPSessionManager` falha com  
     `"task group is not initialized"` em qualquer `POST /mcp`  
   - Ref: https://gofastmcp.com/deployment/asgi
4. `app.mount("/mcp", _mcp_subapp)` com path interno `"/"`  
   - path interno **não** deve ser `/mcp` (evita `/mcp/mcp`)

### Factory

```text
mcp_server.mcp_app() → mcp.http_app(path="/")
```

Tools chamam services do app **direto** (sem HTTP self-loop `localhost:8000 → /mcp → localhost:8000`).

---

## 2. Habilitar `MCP_SERVER_ENABLED`

### `.env` (local / prod)

```bash
# backend/.env (nunca commitar secrets)
MCP_SERVER_ENABLED=true
MCP_SERVER_TRANSPORT=http
MCP_SERVER_PORT=8100
# Opcional: Bearer para clients (se política de auth exigir)
# MCP_API_KEY=<32+ chars>
```

Template: `backend/.env.example` (chaves placeholder, sem secrets reais).

### Settings

| Env | Settings field | Default no código |
|-----|----------------|-------------------|
| `MCP_SERVER_ENABLED` | `mcp_server_enabled: bool` | `True` em `app/config.py` |
| `MCP_SERVER_TRANSPORT` | `mcp_server_transport` | `"http"` |
| `MCP_SERVER_PORT` | `mcp_server_port` | `8100` |

> **Nota local:** se o seu `backend/.env` tiver `MCP_SERVER_ENABLED=false`, o mount **não** sobe mesmo com default `True` no código (env vence). Para smoke local, force `true`.

---

## 3. Endpoints

| Path | Auth (típico) | Função |
|------|---------------|--------|
| `GET /` | público | meta; inclui `"mcp": "/mcp"`, `"mcp_servers": "/mcp-servers"` |
| `GET /mcp-servers` | público | discovery JSON dos servers MCP conhecidos |
| `POST /mcp` (e SSE stream) | client MCP / opcional API key | protocolo MCP (tools/list, tools/call, …) |
| Standalone `POST /` em `:8100` | client MCP | mesmo FastMCP app sem o resto da API |

**Não hardcode** o número de tools no código de produto — inventário muda. Conte com:

```bash
rg -c '@mcp\.tool\(' backend/mcp_server.py
python3 scripts/mcp_tools_inventory.py
```

---

## 4. Smoke **offline** (sem servidor live)

Preferido em CI / laptop sem rede:

```bash
# Inventário estático + wiring de main.py + coding-vps count
python3 scripts/mcp_tools_inventory.py
python3 scripts/mcp_tools_inventory.py --json | head -c 2000

# Pytest (import FastMCP + list_tools + asserts de mount wiring)
cd backend && uv run pytest -v --no-cov \
  tests/test_mcp_mount_smoke.py \
  tests/test_mcp_api.py \
  tests/test_mcp_servers_api.py
```

O que o offline garante:

- `@mcp.tool(name=…)` ≥ 7 (floor) e tools core presentes no source
- Runtime `await mcp.list_tools()` bate com o source
- `mcp_app()` retorna sub-app montável
- `main.py` contém gate + `app.mount("/mcp"` + merge de lifespan
- `GET /mcp-servers` e `GET /` respondem 200

O que o offline **não** garante:

- Handshake StreamableHTTP completo (session + SSE)
- Traefik / prod TLS path
- Tools que batem DB real (`cartorio_consultar_protocolo`, `cartorio_audit_verify`)

---

## 5. Smoke **local live** (servidor)

### 5.1 API com mount

```bash
# terminal 1
export MCP_SERVER_ENABLED=true
# (ou edite backend/.env)
make dev
# uvicorn app.main:app --reload --port 8000

# terminal 2
curl -sS http://localhost:8000/mcp-servers | head -c 600
curl -sS http://localhost:8000/ | head -c 400

# tools/list (JSON-RPC; headers Accept importam para streamable HTTP)
curl -sS -X POST "http://localhost:8000/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.1"}}}' \
  | head -c 800
```

Se o client MCP oficial for preferível (Claude / Cursor / TRAE), use configs em `scripts/mcp_config.*.json` e `scripts/mcp_config.cartorio-api.example.json` (sem secrets no git).

### 5.2 Standalone MCP

```bash
make -C backend mcp-server
# uv run python mcp_server.py  → host 0.0.0.0:8100, endpoint MCP em POST /
```

### 5.3 Prod (referência)

```bash
curl -sS https://api.2notasudi.com.br/mcp-servers | head -c 400
# /mcp só se MCP_SERVER_ENABLED=true no container/swarm
```

---

## 6. Clients / discovery

| Item | Path |
|------|------|
| Discovery API | `GET /mcp-servers` |
| Config global (host) | `~/.mavis/mcp/clients/cartorio-mcp-config.json` |
| Exemplos versionados | `scripts/mcp_config.*.json`, `scripts/mcp_config.cartorio-api.example.json` |
| Install helper | `bash scripts/install_mcp_clients.sh status` |

---

## 7. Critérios de aceite (DoD G7.09.T3)

| # | Critério | Offline | Live |
|---|----------|---------|------|
| 1 | Tools registradas via `@mcp.tool` contáveis sem server | `mcp_tools_inventory.py` / pytest | `tools/list` |
| 2 | `mcp_app()` + mount path `/mcp` documentados e no source | pytest static | `make dev` + curl |
| 3 | Lifespan merge presente (anti “task group is not initialized”) | grep/pytest | POST /mcp |
| 4 | Doc de enable + endpoints + comandos | este arquivo | — |
| 5 | Sem secrets no git | review | — |

---

## 8. Troubleshooting

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| `404` em `/mcp` | `MCP_SERVER_ENABLED=false` | setar `true`, restart |
| `task group is not initialized` | lifespan MCP não mesclado | não remover `combined_lifespan` |
| `POST /mcp` vazio / 406 | Accept / Content-Type MCP | headers streamable HTTP |
| Import `mcp_server` falha com `APP_ENV=test` | literal settings só aceita development/staging/production | usar `APP_ENV=development` (conftest já força) |
| Tool DB retorna erro | Postgres offline | esperado em smoke unitário |

---

## 9. Inventário atual (snapshot — re-gerar)

```bash
python3 scripts/mcp_tools_inventory.py
```

Não copie o número para código de produto. Snapshot de tools cartorio vive também em `docs/platforms/MCP_TOOLS_INVENTORY.md`.

---

**Modified by Gustavo Almeida — cartorio-dev Wave 26 (G7.09.T3)**
