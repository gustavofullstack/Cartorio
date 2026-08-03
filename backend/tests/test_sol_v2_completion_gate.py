"""Testes unitários para o SOL V2 Completion Gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sol_v2_completion_gate import verify_sol_v2_completion


def test_sol_v2_completion_gate_pass(tmp_path: Path) -> None:
    overlay = tmp_path / "state.v2.overlay.json"
    evidence = tmp_path / "evidence.v2.jsonl"
    incident = tmp_path / "INC-GRAPH-EVIDENCE-2026-08-03"
    repo_root = tmp_path

    overlay.write_text("{}", encoding="utf-8")
    evidence.write_text("{}", encoding="utf-8")
    incident.mkdir(parents=True)
    (incident / "commit-inventory.json").write_text("{}", encoding="utf-8")

    hg_dir = repo_root / ".evidence" / "gemini36-v3"
    hg_dir.mkdir(parents=True)
    hg_data = {
        "human_gates": {
            "HG-01": {"status": "BLOCKED_HUMAN"},
            "HG-02": {"status": "BLOCKED_HUMAN"},
            "HG-03": {"status": "BLOCKED_HUMAN"},
            "HG-04": {"status": "BLOCKED_HUMAN"}
        }
    }
    (hg_dir / "human-gates.reconciled.json").write_text(json.dumps(hg_data), encoding="utf-8")

    is_pass, violations = verify_sol_v2_completion(overlay, evidence, incident, repo_root)
    assert is_pass is True
    assert len(violations) == 0
