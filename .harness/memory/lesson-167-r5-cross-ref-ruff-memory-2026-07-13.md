# Lesson 167 — YOLO round 5 orchestrator: 3 fixes (commit 7b11c15) — 2026-07-13

## TL;DR

10-lens R5 panel identified 3 isolated fixes that all auto-applied cleanly in commit `7b11c15`. ruff errors 3→0. Two important DEFER notes: (a) **R3 NOT in prod** still (lens R5-1 confirmed v0.5.4) — VPS-side deploy pending; (b) **3 PII tests failing when unmocked** (R5-4) — blocked on cartorio-lgpd review.

## What was fixed (commit 7b11c15)

| # | File | Change |
|---|------|--------|
| 1 | `GOALS.md`, `.trae/documents/yolo-super-plano-100t-cartorio-2026-07-03.md`, `.trae/documents/PLAN_LOOP_GOALS_CRON_MULTIAGENT.md` | 3 active `.harness/crons/LOOP_OBJECTIVE.md` refs → `.harness/loop-engineer/crons/LOOP_OBJECTIVE.md` |
| 2 | `backend/tests/conftest.py` | E402: moved `import subprocess` above comment block; F821: added `TYPE_CHECKING` guard for `StatefulBus` import |
| 2 | `backend/tests/test_observability_bots.py` | F841: renamed unused `result` to `_result` |
| 3 | `.harness/memory/MEMORY.md` (lines 35-41) | 5 dangling `~/.mavis/agents/mavis/memory/` refs replaced with inlined bullets |

**Total: 6 files, +14/-12 LOC. ruff: 3 → 0 errors. pytest: 62 pass / 1 pre-existing PII failure (not in scope).**

## Critical findings (NOT auto-fixed, requires human/external)

| Lens | Finding | Verdict | Why |
|------|---------|---------|-----|
| R5-1 | R3 commit `c8f9e6b` NOT in prod (still v0.5.4) | **DEFER** | VPS deploy coordination required (EasyPanel Swarm); user has VPS access via Tailnet |
| R5-4 | 3 PII tests fail when unmocked (`test_opencode_go_scrubs_all_pii_in_mixed_message`, `test_opencode_go_scrubs_pii_in_system_message`, `test_scrub_extremo_50_pii_com_cns_cnh`) | **BLOCKED** | PII surface → cartorio-lgpd review mandatory per CLAUDE.md hard rule |
| R5-4 | Modules below 90% coverage: bot_lgpd.py 62%, bot_direito_esquecimento.py 73%, integrations.py 76%, notificacao.py 77%, ws/atendimentos.py 78% | **DEFER** | Aggregate 91.61% passes the gate; individual gaps not blocking |
| R5-3 | `master-2656697941480454339` branch: 16d old, 323 commits diverged, unmerged | **DEFER** | Unmerged work; needs human review before `git branch -D` |
| R5-7 | All 3 SUI blockers open: DNS, Evolution QR, Chatwoot ENABLE_ACCOUNT_SIGNUP | **DEFER** | External/UI actions |
| R5-8 | 5 mavis/mavis dead paths | **FIXED in this commit** | Inlined into MEMORY.md |
| R5-9 | CLAUDE.md hardcodes "13 MCP tools" | **N/A** | False positive — CLAUDE.md says `count in backend/mcp_server.py` (no hardcode); only the README has the numbers |
| R5-10 | `.brain/index.md` and `.brain/loop-state.json` have stale timestamps + inconsistent metrics | **DEFER** | Content reorganization beyond docs-only scope |

## Lessons

1. **Verify R3 deploy check was right.** R5-1 confirmed R4-1 finding — R3 changes (c8f9e6b) are still not in prod. Both lenses independently probed and found `api.2notasudi.com.br` returning 404 on `/healthz`, `/readyz`, `/metrics`, `/mcp/`, `/api/v1/ws/atendimentos`. **Pattern: a "deploy verification" lens should run after every round that touches production-touching code.**

2. **ruff auto-fix landed 10/13 in one shot.** The F401 batch was applied via `ruff check --fix --no-cache` without breaking tests. The remaining 3 (E402 import-order, F821 undefined, F841 unused) needed surgical manual edits but stayed in `tests/`. **Pattern: F401/F841 = auto-fix safe; E402/F821 = read context first.**

3. **Dead references in MEMORY.md are silent rot.** The `~/.mavis/agents/mavis/memory/` directory never existed on this machine. The 5 dangling pointers would have stayed broken indefinitely without grep audit. **Pattern: any "external" path in MEMORY.md needs verification step (does the target exist? if not, inline).**

4. **Pre-existing test failures are NOT my regressions.** The R5 exec agent verified by `git stash` + re-run that `test_scrub_extremo_50_pii_com_cns_cnh` was already failing before the commit. Critical for trust — never claim "all green" when you didn't verify baseline. **Pattern: when a test fails, ALWAYS `git stash` + re-run to confirm it's pre-existing vs introduced.**

5. **The 3 PII test failures (R5-4) are the real outstanding P0.** They are filtered by default addopts but represent real LLM-isolation regression if integration tests run unmocked. The `test_opencode_go_no_pii.py` tests assert that the opencode_go LLM provider scrubs PII — part of the LGPD-by-design contract. **These need fixing BUT they touch PII surface → cartorio-lgpd review gate.**

## How to apply (next round)

Round 6 candidates:
1. **P0 fix: 3 PII tests** (R5-4) — open PR with cartorio-lgpd reviewer (BLOCKED on LGPD review per CLAUDE.md)
2. **Deploy R3 to prod** — VPS action; verify with R5-1 probe afterwards
3. **master-2656697941480454339 branch** — human review then prune
4. **.brain/ index.md/loop-state.json sync** — content reorg, low value
5. **Coverage gaps** in bot_lgpd.py, bot_direito_esquecimento.py — add tests (no PII surface, safe to auto-execute)

## Refs

- Commit `7b11c15` "chore(docs): fix 3 stale .harness/crons/ refs + 3 ruff + 5 dead mavis paths"
- Commits this YOLO session: `c037f33` (R2 types), `c8f9e6b` (R3 routing), `3f938fa` (R4 org), `7b11c15` (R5 docs)
- Memory commits: `f159f00` (lesson-164), `624bd73` (lesson-165), `414ac23` (lesson-166)
- Lens R5-1 confirmed R3 still not in prod (HIGH severity, awaiting user/VPS)
- Lens R5-4 confirmed 3 PII tests failing when unmocked (HIGH severity, LGPD review gate)
- [[2026-07-13-multi-agent-orchestration-loop]] — workflow structure
- [[2026-07-13-yolo-round-2-c037f33]] — R2 prior cycle
- [[2026-07-13-yolo-round-3-c8f9e6b]] — R3 prior cycle
- [[2026-07-13-yolo-round-4-3f938fa]] — R4 prior cycle

Modified by Gustavo Almeida — 2026-07-13 21:40 BRT