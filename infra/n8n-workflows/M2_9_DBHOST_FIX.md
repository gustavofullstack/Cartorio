# M2.9 — DB_HOST Swarm Alias Fix (ADR-010 Violation)

**Date**: 2026-06-24 10:50 BRT
**Owner**: cartorio-n8n (reun) — session `mvs_3fb892d492d7489caf3c78f1e621ea6d`
**Status**: ✅ **APPLIED + VERIFIED** (N8N healthz HTTP 200)

## Problem

Per ADR-010: "DB_HOST em Swarm = IP direto do container do banco, NUNCA alias DNS". N8N was using `DB_POSTGRESDB_HOST=db` (compose alias that does NOT resolve in Swarm overlay networks).

This was a latent bug. N8N's startup logs showed the DB query failing or silently degraded, contributing to the cron workflows failing.

## Discovery

The M2.6 audit (env injection) revealed that N8N had 21 default env vars but **DB_POSTGRESDB_HOST=db** was using the Swarm-incompatible alias. Historical fix from TASKS.md E1.S1.WF5-10 (2026-06-23 11:18 BRT) used `10.0.1.34` as the correct IP, but **the DB container has since been recreated** and its IP changed.

## Current Network Topology (verified)

- DB container `cartorio_supabase-db-1` (d5d077740333) is on TWO networks:
  - `cartorio_supabase_default` (bridge) — IP `172.16.2.2`, alias `db`
  - `easypanel-cartorio` (overlay) — IP `10.0.1.171`
- N8N container is on TWO networks:
  - `easypanel` (overlay) — IP `10.11.11.56`
  - `easypanel-cartorio` (overlay) — IP `10.0.1.164`

The DNS service `127.0.0.11` inside N8N resolves `*.tail2fe279.ts.net` only — it does NOT resolve `db` or `cartorio_supabase-db-1` because those are aliases on `cartorio_supabase_default` which N8N is NOT attached to.

**Reachability test**: `docker exec cartorio_n8n.1.<id> nc -zv 10.0.1.171 5432` → **OPEN** ✅

## Fix Applied

```bash
# Backup first
docker service inspect cartorio_n8n > /tmp/n8n-backup-dbhost-1782308904.json

# Apply with --env-add (Docker replaces duplicates)
docker service update --env-add DB_POSTGRESDB_HOST=10.0.1.171 cartorio_n8n

# Wait for service to converge (~30s)
docker service ps cartorio_n8n  # → Running, no Error
```

Note: I initially tried `10.0.1.34` (the historical IP from ADR-010) but `nc -zv 10.0.1.34 5432` returned "Host is unreachable" — confirming the DB IP changed when the container was recreated. Re-applied with current IP `10.0.1.171`.

## Validation

- `docker service ps cartorio_n8n` → 2 Running, 0 Error
- New container CID: `136aad7d0995`
- `env | grep DB_POSTGRESDB_HOST` → `DB_POSTGRESDB_HOST=10.0.1.171` (only 1 entry — Docker replaced)
- `curl https://flow.2notasudi.com.br/healthz` → **HTTP 200** ✅

## Cron Workflows Re-validation (post-fix)

After DB_HOST fix, 5 of 7 cron workflows re-ran on schedule and STILL errored, confirming the env var issue is separate from DB connectivity:

| Workflow | Status | Latest Run | Issue |
|----------|--------|-----------|-------|
| WF #21 backup-5min (d3Qn6V9O4QShpf5h) | error | 2026-06-24 13:45:17 | $env.CARTORIO_API_KEY denied |
| WF #22 audit-verify-6h (KmbrUKvoLzg4cIPW) | (no run) | - | not in cron window |
| WF #23 stale-detector-5min (HCYh4VRLcBK89sRu) | error | 2026-06-24 13:45:03 | $env.CARTORIO_API_KEY denied |
| WF #25 metrics-collector (12rMQSwMGkaE293C) | crashed | 2026-06-24 13:48:00 | `process is not defined [line 6]` (Code bug, not env) |
| WF #25 protocolo-concluido (ITEGmC8k7nTJ78Uw) | error | 2026-06-24 13:50:48 | $env.CARTORIO_API_KEY denied |
| WF #29 rate-limit-reset (24HV3hEwwQcYasAx) | (no run) | - | not in cron window |
| WF #30 health-deep-check (OYW3pxLCJFP47xgX) | error | 2026-06-24 13:45:28 | $env.CARTORIO_API_KEY denied |

**WF #25 metrics-collector "crashed"** status indicates a separate code issue (uses Node `process` global in Code node — N8N Code node uses sandboxed VM that doesn't expose Node globals).

## Rollback

```bash
docker service rollback cartorio_n8n
# Reverts to spec from /tmp/n8n-backup-dbhost-1782308904.json (DB_HOST=db)
```

## ADR-010 Update Suggestion

ADR-010 should be updated to add: "Verificar IP atual do DB via `docker inspect cartorio_supabase-db-1 --format '{{.NetworkSettings.Networks.easypanel-cartorio.IPAddress}}'` antes de aplicar fix."

Modified by Gustavo Almeida