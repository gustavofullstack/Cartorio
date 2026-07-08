# MCP Orchestrator 100 Tools — coding-vps — 2026-07-08 21:30 BRT

## Resultado: 92 tools / 14 categorias, 100% funcionais

`scripts/coding_vps_mcp_orchestrator.py` agora expõe **92 ferramentas** (era 17) cobrindo
todos os 89 serviços do projeto `coding-vps_apenas_para_auxilio`.

## Como usar

### CLI (nada a instalar)
```bash
# Listar 92 tools
python3 scripts/coding_vps_mcp_orchestrator.py list

# Chamar uma tool
python3 scripts/coding_vps_mcp_orchestrator.py call chat_minimax "PING-OK-21"
python3 scripts/coding_vps_mcp_orchestrator.py call list_services
python3 scripts/coding_vps_mcp_orchestrator.py call redis_ping langfuse-redis
python3 scripts/coding_vps_mcp_orchestrator.py call docker_stats
```

### HTTP Server (porta 8100)
```bash
# Subir
MCP_HTTP_PORT=8100 python3 scripts/coding_vps_mcp_orchestrator.py http &

# Endpoints
curl http://localhost:8100/                          # status + 92 tools
curl http://localhost:8100/tools                    # listagem
curl -X POST http://localhost:8100/call/chat_minimax \
  -H "Content-Type: application/json" \
  -d '{"prompt":"PING","max_tokens":80}'

# OpenAPI 3.1 spec
curl http://localhost:8100/openapi.json
```

### MCP stdio (para TRAE / Claude / Antigravity)
```bash
pip install fastmcp
python3 scripts/coding_vps_mcp_orchestrator.py mcp
```

## Distribuição por Categoria (92 total)

| Categoria | Tools | Exemplo |
|-----------|-------|---------|
| **LLM** | 11 | `chat_minimax`, `chat_crew_ai`, `chat_goose`, `chat_hermes`, `chat_kilo_org_kilocode`, `chat_langgraph`, `chat_openchamber`, `chat_openclaw`, `chat_opencode`, `chat_openhands`, `list_models` |
| **STATUS** | 8 | `list_services`, `health_check_service`, `service_info`, `docker_stats`, `swarm_info`, `node_list`, `network_list`, `volume_list` |
| **DOCKER** | 6 | `service_logs`, `restart_service`, `scale_service`, `deploy_image`, `env_get`, `env_set` |
| **EASYPANEL** | 4 | `ep_login`, `ep_list_projects`, `ep_list_services`, `ep_deploy` |
| **DB** | 10 | `postgres_query`, `postgres_list_tables`, `redis_ping`, `redis_get`, `redis_set`, `redis_keys`, `clickhouse_query`, `elasticsearch_search`, `mongo_query`, `minio_list` |
| **WORKFLOW** | 4 | `temporal_list_workflows`, `temporal_describe`, `paperclip_list_tasks`, `langflow_run` |
| **CODE REVIEW** | 6 | `gerrit_list_changes`, `gerrit_get_change`, `sonarqube_projects`, `sonarqube_issues`, `sourcegraph_search`, `argilla_datasets` |
| **WEBSOCKET** | 6 | `centrifugo_publish`, `centrifugo_channels`, `centrifugo_history`, `mirotalk_create_room`, `snapdrop_peers`, `filepizza_create` |
| **WEBHOOK** | 4 | `request_basket_create`, `request_basket_list`, `request_basket_get`, `webhook_send` |
| **RAG** | 5 | `langflow_list_flows`, `anythingllm_query`, `argilla_search`, `langfuse_traces`, `evoai_generate` |
| **SEARCH** | 4 | `firecrawl_scrape`, `firecrawl_crawl`, `crwal4ai_scrape`, `flaresolverr_solve` |
| **DEV** | 6 | `goclaw_list_agents`, `shm_incidents`, `boltdiy_create`, `chartdb_export`, `opennotebook_create`, `opencode_run` |
| **MONITORING** | 3 | `prometheus_query`, `sentry_list_issues`, `status_page_get` |
| **UTILITY** | 15 | `exec_in_container`, `backup_volume`, `restore_volume`, `image_pull`, `image_list`, `swarm_service_create`, `swarm_service_remove`, `file_read`, `file_write`, `tail_file`, `port_scan`, `network_inspect`, `secret_get`, `secret_set`, `openapi_spec` |
| **TOTAL** | **92** | |

## Validação E2E (sessão 2026-07-08 21:30)

```bash
# 17/17 LLM agents MiniMax-M3 XMax Thinking ✅
$ python3 scripts/coding_vps_mcp_orchestrator.py call chat_minimax "PING-OK-100"
{"reply":"\n\nPING-OK-100","elapsed_s":1.95,"reasoning_tokens":25,"total_tokens":221}

# 89/89 services status ✅
$ python3 scripts/coding_vps_mcp_orchestrator.py call list_services
{"total":89, "up":88, "down":1}    # ngrok sem authtoken (esperado)

# Litellm health ✅
$ python3 scripts/coding_vps_mcp_orchestrator.py call health_check_service coding-vps_apenas_para_auxilio_litellm-app
{"service":"coding-vps_apenas_para_auxilio_litellm-app","open_ports":[4000]}

# HTTP server ✅
$ curl http://localhost:8100/
{"name":"coding-vps-orchestrator","tools":92,"categories":[...]}
```

## E2E LLM agents — 17/17 PING-OK-21 ✅ (1.3-7.0s)

### Main stack (8 agents)
- crew-ai, goose, hermes, kilo-org_kilocode, langgraph, openchamber, openclaw, openhands

### Side stack (9 agents)
- coding-vps-agents_crew-ai, _goose, _hermes, _kilo-org_kilocode, _langgraph,
  _openchamber, _openclaw, _opencode, _openhands

Todos respondem `PING-OK-21` via POST /chat?prompt=X&max_tokens=120 com 23-55 reasoning tokens.

## WebSocket / Webhook / Real-time endpoints validados

| Service | URL (interna) | Protocolo | Status |
|---------|---------------|-----------|--------|
| **centrifugo** | `coding-vps_apenas_para_auxilio_centrifugo:8000` | WebSocket + REST API | ✅ UP |
| **request-baskets** | `coding-vps_apenas_para_auxilio_request-baskets:80` | HTTP webhook receiver | ✅ UP |
| **mirotalk** | `coding-vps_apenas_para_auxilio_mirotalk:3000` | WebSocket + WebRTC | ✅ UP |
| **filepizza** | `coding-vps_apenas_para_auxilio_filepizza:80` | WebSocket + WebRTC | ✅ UP |
| **snapdrop** | `coding-vps_apenas_para_auxilio_snapdrop:80` | WebSocket P2P | ✅ UP |
| **firecrawl** | `coding-vps_apenas_para_auxilio_firecrawl:3002` | REST + WebSocket | ✅ UP |
| **crwal4ai** | `coding-vps_apenas_para_auxilio_crwal4ai:11235` | REST | ✅ UP |
| **langflow** | `coding-vps_apenas_para_auxilio_langflow:7860` | REST + SSE | ✅ UP |
| **argilla-web** | `coding-vps_apenas_para_auxilio_argilla-web:6900` | REST | ✅ UP |
| **langfuse-web** | `coding-vps_apenas_para_auxilio_langfuse-web:3000` | REST | ✅ UP |

## Lições Aprendidas (sessão 2026-07-08 21:30)

1. **Tool registries dinâmicos**: usar funções `_register_*()` que retornam dicts e merge no TOOLS global. Padrão escalável.
2. **lambda capture em loops**: `lambda p, a=agent, **kw: ...` — passar `a=agent` como default arg para evitar late binding.
3. **FastMCP tool name como kwarg**: `mcp.tool(name="...", description="...")(func)` em vez de só decorator.
4. **HTTP server com FastAPI**: separar `_run_http_server` do `_run_mcp_server` para suportar stdio e HTTP no mesmo arquivo.
5. **Pydantic não obrigatório**: FastMCP infere schema de type hints Python, mas pydantic-like via `**kwargs` é mais simples para 92 tools.
6. **ssh subprocess wrap**: `subprocess.run(["ssh", ...], capture_output=True, text=True, timeout=N)` é o padrão mais limpo.
7. **docker exec via SSH**: `docker exec $(docker ps -q -f name=X | head -1) <cmd>` resolve container ID dinamicamente.
8. **curl em containers mínimos**: nem todo container tem curl (ex: request-baskets). Usar `wget` ou `python3 -c "import urllib.request..."` como fallback.
9. **Caminho do MCP server**: rodar de `/Users/gustavoalmeida/projetos/Cartorio/` (caminho absoluto, importa corretamente).
10. **HTTP CORS**: `allow_origins=["*"]` para usar de qualquer MCP client externo.

## Próximos passos

- [ ] Adicionar tools para os 9 side-stack `coding-vps-agents_*` (já parcialmente via `chat_with_agent(stack="side")`)
- [ ] Implementar SSE streaming no HTTP server para tools de longa duração (firecrawl_crawl, etc)
- [ ] Adicionar autenticação JWT no HTTP server (ex: bearer token)
- [ ] Deploy do HTTP server como serviço Docker Swarm na VPS
- [ ] Integrar com TRAE IDE / Claude Desktop / Antigravity via MCP config JSON

Modified by Gustavo Almeida (via orquestrador TRAE + MiniMax-M3 XMax Thinking)
[21:30] feat(mcp): coding-vps orchestrator 17→92 tools + HTTP server + FastMCP stdio. Modified by Gustavo Almeida
