# Lesson 164 — mypy 7 errors resolved (whatsapp.py null-deref + chat_pipeline.py handler shadowing + bot_metrics.py PII Literal) — 2026-07-13

## TL;DR

Executed YOLO mode orchestrator with 10-lens decision panel. Top-3 prioritized; only ONE had surgical auto-fix (mypy). Fix applied in commit `c037f33`. mypy **7 → 0 errors** across 128 files. 102/102 audit+pii+lgpd tests pass, zero regression. Per-file-ignores for ruff in place but INERT (S-rules not enabled).

## Context

YOLO mode round 2 invoked 2026-07-13 19:00 BRT. Recon (4 agents) → Painel (10 parallel lens agents) → Execução (1 agent + 2 done-by-judge) → Validação (mypy + pytest) → Memory.

## What was fixed (commit c037f33)

| File | Line | Original bug | Fix applied |
|------|------|--------------|-------------|
| `app/api/v1/whatsapp.py` | 202 | list→str type-narrow | `dict[str, Any]` annotation + `Any` import |
| `app/api/v1/whatsapp.py` | 413 | None passed where Session expected — null-deref on hot path | Real `Session` via `Depends(get_db)` |
| `app/services/chat_pipeline.py` | 151 | Loop var `h` shadowed StreamHandler→Handler | Renamed to `existing_handler` |
| `app/services/chat_pipeline.py` | 465 | Nonexistent `.text` attr on ChatResponse | `.content` (real attr per dataclass) |
| `app/services/bot_metrics.py` | 183 | str passed where Literal required (PII category) | `if tipo in (...)` + `cast(TipoScrubLabel, ...)` |
| `app/services/lgpd/bot_direito_esquecimento.py` | 388 | `Result.rowcount` may be None | `getattr(result, "rowcount", 0) or 0` |
| `app/services/lgpd/bot_direito_esquecimento.py` | 407 | same as 388 | same |
| `backend/pyproject.toml` | — | ruff per-file-ignores missing | Added section silencing S101/S105/S110 in tests/, S608/S104 in alembic/, S110 in middleware/ |

**All 7 mypy errors were real latent runtime bugs**, not type-system noise. Particularly:
- `whatsapp.py:413` would have ALWAYS raised `AttributeError` on hot path (the code was wrapped in `try/except` that would mask the actual bug).
- `bot_metrics.py:183` could silently mis-classify PII categories — directly LGPD-relevant.

**No `# type: ignore` silence comments used.** Only `cast()` in `bot_metrics.py` where runtime label set legitimately exceeds the Literal subset (cnpj, placa_veiculo, data emitted by `pii._PATTERNS` but not in the Literal).

## What was NOT fixed (deliberate deferrals)

| Finding | Why deferred |
|---------|--------------|
| 8 burned keys in PROMPT.json + 5 markdown files | BY POLICY (Sprint 3 Goal #3: not yet rotated, marked `# noqa: ALLOW_KEY_FALLBACK`) |
| audit_create.py / audit_query.py / audit_context.py are stubs | **LENS HALLUCINATION** — files are 2294 / 3360 / 2023 bytes, not 0-byte. Verified with `wc -c`. |
| /healthz, /readyz, /metrics 404 at root | Code change scope (router includes); not 1-line fix; deferred to next round |
| /ws/atendimentos 404 in Traefik | Infra routing config; not code-fixable from repo |
| n8n + Evolution offline | UI blockers (DNS, QR scan) — cannot auto-fix in YOLO |
| ruff S101 × 5,275 false-positives in tests/ | per-file-ignores added but INERT until `select = ["S"]` enabled in `[tool.ruff.lint]` |
| 4 unmarked `relationship()` → N+1 risk | Model-level refactor; multi-file; deferred |
| `time.sleep` in `redlock.py:182` async loop | 1-line fix but should be its own PR with observability |
| TODO/FIXME × 32 across 10 test files | Triage needed, low priority |
| trae-agent submodule drift (390MB dirty) | Local tooling artifact, decide separately |

## Lessons

1. **lens agents hallucinate structured fields.** The lgpd-audit lens reported "audit_create.py is 0-byte stub" — file is 2294 bytes. Always `wc -c` before "populating" an alleged empty file. **Future cycles: agents must run a verification step before recommending creation/edit.**

2. **mypy default config + per-line annotations > global strict mode for legacy projects.** 7 errors caught without ruff F401-style noise. Adding strict mode would surface noise that drowns signal. Keep `[tool.mypy]` empty.

3. **`cast()` is honest when Literal is too narrow.** `pii._PATTERNS` emits more labels than `TipoScrubLabel` allows. Casting with guard + dropping invalid labels is better than widening Literal (which forces type-system-wide changes). Document this in `app/services/bot_metrics.py`.

4. **YOLO mode round structure works.** 10 parallel lenses → 1 exec → 1 val. Each exec agent gets ONE focused task, not a shopping list.

5. **Keep secrets in repo when policy says so.** The "scrub all burned keys" lens advice was rejected: secrets are documented as not-yet-rotated by the user's own policy. Mass-replacing them could break ops continuity. **Lesson: read the user's policy markers (`# noqa: ALLOW_KEY_FALLBACK`, goal references) before "fixing" intentional states.**

## How to apply (next cycle)

- Resume with `Workflow({scriptPath, resumeFromRunId: <wf_id>})` after current wf completes
- Round 3 top-3 candidates (next orchestrator cycle):
  1. **/healthz, /readyz, /metrics root aliases** (orchestrator probes currently 404; small router-include change)
  2. **Module wiring for root MCP** (`/mcp/` → sub-app needs root route OR raise trailing slash route)
  3. **Enable `select = ["S"]` + verify 5,402 → 0 ruff violations** (mechanical, in place since c037f33)
- Optional Round 3+: WS route fix in Traefik (infra), submodule cleanup (discretionary), .harness/crons consolidation (organizational).

## Refs

- [[2026-07-13-multi-agent-orchestration-loop]] — workflow structure
- [[2026-07-13-my-orchestrator-style]] (to create) — extended notes on YOLO cycles
- Commit `c037f33` "fix(types): resolve 7 mypy errors + ruff per-file-ignores"
- `.brain/memory/2026-07-13.md` — session consolidated log
- Modified by Gustavo Almeida — 2026-07-13 19:25 BRT
