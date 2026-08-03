#!/usr/bin/env python3
"""Append-only, PII-free agent trace ledger for the BRAIN corpus pipeline.

Writes only opaque metadata under ``.evidence/brain-corpus/``. Never records
source filenames, raw text, secrets, or PII values.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
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
    r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b|"  # CNPJ-like
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"  # email
    r"\bR\.?G\.?\s*:?\s*[\d.-]{5,18}\b|"  # RG-like
    r"\b\d{5}-?\d{3}\b|"  # CEP-like
    r"(?:\+?55\s*)?\(?\d{2}\)?\s*9?\d{4,5}[\s-]?\d{4}|"  # phone-like
    r"(?:/|~[/\\]|[A-Z]:[/\\])[A-Za-z0-9_.-]+(?:[/\\][A-Za-z0-9_.-]+)+|"
    r"(?:sk-|lin_api_|ghp_|xox|AKIA|AIza|gAAAAA|rnd_|Bearer\s+eyJ|"
    r"4/[A-Za-z0-9_-]{20,})"  # secret prefixes and OAuth authorization codes
    r")"
)

_SAFE_EVIDENCE_REF = re.compile(
    r"(?:"
    r"derived/(?:manifest|classification|hitl_queue)\.sanitized\.(?:json|jsonl)|"
    r"tests/[A-Za-z0-9_.*-]+\.py|"
    r"docs/[A-Z0-9_.-]+\.md|"
    r"git:[0-9a-f]{7,40}|sha256:[0-9a-f]{64}|gate:T[0-5]"
    r")"
)
_ZERO_HASH = "0" * 64

_ALLOWED_AGENTS = frozenset(
    {
        "cartorio-documentos",
        "cartorio-dev",
        "cartorio-lgpd",
        "codex-root",
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

    # Referências opacas são validadas por gramática fechada. Não aplique os
    # regex de telefone/CEP ao digest: sequências numéricas dentro de SHA-256
    # são falso positivo esperado e não contêm o valor de origem.
    evidence_id = evidence_ref.strip()
    if not evidence_id or len(evidence_id) > 500:
        raise ValueError("evidence_ref inválida")
    if _SAFE_EVIDENCE_REF.fullmatch(evidence_id) is None:
        raise ValueError("evidence_ref não é uma referência opaca permitida")

    if ledger_path.is_symlink():
        raise ValueError("ledger symlink rejeitado")
    ledger_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    ledger_path.parent.chmod(0o700)
    lock_path = ledger_path.with_name(f".{ledger_path.name}.lock")
    lock_descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    os.chmod(lock_path, 0o600)
    with os.fdopen(lock_descriptor, "r+") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        previous_hash = _last_valid_hash(ledger_path)
        record = {
            "schema_version": 2,
            "ts_utc": datetime.now(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "agent": agent_id,
            "action": action_id,
            "gate": _sanitize_field(gate, "gate"),
            "result": _sanitize_field(result, "result"),
            "evidence_ref": evidence_id,
            "notes": _sanitize_field(notes, "notes") if notes else "",
            "previous_hash": previous_hash,
        }
        record["record_sha256"] = _record_hash(record)
        descriptor = os.open(ledger_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                )
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            ledger_path.chmod(0o600)
    return record


def _record_hash(record: dict[str, object]) -> str:
    unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
    canonical = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _last_valid_hash(ledger_path: Path) -> str:
    """Validate every existing record and return the chain head."""
    if not ledger_path.exists():
        return _ZERO_HASH
    if ledger_path.is_symlink():
        raise ValueError("ledger symlink rejeitado")
    previous_hash = _ZERO_HASH
    chained_started = False
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("ledger inválido") from error
        if not isinstance(record, dict) or record.get("record_sha256") != _record_hash(
            record
        ):
            raise ValueError("ledger hash inválido")
        stored_previous = record.get("previous_hash")
        if stored_previous is None:
            if chained_started:
                raise ValueError("ledger chain inválida")
        elif stored_previous != previous_hash:
            raise ValueError("ledger chain inválida")
        else:
            chained_started = True
        previous_hash = str(record["record_sha256"])
    return previous_hash


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
    except (OSError, ValueError):
        print(json.dumps({"ok": False, "error": "trace_rejected"}))
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
