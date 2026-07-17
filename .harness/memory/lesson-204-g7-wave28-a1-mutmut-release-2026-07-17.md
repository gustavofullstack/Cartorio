# Lesson 204 — G7 Wave 28 A1 mutmut + release notes (2026-07-17)

| Campo | Valor |
|-------|--------|
| **Wave** | G7 Wave 28 |
| **Agent** | cartorio-dev (A1) |
| **Tasks** | G7.02.T1, G7.25.T4 |
| **Date** | 2026-07-17 |

## What we did

1. **G7.02.T1** — Re-ran audit/pii mutation-killer suite (not full mutmut score):
   - `tests/test_audit_mutation_killers_g6.py` + `test_audit_mutmut_killers_g6.py` + `test_mutation_gate.py` + pii + audit regression selection.
   - **177 passed**.
   - Full `mutmut run --max-children 1` within 120s **did not re-score** (clean-test failure under mutmut selection; CPU budget).
   - Authoritative score remains **G6 baseline 73.0%** (`docs/MUTMUT_REPORT_G6.md`).
   - Report: `docs/MUTMUT_REPORT_G7_WAVE28.md`.
   - SUPER_PLANO: **[x] Wave28 killers green + report (full score night HOLD 73%)**.

2. **G7.25.T4** — Release notes only (no git tag):
   - `docs/RELEASE_NOTES_v0.7.0-g7-mvp.md` — waves 13–28 summary, metrics, HOLD residual SUI, how-to-tag when Gustavo approves.
   - SUPER_PLANO: **[x] Wave28 notes ready, tag HOLD**.

## Lessons

1. **Agent-side mutmut close ≠ full score.** Task text allows honest close when full mutmut is too slow: killers green + report + re-run command is enough to flip G7.02.T1 to [x] with night HOLD explicit.
2. **mutmut 3.6 CLI** has no `--paths-to-mutate`. Scope only via `backend/setup.cfg` `[mutmut] source_paths` + `pytest_add_cli_args_test_selection`. Temporary cfg edit is the way to focus audit-only night runs.
3. **Never auto-tag** `v0.7.0-g7-mvp` — notes ready is the deliverable; tag is SUI/Gustavo only.
4. **Parallel Wave 28 agents** already wrote W28 SUI/SRE rows in SUPER_PLANO/PROGRESS — append W28-DEV rather than overwriting their rows.
5. **Collection footgun:** schemas using `settings.pydantic_strict_mode` must import `from app.config import settings` (lgpd_consent/agendamento already do). Missing import → NameError across half the suite.

## Commands to remember

```bash
cd backend
uv run pytest -q --no-cov \
  tests/test_audit_mutation_killers_g6.py \
  tests/test_audit_mutmut_killers_g6.py \
  tests/test_mutation_gate.py \
  tests/test_pii.py tests/test_pii_sanitizer.py tests/test_pii_validators.py \
  tests/test_audit.py tests/test_audit_regression_v22_t024_t025.py

# night full re-run (after clean-test green):
uv run mutmut run --max-children 2
uv run mutmut results
```

## Artifacts

- `docs/MUTMUT_REPORT_G7_WAVE28.md`
- `docs/RELEASE_NOTES_v0.7.0-g7-mvp.md`
- `SUPER_PLANO_G7_100_TASKS.md` (G7.02.T1, G7.25.T4, W28-DEV)
- `PROGRESS.md` Wave 28 A1 entry

**Modified by Gustavo Almeida — cartorio-dev Wave 28**
