# Lesson 165 — YOLO round 3 orchestrator: 4 surgical routing/init fixes (commit c8f9e6b) — 2026-07-13

## TL;DR

10-lens R3 panel identified 4 surgical, low-risk fixes with zero LGPD/audit/PII touch. All applied in commit `c8f9e6b`. Validation: ruff pass, mypy pass (3 source files), 87/87 health+ws tests pass. **PUSH BACK on agent "easy" recommendation** — R3-4 (redlock asyncio) was correctly rejected because it would have caused a hot-spin loop, demonstrating the lens verification step works.

## What was fixed (commit c8f9e6b)

| # | File | Change | Why |
|---|------|--------|-----|
| 1 | `backend/app/main.py` | Added `/healthz`, `/readyz` (delegate to existing `/health` and `/ready`) + `/metrics` (410 → /api/v1/metrics/prometheus) | k8s/Traefik orchestrator probes were 404 |
| 2 | `backend/mcp_server.py:496,509` + `app/main.py:221,523,524` | `mcp.http_app(path="/mcp")` → `path="/"` + 3 docstring updates from `/mcp/mcp` to `/mcp` | Documentation already advertised `/mcp`; clients were hitting the wrong path |
| 3 | `backend/app/main.py:118-122` (lifespan) | `_init_sentry()` call at top, DSN-gated, no-op if absent | Sentry SDK was lazy-init on first capture, not at startup; init may never run before first exception |
| 4 | `backend/app/main.py:612` | `app.include_router(ws_router)` → `app.include_router(ws_router, prefix="/api/v1")` | Docs advertise `/api/v1/ws/atendimentos`; clients were getting 404 |

**Total: 58 insertions / 7 deletions across 2 files. Zero new files. Zero changes to audit/pii/lgpd.**

## What was REJECTED (and why this matters)

| Lens | Recommendation | Verdict | Why |
|------|----------------|---------|-----|
| R3-4 | `redlock.py:182 time.sleep → asyncio.sleep` (1-line) | **REJECTED** | Function is sync `@contextmanager`, not async. asyncio.sleep would emit unawaited coroutine warning → hot-spin loop hammering Redis ~60× more than intended. Sync code is correct for sync callers. |
| R3-7 | Triage 32 TODO/FIXME | **SKIP** | Word-bounded grep finds 5; naive grep finds 16. All 5 are Brazilian CPF/CNPJ mask placeholders (`XXX.XXX.XXX-XX`). Zero actionable debt. |
| R3-8 | Sanitize 26 unmarked files with burned keys | **DEFER** | Many are intentional (gateways used by prod); some are infra configs (e.g., `gateway-config-snapshot-t49.json` is loaded by openclaw processes). Rotation must precede redaction. |
| R3-6 | Drop trae-agent submodule (390MB dirty) | **DEFER** | Destructive (`rm -rf`); user confirmation needed; not blocking |
| R3-2 | Enable ruff `select=["S"]` | **DEFER** | Would surface 78 app/ hits, breaking CI without sprint cleanup |
| R3-10 | Standardize rein agent.md (6 satellites need Persona section) | **DEFER** | cartorio-security/watchdog/sre terseness is intentional (boundary statements); needs human sign-off |

## Lessons

1. **Lens verification step is non-negotiable.** R3-4 (redlock asyncio) was the perfect example: a lens recommended a "1-line fix" that would have silently degraded production performance. The exec agent that probed deeper caught the sync `@contextmanager` context and rejected the fix. **Pattern: any lens recommending a "1-line fix" should be verified with a static call-chain check before applying.**

2. **Auto-fix gates need 3 conditions: low risk + surgical scope + zero LGPD/audit/pii touch.** R3 met all 3 for 4 fixes. Anything that touches LGPD/audit/pii surfaces requires human review per CLAUDE.md hard rule.

3. **"/mcp" was documented correctly, but code was lying.** The fix made code match docs — never the reverse. This pattern (docs honest, code buggy) is healthier than the alternative.

4. **WebSocket clients need to migrate to /api/v1/ws/atendimentos.** The 1-line fix breaks old clients but matches docs. Future deploy: check `infra/openclaw-agent/agent-tools-registry.json` clients still work (per R3-9, they were already calling the new path and getting 404 — so migration is no-op for them).

5. **Sentry SDK init in lifespan, not lazy.** Hoisting to startup means OTel + Sentry share the same boot phase; if DSN is rotated mid-process, init captures it correctly. Lazy init only fired on first exception — too late.

## How to apply (next round)

Round 4 candidates (still no LGPD/audit/pii):
1. **test_pii_validators.py + test_pii_sanitizer.py population** — files exist but 0 tests. Add nominal + 2 edge cases per primitive (cpf/cnpj/rg/cnh/pis/email/phone). **WAIT: this is PII surface → needs cartorio-lgpd review first.** Add to queue but flag for sign-off.
2. **Rein agent.md Persona paragraphs** for 6 satellites — non-LGPD reins only (data/evolution/front); security/watchdog/sre need human review.
3. **MEMORY.md 83KB trim** — archive 2026-06-24..2026-06-30 section to `archive/MEMORY_2026-06.md` (lessons file links still work).
4. **trae-agent drop** (390MB) — destructive; needs user GO before `rm -rf`.

Hard-deferred until user rotation + sign-off:
- Secret sanitization (rotation precedes redaction)
- ruff select=['S'] activation (CI breakage without sprint)
- Test pii_*.py population (LGPD review gate)

## Refs

- Commit `c8f9e6b` "fix(routing): root health aliases + MCP route + Sentry init + WS prefix"
- Commit `c037f33` "fix(types): resolve 7 mypy errors + ruff per-file-ignores" (R2)
- Commit `f159f00` "chore(memory): lesson-164 YOLO round 2 orchestrator report + index" (R2 memory)
- `.brain/memory/2026-07-13.md` — consolidated session log
- [[2026-07-13-multi-agent-orchestration-loop]] — workflow structure
- [[2026-07-13-yolo-round-2-c037f33]] — R2 prior cycle

Modified by Gustavo Almeida — 2026-07-13 20:15 BRT