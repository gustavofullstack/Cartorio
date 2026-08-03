"""Testes unitários para o V3 Completion Gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.v3_completion_gate import verify_v3_completion


def test_v3_completion_gate_pass(tmp_path: Path) -> None:
    repo_root = tmp_path
    evidence_root = tmp_path / ".evidence" / "gemini36-v3"
    docs_root = tmp_path / "docs" / "audits" / "gemini36-v3"
    fixture_dir = repo_root / "backend" / "tests" / "fixtures"
    
    evidence_root.mkdir(parents=True)
    docs_root.mkdir(parents=True)
    fixture_dir.mkdir(parents=True)
    
    (docs_root / "00_V2_AUDIT_OF_AUDIT.md").write_text("# Audit", encoding="utf-8")
    
    hg_data = {
        "human_gates": {
            "HG-01": {"status": "BLOCKED_HUMAN"},
            "HG-02": {"status": "BLOCKED_HUMAN"},
            "HG-03": {"status": "BLOCKED_HUMAN"},
            "HG-04": {"status": "BLOCKED_HUMAN"}
        }
    }
    (evidence_root / "human-gates.reconciled.json").write_text(json.dumps(hg_data), encoding="utf-8")
    
    sample_json = json.dumps({"case_id": "1"}) + "\n"
    lines = [sample_json] * 200
    (fixture_dir / "cartorio_eval_v3.jsonl").write_text("".join(lines), encoding="utf-8")
    (evidence_root / "eval-deterministic-results.json").write_text("{}", encoding="utf-8")
    
    is_pass, violations = verify_v3_completion(repo_root, evidence_root, docs_root)
    assert is_pass is True
    assert len(violations) == 0
