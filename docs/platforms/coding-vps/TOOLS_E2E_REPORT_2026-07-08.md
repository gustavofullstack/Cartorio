# Coding-VPS MCP Orchestrator — Tools E2E Report

**Date:** 2026-07-08  
**Squad:** 2 (Tools E2E Validation)  
**Orchestrator:** `scripts/coding_vps_mcp_orchestrator.py`  
**Host:** Tailscale `100.99.172.84` (`vps-cartorio.tail2fe279.ts.net`)  
**Constraints honored:** no Telegram spam, no key rotation, no cartório production service mutation

---

## Executive summary

| Metric | Value |
|--------|-------|
| **Total tools registered** | **62** (13 categories) |
| **Claimed target** | ~100 tools |
| **Gap vs claim** | **~38 tools** (62/100 = 62%) |
| **Tools explicitly exercised this run** | 14 primary + 4 redis/centrifugo variants |
| **Primary suite structural pass** | 12 / 14 |
| **Primary suite structural fail** | 2 / 14 |
| **Functional issues in "PASS" tools** | 2 (redis_keys NOAUTH, centrifugo curl missing) |
| **validate_coding_vps_e2e.sh** | 8/17 agents OK (main 8/8, side-stack 0/9) |

### JSON-like summary

```json
{
  "total_tools": 62,
  "claimed_tools": 100,
  "gap": 38,
  "categories": 13,
  "validated_primary": 14,
  "passed_structural": 12,
  "failed_structural": 2,
  "passed_functional": 10,
  "partial_functional": 2,
  "failed_functional": 2,
  "validate_script_score": "8/17",
  "validate_main_stack": "8/8",
  "validate_side_stack": "0/9"
}
```

---

## 1. Tool inventory (`list`)

Command:

```bash
python3 scripts/coding_vps_mcp_orchestrator.py list
```

Observed (latest run during report): **62 tools in 13 categories**.

| Category | Count | Tools |
|----------|------:|-------|
| CODE-REVIEW | 2 | `sonarqube_projects`, `sonarqube_issues` |
| DB | 7 | `postgres_query`, `postgres_list_tables`, `redis_cmd`, `redis_ping`, `redis_get`, `redis_set`, `redis_keys` |
| DEV | 1 | `opencode_run` |
| DOCKER | 6 | `service_logs`, `restart_service`, `scale_service`, `deploy_image`, `env_get`, `env_set` |
| EASYPANEL | 4 | `ep_login`, `ep_list_projects`, `ep_list_services`, `ep_deploy` |
| LLM | 3 | `chat_minimax`, `chat_with_agent`, `list_models` |
| NETWORKING | 1 | `tailscale_status` |
| RAG | 3 | `langflow_list_flows`, `anythingllm_query`, `langfuse_traces` |
| STATUS | 10 | `list_services`, `health_check_service`, `health_check_all`, `service_info`, `service_tasks`, `docker_stats`, `swarm_info`, `node_list`, `network_list`, `volume_list` |
| UTILITY | 17 | `exec_in_container`, `service_http_get`, `service_http_post`, `backup_volume`, `restore_volume`, `image_pull`, `image_list`, `swarm_service_create`, `swarm_service_remove`, `file_read`, `file_write`, `tail_file`, `port_scan`, `network_inspect`, `secret_get`, `secret_set`, `openapi_spec` |
| WEBHOOK | 1 | `webhook_send` |
| WEBSOCKET | 4 | `centrifugo_publish`, `centrifugo_channels`, `centrifugo_history`, `mirotalk_create_room` |
| WORKFLOW | 3 | `temporal_list_workflows`, `temporal_describe`, `langflow_run` |
| **TOTAL** | **62** | |

> Note: first inventory in this session showed **60** tools; a subsequent `list` mid-session showed **62** (`redis_ping`, `health_check_all` present). Report uses **62** as current truth. `openapi_spec` still reported `"tools": 60` when called earlier in the session — registry drift within the same work window.

---

## 2. Per-tool validation (CLI `call`)

Method: `python3 scripts/coding_vps_mcp_orchestrator.py call <tool> [k=v ...]` with wall-clock timing via subprocess (timeout 180s per tool).

### Verdict legend

- **PASS** — HTTP/CLI returned JSON without top-level `error`; payload usable.
- **PARTIAL** — no top-level `error`, but payload shows runtime failure (missing binary, auth, empty useful data).
- **FAIL** — top-level `error` or non-usable response.

| # | Tool | Args | Structural | Functional | Latency | Notes |
|---|------|------|------------|------------|--------:|-------|
| 1 | `chat_minimax` | `prompt=PING-OK-TOOLS` `max_tokens=32` | PASS | PASS* | 4.917s | Reply nearly empty (`"\n\n"`) but model responded (`reasoning_tokens=34`, `total_tokens=214`, `elapsed_s=1.38`). LiteLLM/MiniMax path alive. |
| 2 | `list_services` | (none) | PASS | PASS | 0.877s | `total=80`, `up=29`, `down=51`. Swarm stack visible. |
| 3 | `list_models` | (none) | PASS | PASS | 5.645s | Returns MiniMax-M3 via LiteLLM OpenAI-compatible `/v1/models`. |
| 4 | `docker_stats` | (none) | PASS | PASS | 6.417s | `count=29` containers with CPU/mem. Slow but healthy. |
| 5a | `redis_keys` | `redis_service=langfuse-redis` `pattern=*` | PASS | **PARTIAL** | 1.733s | Keys array is `["NOAUTH Authentication required."]`. Tool does **not** use auth wrapper. |
| 5b | `redis_keys` | `redis_service=argilla-redis` `pattern=*` | FAIL† | **FAIL** | 2.321s | Same NOAUTH (counted FAIL on functional re-eval). |
| 5c | `redis_cmd` | `redis_service=langfuse-redis` `command=PING` | PASS | **PASS** | 1.468s | `result: PONG`. Auth wrapper works. |
| 5d | `redis_cmd` | `redis_service=argilla-redis` `command=PING` | PASS | **PASS** | 1.027s | `result: PONG`. |
| 6 | `tailscale_status` | (none) | PASS | PASS | 0.403s | Backend Running; IPs `100.99.172.84` / `fd7a:115c:a1e0::d43b:ac55`; hostname `srv1769726`. |
| 7 | `swarm_info` | (none) | PASS | PASS | 1.027s | Swarm active, 1 manager, 1 node. |
| 8 | `node_list` | (none) | PASS | PASS | 0.680s | 1 node Ready/Active/Leader (`srv1769726`). |
| 9 | `centrifugo_channels` | `pattern=*` (default) | PASS | **PARTIAL** | 1.378s | Payload: `OCI runtime exec failed: ... exec: "curl": executable file not found in $PATH`. Image lacks `curl`. |
| 10 | `webhook_send` | `url=http://httpbin.org/post` `method=POST` `payload={"ping":"e2e-tools"}` | PASS | PASS | 0.532s | httpbin echoed body; egress OK from orchestrator host/network. |
| 11 | `openapi_spec` | (none) | PASS | PASS | 0.054s | `{"openapi":"3.1.0","tools":60}` — local, no SSH. Spec is minimal (not full OpenAPI schemas). |
| 12 | `port_scan` | `host=100.99.172.84` `ports=3000,4000,8100` | PASS | PASS* | 3.009s | Only `3000 OPEN` reported. 4000/8100 not open from scan vantage (`litellm-app` container). CLI string ports luckily parse as Python ints in generated loop. |
| 13 | `chat_with_agent` | `agent=openclaw` `prompt=PING` `stack=main` | **FAIL** | **FAIL** | 1.424s | `{"error":"agent openclaw not running"}` — **false negative**: `list_services` shows `coding-vps_apenas_para_auxilio_openclaw` **up 1/1**. |
| 14 | `chat_with_agent` | `agent=crew-ai` `prompt=PING` `stack=main` | **FAIL** | **FAIL** | 1.304s | Same false negative; service up 1/1. |

\* Usable but degraded response quality / partial port visibility.  
† Structural pass originally (no `error` key); reclassified FAIL/PARTIAL on functional review.

### Primary suite scoreboard (requested tools)

| Tool | Result | Latency |
|------|--------|--------:|
| chat_minimax | PASS | 4.92s |
| list_services | PASS | 0.88s |
| list_models | PASS | 5.65s |
| docker_stats | PASS | 6.42s |
| redis (keys vs cmd) | keys PARTIAL / **cmd PASS** | 1.0–1.7s |
| tailscale_status | PASS | 0.40s |
| swarm_info | PASS | 1.03s |
| node_list | PASS | 0.68s |
| centrifugo_channels | PARTIAL | 1.38s |
| webhook_send | PASS | 0.53s |
| openapi_spec | PASS | 0.05s |
| port_scan | PASS (3000 only) | 3.01s |
| chat_with_agent openclaw | **FAIL** | 1.42s |
| chat_with_agent crew-ai | **FAIL** | 1.30s |

**Structural:** 12 PASS / 2 FAIL  
**Functional (stricter):** 10 PASS / 2 PARTIAL / 2 FAIL  

---

## 3. `validate_coding_vps_e2e.sh`

Script exists: `scripts/validate_coding_vps_e2e.sh`  
Run: short full agent matrix (SSH to VPS + MiniMax ping). Wall ~35s; exit 0 despite partial failures (script reports score, does not fail hard on agent errors).

```
SCORE: 8/17
  side-stack: 0/9
  main:       8/8
```

| Stack | Agent | Status | Time |
|-------|-------|--------|-----:|
| side-stack | crew-ai, goose, hermes, langgraph, openchamber, openclaw, openhands, kilo, opencode | **FAIL** DNS `urlopen [Errno -2]` | ~0–1.8s |
| main | crew-ai | OK | 2.47s |
| main | goose | OK | 3.32s |
| main | hermes | OK | 1.29s |
| main | kilo-org_kilocode | OK | 1.68s |
| main | langgraph | OK | 2.70s |
| main | openchamber | OK | 18.59s |
| main | openclaw | OK | 1.81s |
| main | openhands | OK | 1.80s |

**Implication:** main coding agents are healthy via in-VPS HTTP. `chat_with_agent` orchestrator path is broken relative to that (container discovery via `docker ps -f name=...` returns empty even when Swarm service is 1/1). Side-stack DNS/network not resolvable from validation runner on VPS.

---

## 4. Gaps vs “100 tools” claim

| Item | Value |
|------|------:|
| Claimed | ~100 |
| Registered now | **62** |
| Absolute gap | **38** |
| Coverage of claim | **62%** |

### Category gaps / thin areas

| Area | Current | Notes toward 100 |
|------|--------:|------------------|
| WEBHOOK | 1 | Code comments mention request-basket helpers; only `webhook_send` registered |
| NETWORKING | 1 | Only `tailscale_status` |
| DEV | 1 | Only `opencode_run` |
| LLM | 3 | No multi-model direct chat, no embeddings tool, no batch |
| CODE-REVIEW | 2 | Sonar only |
| RAG | 3 | Langflow/AnythingLLM/Langfuse — thin |
| WORKFLOW | 3 | Temporal + langflow_run only |
| WEBSOCKET | 4 | Centrifugo tools broken without curl; MiroTalk untested |
| Deprecated DB helpers | 0 live | `clickhouse_query`, `mongo_query`, `minio_list`, `elasticsearch_search` exist as stubs/removed — not counted as working tools |

### Quality gaps (tools exist but degraded)

1. **`redis_keys` / `redis_get` / `redis_set`** likely share missing auth vs `redis_cmd`/`_redis_cmd` wrapper.  
2. **`centrifugo_*` / other curl-based tools** fail inside images without `curl` (prefer `python3 urllib` like LiteLLM helpers).  
3. **`chat_with_agent`** false negative on Swarm service discovery; agents proven up by `list_services` + `validate_coding_vps_e2e.sh`.  
4. **`openapi_spec`** is a stub (`tools` count only), not full per-tool schemas.  
5. **Side-stack agents** down / unresolvable (0/9).  
6. **`port_scan`** vantage limited to `litellm-app` container network namespace.  
7. Registry count drift (60→62) and `openapi_spec` lagging live `TOOLS` length.

### Suggested path to ~100 (illustrative, not implemented)

- Register request-basket / webhook inspect tools (~3–4)  
- Fix + expand Centrifugo / MiroTalk / peer tools without curl (~5)  
- Re-expose ClickHouse/MinIO/ES/Mongo via thin wrappers around `exec_in_container` (~4)  
- Health matrix tools (per-agent status bulk) (~2)  
- Metrics/Prometheus query tools (~3)  
- Git/deploy/rollback helpers (~5)  
- Search / browser / scrape utilities if policy allows (~5)  
- Deeper EasyPanel CRUD (~5)  
- Redis/Postgres convenience suite (auth-aware) (~5)  
- File/log/backup pack (~5)  
- Remaining LLM/RAG/workflow utilities (~10+)

---

## 5. Root-cause notes (no production changes made)

### `chat_with_agent` false negative

```218:249:scripts/coding_vps_mcp_orchestrator.py
def chat_with_agent(agent: str, prompt: str, max_tokens: int = 500, stack: str = "auto") -> dict:
    ...
    for host in stacks_to_try:
        check = ssh(f"docker ps -q -f name={host} | head -1")
        if not check["stdout"].strip():
            continue
        ...
    return {"error": f"agent {agent} not running"}
```

- Swarm services **are** up (`openclaw`, `crew-ai` 1/1).  
- `validate_coding_vps_e2e.sh` chats successfully on main stack.  
- Discovery likely broken by `docker ps -f name=` matching / SSH output handling / replica naming. Fix candidates: `docker service ps`, `docker ps --filter label=com.docker.swarm.service.name=...`, or reuse `list_services` up-check.

### `redis_keys` NOAUTH

```558:567:scripts/coding_vps_mcp_orchestrator.py
def redis_keys(...):
    r = docker_exec(..., f"redis-cli keys '{pattern}' ...")  # no auth
def redis_cmd(...):
    out = _redis_cmd(...)  # uses auto-auth wrapper
```

Prefer routing `redis_keys`/`redis_get`/`redis_set` through `_redis_cmd`.

### `centrifugo_channels` missing curl

Container has no `curl`. Same class of bug as other “curl inside alpine/slim image” tools. Prefer host-side `service_http_post` or python urllib in a known-good container.

---

## 6. Safety / scope confirmation

| Action | Done? |
|--------|-------|
| List + call tools | Yes |
| Read-only status/stats/redis PING | Yes |
| webhook to public httpbin | Yes (non-prod) |
| Telegram | **Not used** |
| Key rotation / secret_set | **Not used** |
| Cartório production services mutate | **Not done** |
| scale/restart/deploy cartório | **Not done** |

---

## 7. Artifacts

| Path | Content |
|------|---------|
| `/tmp/coding_vps_e2e/summary.json` | Primary 14-tool results + previews |
| `/tmp/coding_vps_e2e/extra_summary.json` | Redis/centrifugo variants |
| `/tmp/coding_vps_e2e/*.json` | Per-tool raw CLI stdout |
| `/tmp/coding_vps_e2e/validate_script.out` | Agent matrix output |
| This file | `docs/platforms/coding-vps/TOOLS_E2E_REPORT_2026-07-08.md` |

---

## 8. Final scorecard

```
total_tools:     62
claimed:         100
gap:             38
passed:          12 structural / 10 functional (primary suite)
failed:          2 structural (chat_with_agent x2)
partial:         2 (redis_keys, centrifugo_channels)
validate_e2e:    8/17 (main 8/8, side 0/9)
```

**Bottom line:** Orchestrator surface is real and mostly live (~60 tools, not 100). Status/Docker/Tailscale/LiteLLM paths are solid. Highest-priority fixes: (1) `chat_with_agent` Swarm discovery, (2) Redis auth on non-cmd helpers, (3) curl-less Centrifugo/HTTP tools, (4) side-stack DNS/agent stack, (5) grow registry honestly toward 100 with working tools rather than stubs.
