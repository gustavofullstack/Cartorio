#!/usr/bin/env python3
"""Offline classification of sanitized BRAIN corpus derivatives.

Reads only ``derived/manifest.sanitized.json`` and ``derived/units.sanitized.jsonl``.
Writes ``derived/classification.sanitized.json`` without source names, raw text,
or network/LLM calls. Never promotes to PUBLISHED.
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

from app.services.conhecimento_pipeline import (  # noqa: E402
    escrever_classificacao_sanitizada,
    executar_pipeline_classificacao,
)

DEFAULT_DERIVED = (
    PROJECT_ROOT
    / ".private/brain-ingest-quarantine/2026-07-31-ce236ba32b01/derived"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline sanitized BRAIN corpus classification (no publish)"
    )
    parser.add_argument("--derived", type=Path, default=DEFAULT_DERIVED)
    arguments = parser.parse_args(argv)

    derived = arguments.derived.resolve()
    if not derived.is_dir():
        print(json.dumps({"is_blocked": True, "reason": "derived_missing"}))
        return 2

    try:
        summary, payload = executar_pipeline_classificacao(derived)
        escrever_classificacao_sanitizada(derived, payload)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        print(json.dumps({"is_blocked": True, "reason": "classification_failure"}))
        return 2

    print(json.dumps(summary.as_dict(), sort_keys=True))
    return 2 if summary.is_blocked else 0


if __name__ == "__main__":
    sys.exit(main())
