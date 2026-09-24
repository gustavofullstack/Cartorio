#!/usr/bin/env python3
"""Build a sanitized HITL review queue from classification.sanitized.json.

Offline, fail-closed, no network/LLM. Never promotes to PUBLISHED.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.conhecimento_hitl_queue import (  # noqa: E402
    build_and_write_hitl_queue,
)

DEFAULT_DERIVED = (
    PROJECT_ROOT / ".private/brain-ingest-quarantine/2026-07-31-ce236ba32b01/derived"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline HITL queue builder")
    parser.add_argument("--derived", type=Path, default=DEFAULT_DERIVED)
    args = parser.parse_args(argv)
    derived = args.derived.resolve()
    if not derived.is_dir():
        print(json.dumps({"is_blocked": True, "reason": "derived_missing"}))
        return 2
    try:
        summary, _path = build_and_write_hitl_queue(derived)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        print(json.dumps({"is_blocked": True, "reason": "hitl_queue_failure"}))
        return 2
    print(json.dumps(summary.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
