# ADR-013: Supabase stack — POSTGRES_PASSWORD must match volume cluster init

| Field         | Value                                                          |
|---------------|----------------------------------------------------------------|
| Status        | Accepted (pending lessons-learned propagation)                 |
| Date          | 2026-06-23                                                     |
| Author        | cartorio-dev (Mavis/MiniMax)                                   |
| Trigger       | P0 incident: db-1 + supavisor-1 restart loop + 178 auth fails/min for user `supabase_admin` |
| Related       | ADR-009 (backup obrigatorio), ADR-010 (DB isolation), ADR-011 (backup VPS-side) |

---

## Context

On 2026-06-23 at ~14:23 BRT (17:23 UTC), the Supabase stack running on the
Easypanel VPS (100.99.172.84) entered a degraded state:

1. `cartorio_supabase-supavisor-1` entered a `Restarting (1)` loop (~every 27-59s)
2. `cartorio_supabase-auth-1 / rest-1 / storage-1` restarted once and recovered
3. `db-1` logs began printing `"password authentication failed for user
   supabase_admin"` 178 times/minute continuously
4. `pg_hba.conf line 89: host all all 172.16.0.0/12 scram-sha-256` was the
   matching auth rule (so auth_method itself was correct — only the stored
   SCRAM verifier was wrong)
5. `/api/v1/health/radar` returned GREEN (falso positivo: check is TCP only,
   not authentication)
6. `/api/v1/audit/verify` and `/api/v1/atendimentos/ultimas-24h` continued to
   return 200 OK for ~5 minutes via **cached psycopg connections from
   pre-restart state**, expected to break when pool reconnects (timeout/idle
   disconnect)

The cartorio API uses user `supabase_admin` directly via
`backend/.env: DATABASE_URL=postgresql+psycopg://supabase_admin:e999b74...@db:5432/cartorio`
(see SESSION_SUMMARY_2026-06-23.md line 174 for the documented credential).
Therefore, fixing this user is NOT optional — the API cannot be redirected
to `authenticator` without backend config changes.

## Decision

**Treat POSTGRES_PASSWORD in the `db-1` service env as a binding contract
with the cluster-init SCRAM verifier stored in the `db_data` Docker volume.**

Specifically:

1. The `.env` file at `/etc/easypanel/projects/cartorio/supabase/.env` MUST
   carry the same `POSTGRES_PASSWORD` value that was used when the cluster
   was first initialized. Changing it after init **does NOT** re-hash existing
   users — it only takes effect on a fresh `initdb` (which won't run if the
   volume already contains a cluster).

2. `backend/.env: DATABASE_URL` MUST carry the same password as `db-1` env.
   These two values are coupled and must be rotated together.

3. The placeholder value `your-super-secret-and-long-postgres-password` from
   Supabase's template README MUST be replaced in three places (db-1 env,
   backend .env, any future admin script) before first deployment. If left
   in db-1 env, `initdb` will run with the placeholder, then the volume will
   persist a SCRAM hash of the placeholder — and any subsequent
   `POSTGRES_PASSWORD=e999b74...` change in env will not retroactively
   re-hash the existing role.

4. **Detection of drift**: if `docker exec db-1 psql -U supabase_admin -c
   "SELECT 1"` fails with `password authentication failed`, it means the
   SCRAM hash stored in `pg_authid.rolpassword` for that role does not match
   the current `POSTGRES_PASSWORD` env var.

## Consequences

### Positive

- Future operators have a single source of truth: the role password in
  pg_authid. POSTGRES_PASSWORD env is just a seed for initdb.
- Documented runbook (`docs/INCIDENT_2026-06-23_SUPABASE_AUTH.md`) and
  idempotent fix script (`infra/supabase/scripts/fix-admin-password.sh`)
  reduce MTTR for the next occurrence from ~30min to ~5min.
- Radar healthcheck upgraded from TCP-only to authentication-check
  (out of scope for this ADR but flagged for Sprint 3).

### Negative

- Requires dual-config discipline: any password rotation must update BOTH
  the volume (via ALTER USER) AND the env vars on db-1 + backend. Forgetting
  one side = same bug class.
- The `/etc/easypanel/projects/cartorio/supabase/.env` file is on the VPS,
  not in git, so onboarding a new operator requires a manual handoff of
  these credentials. Documented in runbook onboarding section.

### Risks

- **Data loss risk** in fix script Option B (drop volume + reinit) — only
  viable after a verified backup. Mitigated by mandatory backup pre-flight
  in `fix-admin-password.sh`.
- **Connection pool poisoning** — if some clients have cached SCRAM auth
  and others have the new hash, race conditions may surface. Mitigated by
  rolling restart (db-1 first, wait for stable, then supavisor).

## Alternatives Considered

### A. ALTER USER supabase_admin PASSWORD '<real>' inside cluster

- **Pro**: preserves all data, low downtime, recoverable.
- **Con**: must be executed from inside cluster (docker exec db-1 psql -U
  postgres as superuser). Requires local docker access on VPS.
- **Decision**: PRIMARY recommended fix. Script: `fix-admin-password.sh`
  step 3.

### B. Recreate role via DROP + CREATE

- **Pro**: clean state, role recreated from scratch.
- **Con**: drops any role-specific grants, policies, owned objects.
- **Decision**: rejected for `supabase_admin` (too critical). Only viable
  for non-essential roles.

### C. Use a different role (authenticator) in DATABASE_URL

- **Pro**: decouples cartorio API from admin user, smaller blast radius.
- **Con**: requires schema grants migration, RLS policy review, role-based
  permission audit. Out of scope for incident response.
- **Decision**: future work, tracked in Sprint 3 (T2.SUP.T11 — encryption
  at-rest + role separation).

### D. Snapshot volume + drop + reinit with correct password

- **Pro**: cleanest state, matches fresh deploy.
- **Con**: requires verified backup AND volume replacement AND full
  schema/migration re-run. Total downtime ~30min. Risk of incomplete
  restore.
- **Decision**: LAST RESORT only. ADR-009 backup pre-flight is mandatory.

## Lesson Learned

`POSTGRES_PASSWORD` in the `db-1` service env MUST be:

1. **Commit-friendly** — same value as in `backend/.env` (no placeholders,
   no environment-specific substitutions).
2. **Validated against volume cluster init** — on first deploy, after
   `initdb` runs once, the SCRAM hash is fixed. Changing the env var
   afterwards is a no-op.
3. **Tracked in onboarding runbook** — see
   `docs/RUNBOOK_VPS.md` → "Onboarding new operator" → "Supabase credentials
   handoff" (to be added in this PR).

The radar `/api/v1/health/radar` MUST evolve from TCP-only to authentication-
check (out of scope for this incident, filed in Sprint 3 backlog as
T2.SUP.T14 follow-up).

## Implementation Artifacts

- `infra/supabase/scripts/fix-admin-password.sh` — idempotent fix script
  with `--dry-run` flag and pre-flight checks.
- `docs/INCIDENT_2026-06-23_SUPABASE_AUTH.md` — incident runbook (timeline,
  options A/B/C/D with risks, rollback plan, validation).
- `backend/.env.example` — updated with explicit warning about
  `POSTGRES_PASSWORD` synchronization with db-1 service env.

Modified by Gustavo Almeida