#!/usr/bin/env python3
"""Coverage gap report (G7.01.T2) — lista módulos app/ < threshold.

Requer backend/.coverage gerado por pytest --cov.

Uso:
  cd backend && uv run pytest --cov=app --cov-report=term-missing -q --maxfail=1  # opcional
  python3 scripts/coverage_gap_report.py
  python3 scripts/coverage_gap_report.py --threshold 90 --md docs/COVERAGE_GAP_G7.md

Modified by Gustavo Almeida — G7 Wave 22.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COV_FILE = ROOT / "backend" / ".coverage"


def analyze(threshold: float) -> list[tuple[float, int, int, str]]:
    try:
        from coverage import Coverage
    except ImportError:
        print("[FAIL] coverage package not installed", file=sys.stderr)
        return []

    if not COV_FILE.is_file():
        print(f"[FAIL] missing {COV_FILE} — run pytest with --cov first", file=sys.stderr)
        return []

    c = Coverage(data_file=str(COV_FILE))
    c.load()
    data = c.get_data()
    rows: list[tuple[float, int, int, str]] = []
    for f in sorted(data.measured_files()):
        norm = f.replace("\\", "/")
        if "/app/" not in norm or "site-packages" in norm:
            continue
        try:
            analysis = c._analyze(f)
            n = analysis.numbers
            stmts = n.n_statements
            miss = n.n_missing
            if stmts <= 0:
                continue
            pct = 100.0 * (stmts - miss) / stmts
            if pct < threshold:
                rel = norm.split("/app/", 1)[-1]
                rows.append((pct, miss, stmts, rel))
        except Exception:
            continue
    rows.sort()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=90.0)
    parser.add_argument("--md", type=Path, default=None)
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args()

    rows = analyze(args.threshold)
    if not rows and not COV_FILE.is_file():
        return 2

    print(f"Coverage gap (<{args.threshold}%): {len(rows)} modules")
    for pct, miss, stmts, rel in rows[: args.top]:
        print(f"  {pct:5.1f}%  miss={miss:4d}/{stmts:4d}  app/{rel}")

    if args.md:
        lines = [
            f"# Coverage Gap Report (G7.01.T2)",
            "",
            f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
            f"**Threshold**: < {args.threshold}%",
            f"**Modules below threshold**: {len(rows)}",
            "",
            "| % | Miss | Stmts | Module |",
            "|---|------|-------|--------|",
        ]
        for pct, miss, stmts, rel in rows[: args.top]:
            lines.append(f"| {pct:.1f} | {miss} | {stmts} | `app/{rel}` |")
        lines += [
            "",
            "## Prioridade de testes",
            "",
            "1. `dead_mans_switch.py` / `evolution_ingest.py` — smaller, high leverage",
            "2. `health_radar_expanded.py` — prod observability",
            "3. `rate_limit_by_key.py` — security path",
            "4. `main.py` / `router.py` — large; prefer route-level tests already exist",
            "",
            "**Modified by Gustavo Almeida — G7 Wave 22**",
            "",
        ]
        args.md.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote {args.md}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
