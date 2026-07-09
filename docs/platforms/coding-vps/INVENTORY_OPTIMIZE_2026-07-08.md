# Coding VPS Inventory & Optimization Classification

**Host:** `100.99.172.84` (srv1769726)  
**Date:** 2026-07-08  
**Scope:** Docker Swarm stacks `coding-vps_apenas_para_auxilio` and `coding-vps-agents`  
**Action:** Document only — **no deletes, no scale changes** performed by this inventory.  
**Out of scope:** `cartorio_*` services (not touched).

---

## 1. Host health snapshot

| Metric | Value | Notes |
|--------|-------|-------|
| Uptime | 16 days, 7:15 | Snapshot ~01:52 UTC-ish local |
| Load average | **15.38 / 10.61 / 9.63** | High for 15 GiB box — contention |
| RAM | 15 GiB total, **8.9 GiB used**, 379 MiB free, **6.7 GiB available** | Pressure relieved by page cache |
| Swap | 4.0 GiB total, **3.6 GiB used**, 366 MiB free | **Critical** — thrashing risk |
| Root disk `/` | 193 G total, **102 G used (53%)**, 92 G avail | OK |
| Docker images | 82 total / 53 active — **91.18 GB** (26.2 GB reclaimable) | Large image footprint |
| Docker containers | 152 total / 71 active — 535 MB | |
| Local volumes | 21 / 15 active — 1.33 GB | |
| Build cache | 106 / 18 active — 5.0 GB | |

**Coding-VPS live containers (fresh pass):** ~26 running, ~**1.8 GiB** RSS combined (approx from `docker stats`).

### Volatility during inventory

Two scrapes ~minutes apart:

| Item | First scrape | Fresh scrape (authoritative for tables below) |
|------|--------------|-----------------------------------------------|
| `coding-vps-agents_*` services | **10 services present** (9× `1/1`, opencode `0/1`) | **Stack gone** (`docker service ls` empty for agents) |
| Heavy apps (SonarQube, Sourcegraph, Temporal, Paperclip, ChartDB, MiroTalk, Open Notebook, Argilla DBs) | Several reported `1/1` | All **`0/0`** |
| Live coding-vps containers | Mixed | **26** |

→ Someone/something was already scaling down. Tables reflect the **fresh** state; §7 records the agents stack as **DELETE_DUPLICATE** historical inventory.

---

## 2. Classification legend

| Class | Meaning |
|-------|---------|
| **KEEP_CORE** | Coding agents (patched), LiteLLM, MCP orchestrator, essential DBs for those |
| **KEEP_USEFUL** | Langflow, Langfuse, ZincSearch, Centrifugo, CrowdSec, Request Baskets; Temporal **if** productively used |
| **SCALE_DOWN** | Heavy / rarely used apps — keep service def optional, replicas 0 until needed |
| **DELETE_DUPLICATE** | Side-stack agents that duplicate main patched agents |
| **ZOMBIE_0** | Already `0/0`; never needed or retired — candidates to **remove service definition** (cleanup only, not done here) |

---

## 3. Summary counts (fresh state)

| Classification | Count | Notes |
|----------------|------:|-------|
| **KEEP_CORE** | **12** | 9 agents + litellm-app + litellm-db + mcp-orchestrator |
| **KEEP_USEFUL** | **13** | langflow(+db), langfuse×6, zincsearch, centrifugo, crowdsec, request-baskets |
| **SCALE_DOWN** | **3** | anything-llm, crawl4ai (`crwal4ai`), ngrok (desired 1 but failing) |
| **DELETE_DUPLICATE** | **10** | entire `coding-vps-agents` stack (removed during inventory; documented) |
| **ZOMBIE_0** | **52** | all remaining `0/0` on main stack |
| **Total services documented** | **90** | 80 main-stack fresh + 10 agents historical |

### Replica status (main stack only, fresh)

| Replicas | Count |
|----------|------:|
| `1/1` running | **26** |
| `0/1` failing desired | **1** (ngrok) |
| `0/0` scaled off | **53** |
| **Total main stack** | **80** |

`coding-vps-agents`: **0** services present after second scrape (was 10).

---

## 4. Top 10 memory hogs (coding-vps live containers)

From `docker stats --no-stream` (fresh), sorted by usage:

| # | Service (short) | Mem usage | Limit | Class |
|--:|-----------------|----------:|------:|-------|
| 1 | `langfuse-clickhouse` | **425 MiB** | 1.5 GiB | KEEP_USEFUL |
| 2 | `langfuse-web` | **218 MiB** | 512 MiB | KEEP_USEFUL |
| 3 | `litellm-app` | **172 MiB** | 2 GiB | KEEP_CORE |
| 4 | `langfuse-worker` | **143 MiB** | 512 MiB | KEEP_USEFUL |
| 5 | `crowdsec` | **106 MiB** | 512 MiB | KEEP_USEFUL |
| 6 | `crwal4ai` (crawl4ai) | **82 MiB** | 512 MiB | SCALE_DOWN |
| 7 | `langfuse-minio` | **70 MiB** | 512 MiB | KEEP_USEFUL |
| 8 | `langflow` | **49 MiB** | 1 GiB | KEEP_USEFUL |
| 9 | `crew-ai` | **39 MiB** | 512 MiB | KEEP_CORE |
| 10 | `mcp-orchestrator` | **37 MiB** | unlimited | KEEP_CORE |

**Langfuse cluster alone ≈ 425+218+143+70+17+5 ≈ 878 MiB** — largest useful non-core consumer.  
**LiteLLM** is the heaviest true core process.

If swap pressure persists after zombie cleanup: (1) scale crawl4ai + anything-llm to 0 when idle; (2) consider ClickHouse memory caps / Langfuse retention; (3) do **not** re-enable SonarQube/Sourcegraph/Temporal without dedicated RAM.

---

## 5. KEEP_CORE — agents, LiteLLM, MCP, essential DBs

| Name | Replicas | Image | Mem (live / limit) | Classification | Reason |
|------|----------|-------|--------------------|----------------|--------|
| `…_crew-ai` | 1/1 | `coding-vps/agent:patched` | ~39 MiB / 512 MiB | KEEP_CORE | Main patched agent |
| `…_goose` | 1/1 | `coding-vps/agent:patched` | ~25 MiB / 512 MiB | KEEP_CORE | Main patched agent |
| `…_hermes` | 1/1 | `coding-vps/agent:patched` | ~25 MiB / 512 MiB | KEEP_CORE | Main patched agent |
| `…_kilo-org_kilocode` | 1/1 | `coding-vps/agent:patched` | ~33 MiB / 512 MiB | KEEP_CORE | Main patched agent (port map used by agents stack historically) |
| `…_langgraph` | 1/1 | `coding-vps/agent:patched` | ~25 MiB / 512 MiB | KEEP_CORE | Main patched agent |
| `…_openchamber` | 1/1 | `coding-vps/agent:patched` | ~28 MiB / 512 MiB | KEEP_CORE | Main patched agent |
| `…_openclaw` | 1/1 | `coding-vps/agent:patched` | ~26 MiB / 512 MiB | KEEP_CORE | Main patched agent |
| `…_opencode` | 1/1 | `easypanel/coding-vps_apenas_para_auxilio/opencode:latest` | ~28 MiB / 512 MiB | KEEP_CORE | Agent surface; **image not `:patched`** — align with others if possible |
| `…_openhands` | 1/1 | `coding-vps/agent:patched` | ~27 MiB / 512 MiB | KEEP_CORE | Main patched agent |
| `…_litellm-app` | 1/1 | `ghcr.io/berriai/litellm:v1.85.0` | ~172 MiB / 2 GiB | KEEP_CORE | LLM gateway for agents |
| `…_litellm-db` | 1/1 | `postgres:17` | ~35 MiB / unlimited | KEEP_CORE | LiteLLM state DB |
| `…_mcp-orchestrator` | 1/1 | `coding-vps/mcp-orchestrator:latest` | ~37 MiB / unlimited | KEEP_CORE | MCP hub; **no mem limit** — consider 512 MiB–1 GiB cap |

Prefix: `coding-vps_apenas_para_auxilio_`.

**Approx core RSS:** ~500 MiB (agents ~250 + litellm ~210 + mcp ~37).

---

## 6. KEEP_USEFUL — observability, realtime, security, light tooling

| Name | Replicas | Image | Mem (live / limit) | Classification | Reason |
|------|----------|-------|--------------------|----------------|--------|
| `…_langflow` | 1/1 | `langflowai/langflow:1.9.2` | ~49 MiB / 1 GiB | KEEP_USEFUL | Visual agent flows |
| `…_langflow-db` | 1/1 | `postgres:16` | ~24 MiB / 512 MiB | KEEP_USEFUL | Langflow DB |
| `…_langfuse-web` | 1/1 | `langfuse/langfuse:3.174.1` | ~218 MiB / 512 MiB | KEEP_USEFUL | LLM observability UI (CPU-hot in samples) |
| `…_langfuse-worker` | 1/1 | `langfuse/langfuse-worker:3.155` | ~143 MiB / 512 MiB | KEEP_USEFUL | Langfuse async worker |
| `…_langfuse-db` | 1/1 | `postgres:17` | ~17 MiB / 512 MiB | KEEP_USEFUL | Langfuse PG |
| `…_langfuse-clickhouse` | 1/1 | `clickhouse/clickhouse-server:latest` | **~425 MiB / 1.5 GiB** | KEEP_USEFUL | Heaviest useful service — keep only if traces used |
| `…_langfuse-minio` | 1/1 | `minio/minio:latest` | ~70 MiB / 512 MiB | KEEP_USEFUL | Langfuse blob store |
| `…_langfuse-redis` | 1/1 | `redis:7` | ~5 MiB / 512 MiB | KEEP_USEFUL | Langfuse cache/queue |
| `…_zincsearch` | 1/1 | `public.ecr.aws/zinclabs/zincsearch:0.4.10` | ~23 MiB / 512 MiB | KEEP_USEFUL | Light log/search |
| `…_centrifugo` | 1/1 | `centrifugo/centrifugo:v6.7.1` | ~15 MiB / 512 MiB | KEEP_USEFUL | Realtime websocket bus |
| `…_crowdsec` | 1/1 | `crowdsecurity/crowdsec:latest` | ~106 MiB / 512 MiB | KEEP_USEFUL | IDS / ban automation |
| `…_request-baskets` | 1/1 | `darklynx/request-baskets:v1.2.3` | ~11 MiB / 512 MiB | KEEP_USEFUL | Webhook dump/debug |
| **Temporal stack** (see ZOMBIE_0) | 0/0 | temporalio/* + ES + PG | — | KEEP_USEFUL **if re-enabled with demand** | Currently scaled to 0; treat as on-demand, not always-on |

---

## 7. DELETE_DUPLICATE — `coding-vps-agents` (historical first scrape)

These **duplicated** the main stack’s patched agents with separate images (`coding-vps/<agent>:latest|patched`). Present only on first scrape; **removed by second scrape**. Do not recreate.

| Name | Replicas (1st) | Image | Classification | Reason |
|------|----------------|-------|----------------|--------|
| `coding-vps-agents_crew-ai` | 1/1 | `coding-vps/crew-ai:latest` | DELETE_DUPLICATE | Dup of main `crew-ai` patched |
| `coding-vps-agents_goose` | 1/1 | `coding-vps/goose:latest` | DELETE_DUPLICATE | Dup of main goose |
| `coding-vps-agents_hermes` | 1/1 | `coding-vps/hermes:latest` | DELETE_DUPLICATE | Dup of main hermes |
| `coding-vps-agents_kilo-org_kilocode` | 1/1 | `coding-vps/kilo-org_kilocode:patched` | DELETE_DUPLICATE | Dup; had `*:8004->8000/tcp` |
| `coding-vps-agents_langgraph` | 1/1 | `coding-vps/langgraph:latest` | DELETE_DUPLICATE | Dup of main langgraph |
| `coding-vps-agents_openchamber` | 1/1 | `coding-vps/openchamber:latest` | DELETE_DUPLICATE | Dup |
| `coding-vps-agents_openclaw` | 1/1 | `coding-vps/openclaw:latest` | DELETE_DUPLICATE | Dup |
| `coding-vps-agents_opencode` | 0/1 | `coding-vps/opencode:patched` | DELETE_DUPLICATE | Dup; was unhealthy |
| `coding-vps-agents_openhands` | 1/1 | `coding-vps/openhands:latest` | DELETE_DUPLICATE | Dup |
| *(implicit 10th from first list)* | — | — | DELETE_DUPLICATE | Stack fully absent on recheck |

**Recommendation:** Keep **only** `coding-vps_apenas_para_auxilio_*` agents with `coding-vps/agent:patched`. Prefer single image family + shared LiteLLM.

---

## 8. SCALE_DOWN — heavy / optional while running

| Name | Replicas | Image | Mem | Classification | Reason |
|------|----------|-------|-----|----------------|--------|
| `…_anything-llm` | 1/1 | `mintplexlabs/anythingllm:1.12` | ~33 MiB / 512 MiB | SCALE_DOWN | Nice RAG UI; not required for agent pipeline; scale 0 when idle |
| `…_crwal4ai` | 1/1 | `unclecode/crawl4ai:latest` | **~82 MiB** / 512 MiB | SCALE_DOWN | Browser crawl stack; intermittent use; top optional RSS |
| `…_ngrok` | **0/1** | `ngrok/ngrok:3.39.1-alpine` | — | SCALE_DOWN | Desired 1 but not running — fix token/config or set replicas 0 |

---

## 9. ZOMBIE_0 — already `0/0` (main stack)

Candidates to **remove service definitions** or leave parked. **No deletes performed.**

### 9.1 Heavy product stacks (SCALE_DOWN if ever re-enabled; currently ZOMBIE_0)

| Name | Replicas | Image | Reason |
|------|----------|-------|--------|
| `…_sonarqube` | 0/0 | `sonarqube:26.4.0.121862-community` | Heavy JVM (limit was 2 GiB when up) — on-demand only |
| `…_sonarqube-db` | 0/0 | `postgres:17` | Companion |
| `…_sourcegraph` | 0/0 | `sourcegraph/server:6.12.5040` | Very heavy mono image — avoid on 15 GiB host |
| `…_temporal-server` | 0/0 | `temporalio/auto-setup:1.29.0` | Workflow engine — re-enable only with workload |
| `…_temporal-web` | 0/0 | `temporalio/ui:2.34.0` | UI |
| `…_temporal-admin-tools` | 0/0 | `temporalio/admin-tools:1.29` | Ops tools |
| `…_temporal-db` | 0/0 | `postgres:17` | Companion |
| `…_temporal-elasticsearch` | 0/0 | `elasticsearch:9.1.0` | ES is RAM-hungry |
| `…_firecrawl` | 0/0 | `ghcr.io/firecrawl/firecrawl:latest` | Full crawl platform |
| `…_firecrawl-playwright` | 0/0 | `ghcr.io/firecrawl/playwright-service:latest` | Browser workers |
| `…_firecrawl-rabbitmq` | 0/0 | `rabbitmq:3-management` | Queue |
| `…_firecrawl-redis` | 0/0 | `redis:alpine` | Cache |
| `…_firecrawl-nuq-postgres` | 0/0 | `ghcr.io/firecrawl/nuq-postgres:latest` | DB |
| `…_flaresolverr` | 0/0 | `ghcr.io/flaresolverr/flaresolverr:v3.4.6` | CF bypass helper |
| `…_goclaw` | 0/0 | `ghcr.io/nextlevelbuilder/goclaw:v3.11.3-full` | Alt claw stack |
| `…_goclaw-ui` | 0/0 | `ghcr.io/nextlevelbuilder/goclaw-web:v3.11.3` | UI |
| `…_goclaw-chrome` | 0/0 | `zenika/alpine-chrome:124` | Browser |
| `…_goclaw-db` | 0/0 | `pgvector/pgvector:pg17` | DB |
| `…_gerrit` | 0/0 | `gerritcodereview/gerrit:3.13.6` | Code review — unused |
| `…_paperclip` | 0/0 | `ghcr.io/paperclipai/paperclip:sha-8af38fb` | Rare tool |
| `…_paperclip-db` | 0/0 | `postgres:17` | Companion |
| `…_open-notebook` | 0/0 | `lfnovo/open_notebook:1.8.5` | Notebook UI |
| `…_open-notebook-surrealdb` | 0/0 | `surrealdb/surrealdb:v2.6.5-dev` | Companion |
| `…_argilla-web` | 0/0 | `argilla/argilla-server:v2.8.0` | Labeling stack |
| `…_argilla-worker` | 0/0 | `argilla/argilla-server:v2.8.0` | Worker |
| `…_argilla-elasticsearch` | 0/0 | `elasticsearch:8.12.2` | ES |
| `…_argilla-db` | 0/0 | `postgres:17` | Was orphan-running earlier; now 0 |
| `…_argilla-redis` | 0/0 | `redis:7` | Was orphan-running earlier; now 0 |

### 9.2 Collab / share / misc (never essential on coding VPS)

| Name | Replicas | Image | Reason |
|------|----------|-------|--------|
| `…_boltdiy` | 0/0 | `easypanel/.../boltdiy:latest` | DIY builder — unused |
| `…_calcom-db` | 0/0 | `postgres:17` | Orphan DB (no calcom app) |
| `…_chartdb` | 0/0 | `ghcr.io/chartdb/chartdb:1.20.1` | Schema visualizer |
| `…_evo-ai-api` | 0/0 | `evoapicloud/evo-ai:0.1.0` | Alt AI stack |
| `…_evo-ai-frontend` | 0/0 | `evoapicloud/evo-ai-frontend:0.1.0` | UI |
| `…_evo-ai-postgres` | 0/0 | `postgres:17` | Companion |
| `…_evo-ai-redis` | 0/0 | `redis:7` | Companion |
| `…_ferron` | 0/0 | `ferronserver/ferron:2-debian` | Web server experiment |
| `…_filepizza` | 0/0 | `kern/filepizza:3258673` | P2P file transfer |
| `…_filepizza-coturn` | 0/0 | `coturn/coturn:4.7` | TURN |
| `…_filepizza-redis` | 0/0 | `redis:7` | Companion (was orphan-running earlier) |
| `…_karakeep-web` | 0/0 | `ghcr.io/karakeep-app/karakeep:0.31.0` | Bookmarks |
| `…_karakeep-meilisearch` | 0/0 | `getmeili/meilisearch:v1.15.2` | Search |
| `…_karakeep-chrome` | 0/0 | `gcr.io/zenika-hub/alpine-chrome:123` | Browser |
| `…_lynx` | 0/0 | `jackbailey/lynx:1.10.1` | Link shortener-ish |
| `…_lynx-db` | 0/0 | `mongo:4` | Companion |
| `…_maxun-db` | 0/0 | `postgres:17` | Orphan (no maxun app) |
| `…_mirotalk` | 0/0 | `mirotalk/p2p:latest` | WebRTC chat |
| `…_morphic-redis` | 0/0 | `redis:7` | Orphan redis |
| `…_postiz-db` | 0/0 | `postgres:17` | Social scheduler stack gone |
| `…_postiz-redis` | 0/0 | `redis:7` | Companion |
| `…_shm` | 0/0 | `ghcr.io/kolapsis/shm:sha-fd3affa` | Unused app |
| `…_shm-db` | 0/0 | `postgres:17` | Companion |
| `…_snapdrop` | 0/0 | `lscr.io/linuxserver/snapdrop:…` | Local file drop |
| `…_yacy` | 0/0 | `yacy/yacy_search_server:…` | P2P search — heavy when up |

**ZOMBIE_0 subtotal:** 52 services (fresh main stack `0/0`).

---

## 10. Full master table (main stack, fresh)

| Name | Replicas | Image | Mem if known | Class | Reason |
|------|----------|-------|--------------|-------|--------|
| anything-llm | 1/1 | mintplexlabs/anythingllm:1.12 | ~33 MiB / 512 MiB | SCALE_DOWN | Optional RAG UI |
| argilla-db | 0/0 | postgres:17 | — | ZOMBIE_0 | App off |
| argilla-elasticsearch | 0/0 | elasticsearch:8.12.2 | — | ZOMBIE_0 | App off |
| argilla-redis | 0/0 | redis:7 | — | ZOMBIE_0 | App off |
| argilla-web | 0/0 | argilla-server:v2.8.0 | — | ZOMBIE_0 | Unused labeling |
| argilla-worker | 0/0 | argilla-server:v2.8.0 | — | ZOMBIE_0 | Unused |
| boltdiy | 0/0 | easypanel boltdiy:latest | — | ZOMBIE_0 | Unused |
| calcom-db | 0/0 | postgres:17 | — | ZOMBIE_0 | Orphan DB |
| centrifugo | 1/1 | centrifugo:v6.7.1 | ~15 MiB / 512 MiB | KEEP_USEFUL | Realtime |
| chartdb | 0/0 | chartdb:1.20.1 | — | ZOMBIE_0 | Rare schema UI |
| crew-ai | 1/1 | coding-vps/agent:patched | ~39 MiB / 512 MiB | KEEP_CORE | Agent |
| crowdsec | 1/1 | crowdsec:latest | ~106 MiB / 512 MiB | KEEP_USEFUL | Security |
| crwal4ai | 1/1 | crawl4ai:latest | ~82 MiB / 512 MiB | SCALE_DOWN | On-demand crawl |
| evo-ai-api | 0/0 | evo-ai:0.1.0 | — | ZOMBIE_0 | Dup AI product |
| evo-ai-frontend | 0/0 | evo-ai-frontend:0.1.0 | — | ZOMBIE_0 | Dup AI product |
| evo-ai-postgres | 0/0 | postgres:17 | — | ZOMBIE_0 | Companion |
| evo-ai-redis | 0/0 | redis:7 | — | ZOMBIE_0 | Companion |
| ferron | 0/0 | ferron:2-debian | — | ZOMBIE_0 | Experiment |
| filepizza | 0/0 | filepizza | — | ZOMBIE_0 | P2P share |
| filepizza-coturn | 0/0 | coturn:4.7 | — | ZOMBIE_0 | Companion |
| filepizza-redis | 0/0 | redis:7 | — | ZOMBIE_0 | Companion |
| firecrawl | 0/0 | firecrawl:latest | — | ZOMBIE_0 | Heavy crawl platform |
| firecrawl-nuq-postgres | 0/0 | nuq-postgres | — | ZOMBIE_0 | Companion |
| firecrawl-playwright | 0/0 | playwright-service | — | ZOMBIE_0 | Companion |
| firecrawl-rabbitmq | 0/0 | rabbitmq:3-management | — | ZOMBIE_0 | Companion |
| firecrawl-redis | 0/0 | redis:alpine | — | ZOMBIE_0 | Companion |
| flaresolverr | 0/0 | flaresolverr:v3.4.6 | — | ZOMBIE_0 | Helper for firecrawl |
| gerrit | 0/0 | gerrit:3.13.6 | — | ZOMBIE_0 | Code review unused |
| goclaw | 0/0 | goclaw:v3.11.3-full | — | ZOMBIE_0 | Alt agent stack |
| goclaw-chrome | 0/0 | alpine-chrome:124 | — | ZOMBIE_0 | Companion |
| goclaw-db | 0/0 | pgvector:pg17 | — | ZOMBIE_0 | Companion |
| goclaw-ui | 0/0 | goclaw-web:v3.11.3 | — | ZOMBIE_0 | Companion |
| goose | 1/1 | coding-vps/agent:patched | ~25 MiB / 512 MiB | KEEP_CORE | Agent |
| hermes | 1/1 | coding-vps/agent:patched | ~25 MiB / 512 MiB | KEEP_CORE | Agent |
| karakeep-chrome | 0/0 | alpine-chrome:123 | — | ZOMBIE_0 | Bookmarks stack |
| karakeep-meilisearch | 0/0 | meilisearch:v1.15.2 | — | ZOMBIE_0 | Companion |
| karakeep-web | 0/0 | karakeep:0.31.0 | — | ZOMBIE_0 | Companion |
| kilo-org_kilocode | 1/1 | coding-vps/agent:patched | ~33 MiB / 512 MiB | KEEP_CORE | Agent |
| langflow | 1/1 | langflow:1.9.2 | ~49 MiB / 1 GiB | KEEP_USEFUL | Flows |
| langflow-db | 1/1 | postgres:16 | ~24 MiB / 512 MiB | KEEP_USEFUL | DB |
| langfuse-clickhouse | 1/1 | clickhouse-server:latest | ~425 MiB / 1.5 GiB | KEEP_USEFUL | Observability (heavy) |
| langfuse-db | 1/1 | postgres:17 | ~17 MiB / 512 MiB | KEEP_USEFUL | DB |
| langfuse-minio | 1/1 | minio:latest | ~70 MiB / 512 MiB | KEEP_USEFUL | Blobs |
| langfuse-redis | 1/1 | redis:7 | ~5 MiB / 512 MiB | KEEP_USEFUL | Cache |
| langfuse-web | 1/1 | langfuse:3.174.1 | ~218 MiB / 512 MiB | KEEP_USEFUL | UI |
| langfuse-worker | 1/1 | langfuse-worker:3.155 | ~143 MiB / 512 MiB | KEEP_USEFUL | Worker |
| langgraph | 1/1 | coding-vps/agent:patched | ~25 MiB / 512 MiB | KEEP_CORE | Agent |
| litellm-app | 1/1 | litellm:v1.85.0 | ~172 MiB / 2 GiB | KEEP_CORE | LLM gateway |
| litellm-db | 1/1 | postgres:17 | ~35 MiB / ∞ | KEEP_CORE | Essential DB |
| lynx | 0/0 | lynx:1.10.1 | — | ZOMBIE_0 | Unused |
| lynx-db | 0/0 | mongo:4 | — | ZOMBIE_0 | Companion |
| maxun-db | 0/0 | postgres:17 | — | ZOMBIE_0 | Orphan DB |
| mcp-orchestrator | 1/1 | mcp-orchestrator:latest | ~37 MiB / ∞ | KEEP_CORE | MCP hub |
| mirotalk | 0/0 | mirotalk/p2p:latest | — | ZOMBIE_0 | WebRTC unused |
| morphic-redis | 0/0 | redis:7 | — | ZOMBIE_0 | Orphan |
| ngrok | 0/1 | ngrok:3.39.1-alpine | — | SCALE_DOWN | Failing tunnel |
| open-notebook | 0/0 | open_notebook:1.8.5 | — | ZOMBIE_0 | Optional notebook |
| open-notebook-surrealdb | 0/0 | surrealdb:v2.6.5-dev | — | ZOMBIE_0 | Companion |
| openchamber | 1/1 | coding-vps/agent:patched | ~28 MiB / 512 MiB | KEEP_CORE | Agent |
| openclaw | 1/1 | coding-vps/agent:patched | ~26 MiB / 512 MiB | KEEP_CORE | Agent |
| opencode | 1/1 | easypanel …/opencode:latest | ~28 MiB / 512 MiB | KEEP_CORE | Agent (unpatched image) |
| openhands | 1/1 | coding-vps/agent:patched | ~27 MiB / 512 MiB | KEEP_CORE | Agent |
| paperclip | 0/0 | paperclip:sha-8af38fb | — | ZOMBIE_0 | Rare |
| paperclip-db | 0/0 | postgres:17 | — | ZOMBIE_0 | Companion |
| postiz-db | 0/0 | postgres:17 | — | ZOMBIE_0 | Social stack off |
| postiz-redis | 0/0 | redis:7 | — | ZOMBIE_0 | Companion |
| request-baskets | 1/1 | request-baskets:v1.2.3 | ~11 MiB / 512 MiB | KEEP_USEFUL | Webhook debug |
| shm | 0/0 | shm:sha-fd3affa | — | ZOMBIE_0 | Unused |
| shm-db | 0/0 | postgres:17 | — | ZOMBIE_0 | Companion |
| snapdrop | 0/0 | snapdrop | — | ZOMBIE_0 | File drop |
| sonarqube | 0/0 | sonarqube community | — | ZOMBIE_0 | Heavy — on-demand |
| sonarqube-db | 0/0 | postgres:17 | — | ZOMBIE_0 | Companion |
| sourcegraph | 0/0 | sourcegraph/server:6.12.5040 | — | ZOMBIE_0 | Too heavy for host |
| temporal-admin-tools | 0/0 | admin-tools:1.29 | — | ZOMBIE_0 | On-demand Temporal |
| temporal-db | 0/0 | postgres:17 | — | ZOMBIE_0 | Companion |
| temporal-elasticsearch | 0/0 | elasticsearch:9.1.0 | — | ZOMBIE_0 | Heavy companion |
| temporal-server | 0/0 | auto-setup:1.29.0 | — | ZOMBIE_0 | On-demand |
| temporal-web | 0/0 | ui:2.34.0 | — | ZOMBIE_0 | On-demand |
| yacy | 0/0 | yacy_search_server | — | ZOMBIE_0 | P2P search unused |
| zincsearch | 1/1 | zincsearch:0.4.10 | ~23 MiB / 512 MiB | KEEP_USEFUL | Light search/logs |

*(Names abbreviated; full Swarm name = `coding-vps_apenas_para_auxilio_<name>`.)*

---

## 11. Resource limits observed

| Pattern | Limit |
|---------|-------|
| Most services | **512 MiB** |
| langflow | 1 GiB |
| langfuse-clickhouse | **1.5 GiB** |
| litellm-app | **2 GiB** |
| sonarqube (when defined) | 2 GiB |
| temporal-server (when defined) | 1 GiB |
| litellm-db, mcp-orchestrator, sourcegraph, sonarqube-db | **0 (unlimited)** |

**Gap:** `mcp-orchestrator` and `litellm-db` should get explicit limits to protect the host.

---

## 12. Recommended next actions (documentation only — not executed)

1. **Confirm** `coding-vps-agents` stack stays removed (DELETE_DUPLICATE done by environment already).
2. **Scale to 0 when idle:** `crwal4ai`, `anything-llm`, fix or zero `ngrok`.
3. **Prune ZOMBIE_0 service definitions** in EasyPanel/Swarm after volume backup review (especially orphan Postgres volumes).
4. **Never co-schedule** Sourcegraph + SonarQube + Temporal ES + Langfuse ClickHouse on this 15 GiB node.
5. **Image reclaim:** `docker system df` shows **~26 GB reclaimable images** — safe prune after snapshot.
6. **Swap:** 3.6/4 GiB used — prioritize reducing Langfuse ClickHouse or optional crawlers before adding any heavy stack.
7. **Align** `opencode` image to `coding-vps/agent:patched` like peers.
8. **Cap** `mcp-orchestrator` + `litellm-db` memory.

---

## 13. Commands used

```bash
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84
docker service ls | grep coding-vps
free -h; uptime; df -h /
docker system df
docker stats --no-stream   # filtered to coding-vps
docker service inspect …   # memory limits
```

---

## 14. Classification count rollup

Strict exclusive class for **fresh main stack (`coding-vps_apenas_para_auxilio`, 80 services)**:

| Class | Count |
|-------|------:|
| KEEP_CORE | 12 |
| KEEP_USEFUL | 12 |
| SCALE_DOWN | 3 |
| ZOMBIE_0 | 53 |
| **Main stack total** | **80** |

Plus historical **DELETE_DUPLICATE = 10** (`coding-vps-agents`, present on first scrape only).

| Grand total documented | **90** service entries |

Temporal / SonarQube / Sourcegraph / Firecrawl remain **ZOMBIE_0** today; if productively re-enabled, reclassify Temporal (+ deps) → KEEP_USEFUL and Sonar/Sourcegraph/Firecrawl → SCALE_DOWN (never always-on on this host).

---

*Inventory only. No service was deleted, scaled, or modified by Squad 1. `cartorio_*` left untouched.*  
*Generated 2026-07-08 for coding-vps_apenas_para_auxilio optimization track.*
