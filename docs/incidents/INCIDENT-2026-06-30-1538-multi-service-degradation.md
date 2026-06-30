# INCIDENT-2026-06-30-1538 — Multi-service degradation

**Status**: OPEN — diagnostic complete, awaiting Gustavo GO for prod fixes
**Severity**: P1 (radar red, but core API + WhatsApp + OpenClaw + Evolution UP)
**Detected**: 2026-06-30 15:38 BRT (radar health check + manual inspection)
**Reporter**: Pietra session `mvs_ad28a7e4c0064e70b252d188d932ee0e`

---

## TL;DR

4 services degraded, 3 root causes identified. None caused customer-facing outage (radar RED but API radar still serving). Hermes is the only one blocking a Turno 38 deliverable.

---

## Affected services

### 1. Hermes — CRASH LOOP (P1)

**Symptom**: 5 consecutive container exits within 41s. `cartorio_hermes.1` UP 1s, then crash, repeat.

**Root cause** (from container logs):
```
Refusing to bind dashboard to 0.0.0.0 — the auth gate engages on
non-loopback binds, but no auth providers are registered.
Configure an auth provider before exposing the dashboard:
  • Password: set dashboard.basic_auth.username + password_hash in config.yaml
  • OAuth: run `hermes dashboard register` (Nous Portal)
```

The Hermes config (deployed in Turno 38 commit, image `easypanel/cartorio/hermes:latest`) has no `dashboard.bind` and no `basic_auth` configured. Hermes refuses to start.

**Fix** (autonomous, no prod risk — Hermes already broken):
- Option A: bind dashboard to `127.0.0.1` (only accessible via SSH/Tailscale)
- Option B: set `dashboard.basic_auth.username + password_hash`

**Rollback**: restore previous compose / image tag.

---

### 2. Supabase — 502 BAD GATEWAY (P1)

**Symptom**: `https://supbase.2notasudi.com.br/auth/v1/health` returns HTTP 502. Radar reports `supabase: offline`.

**Root cause** (from `docker ps -a`):
| Container | Status |
|-----------|--------|
| `cartorio_supabase-kong-1` | Up 6h (healthy) |
| `cartorio_supabase-db-1` | Up 6h (healthy) |
| `cartorio_supabase-rest-1` | Up 6h |
| `cartorio_supabase-functions-1` | **Restarting (1)** |
| `cartorio_supabase-realtime-1` | **Restarting (1)** |
| `cartorio_supabase-supavisor-1` | **Restarting (1)** ← connection pooler |
| `cartorio_supabase-analytics-1` | **Unhealthy** |
| `cartorio_supabase-auth-1` | Up 6h (healthy) |
| others | Up 6h (healthy) |

**Supavisor is the connection pooler.** When it crashes, all queries routed through PostgREST/GoTrue fail. 3 containers in restart loop means a config/OOM issue affecting auxiliary services.

**Fix** (requires Gustavo GO, prod risk):
- Restart sequence: `supavisor → db → auth → kong`
- Investigate OOM or config root cause via per-container logs (`supabase-functions`, `supabase-realtime`)
- Rollback: start containers in reverse order

**Window**: ~30s of total Supabase unavailability during restart.

---

### 3. N8N — TIMEOUT (P2)

**Symptom**: `https://flow.2notasudi.com.br/healthz` times out after 10s. Radar reports `n8n: online` (likely stale cache — radar reads `/api/v1/health/radar` which doesn't directly hit N8N).

**Root cause** (from `docker service logs cartorio_n8n`):
```
Unknown filter parameter operator "string:notEqual"  (×8)
OpenTelemetry diagnostics error (×8)
Received SIGTERM. Shutting down...
```

Container was restarted 6h ago (`Failed 6 hours ago: task: non-zero exit (1)`). Now running for 3h but emitting persistent filter errors. N8N 2.x has known incompatibility with some plugin filters using `string:notEqual` (deprecated).

**Fix** (autonomous, low risk — 5-10s downtime):
- `docker service update --force cartorio_n8n` (drains queue + restart)
- Investigate `string:notEqual` operator source (likely webhook payload filter in B07 retry/backoff pattern)

**Workflow persistence**: any in-flight execution continues; completed ones are saved.

---

### 4. API — OOMKilled 59min ago (P2)

**Symptom**: Radar currently healthy, but `cartorio_api.1.kkubnjoq8ijxj76clo1o1fvei` exited with code 137 (SIGKILL/OOM) 59min ago.

**Root cause hypothesis**: Memory limit too low vs load (164 MCP tools + LGPD audit chain + 21/21 live test battery from Turno 38).

**Fix** (autonomous, low risk): Increase memory limit in compose, redeploy. **Recommendation**: 2G → 4G. Verify with `docker stats` before/after.

---

## Service health matrix (15:38 BRT)

| Service | Radar | Container | Notes |
|---------|-------|-----------|-------|
| API | OK | Up 1h (healthy) | Restarted 59min ago (OOM 137) |
| OpenClaw | OK | Up 7h (healthy) | |
| Evolution | OK | Up 5h | TriQ Hub test connected |
| Chatwoot | OK | Up 6h | |
| Redis | OK | Up 6h | |
| N8N | OK (stale) | Up 3h (errors) | /healthz timeout 10s |
| Supabase | OFFLINE | Up 6h (3 in restart) | 502 Bad Gateway |
| Hermes | n/a | Crash loop | auth/bind config missing |
| Easypanel | OK | Up 6h | |

---

## Recommended action plan

**Phase 1 (autonomous, no GO)**:
1. Fix Hermes config (Option A: bind 127.0.0.1 OR Option B: basic_auth) — 5 min
2. Restart N8N (`docker service update --force cartorio_n8n`) — 1 min
3. Increase API memory limit + redeploy — 10 min

**Phase 2 (requires Gustavo GO)**:
4. Restart Supabase stack in order — 5 min, 30s window of unavailability

---

## Lessons (to be appended to MEMORY after fix)

- **L214a**: Hermes dashboard auth gate — non-loopback bind requires explicit auth config. Default config safe = `127.0.0.1`.
- **L214b**: Supabase radar status goes OFFLINE if supavisor (connection pooler) crashes, even if db/auth/kong UP. Check `docker ps -a` for `Restarting` containers before declaring Supabase truly down.
- **L214c**: N8N 2.x deprecates `string:notEqual` filter operator — backlog of webhook retries can cause persistent error logs.

---

**Modified by Gustavo Almeida**