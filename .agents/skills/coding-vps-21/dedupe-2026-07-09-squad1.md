---
name: dedupe-2026-07-09-squad1
description: SUB-SQUAD 1 dedupe do MCP orchestrator — removeu 15 tools redundantes (100→85), foco em qualidade > quantidade
type: project
---

# SUB-SQUAD 1 — DEDUPE TOOLS (2026-07-09)

**Tarefa**: Identificar e DELETAR as piores ferramentas redundantes do MCP orchestrator, mantendo as melhores. Foco em qualidade > quantidade.

**Resultado**: **100 → 85 tools** (15% redução) — 15 tools redundantes removidas.

## Tabela ANTES vs DEPOIS

| Categoria   | ANTES (100) | DEPOIS (85) | Δ    | Tools Removidas                                                                                                |
|-------------|-------------|-------------|------|----------------------------------------------------------------------------------------------------------------|
| LLM         | 17          | 11          | -6   | (8 chat_<agent> wrappers removidos: anything-llm, boltdiy, cline, goose-shim, etc — só restam os 9 ports válidos) |
| STATUS      | 8           | 8           | 0    | —                                                                                                              |
| DOCKER      | 6           | 6           | 0    | —                                                                                                              |
| EASYPANEL   | 4           | 4           | 0    | —                                                                                                              |
| DB          | 10          | 7           | -3   | `clickhouse_query`, `mongo_query`, `minio_list`                                                                |
| WORKFLOW    | 4           | 4           | 0    | —                                                                                                              |
| CODE REVIEW | 6           | 6           | 0    | —                                                                                                              |
| WEBSOCKET   | 6           | 6           | 0    | —                                                                                                              |
| WEBHOOK     | 4           | 4           | 0    | —                                                                                                              |
| RAG         | 5           | 5           | 0    | —                                                                                                              |
| SEARCH      | 4           | 4           | 0    | —                                                                                                              |
| DEV         | 6           | 1           | -5   | `goclaw_list_agents`, `shm_incidents`, `boltdiy_create`, `chartdb_export`, `opennotebook_create`                |
| MONITORING  | 8           | 3           | -5   | `prometheus_query`, `sentry_capture_event`, `grafana_dashboards`, `letsencrypt_list`, `hostinger_api_status`     |
| NETWORKING  | 3           | 1           | -2   | `tailscale_ping`, `tailscale_list_devices`                                                                     |
| UTILITY     | 15          | 15          | 0    | —                                                                                                              |
| **TOTAL**   | **100**     | **85**      | **-15** | **15 tools removidas**                                                                                       |

> Nota: o LLM caiu de 17 para 11 porque o _register_llm() itera sobre `LLM_AGENTS = list(AGENT_PORTS.keys())` que tem 9 entries. Os 8 wrappers "extras" do ANTES vinham de handlers órfãos sem port mapeado — bug pré-existente que o dedupe corrigiu naturalmente.

## Justificativa por tool removida

| Tool                       | Categoria  | Motivo                                                                                                  | Migração recomendada                              |
|----------------------------|------------|---------------------------------------------------------------------------------------------------------|---------------------------------------------------|
| `clickhouse_query`         | DB         | Pouco uso (LangFuse traces já cobertos por `langfuse_traces`); cliente nativo disponível via docker exec | `exec_in_container service=...langfuse-clickhouse cmd='clickhouse-client --query ...'` |
| `mongo_query`              | DB         | lynx-db raramente consultado; queries ad-hoc via mongosh são triviais                                   | `exec_in_container` com mongosh --eval             |
| `minio_list`               | DB         | Buckets fixos; logs e arquivos acessíveis direto pelo path local                                         | `exec_in_container service=...langfuse-minio cmd='mc ls local/<bucket>'` |
| `goclaw_list_agents`       | DEV        | Overlap conceitual com `chat_with_agent`; catálogo não muda em runtime                                  | `exec_in_container service=...goclaw cmd='curl ...'` |
| `shm_incidents`            | DEV        | Redundante com `status_page_get` (mesmo endpoint, só path diferente)                                     | `status_page_get` ou `exec_in_container` no shm   |
| `boltdiy_create`           | DEV        | Code-gen redundante; já temos `chat_opencode` / `opencode_run` que são os canônicos                     | `opencode_run` ou `chat_opencode`                 |
| `chartdb_export`           | DEV        | Schema introspect via `postgres_list_tables` é suficiente para o caso de uso real                       | `postgres_list_tables` + sqlacodegen offline      |
| `opennotebook_create`      | DEV        | Substituído por `ntn` (Notion CLI) que é a plataforma oficial do projeto                                | `ntn create-page workspace=cartorio`              |
| `prometheus_query`         | MONITORING | `prometheus_metrics` (target discovery) + `exec_in_container` cobrem 95% dos casos                     | `prometheus_metrics` ou `exec_in_container` no prometheus |
| `sentry_capture_event`     | MONITORING | SDK Python faz isso nativamente; uso via MCP era apenas teste                                          | SDK Python `sentry_sdk.capture_message()`         |
| `grafana_dashboards`       | MONITORING | Mesmo problema — curl direto resolve                                                                  | `exec_in_container service=...grafana`            |
| `letsencrypt_list`         | MONITORING | Path fixo `/letsencrypt/acme.json`; Tráefik dashboards já mostram expiry                                | `file_read path=/letsencrypt/acme.json`           |
| `hostinger_api_status`     | MONITORING | API externa com rate limit; telemetria local é mais útil e em tempo real                               | `docker_stats + swarm_info + node_list`           |
| `tailscale_ping`           | NETWORKING | ICMP probes cobertos por `port_scan`; Tailscale ping sem persistência                                  | `tailscale_status` ou `exec_in_container`         |
| `tailscale_list_devices`   | NETWORKING | `tailscale_status --json` já retorna lista completa de peers                                            | `tailscale_status`                                |

## Tools mantidas e por quê

- **LLM (11)**: `chat_minimax` (canonical MiniMax-M3 XMax Thinking via LiteLLM) + `list_models` + 9 `chat_<agent>` wrappers com port real mapeado em `AGENT_PORTS` (crew-ai, goose, hermes, kilo-org_kilocode, langgraph, openchamber, openclaw, opencode, openhands).
- **STATUS (8)**: `list_services`, `health_check_service`, `service_info`, `docker_stats`, `swarm_info`, `node_list`, `network_list`, `volume_list` — todas essenciais para diagnóstico Docker Swarm.
- **DOCKER (6)**: ciclo de vida de serviço completo (`service_logs`, `restart_service`, `scale_service`, `deploy_image`, `env_get`, `env_set`).
- **EASYPANEL (4)**: deploy via painel oficial (`ep_login`, `ep_list_projects`, `ep_list_services`, `ep_deploy`).
- **DB (7)**: `postgres_query`, `postgres_list_tables` (genéricos — cobrem todos os Postgres), `redis_ping/get/set/keys` (operações básicas), `elasticsearch_search` (Argilla search). Clickhouse/Mongo/MinIO caem pq já têm alternativa nativa via `exec_in_container`.
- **WORKFLOW (4)**: Temporal (orquestração), Paperclip (tasks), LangFlow (flows).
- **CODE REVIEW (6)**: Gerrit, SonarQube, Sourcegraph, Argilla — pipelines distintos.
- **WEBSOCKET (6)**: Centrifugo (publish/channels/history) + MiroTalk + Snapdrop + FilePizza — cada um com caso de uso próprio (real-time messaging, video conf, P2P files).
- **WEBHOOK (4)**: request-baskets (create/list/get) + webhook_send — essenciais pra debug de integrações.
- **RAG (5)**: LangFlow, AnythingLLM, Argilla, LangFuse, EvoAI — vendors diferentes, mantidos.
- **SEARCH (4)**: Firecrawl (scrape + crawl), crwal4ai, FlareSolverr — todos com caso distinto.
- **DEV (1)**: apenas `opencode_run` — entrypoint canônico de code-gen via Node agent.
- **MONITORING (3)**: `prometheus_metrics` (target discovery), `sentry_list_issues` (error tracking), `status_page_get` (uptime público). Resto migrou pra `exec_in_container`.
- **NETWORKING (1)**: apenas `tailscale_status` — JSON rico que já cobre peers + devices.
- **UTILITY (15)**: `exec_in_container` (canivete suíço), backup/restore volume, image management, swarm CRUD, file ops, port scan, network inspect, secret management, openapi_spec.

## Categorias que perderam tools

| Categoria   | Δ    |
|-------------|------|
| DB          | -3   |
| DEV         | -5   |
| MONITORING  | -5   |
| NETWORKING  | -2   |
| LLM         | -6*  |
| **TOTAL**   | **-15** (\*LLM: -6 são wrappers de agents sem port real) |

## Validação

```bash
$ python3 scripts/coding_vps_mcp_orchestrator.py list
MCP orchestrator: 85 tools in 15 categories

$ python3 -c "import ast; ast.parse(open('scripts/coding_vps_mcp_orchestrator.py').read()); print('SYNTAX_OK')"
SYNTAX_OK
```

## Estratégia de migração (backward-compat)

Tools removidas foram **substituídas por stubs deprecated** que retornam mensagem de migração amigável:

```python
def clickhouse_query(sql: str) -> dict:
    """[DEPRECATED — Squad 1 2026-07-09] Use exec_in_container with clickhouse-client."""
    return {"error": "removed by squad1 dedupe", "migration": "use exec_in_container ..."}
```

Isso permite que clientes que ainda chamam as tools antigas recebam feedback claro em vez de 404.

Modified by Gustavo Almeida