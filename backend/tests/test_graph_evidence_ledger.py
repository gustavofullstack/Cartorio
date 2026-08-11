"""Testes unitários para o ledger com cadeia de hashes (V3)."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.graph_evidence_ledger import ChainedEvidenceLedger


def test_chained_ledger_append_and_verify(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = ChainedEvidenceLedger(ledger_path)
    
    e1 = ledger.append_entry("G0.01", "ACCEPTED", {"cmd": "git status"})
    e2 = ledger.append_entry("G0.02", "ACCEPTED", {"cmd": "cat precedence.md"})
    
    assert e2["previous_hash"] == e1["entry_hash"]
    assert ledger.verify_chain() is True


def test_chained_ledger_tamper_detection(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = ChainedEvidenceLedger(ledger_path)
    
    ledger.append_entry("G0.01", "ACCEPTED", {"cmd": "git status"})
    ledger.append_entry("G0.02", "ACCEPTED", {"cmd": "cat precedence.md"})
    
    # Tamper with first entry
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    item = json.loads(lines[0])
    item["status"] = "TAMPERED"
    lines[0] = json.dumps(item)
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    
    assert ledger.verify_chain() is False
