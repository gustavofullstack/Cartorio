# N8N Pre-commit Workflow Lint (G8.14.T4)

> Lightweight, per-file pre-commit hook that validates `infra/n8n-workflows/*.json`
> exports before they land on `master`. Stdlib-only. LGPD anti-PII check built-in.

**Author**: cartorio-n8n · **Wave**: G8.14 · **Date**: 2026-07-18

---

## What it does

A new hook (`n8n-workflow-lint`) is wired into `.pre-commit-config.yaml`. When
you `git commit` a change to any `infra/n8n-workflows/*.json`, the hook runs
**only on the changed file(s)** (per-file, sub-second) and blocks the commit
if any of these fail:

| # | Check | Severity | Why |
|---|-------|----------|-----|
| 1 | File is valid JSON (RFC 8259) | BLOCKER | Broken JSON breaks downstream n8n import |
| 2 | Top-level has `name`, `nodes`, `connections` | BLOCKER | Required by n8n runtime |
| 3 | `nodes` is a list of dicts with `name` + `type` | BLOCKER | Without `type`, n8n can't render the node |
| 4 | LGPD: CPF / CNPJ regex in node `name` | BLOCKER | PII in workflow labels leaks via export |
| 5 | LGPD: CPF / CNPJ / PHONE-BR regex in `parameters` | BLOCKER | PII in HTTP body / form fields violates LGPD Art. 46 |

The hook is intentionally **separate from** the existing global
`workflow-validator` hook (which scans the whole directory and takes seconds);
the per-file lint short-circuits on just the diff and gives clear, line-level
errors.

---

## Setup (one-time)

```bash
uv tool install pre-commit
pre-commit install
```

Verify the new hook is registered:

```bash
pre-commit run n8n-workflow-lint --all-files
# → N8N pre-commit lint OK (39 file(s) checked)
```

---

## Example failure

```text
$ git commit -am "feat(n8n): export 50-protocolo-renewal"
N8N pre-commit lint FAILED:
  - infra/n8n-workflows/50-protocolo-renewal.json: nodes[2].parameters contains PII (CPF) — use PII scrubber / variable; node='HTTP Send'
  - infra/n8n-workflows/50-protocolo-renewal.json: nodes[5].name contains PII (PHONE-BR-DASHED): 'Send to 98855-1234'

2 violation(s) found. Fix or bypass with SKIP=n8n-workflow-lint git commit ...
```

---

## How to bypass (escape hatch)

If you have a legitimate, justified reason to commit a WF that triggers the
hook (e.g. you're shipping a deliberately-redacted demo fixture and have
documented the exception), bypass per commit:

```bash
SKIP=n8n-workflow-lint git commit -m "..."
```

**Do not** add `# noqa: N8N_LINT` markers in JSON — the script doesn't read
those. If you find yourself bypassing repeatedly, open a lesson in
`.harness/memory/` explaining why and fix the underlying cause.

---

## LGPD regex catalog

| Label | Pattern | Examples that match | Examples that don't |
|-------|---------|---------------------|---------------------|
| `CPF` | `\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b` | `000.000.000-00`, `11122233344` | `1234567` (7 digits), `1234567890` (10 digits) |
| `CNPJ` | `\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b` | `11.111.111/0001-11`, `11111111000111` | `12345678` (8 digits) |
| `PHONE-BR-PARENS` | `\(\d{2}\)\s*\d{4,5}-?\d{4}` | `(34) 98855-1234`, `(11) 3333-4444` | `(34) 988551234` (no dashes; bare 11-digit not matched by this pattern, but flagged by `PHONE-BR-DASHED` only when dashed) |
| `PHONE-BR-DASHED` | `\b\d{4,5}-\d{4}\b` | `98855-1234` (mobile w/o DDD), `3333-4444` (landline w/o DDD) | `31583914` (N8N assignment id, no dash) |

> **False-positive guard**: the original draft used `?\d{4}` (optional dash)
> for phone numbers, which produced spurious matches on N8N assignment ids
> like `31583914`. Final regex requires the dash to be **mandatory** (or the
> parenthesized form), eliminating the false positive. Regression test:
> `test_lint_8digit_assignment_id_does_not_trigger_phone_match`.

---

## Standalone usage (no pre-commit)

The script works as a plain CLI too — useful for CI or one-off scans:

```bash
# Lint a single file
python3 scripts/n8n_precommit_lint.py infra/n8n-workflows/01-consulta-emolumento.json

# Lint many files at once
python3 scripts/n8n_precommit_lint.py infra/n8n-workflows/*.json

# Quiet mode (suppress OK line; errors always print)
python3 scripts/n8n_precommit_lint.py --quiet infra/n8n-workflows/*.json

# Show help
python3 scripts/n8n_precommit_lint.py --help
```

Exit codes:

- `0` — all files OK (or skipped: non-existent / non-`.json`)
- `1` — at least one violation found

---

## Why a NEW hook instead of extending `workflow-validator`?

| Aspect | `workflow-validator` (existing, G6.B.T1) | `n8n-workflow-lint` (NEW, G8.14.T4) |
|--------|-------------------------------------------|--------------------------------------|
| Scope | Whole `infra/n8n-workflows/` dir | **Only changed files** (per-file args) |
| Time | ~3–5 s on 39 WFs | < 100 ms per file |
| Output | Aggregated 33-rule report | One-line per violation with file path |
| When | Global sanity check | Per-commit fast feedback |
| LGPD regex on values | Field-name based (`cpf`, `rg`, …) | **Regex on values** (CPF/CNPJ/PHONE-BR) |

Both hooks run together: the global one catches cross-workflow issues
(duplicate webhook paths), the per-file one catches mistakes in the diff
you're about to ship.

---

## Tests

`backend/tests/test_n8n_precommit_lint_g8.py` — 16 tests covering:

- Positive paths (valid WF, empty argv, skip non-JSON, skip missing)
- Negative paths (invalid JSON, missing keys, bad `nodes` type, missing
  `type`, PII in name, PII in parameters — CPF/CNPJ/PHONE)
- Anti-false-positive regression (8-digit N8N assignment IDs)
- CLI surface (`--help`, `--quiet`)

Run:

```bash
cd backend && uv run pytest tests/test_n8n_precommit_lint_g8.py -v --no-cov
# → 16 passed in <1s
```

---

## Related

- `scripts/n8n_workflow_validator.py` — global 33-rule validator (G6.B.T1)
- `scripts/n8n_wf_inventory.py` — offline parse + count (Wave 29)
- `scripts/n8n_orphan_detector.py` — orphan exporter detector (Wave 39)
- `docs/N8N_WF_INVENTORY_WAVE29_G7.md` — Wave 29 inventory lesson
- `.harness/memory/lesson-238-g8-14-t4-n8n-precommit-2026-07-18.md` — this
  task's lesson (decisions, anti-patterns, gotchas)

Modified by Gustavo Almeida — 2026-07-18.
