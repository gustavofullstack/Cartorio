# Audit Log Integrity Report

**Generated:** 2026-07-14T02:29:06.421966+00:00
**Run started:** 2026-07-14T02:29:05.885946+00:00
**Duration:** 0.536s
**Overall status:** 🟢 PASS

## TL;DR

- **Rows scanned:** 1,000
- **SHA256 chain:** ✅ intact
- **HMAC signatures:** ✅ all valid
- **Dead-man-switch:** ✅ **HEALTHY** — chain intact and fresh
- **Tamper detection:** ✅ all 4 scenarios detected

## HMAC key fingerprint (NOT the key)

These fingerprints identify the HMAC key used to sign the chain without exposing it.

- **HMAC key id hash (SHA256 of key):** `ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb`
- **HMAC key length:** 64 chars
- **HMAC key first-8 SHA256 fingerprint:** `1f3ce40415a2081fa3eee75fc39fff8e56c22270d1a978a7249b592dcebd20b4`

> The actual HMAC key is intentionally **not** included. To rotate, generate a new 64-char hex
> key and compare its `key_id_hash` against this value; mismatch = key rotation occurred.

## Dead-man-switch status (A13)

- **Level:** ✅ **HEALTHY**
- **Reason:** chain intact and fresh
- **Chain OK:** True
- **Total rows:** 1,000
- **Last entry age:** 0.015s
- **Threshold:** 60s (2x threshold = 120s)

## SHA256 chain verification

- **OK:** True
- **Last valid position:** 1,000 / 1,000

Algorithm: per entry, recompute `SHA256(canonical_json({prev_hash, timestamp, payload}))`
and compare with stored `hash`. Also assert `entry.prev_hash == previous_entry.hash`.

## HMAC verification

- **OK:** True
- **First bad id:** None

Algorithm: per entry, recompute `HMAC_SHA256(key, f"{hash}:{timestamp}:{actor_id}:{action}")`
and `hmac.compare_digest` with stored signature. This complements `verify_chain` which only
checks the SHA256 chain, not the HMAC layer.

## Tamper-detection scenarios (isolated clones)

Each scenario runs on a CLONED engine so the primary chain is not affected.

| Scenario | Description | Chain OK | Last valid | HMAC OK | Detected |
|----------|-------------|----------|------------|---------|----------|
| `payload_retro_edit` | Edita payload de uma entrada no meio da cadeia | False | 7 | True | ✅ |
| `midchain_delete` | Deleta entrada no meio da cadeia | False | 50 | True | ✅ |
| `hmac_byte_flip` | Altera 1 byte da HMAC signature sem mexer no hash | True | 1000 | False | ✅ |
| `prev_hash_swap` | Substitui prev_hash por valor invalido | False | 20 | True | ✅ |

### Per-scenario detail

- **`payload_retro_edit`** — tampered entry id=8 action='lgpd.export' original_payload_keys=['canal', 'destinatario_hash', 'seq', 'ts_seed'] -> chain_ok=False last_valid=7 hmac_ok=True
- **`midchain_delete`** — deleted entry id=51 -> chain_ok=False last_valid=50
- **`hmac_byte_flip`** — flipped hmac on entry id=13 action='system.startup' (9742d373... -> f742d373...) -> chain_ok=True hmac_ok=False
- **`prev_hash_swap`** — swapped prev_hash on entry id=21 -> chain_ok=False last_valid=20

## Methodology

- **Standalone harness**: SQLite in-memory engine, schema mirrored from `app/models/base.py`.
- **Production code under test**: `app/services/audit.py` (`AuditService.log`, `AuditService.verify_chain`).
- **Realistic dataset**: 1,000 entries cycling through 12 real Cartório
  event shapes (system.startup, protocolo.create/update/finalize, conversa.handoff, cliente.update,
  documento.emit/assina, lgpd.export, cron.retencao_run, system.health_check) — same
  distribution observed in production.
- **HMAC verification** is explicit because the production `verify_chain()` only validates the
  SHA256 chain, not the HMAC signature. Both layers must hold.
- **Dead-man-switch** mirrors the A13 briefing: healthy (age <= threshold), warning (age in
  (threshold, 2x threshold]), critical (broken or age > 2x threshold or empty).

## Scope & limitations

- This run is a **harness verification of the audit algorithm and tamper-detection logic**
  executed in a sandboxed worktree. The production PostgreSQL `audit_log` table is hosted on
  the VPS (`supbase.2notasudi.com.br`) and is not reachable from this worktree — credentials
  for the prod DB live in `~/.mavis/secrets/cartorio.env` and are not loaded here.
- **Production runtime protection (independent of this harness):**
  - Cron `audit_verify_diario` runs nightly at 03:00 BRT (06:00 UTC) — see ADR-019.
  - In-process dead-man-switch scheduler runs every 15 min in app lifespan (lifespan of
    `backend/app/main.py`) — emits Telegram GRUPO PIETRA SQUAD alerts when chain goes stale
    > 60 min or breaks.
  - Prometheus metric `audit_dead_mans_status` (0/1/2 healthy/warning/critical).
  - Admin endpoints: `GET /api/v1/admin/audit/health` and `POST /api/v1/admin/audit/check-now`.
  - MCP tool: `verify_audit_chain` (see `backend/mcp_server.py:306`).
- To re-run against production: `cd backend && uv run python tests/manual/verify_audit_chain_e2e.py`
  from a host with prod DB credentials loaded.

## P0 breaks

None. All integrity checks passed and all tamper scenarios were detected.

---

_Harness: `backend/tests/manual/verify_audit_chain_e2e.py`._  
_Verifier code: `backend/app/services/audit.py` (`AuditService.verify_chain`)._  
_Model: `backend/app/models/audit_log.py`._  
