# INCIDENT 2026-06-23 — Supabase db-1 password authentication failure (P0)

| Field             | Value                                                          |
|-------------------|----------------------------------------------------------------|
| Severity          | P0 (production DB rejecting connections)                       |
| Status            | Mitigated via cached connections (degrading)                   |
| Start (detected)  | 2026-06-23 14:23 BRT (17:23 UTC)                               |
| Detected by       | Pietra (orquestrador) — SSH audit on 100.99.172.84            |
| Diagnosed by      | cartorio-dev (Mavis/MiniMax) — backend/.env analysis          |
| Affected          | supabase_admin role (used by cartorio API directly)            |
| Fix status        | AWAITING Gustavo authorization (Options A/B/C/D below)         |
| Related           | ADR-013 (decisão + lessons learned)                            |

---

## TL;DR (60 seconds)

The cartorio API uses `supabase_admin` directly via
`backend/.env: DATABASE_URL`. That role's SCRAM password hash, stored in
PostgreSQL's `pg_authid.rolpassword`, was generated from the **real** password
`e999b7439deb35dfe05c33f265dae1ea` when `db-1` first initialized.

But `/etc/easypanel/projects/cartorio/supabase/.env` (env of the `db-1`
service) has the **placeholder** value from the Supabase template:
`POSTGRES_PASSWORD=your-super-secret-and-long-postgres-password`.

After `db-1` restart, **new connections** (supavisor-1, auth-1, rest-1,
storage-1) attempt SCRAM auth with the placeholder password. The stored hash
is for the real password, so they fail. ~178 fails/min.

**Cached connections** from before the restart still work — that's why
`/audit/verify` and `/atendimentos/ultimas-24h` return 200 OK. They'll break
when the pool reconnects (timeout/idle disconnect).

**GREEN radar** is a false positive — `GET /api/v1/health/radar` only checks
TCP reachability, not authentication.

---

## Timeline (BRT = UTC-3)

| Time (BRT)  | Event                                                          |
|-------------|----------------------------------------------------------------|
| 14:23       | db-1 logs start printing "password authentication failed for user supabase_admin" — 178 fails/min |
| 14:23       | supavisor-1 enters Restarting loop (~27-59s cycle)             |
| 14:23       | auth-1/rest-1/storage-1 restart once and recover               |
| 14:24       | Pietra escalates P0 to all reins                               |
| 14:24       | cartorio-dev reads `backend/.env` and finds `DATABASE_URL` uses `supabase_admin:e999b74...` |
| 14:25       | cartorio-dev confirms RCA: SCRAM hash mismatch (real password vs placeholder env) |
| 14:26       | Pietra confirms via SSH: cached connections still serve 200 OK; pool will degrade |
| 14:27       | ADR-013 draft + fix script + runbook authored (read-only, no prod mutation) |
| 14:30+      | Awaiting Gustavo's choice of fix option (A/B/C/D)              |

---

## Root Cause Analysis

### What changed

`db-1` was restarted. The Docker Swarm service definition for `db-1`
in `/etc/easypanel/projects/cartorio/supabase/docker-compose.yml` (or
equivalent) was unchanged. The env file
`/etc/easypanel/projects/cartorio/supabase/.env` was unchanged.

What changed is that on first deployment (weeks/months ago), whoever set up
the Supabase stack:

1. Replaced `POSTGRES_PASSWORD=your-super-secret-and-long-postgres-password`
   in the env file with the real value `e999b7439deb35dfe05c33f265dae1ea`.
2. Ran `initdb` via the Supabase entrypoint, which hashed that real password
   and stored it in `pg_authid.rolpassword` for all default roles.
3. **Then the env file got reset to the placeholder** — either by an
   Easypanel re-deploy, a template re-apply, or manual mistake. The volume
   `cartorio_supabase_db-data` retains the SCRAM hash of the real password.

After restart, the entrypoint sees a volume with an existing cluster, so it
**skips initdb**. The env file with placeholder is read but never applied to
existing roles. New connections present the placeholder password, SCRAM
hash comparison fails.

### Why it's not obvious

- `/health/radar` returns GREEN (TCP-only probe).
- Cached psycopg connections in the cartorio API's connection pool remain
  authenticated from before the restart.
- The error logs (178 fails/min) are buried in `db-1` stdout — not surfaced
  to any Grafana dashboard yet (T2.SUP.T14 backlog).

### The exact mismatch

| Location                                                      | Value                                                |
|---------------------------------------------------------------|------------------------------------------------------|
| `backend/.env` line 18 `DATABASE_URL` (URL-encoded)           | `e999b7439deb35dfe05c33f265dae1ea` (real)            |
| `/etc/easypanel/projects/cartorio/supabase/.env` `POSTGRES_PASSWORD` | `your-super-secret-and-long-postgres-password` (placeholder) |
| `pg_authid.rolpassword` for `supabase_admin` (in volume)      | `SCRAM-SHA-256$...:e999b7439deb35dfe05c33f265dae1ea` (real hash) |
| What `supavisor-1`, `auth-1`, `rest-1`, `storage-1` try to use | placeholder (mismatch → auth fail)                   |

---

## Options (A/B/C/D) — pick one

### Option A — ALTER USER (recommended, lowest blast radius)

**Action**: Inside the existing cluster, run `ALTER USER supabase_admin
PASSWORD 'e999b7439deb35dfe05c33f265dae1ea'`. Then rolling-restart
supavisor-1, auth-1, rest-1, storage-1.

**Pros**:
- Preserves all data, all roles, all schemas.
- ~5 min downtime (rolling restart of stateless services).
- Scriptable and idempotent.

**Cons**:
- Requires docker exec on VPS.
- After restart, `db-1` env still has placeholder. **Drift will recur** on
  next db-1 restart UNLESS we also fix the env file (recommended follow-up).

**Script**: `infra/supabase/scripts/fix-admin-password.sh` — idempotent,
with `--dry-run` (default) and `--apply` modes. Pre-flight checks
(docker present, container up, backup <26h) gate the apply.

**Recommended follow-up**: After ALTER USER succeeds, edit
`/etc/easypanel/projects/cartorio/supabase/.env` to replace placeholder
with real password. This is a 1-line change, no restart needed.

### Option B — DROP and recreate role

**Action**: `DROP ROLE supabase_admin; CREATE ROLE supabase_admin WITH
PASSWORD 'e999b7439deb35dfe05c33f265dae1ea' SUPERUSER;`

**Pros**: Clean state for that role.

**Cons**:
- Drops role-specific grants, owned objects, default privileges.
- For `supabase_admin`, this is risky — it owns schemas and tables.
- Requires manual re-grant of all privileges.

**Decision**: **REJECTED**. Too invasive for the role in question.

### Option C — Use a different role (authenticator) in DATABASE_URL

**Action**: Change `backend/.env: DATABASE_URL` to use `authenticator` role
instead of `supabase_admin`. Audit and fix schema grants.

**Pros**:
- Decouples cartorio API from admin user. Smaller blast radius for future
  auth incidents.
- Aligns with Supabase best practice (anon/authenticator/service_role
  separation).

**Cons**:
- Requires schema grants migration, RLS policy review, role-based
  permission audit. ~2-4 hours of work.
- Out of scope for incident response (incident needs to be resolved in
  <30 min, not hours).

**Decision**: **REJECTED** for incident. Filed as Sprint 3 follow-up
(T2.SUP.T11 — encryption at-rest + role separation).

### Option D — Snapshot volume + drop + reinit with correct password

**Action**: Stop db-1, snapshot volume `cartorio_supabase_db-data`, drop
volume, restart db-1 (initdb runs fresh with placeholder from env — but
we'd need to override env file FIRST), restore from backup.

**Pros**: Cleanest state, matches fresh deploy.

**Cons**:
- High downtime (~30 min).
- Backup must be verified (ADR-009 + ADR-011 pre-flight).
- Risk of incomplete restore.
- Loss of any writes between last backup and incident.

**Decision**: **LAST RESORT** only. Reject unless Options A, B, C all fail.

---

## Pre-Flight Checklist (BEFORE any fix)

- [ ] Confirm incident is still active (re-run `docker logs
      cartorio_supabase-db-1 --tail 50 | grep "authentication failed" | wc -l`)
- [ ] Verify backup is recent: `ls -la /var/backups/cartorio/` (ADR-009)
- [ ] Verify business hours vs pilot customer impact (ask Gustavo)
- [ ] Notify #cartorio-incidents Slack/Telegram channel
- [ ] Snapshot `cartorio_supabase_db-data` volume (5 min, before any mutation)

## Validation (AFTER fix)

- [ ] `docker exec cartorio_supabase-db-1 psql -U supabase_admin -c "SELECT 1"`
- [ ] `curl https://api.2notasudi.com.br/api/v1/health/radar` → GREEN, all 5/5
- [ ] `curl https://api.2notasudi.com.br/api/v1/audit/verify` → `chain_ok: true`
- [ ] `curl https://api.2notasudi.com.br/api/v1/atendimentos/ultimas-24h` → 200 OK
- [ ] `docker logs cartorio_supabase-supavisor-1 --tail 50` → no restart loop
- [ ] `docker logs cartorio_supabase-db-1 --tail 50 | grep "authentication failed" | wc -l` → 0
- [ ] (Optional) End-to-end: send a test WhatsApp message via Evolution, verify webhook
      reaches chatwoot → n8n → API → DB write.

## Rollback Plan

If Option A fix breaks something:

1. `docker exec cartorio_supabase-db-1 psql -U postgres -c "ALTER USER supabase_admin PASSWORD 'your-super-secret-and-long-postgres-password';"`
   (revert to placeholder; will re-break on next new connection)
2. Stop and restore from volume snapshot (5 min snapshot taken in pre-flight)
3. Stop and restore from /var/backups/cartorio/*.tar.gz (ADR-011)

If Option D (drop volume + reinit) breaks something:

1. Stop db-1
2. `docker volume rm cartorio_supabase_db-data`
3. Restore volume from `docker run --rm -v cartorio_supabase_db-data:/data -v /var/backups/cartorio/db-data-snapshot:/backup alpine tar xf /backup/db-data-snapshot.tar -C /data`
4. Restart db-1
5. Validate radar + audit/verify

---

## Lessons Learned (incorporated into ADR-013)

1. `POSTGRES_PASSWORD` env in db-1 service **MUST** be committed-friendly and
   match the cluster init password. Drift is silent until restart.
2. `/api/v1/health/radar` MUST evolve from TCP-only to authentication check
   (out of scope for this incident, filed in Sprint 3 backlog).
3. Critical role passwords MUST be visible in 2+ places (backend .env AND
   db-1 service env) for cross-validation. Drift detection script filed as
   Sprint 3 follow-up.
4. New operator onboarding MUST include explicit handoff of these 3 values
   (backend DATABASE_URL, db-1 POSTGRES_PASSWORD, pg_authid actual hash).
   Documented in `docs/RUNBOOK_VPS.md` (to be added in this PR).

---

## References

- `docs/adr/ADR-013-supabase-password-mismatch.md` — full decision record
- `infra/supabase/scripts/fix-admin-password.sh` — idempotent fix script
- `SESSION_SUMMARY_2026-06-23.md` line 174 — credential documentation
- `.harness/TASKS.md` line 489-501 — Sprint 2 T2.SUP tasks (this incident
  unblocks T1-T15)

Modified by Gustavo Almeida