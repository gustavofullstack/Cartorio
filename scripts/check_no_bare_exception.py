#!/usr/bin/env python3
"""Gate: proibe `raise Exception(...)` em app/ (G7.21.T4).

Use exceptions tipadas de `app.core.exceptions`.
Exit 0 = clean; 1 = violacoes; 2 = path missing.

Modified by Gustavo Almeida — G7 Wave 16.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "backend" / "app"
PATTERN = re.compile(r"^\s*raise\s+Exception\s*\(")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=APP)
    args = parser.parse_args()
    if not args.path.is_dir():
        print(f"[ERROR] path not found: {args.path}", file=sys.stderr)
        return 2

    hits: list[str] = []
    for py in sorted(args.path.rglob("*.py")):
        try:
            lines = py.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            print(f"[WARN] {py}: {exc}", file=sys.stderr)
            continue
        for i, line in enumerate(lines, 1):
            if PATTERN.search(line) and "noqa" not in line:
                rel = py.relative_to(ROOT)
                hits.append(f"{rel}:{i}: {line.strip()}")

    if hits:
        print(f"[FAIL] {len(hits)} bare raise Exception( in {args.path}")
        for h in hits[:50]:
            print(f"  {h}")
        if len(hits) > 50:
            print(f"  ... +{len(hits) - 50} more")
        return 1

    print(f"[WORK] zero bare raise Exception( under {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
