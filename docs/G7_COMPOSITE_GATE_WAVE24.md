# G7 Composite Gate — Wave 24 (G7.24.T3)

**Generated**: 2026-07-27T11:30:09.678405+00:00
**Overall**: **OK** (exit `0`)

## Exit code semantics

| Code | Meaning |
|------|---------|
| `0` | All local OK (and prod WORK if checked) |
| `1` | Local fail (ruff / mypy / pytest / import) |
| `2` | Local OK, prod HOLD (dns / radar partial or unreachable) |

## Checks

| Gate | Tier | Verdict | Exit | Notes |
|------|------|---------|------|-------|
| `quick_import` | local | **WORK** | 0 | 0 |
| `dns` | prod | **WORK** | 0 | 0 |
| `radar` | prod | **WORK** | 0 | status=yellow |

## How to run

```bash
make g7-composite
python3 scripts/g7_composite_gate.py --ruff --pytest
python3 scripts/g7_composite_gate.py --import-only --json
```

## Notes

- Prod network may fail offline — treated as **HOLD (exit 2)**, never local FAIL.
- Default local gate is quick import (fast). Use `--pytest` for collect-only.
- Related: `scripts/g7_super_validator.py` (broader), `make g7-validate`.

---

Modified by Gustavo Almeida — G7 Wave 24 auto-report
