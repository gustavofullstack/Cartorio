"""Testes unitários para o audit engine de evidências V3."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.graph_evidence_audit import GraphEvidenceAuditor


def test_auditor_passes_clean_matrix(tmp_path: Path) -> None:
    ev_dir = tmp_path / ".evidence" / "gemini36-v3"
    ev_dir.mkdir(parents=True)

    matrix = [
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
    (ev_dir / "claim-evidence-matrix.json").write_text(json.dumps(matrix), encoding="utf-8")

    auditor = GraphEvidenceAuditor(tmp_path, ev_dir)
    res = auditor.run_audit()
    assert res.is_valid is True
    assert res.nodes_verified == 2


def test_auditor_fails_weak_evidence(tmp_path: Path) -> None:
    ev_dir = tmp_path / ".evidence" / "gemini36-v3"
    ev_dir.mkdir(parents=True)

    matrix = [
        {
            "task_id": "G0.01",
            "reconciled_status": "ACCEPTED",
            "actual_evidence_level": "E0_SELF_ASSERTED",
        }
    ]
    (ev_dir / "claim-evidence-matrix.json").write_text(json.dumps(matrix), encoding="utf-8")

    auditor = GraphEvidenceAuditor(tmp_path, ev_dir)
    res = auditor.run_audit()
    assert res.is_valid is False
    assert len(res.violations) == 1
