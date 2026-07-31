#!/usr/bin/env python3
"""Append-only, PII-free agent trace ledger for the BRAIN corpus pipeline.

Writes only opaque metadata under ``.evidence/brain-corpus/``. Never records
source filenames, raw text, secrets, or PII values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = PROJECT_ROOT / ".evidence" / "brain-corpus" / "agent-trace.jsonl"

# Reject accidental PII/secret patterns in free-text fields.
_BLOCKED = re.compile(
    r"(?i)("
    r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|"  # CPF-like
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"  # email
    r"(sk-|lin_api_|ghp_|xox|AKIA|AIza|gAAAAA|rnd_)"  # key prefixes
    r")"
)

_ALLOWED_AGENTS = frozenset(
    {
        "codex",
        "terra",
        "grok",
        "kimi",
        "agy",
        "pietra",
        "pipeline",
        "human",
        "gustavo",
    }
)

_ALLOWED_ACTIONS = frozenset(
    {
        "extract",
        "inventory",
        "classify",
        "review",
        "approve",
        "reject",
        "publish",
        "revoke",
        "supersede",
        "test",
        "document",
        "plan",
        "rollback",
    }
)


def _sanitize_field(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} empty")
    if _BLOCKED.search(cleaned):
        raise ValueError(f"{field_name} contains blocked pattern")
    if len(cleaned) > 500:
        raise ValueError(f"{field_name} too long")
    return cleaned


def append_trace(
    *,
    agent: str,
    action: str,
    gate: str,
    result: str,
    evidence_ref: str,
    notes: str = "",
    ledger_path: Path = DEFAULT_LEDGER,
) -> dict[str, object]:
    """Append one sanitized trace record. Returns the record (no secrets)."""
    agent_id = _sanitize_field(agent, "agent").lower()
    action_id = _sanitize_field(action, "action").lower()
    if agent_id not in _ALLOWED_AGENTS:
        raise ValueError("agent not in allowlist")
    if action_id not in _ALLOWED_ACTIONS:
        raise ValueError("action not in allowlist")

    record = {
        "schema_version": 1,
        "ts_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "agent": agent_id,
        "action": action_id,
        "gate": _sanitize_field(gate, "gate"),
        "result": _sanitize_field(result, "result"),
        "evidence_ref": _sanitize_field(evidence_ref, "evidence_ref"),
        "notes": _sanitize_field(notes, "notes") if notes else "",
    }
    canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    record["record_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append PII-free BRAIN agent trace")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--evidence-ref", required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args(argv)
    try:
        record = append_trace(
            agent=args.agent,
            action=args.action,
            gate=args.gate,
            result=args.result,
            evidence_ref=args.evidence_ref,
            notes=args.notes,
            ledger_path=args.ledger,
        )
    except ValueError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "record_sha256": record["record_sha256"],
                "agent": record["agent"],
                "action": record["action"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
