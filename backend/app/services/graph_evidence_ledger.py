"""Ledger append-only de evidências com cadeia de hashes (V3)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ChainedEvidenceLedger:
    def __init__(self, ledger_file: Path):
        self.ledger_file = ledger_file
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)

    def get_last_hash(self) -> str:
        if not self.ledger_file.exists() or self.ledger_file.stat().st_size == 0:
            return "0" * 64
        lines = [line.strip() for line in self.ledger_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return "0" * 64
        last_entry = json.loads(lines[-1])
        return str(last_entry.get("entry_hash", "0" * 64))

    def append_entry(self, task_id: str, status: str, evidence_data: dict[str, Any]) -> dict[str, Any]:
        prev_hash = self.get_last_hash()
        payload = {
            "task_id": task_id,
            "status": status,
            "previous_hash": prev_hash,
            "evidence_data": evidence_data,
        }
        canonical_str = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        entry_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
        
        full_record = {**payload, "entry_hash": entry_hash}
        
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(full_record) + "\n")
            
        return full_record

    def verify_chain(self) -> bool:
        if not self.ledger_file.exists():
            return True
        lines = [line.strip() for line in self.ledger_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return True
            
        expected_prev = "0" * 64
        for line in lines:
            entry = json.loads(line)
            if entry.get("previous_hash") != expected_prev:
                return False
            payload = {
                "task_id": entry["task_id"],
                "status": entry["status"],
                "previous_hash": entry["previous_hash"],
                "evidence_data": entry["evidence_data"],
            }
            canonical_str = json.dumps(payload, sort_keys=True, ensure_ascii=True)
            calc_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
            if calc_hash != entry.get("entry_hash"):
                return False
            expected_prev = entry["entry_hash"]
        return True
