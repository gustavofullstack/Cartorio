---
name: coding-vps-tools-100
description: |
  Catálogo REAL do toolkit coding-vps_apenas_para_auxilio e do MCP orchestrator
  scripts/coding_vps_mcp_orchestrator.py. Nome histórico "tools-100" — o CLI atual
  expõe 62 tools (dedupe Squad 10 + aliases Squad 5), sobre ~89 serviços Swarm.
  Integração TRAE / Antigravity / Claude / Cursor documentada em
  docs/platforms/coding-vps/INTEGRATION_TRAE_ANTIGRAVITY.md.

  Source: Squad 5 2026-07-08 | Infra: 100.99.172.84 (Tailscale SSH)
---

# Coding-VPS Tools — Catálogo & Status REAL

## Status Atual (HONESTO — 2026-07-08, Squad 5)

> **Não confiar em claims antigos de "100 tools" / "92 tools" / "85 tools".**
> Rode `python3 scripts/coding_vps_mcp_orchestrator.py list` para o número real.

| Métrica | Valor real | Notas |
|---------|------------|-------|
| **MCP orchestrator tools (CLI `list`)** | **62** | 13 categorias |
| **Antes do Squad 10 dedupe** | 100 (muitas stubs/DOWN) | inflado; ~42% OK em validação |
| **Services Docker Swarm (coding-vps*)** | **80 listados (26 up / 54 down)** | Snapshot Squad 5 via `health_check_all stack=all` — scale=0 conta como down |
| **Coding agents LLM (main + side)** | até 17 endpoints | MiniMax-M3 via LiteLLM |
| **MCP client configs versionados** | TRAE / Antigravity / Cursor / Claude Desktop | `scripts/mcp_config.*.json` |
| **Smoke script** | `scripts/validate_coding_vps_tools_60.sh` | exit ≠ 0 se falhar |

### Breakdown das 62 tools (13 categorias)

| # | Categoria | Qtd | Exemplos |
|---|-----------|----:|----------|
| 1 | LLM | 3 | `chat_minimax`, `chat_with_agent`, `list_models` |
| 2 | STATUS | 10 | `list_services`, `health_check_service`, **`health_check_all`**, `docker_stats`, … |
| 3 | DOCKER | 6 | `service_logs`, `restart_service`, `scale_service`, `deploy_image`, `env_*` |
| 4 | EASYPANEL | 4 | `ep_login`, `ep_list_projects`, `ep_list_services`, `ep_deploy` |
| 5 | DB | 7 | `postgres_*`, `redis_cmd`, **`redis_ping`**, `redis_get/set/keys` |
| 6 | WORKFLOW | 3 | `temporal_*`, `langflow_run` |
| 7 | CODE-REVIEW | 2 | `sonarqube_projects`, `sonarqube_issues` |
| 8 | WEBSOCKET | 4 | `centrifugo_*`, `mirotalk_create_room` |
| 9 | WEBHOOK | 1 | `webhook_send` |
| 10 | RAG | 3 | `langflow_list_flows`, `anythingllm_query`, `langfuse_traces` |
| 11 | DEV | 1 | `opencode_run` |
| 12 | NETWORKING | 1 | `tailscale_status` |
| 13 | UTILITY | 17 | `exec_in_container`, `service_http_*`, files, swarm, secrets, `openapi_spec` |

**Squad 5 aliases (easy wins):**
- `redis_ping` — já implementada; estava **fora** de `_register_db()`; agora registrada.
- `health_check_all` — wrapper de `list_services` (summary up/down, sem TCP massivo).

**Removidos de propósito (Squad 10):** per-agent `chat_<name>` wrappers (use `chat_with_agent`), search/monitoring stubs ligados a serviços DOWN, tools deprecated com `error: removed by squad1 dedupe`.

## Acesso

| Item | Valor |
|------|-------|
| **VPS Tailscale** | `100.99.172.84` |
| **SSH Key** | `~/.ssh/id_ed25519_cartorio` (`SSH_PRIVATE_KEY`) |
| **Easypanel** | `http://100.99.172.84:3000` |
| **LiteLLM Proxy** | host Docker `…_litellm-app:4000` (key via `LITELLM_API_KEY` env — **não commitar**) |
| **Orchestrator** | `scripts/coding_vps_mcp_orchestrator.py` |
| **E2E agents** | `bash scripts/validate_coding_vps_e2e.sh` |
| **Smoke 62 tools** | `bash scripts/validate_coding_vps_tools_60.sh` |

## MCP integration (TRAE / Antigravity / Claude / Cursor)

```bash
# Install em todos os clients locais
bash scripts/install_mcp_clients.sh install
bash scripts/install_mcp_clients.sh status

# Snippets JSON exatos:
# docs/platforms/coding-vps/INTEGRATION_TRAE_ANTIGRAVITY.md
```

Comando canônico do server:

```text
python3 …/scripts/coding_vps_mcp_orchestrator.py mcp
```

## CLI rápido

```bash
python3 scripts/coding_vps_mcp_orchestrator.py list
python3 scripts/coding_vps_mcp_orchestrator.py call list_services stack=all
python3 scripts/coding_vps_mcp_orchestrator.py call health_check_all stack=main
python3 scripts/coding_vps_mcp_orchestrator.py call redis_ping redis_service=langfuse-redis
python3 scripts/coding_vps_mcp_orchestrator.py call chat_minimax prompt="PING-OK-62" max_tokens=30
python3 scripts/coding_vps_mcp_orchestrator.py mcp   # stdio MCP
python3 scripts/coding_vps_mcp_orchestrator.py http  # debug HTTP :8100
```

## Serviços (visão operacional — não confundir com tool count)

O VPS hospeda dezenas de serviços agentic (LLM agents, RAG, code-review, scrapers, DBs, websockets, etc.). **Nem todo serviço tem tool dedicada** — o design pós-dedupe prefere genéricos:

| Preferir | Em vez de |
|----------|-----------|
| `chat_with_agent agent=crew-ai` | 9× `chat_crew_ai` … |
| `redis_cmd` / `redis_ping` | client Redis custom por app |
| `service_http_get` / `service_http_post` | dezenas de wrappers HTTP |
| `exec_in_container` | CLIs one-off por imagem |
| `health_check_all` | TCP probe em 89 hosts |

### LLM agents (quando UP)

**Main stack only** `coding-vps_apenas_para_auxilio_*` (side-stack `coding-vps-agents_*` **removido** 2026-07-09 — duplicata cara de RAM):
crew-ai, goose, hermes, kilo-org_kilocode, langgraph, openchamber, openclaw, opencode, openhands (+ cline offline esperado — extensão VSCode).

Todos os agents ativos falam MiniMax-M3 XMax Thinking via LiteLLM.

**Bugfix 2026-07-09:** `chat_with_agent` usava `curl` dentro da imagem slim (sem curl) e reportava falso "not running". Agora usa `python3 urllib` (fallback `node fetch` para opencode).

### Infra crítica

| Service | Role |
|---------|------|
| litellm-app | proxy LLM + health |
| anything-llm / langflow / langfuse-* | RAG + observability |
| sonarqube / gerrit / sourcegraph | code review (parcialmente tool-backed) |
| centrifugo / mirotalk | realtime |
| vários postgres/redis | dados (tools DB genéricas) |

## Protocolos

| Protocolo | Uso no orchestrator |
|-----------|---------------------|
| MCP stdio | clients TRAE/Antigravity/Claude/Cursor |
| HTTP debug | `… http` porta 8100 |
| SSH + Tailscale | quase todas as tools |
| Redis RESP via redis-cli | `redis_*` com `$REDIS_PASSWORD` |
| Docker Swarm API (CLI) | status/docker/utility |

## Lições (não repetir)

1. **Tool count no marketing ≠ tools que funcionam** — validação 100-tool era ~42% OK; dedupe para 60/62 foi correto.
2. **Função Python ≠ tool registrada** — `redis_ping` existia e não aparecia no `list` até Squad 5.
3. **Secrets fora do git** — `mcp_config.*.json` versionados só com paths SSH; `LITELLM_API_KEY` local.
4. **Redis AUTH** — sempre `redis-cli -a "$REDIS_PASSWORD" --no-auth-warning`.
5. **Side-stack DNS** — side-stack agents não resolvem main project; E2E roda de dentro do litellm-app.

## Leitura complementar

- `docs/platforms/coding-vps/INTEGRATION_TRAE_ANTIGRAVITY.md` — JSON por client
- `docs/platforms/coding-vps/MEMORY_2026-07-08.md` — lesson integração
- `scripts/MCP_USAGE.md` — protocolo MCP
- `.agents/skills/coding-vps-21/SKILL.md` — agents MiniMax
- `.agents/skills/minimax-m3/SKILL.md` — provider
- `.harness/memory/lesson-158-coding-vps-real-state-2026-07-08.md` — estado VPS

## Modified by Gustavo Almeida

[Squad 5 2026-07-08] status real 62 tools + integração TRAE/Antigravity + redis_ping/health_check_all. Modified by Gustavo Almeida
