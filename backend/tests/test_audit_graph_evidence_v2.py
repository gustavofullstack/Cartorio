"""Testes unitários para o detector de integridade de evidência (V2)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure scripts module is importable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_graph_evidence_v2 import audit_evidence  # noqa: E402


def test_audit_evidence_matrix_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_evidence_dir = tmp_path / ".evidence" / "gemini36-v2"
    test_evidence_dir.mkdir(parents=True)

    sample_matrix = [
        {
            "task_id": "G0.01",
            "reconciled_status": "VALIDATED_ACCEPTED",
            "actual_evidence_level": "E2_LOCAL_EXECUTION",
        },
        {
            "task_id": "G1.18",
            "reconciled_status": "BLOCKED_HUMAN",
            "actual_evidence_level": "E0_SELF_ASSERTED",
        },
    ]

    (test_evidence_dir / "claim-evidence-matrix.json").write_text(
        json.dumps(sample_matrix), encoding="utf-8"
    )

    monkeypatch.setattr("scripts.audit_graph_evidence_v2.EVIDENCE_V2_DIR", test_evidence_dir)
    assert audit_evidence() == 0


def test_audit_evidence_detects_false_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_evidence_dir = tmp_path / ".evidence" / "gemini36-v2"
    test_evidence_dir.mkdir(parents=True)

    bad_matrix = [
        {
            "task_id": "G2.39",
            "reconciled_status": "ACCEPTED",
            "actual_evidence_level": "E0_SELF_ASSERTED",
        }
    ]

    (test_evidence_dir / "claim-evidence-matrix.json").write_text(
        json.dumps(bad_matrix), encoding="utf-8"
    )

    monkeypatch.setattr("scripts.audit_graph_evidence_v2.EVIDENCE_V2_DIR", test_evidence_dir)
    assert audit_evidence() == 1
