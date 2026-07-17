#!/usr/bin/env python3
"""Smoke / E2E inventory + optional runner (G7.03.T2).

Lista testes sob backend/tests/smoke e documenta como habilitar markers
(excluídos por default em addopts).

Uso:
  python3 scripts/smoke_inventory.py
  python3 scripts/smoke_inventory.py --json
  # rodar smoke real (precisa rede/prod):
  cd backend && SMOKE_TARGET=prod uv run pytest -m smoke -v --no-cov

Modified by Gustavo Almeida — G7 Wave 21.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE_DIR = ROOT / "backend" / "tests" / "smoke"
TEST_FN = re.compile(r"^def (test_\w+)", re.M)


def inventory() -> dict:
    files: list[dict] = []
    total_tests = 0
    if not SMOKE_DIR.is_dir():
        return {"error": "smoke dir missing", "files": [], "total_tests": 0}

    for py in sorted(SMOKE_DIR.glob("test_*.py")):
        text = py.read_text(encoding="utf-8", errors="replace")
        tests = TEST_FN.findall(text)
        has_smoke_mark = "pytest.mark.smoke" in text or "mark.smoke" in text
        total_tests += len(tests)
        files.append(
            {
                "file": py.name,
                "tests": tests,
                "count": len(tests),
                "smoke_marker": has_smoke_mark,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dir": str(SMOKE_DIR.relative_to(ROOT)),
        "files": files,
        "total_files": len(files),
        "total_tests": total_tests,
        "how_to_run": [
            "cd backend && SMOKE_TARGET=prod uv run pytest tests/smoke -m smoke -v --no-cov",
            "cd backend && E2E_BASE_URL=https://api.2notasudi.com.br uv run pytest -m e2e --no-cov",
            "Note: default addopts excludes smoke/integration/e2e",
        ],
        "gaps": [
            "Meta G7.03.T2 pede 20 cenários Telegram — hoje smoke/ tem foco infra+WA+RIPD",
            "Expandir tests/smoke/test_telegram_*.py ou reativar suite em tests/smoke legado",
        ],
        "verdict": "WORK" if total_tests >= 5 else "HOLD",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    inv = inventory()
    if args.json:
        print(json.dumps(inv, indent=2, ensure_ascii=False))
    else:
        print(f"Smoke inventory — {inv.get('verdict')} · {inv.get('total_tests')} tests in {inv.get('total_files')} files")
        for f in inv.get("files") or []:
            mark = "smoke" if f["smoke_marker"] else "no-mark"
            print(f"  {f['file']}: {f['count']} tests [{mark}]")
            for t in f["tests"][:8]:
                print(f"    - {t}")
            if f["count"] > 8:
                print(f"    ... +{f['count'] - 8}")
        print("Run:", inv["how_to_run"][0])
        for g in inv.get("gaps") or []:
            print(f"  [GAP] {g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
