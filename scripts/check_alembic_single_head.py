#!/usr/bin/env python3
"""Gate: Alembic deve ter exatamente 1 head (G7.08.T1).

Offline — não conecta no Postgres. Lê o graph em backend/alembic/versions.

Exit codes:
  0 = single head (OK)
  1 = zero ou múltiplos heads
  2 = config/path inválido

Uso:
  python scripts/check_alembic_single_head.py
  python scripts/check_alembic_single_head.py --backend-dir /path/to/backend

Modified by Gustavo Almeida — G7 Wave 24.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKEND = ROOT / "backend"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail if Alembic has != 1 head")
    parser.add_argument(
        "--backend-dir",
        type=Path,
        default=DEFAULT_BACKEND,
        help="Path to backend/ (contains alembic.ini + alembic/)",
    )
    args = parser.parse_args()
    backend: Path = args.backend_dir.resolve()
    ini = backend / "alembic.ini"
    if not ini.is_file():
        print(f"[ERROR] alembic.ini not found: {ini}", file=sys.stderr)
        return 2

    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
    except ImportError as exc:
        print(
            f"[ERROR] alembic not installed in this interpreter: {exc}",
            file=sys.stderr,
        )
        print(
            "Hint: run from backend venv, e.g. "
            "`cd backend && uv run python ../scripts/check_alembic_single_head.py`",
            file=sys.stderr,
        )
        return 2

    # Config relative to backend so script_location=alembic resolves.
    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(backend / "alembic"))

    try:
        script = ScriptDirectory.from_config(cfg)
        heads = list(script.get_heads())
    except Exception as exc:  # noqa: BLE001 — gate script: report any load failure
        print(
            f"[ERROR] failed to load Alembic script directory: {exc}", file=sys.stderr
        )
        return 2

    if len(heads) == 1:
        print(f"[OK] single Alembic head: {heads[0]}")
        return 0

    if not heads:
        print("[FAIL] zero Alembic heads (empty versions?)", file=sys.stderr)
        return 1

    print(f"[FAIL] multiple Alembic heads ({len(heads)}):", file=sys.stderr)
    for h in heads:
        print(f"  - {h}", file=sys.stderr)
    print(
        "Fix: create a merge revision "
        "(`alembic merge -m 'merge heads' heads`) and re-run.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
