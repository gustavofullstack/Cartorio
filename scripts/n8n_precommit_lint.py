#!/usr/bin/env python3
"""Pre-commit lint for N8N workflow JSON exports (G8.14.T4).

Runs per-file checks on `infra/n8n-workflows/*.json` BEFORE a commit lands.
This hook is intentionally lightweight (stdlib-only) and per-file so it can
short-circuit on just the changed JSONs in the commit (unlike the global
`n8n_workflow_validator.py` which scans the whole dir and takes seconds).

Checks performed per file (each is a hard fail in pre-commit):
    1. JSON parses (RFC 8259) — invalid JSON blocks the commit
    2. Required top-level keys present (`name`, `nodes`, `connections`)
    3. `nodes` is a list and each entry is a dict with `name` + `type`
    4. LGPD anti-PII: CPF / CNPJ / PHONE-BR regex on node names
    5. LGPD anti-PII: same regex on stringified node parameters
       (parameters may legitimately hold CPFs in test fixtures, but pre-commit
       defaults to BLOCKING; bypass via `SKIP=n8n-workflow-lint git commit ...`)

Exit codes:
    0 = all files OK (or skipped because non-existent / non-json)
    1 = at least one violation found (commit blocked)

Bypass: SKIP=n8n-workflow-lint git commit ...

Usage:
    python3 scripts/n8n_precommit_lint.py infra/n8n-workflows/01-foo.json [...]
    python3 scripts/n8n_precommit_lint.py --quiet infra/n8n-workflows/*.json

Modified by Gustavo Almeida — G8.14.T4 (cartorio-n8n).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

REQUIRED_TOP_KEYS: tuple[str, ...] = ("name", "nodes", "connections")

# LGPD anti-PII patterns (BR national identifiers). Pre-compiled once.
# Real BR phones ALWAYS use a dash or parens-formatted area code; bare 8-digit
# numeric IDs (e.g. N8N assignment ids like "31583914") must NOT match.
PII_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "CPF"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), "CNPJ"),
    (re.compile(r"\(\d{2}\)\s*\d{4,5}-?\d{4}"), "PHONE-BR-PARENS"),
    (re.compile(r"\b\d{4,5}-\d{4}\b"), "PHONE-BR-DASHED"),
)


def pii_hits(value: str) -> list[str]:
    """Return list of PII labels found in `value` (may be empty)."""
    if not isinstance(value, str):
        return []
    return [label for pat, label in PII_PATTERNS if pat.search(value)]


def _stringify_params(params: object) -> str:
    """Stringify node.parameters (dict, list, scalar) for PII regex scan."""
    if params is None:
        return ""
    if isinstance(params, str):
        return params
    try:
        return json.dumps(params, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(params)


def lint_workflow(path: Path) -> list[str]:
    """Validate a single N8N workflow JSON. Returns list of error messages."""
    errors: list[str] = []

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: cannot read: {exc}"]

    try:
        wf = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"{path}: JSON invalid: {exc.msg} (line {exc.lineno} col {exc.colno})"]

    if not isinstance(wf, dict):
        return [f"{path}: top-level is not a dict (got {type(wf).__name__})"]

    for key in REQUIRED_TOP_KEYS:
        if key not in wf:
            errors.append(f"{path}: missing required top-level key '{key}'")

    nodes = wf.get("nodes")
    if not isinstance(nodes, list):
        errors.append(f"{path}: 'nodes' must be a list (got {type(nodes).__name__})")
        return errors  # can't continue without nodes list

    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"{path}: nodes[{i}] is not a dict (got {type(node).__name__})")
            continue
        if "name" not in node:
            errors.append(f"{path}: nodes[{i}] missing 'name'")
        if "type" not in node:
            errors.append(f"{path}: nodes[{i}] missing 'type'")

        node_name = str(node.get("name", ""))
        for label in pii_hits(node_name):
            errors.append(f"{path}: nodes[{i}].name contains PII ({label}): '{node_name}'")

        params_str = _stringify_params(node.get("parameters"))
        for label in pii_hits(params_str):
            errors.append(
                f"{path}: nodes[{i}].parameters contains PII ({label}) — "
                f"use PII scrubber / variable; node='{node_name}'"
            )

    return errors


def lint_paths(paths: Iterable[Path]) -> list[str]:
    """Lint a collection of paths. Non-existent / non-json are skipped silently."""
    all_errors: list[str] = []
    seen: set[Path] = set()
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        if not p.exists():
            continue
        if p.suffix.lower() != ".json":
            continue
        all_errors.extend(lint_workflow(p))
    return all_errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pre-commit lint for N8N workflow JSON exports.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="JSON file paths to lint (passed by pre-commit per-file).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress OK summary line (errors always printed).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    errors = lint_paths(args.files)

    if errors:
        print("\nN8N pre-commit lint FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            f"\n{len(errors)} violation(s) found. Fix or bypass with "
            "SKIP=n8n-workflow-lint git commit ...",
            file=sys.stderr,
        )
        return 1

    if not args.quiet:
        print(
            f"N8N pre-commit lint OK ({len(args.files)} file(s) checked)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
