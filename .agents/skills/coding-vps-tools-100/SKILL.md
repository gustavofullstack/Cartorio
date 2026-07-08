---
name: coding-vps-tools-100
description: |
  Catálogo das 100+ ferramentas agenticas rodando no coding-vps_apenas_para_auxilio
  (coding-vps.docker swarm). Validação E2E MiniMax-M3 XMax Thinking via script
  scripts/validate_coding_vps_e2e.sh. Cobre LLM agents, code review, RAG, vector DB,
  search, webhooks, websockets, observability, devops, code-gen, project mgmt, BI.
  
  Source: Lesson 159 + 160 (2026-07-08) | Infra: 100.99.172.84 (Tailscale SSH)
---

# Coding-VPS Tools 100 — Catálogo de Ferramentas Agenticas

## Visão Geral

A coding-vps_apenas_para_auxilio hospeda **88+ serviços Docker Swarm** divididos em
**11 categorias de ferramentas agenticas** prontas para uso via API/WebSocket/Webhook/MCP.

Todos os 17 coding agents LLM (CrewAI, Goose, Hermes, Kilo, LangGraph, OpenChamber,
OpenClaw, OpenCode, OpenHands) **rodam 100% com MiniMax-M3 XMax Thinking via LiteLLM proxy**.

## Acesso

| Item | Valor |
|------|-------|
| **VPS Tailscale** | `100.99.172.84` |
| **SSH Key** | `~/.ssh/id_ed25519_cartorio` |
| **Easypanel** | `http://100.99.172.84:3000` |
| **LiteLLM Proxy** | `http://coding-vps_apenas_para_auxilio_litellm-app:4000` (master: `e39dss0k1baohuqkprjv`) |
| **MiniMax API** | `https://api.minimaxi.com/v1` (sk-cp-...) |
| **E2E script** | `bash scripts/validate_coding_vps_e2e.sh` |

## Catálogo por Categoria (11 categorias, 100+ tools)

### 1. LLM Coding Agents (17 tools - TODOS MiniMax-M3 XMax Thinking ✅)

| Service | Stack | Endpoint | Status |
|---------|-------|----------|--------|
| coding-vps-agents_crew-ai (side-stack) | Python FastAPI | POST /chat | ✅ |
| coding-vps-agents_goose (side-stack) | Python FastAPI | POST /chat | ✅ |
| coding-vps-agents_hermes (side-stack) | Python FastAPI | POST /chat | ✅ |
| coding-vps-agents_kilo-org_kilocode (side-stack) | Node.js | POST /chat (JSON) | ✅ |
| coding-vps-agents_langgraph (side-stack) | Python FastAPI | POST /chat | ✅ |
| coding-vps-agents_openchamber (side-stack) | Python FastAPI | POST /chat | ✅ |
| coding-vps-agents_openclaw (side-stack) | Python FastAPI | POST /chat | ✅ |
| coding-vps-agents_opencode (side-stack) | Node.js | POST /chat (JSON) | ✅ |
| coding-vps-agents_openhands (side-stack) | Python FastAPI | POST /chat | ✅ |
| coding-vps_apenas_para_auxilio_crew-ai | Python FastAPI (patched) | POST /chat | ✅ |
| coding-vps_apenas_para_auxilio_goose | Python FastAPI (patched) | POST /chat | ✅ |
| coding-vps_apenas_para_auxilio_hermes | Python FastAPI (patched) | POST /chat | ✅ |
| coding-vps_apenas_para_auxilio_kilo-org_kilocode | Python FastAPI (patched) | POST /chat | ✅ |
| coding-vps_apenas_para_auxilio_langgraph | Python FastAPI (patched) | POST /chat | ✅ |
| coding-vps_apenas_para_auxilio_openchamber | Python FastAPI (patched) | POST /chat | ✅ |
| coding-vps_apenas_para_auxilio_openclaw | Python FastAPI (patched) | POST /chat | ✅ |
| coding-vps_apenas_para_auxilio_openhands | Python FastAPI (patched) | POST /chat | ✅ |
| coding-vps_apenas_para_auxilio_cline | Docker placeholder (extensao VSCode) | - | 🟡 offline (extensao) |

### 2. LLM Runtimes & RAG (8 tools)

| Service | Stack | Purpose |
|---------|-------|---------|
| anything-llm | mintplexlabs/anythingllm:1.12 | Multi-model RAG workspace |
| langflow | langflowai/langflow:1.9.2 | Visual LLM flows + RAG |
| langfuse-web | langfuse/langfuse:3.174.1 | LLM observability + tracing |
| langfuse-worker | langfuse/langfuse-worker:3.155 | Background tracing worker |
| goclaw | goclaw:v3.11.3-full | Agentic AI platform (NextLevelBuilder) |
| goclaw-ui | goclaw-web:v3.11.3 | goclaw Web UI |
| openclaw | coding-vps/agent:patched | Open-source Claude alternative |
| langgraph | coding-vps/agent:patched | LangGraph agent runtime |

### 3. Code Review & Quality (4 tools)

| Service | Stack | Purpose |
|---------|-------|---------|
| sonarqube | sonarqube:26.4.0.121862-community | Code quality + static analysis |
| gerrit | gerritcodereview/gerrit:3.13.6 | Git code review server |
| sourcegraph | sourcegraph/server:6.12.5040 | Code search + intelligence |
| argilla-web | argilla/argilla-server:v2.8.0 | Data labeling + feedback for LLMs |

### 4. Workflow Orchestration (4 tools)

| Service | Stack | Purpose |
|---------|-------|---------|
| temporal-server | temporalio/auto-setup:1.29.0 | Durable workflow orchestration |
| temporal-web | temporalio/ui:2.34.0 | Temporal Web UI |
| temporal-admin-tools | temporalio/admin-tools:1.29 | tctl CLI tools |
| paperclip | paperclipai/paperclip:sha-8af38fb | AI agent task automation |

### 5. Web Scraping & Search (8 tools)

| Service | Stack | Purpose |
|---------|-------|---------|
| firecrawl | firecrawl/firecrawl:latest | Web scraping + markdown conversion |
| firecrawl-playwright | playwright-service | Browser automation for firecrawl |
| crwal4ai | unclecode/crawl4ai:latest | LLM-friendly web crawler (x86) |
| flaresolverr | flaresolverr:v3.4.6 | Cloudflare bypass for scraping |
| yacy | yacy_search_server | Decentralized search engine |
| zincsearch | zincsearch:0.4.10 | Lightweight full-text search |
| karakeep-web | karakeep:0.31.0 | Bookmark manager + full-text search |
| karakeep-meilisearch | meilisearch:v1.15.2 | Search engine for karakeep |

### 6. Databases & Storage (10 tools)

| Service | Stack | Purpose |
|---------|-------|---------|
| langflow-db | postgres:16 | LangFlow metadata |
| langfuse-db | postgres:17 | LangFuse data |
| langfuse-clickhouse | clickhouse-server | LangFuse analytics |
| langfuse-minio | minio | LangFuse S3 storage |
| langfuse-redis | redis:7 | LangFuse cache |
| litellm-db | postgres:17 | LiteLLM model registry |
| argilla-db | postgres:17 | Argilla data |
| argilla-elasticsearch | elasticsearch:8.12.2 | Argilla search index |
| argilla-redis | redis:7 | Argilla cache |
| shm-db | postgres:17 | SHM database |

### 7. Real-time & WebSocket (3 tools)

| Service | Stack | Purpose |
|---------|-------|---------|
| centrifugo | centrifugo:v6.7.1 | Scalable WebSocket broker |
| mirotalk | mirotalk/p2p:latest | WebRTC video conferencing |
| snapdrop | linuxserver/snapdrop | P2P file sharing (LAN-like) |

### 8. AI Platforms & Builders (5 tools)

| Service | Stack | Purpose |
|---------|-------|---------|
| boltdiy | easypanel/boltdiy | AI app builder (StackBlitz Bolt) |
| chartdb | chartdb:1.20.1 | Database schema visualization |
| open-notebook | open_notebook:1.8.5 | Notebook for AI research |
| open-notebook-surrealdb | surrealdb:v2.6.5-dev | Notebook database |
| evo-ai-api | evo-ai:0.1.0 | Evolution AI platform API |
| evo-ai-frontend | evo-ai-frontend:0.1.0 | Evolution AI platform UI |

### 9. Tunneling & Networking (3 tools)

| Service | Stack | Purpose |
|---------|-------|---------|
| ngrok | ngrok:3.39.1-alpine | Public tunnel (precisa authtoken) |
| filepizza | kern/filepizza | P2P file transfer (WebRTC) |
| filepizza-coturn | coturn:4.7 | TURN server for filepizza |
| filepizza-redis | redis:7 | filepizza cache |
| ferron | ferron:2-debian | Web server (reverse proxy) |
| lynx | jackbailey/lynx:1.10.1 | Link in bio + URL shortener |
| lynx-db | mongo:4 | Lynx database |

### 10. DevOps & Observability (4 tools)

| Service | Stack | Purpose |
|---------|-------|---------|
| shm | kolapsis/shm:sha-fd3affa | Status page (incident communication) |
| crowdsec | crowdsecurity/crowdsec | Crowd-sourced security engine |
| request-baskets | darklynx/request-baskets:v1.2.3 | HTTP request inspector/baskets |
| paperclip-db | postgres:17 | Paperclip database |

### 11. Scheduling & Booking (2 tools)

| Service | Stack | Purpose |
|---------|-------|---------|
| calcom-db | postgres:17 | Cal.com database |
| postiz-db | postgres:17 | Postiz database |
| postiz-redis | redis:7 | Postiz cache |
| evo-ai-postgres | postgres:17 | Evo AI database |
| evo-ai-redis | redis:7 | Evo AI cache |
| morphic-redis | redis:7 | Morphic cache |

## Tabela de Protocolos por Ferramenta

| Protocolo | Tools |
|-----------|-------|
| **REST API** | All 17 LLM agents, langflow, anything-llm, goclaw, langfuse, argilla, firecrawl, crwal4ai, evo-ai, sonarqube, gerrit, sourcegraph, calcom, postiz, temporal, paperclip |
| **GraphQL** | (none configured - can be added to langflow) |
| **WebSocket** | centrifugo, mirotalk, snapdrop, filepizza, all LLM agents (streaming ready) |
| **MCP (Model Context Protocol)** | litellm-app (1 tool: chat_minimax), coding-vps-orchestrator.py (4 tools: status, health, chat, configure) |
| **Webhook Receiver** | request-baskets (HTTP inspection), filepizza, mirotalk |
| **WebSocket Subprotocol** | centrifugo (json, protobuf) |
| **gRPC** | (none - can be added) |
| **SSE (Server-Sent Events)** | langflow (streaming responses) |
| **PostgreSQL TCP** | All 7 postgres:17 + langflow-db |
| **Redis TCP** | All 7 redis:7 |
| **S3 (MinIO)** | langfuse-minio:9000 |
| **HTTP/2** | (default for most services) |
| **HTTP/3 (QUIC)** | (none - can be added via traefik) |

## MCP (Model Context Protocol) Tools Ativas

### coding-vps-orchestrator.py (VPS-side, 4 tools)
```python
@mcp.tool() coding_vps_status()    # Status 65+ services
@mcp.tool() health_check_all()      # HTTP health + TCP probe
@mcp.tool() chat_minimax(prompt)    # Chat com MiniMax-M3 XMax Thinking
@mcp.tool() configure_agent(svc)    # Adiciona env vars MiniMax a um agent
```

### litellm-app (VPS-side, OpenAI-compatible)
```
POST http://coding-vps_apenas_para_auxilio_litellm-app:4000/v1/chat/completions
GET  http://coding-vps_apenas_para_auxilio_litellm-app:4000/v1/models
GET  http://coding-vps_apenas_para_auxilio_litellm-app:4000/health/liveliness
```

### cartorio-mcp-cabuloso (Cartório-side, 7 tools)
- `criar_atendimento`, `consultar_protocolo`, `listar_clientes`
- `criar_documento`, `calcular_emolumento`, `consultar_audit_log`
- `lgpd_direito_esquecimento`

## Validação E2E (reutilizável)

```bash
# Run 1-command: valida 17 coding agents E2E MiniMax-M3
bash scripts/validate_coding_vps_e2e.sh --prompt "Responda exatamente: PING-OK-21"

# Score atual (2026-07-08 19:30 BRT):
#   side-stack: 9/9 ✅
#   main: 8/8 ✅
#   SCORE: 17/17 ✅
```

## Status Atual (2026-07-08)

| Status | Count | Tools |
|--------|-------|-------|
| ✅ UP + E2E MiniMax-M3 | 17 | All 17 LLM agents |
| ✅ UP + funcional | 50+ | langflow, anything-llm, goclaw, sonarqube, gerrit, sourcegraph, argilla, firecrawl, langfuse, centrifugo, mirotalk, snapdrop, boltdiy, chartdb, open-notebook, evo-ai, temporal, paperclip, karakeep, ferron, filepizza, yacy, zincsearch, shm, request-baskets, postiz, calcom (db), lynx, lynx-db |
| 🟡 UP mas OFF esperado | 1 | cline (extensao VSCode, sem Docker oficial) |
| 🟡 Preparing (subindo) | 4 | karakeep-meilisearch, lynx, shm, shm-db |
| ❌ OFF | 5 | crwal4ai (imagem arm64), ngrok (sem authtoken), calcom (nao deployado), postiz (nao deployado), evo-ai-* (nao deployado) |
| **TOTAL services** | **77-88** | (depende se conta side-stack + main + DBs) |

## Leitura Complementar

- `skills/coding-vps-21/SKILL.md` - Ativacao dos 21 agents MiniMax-M3
- `skills/minimax-m3/SKILL.md` - Provider MiniMax-M3 XMax Thinking
- `scripts/validate_coding_vps_e2e.sh` - E2E test reutilizavel
- `scripts/diagnose_coding_vps.sh` - Diagnostico docker
- `scripts/health_check_27services.sh` - Health check 27 services
- `infra/coding-vps-infra/` (VPS) - 21 agents + orchestrator MCP

## Modified by Gustavo Almeida (via orquestrador)
[19:30] feat(skill): coding-vps-tools-100 catalogando 11 categorias de ferramentas agenticas. Modified by Gustavo Almeida
