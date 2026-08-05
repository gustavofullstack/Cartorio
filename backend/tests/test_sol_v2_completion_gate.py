# noqa: E402
"""Testes unitários para o SOL V2 Completion Gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sol_v2_completion_gate import verify_sol_v2_completion  # noqa: E402


def _write_minimal_v2_artifacts(base: Path) -> tuple[Path, Path, Path]:
    overlay = base / "state.v2.overlay.json"
    evidence = base / "evidence.v2.jsonl"
    incident = base / "INC-GRAPH-EVIDENCE-2026-08-03"
    incident.mkdir(parents=True)
    (incident / "commit-inventory.json").write_text(
        json.dumps(
            {
                "incident_id": "INC-GRAPH-EVIDENCE-2026-08-03",
                "base_trusted": "d5427b42ff998005fdef12b9b5a8f764033eeca7",
                "concurrent_commits": [
                    {"sha": "a06c8c19b7a3bf548df92689e51f4d59581b02a2"},
                    {"sha": "60f801bfb03b695348dec5b837a3a48a39e5c9d3"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (incident / "file-classification.csv").write_text(
        "path,classification,reason\n.brain/graph-engineer/state.json,UNTRUSTED_SELF_CERTIFICATION,Self-asserted status\n",
        encoding="utf-8",
    )
    (incident / "original-checksums.sha256").write_text(
        "abc123  a.txt\ndef456  b.txt\n",
        encoding="utf-8",
    )
    (incident / "salvaged-artifacts.json").write_text('{"salvaged_facts":[]}', encoding="utf-8")
    (incident / "supersession-manifest.json").write_text('{"superseded_by":"V2_FORWARD_ONLY_REMEDIATION","action":"QUARANTINED"}', encoding="utf-8")
    (incident / "invalidated-claims.jsonl").write_text('{"claim":"LARK_CERTIFIED","status":"INVALIDATED"}\n', encoding="utf-8")

    (base / ".evidence" / "incidents" / "INC-GRAPH-EVIDENCE-2026-08-03").mkdir(parents=True, exist_ok=True)
    (base / ".evidence" / "incidents" / "INC-GRAPH-EVIDENCE-2026-08-03" / "invalidated-claims.jsonl").write_text('{"claim":"LARK_CERTIFIED","status":"INVALIDATED"}\n', encoding="utf-8")

    overlay.write_text(
        json.dumps(
            {
                "version": 2,
                "orchestrator": "SOL-V2-RECOVERY-ORCHESTRATOR",
                "wave0_status": "WAVE_0R_GO",
                "nodes": {f"V2.R{i:02d}": "ACCEPTED" for i in range(1, 31)},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    evidence.write_text(
        "\n".join(
            [json.dumps({"task_id": f"V2.R{i:02d}", "status": "ACCEPTED"}) for i in range(1, 31)]
        )
        + "\n",
        encoding="utf-8",
    )

    (base / ".orchestration" / "cartorio-super-graph-v2").mkdir(parents=True, exist_ok=True)
    (base / ".orchestration" / "cartorio-super-graph-v2" / "completion-report.json").write_text(
        json.dumps({"status": "WAVE_0R_GO", "verdict": "PR_READY_PENDING_HUMANS"}, ensure_ascii=False),
        encoding="utf-8",
    )

    return overlay, evidence, incident


def _write_hg(base: Path) -> None:
    hg_dir = base / ".evidence" / "gemini36-v3"
    hg_dir.mkdir(parents=True)
    hg_data = {
        "human_gates": {
            "HG-01": {"status": "BLOCKED_HUMAN"},
            "HG-02": {"status": "BLOCKED_HUMAN"},
            "HG-03": {"status": "BLOCKED_HUMAN"},
            "HG-04": {"status": "BLOCKED_HUMAN"},
        }
    }
    (hg_dir / "human-gates.reconciled.json").write_text(json.dumps(hg_data), encoding="utf-8")


def test_sol_v2_completion_gate_pass(tmp_path: Path) -> None:
    overlay, evidence, incident = _write_minimal_v2_artifacts(tmp_path)
    _write_hg(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "backend" / "tests").mkdir(parents=True)
    (tmp_path / "scripts" / "sol_v2_completion_gate.py").write_text(
        "#!/usr/bin/env python3\n",
        encoding="utf-8",
    )
    (tmp_path / "backend" / "tests" / "test_sol_v2_completion_gate.py").write_text(
        "# test\n",
        encoding="utf-8",
    )

    repo_root = tmp_path

    is_pass, violations = verify_sol_v2_completion(overlay, evidence, incident, repo_root)
    assert is_pass is True
    assert len(violations) == 0


def test_sol_v2_completion_gate_fails_without_overlay(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.v2.jsonl"
    evidence.write_text("{}", encoding="utf-8")
    incident = tmp_path / "INC-GRAPH-EVIDENCE-2026-08-03"
    incident.mkdir(parents=True)
    (incident / "commit-inventory.json").write_text("{}", encoding="utf-8")
    is_pass, violations = verify_sol_v2_completion(tmp_path / "missing-overlay.json", evidence, incident, tmp_path)
    assert is_pass is False
    assert any("Overlay file missing" in item for item in violations)


def test_sol_v2_completion_gate_fails_if_nodes_incomplete(tmp_path: Path) -> None:
    overlay = tmp_path / "state.v2.overlay.json"
    evidence = tmp_path / "evidence.v2.jsonl"
    incident = tmp_path / "INC-GRAPH-EVIDENCE-2026-08-03"

    overlay.write_text(
        json.dumps(
            {
                "version": 2,
                "orchestrator": "SOL-V2-RECOVERY-ORCHESTRATOR",
                "wave0_status": "WAVE_0R_GO",
                "nodes": {"V2.R01": "ACCEPTED"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "scripts").mkdir()
    (tmp_path / "backend" / "tests").mkdir(parents=True)
    (tmp_path / "scripts" / "sol_v2_completion_gate.py").write_text(
        "#!\n",
        encoding="utf-8",
    )
    (tmp_path / "backend" / "tests" / "test_sol_v2_completion_gate.py").write_text(
        "#!\n",
        encoding="utf-8",
    )

    evidence.write_text(
        "{\"task_id\":\"V2.R01\",\"status\":\"ACCEPTED\"}\n",
        encoding="utf-8",
    )

    incident.mkdir(parents=True)
    (incident / "commit-inventory.json").write_text(
        json.dumps(
            {
                "incident_id": "INC-GRAPH-EVIDENCE-2026-08-03",
                "base_trusted": "d5427b42ff998005fdef12b9b5a8f764033eeca7",
                "concurrent_commits": [
                    {"sha": "a06c8c19b7a3bf548df92689e51f4d59581b02a2"},
                    {"sha": "60f801bfb03b695348dec5b837a3a48a39e5c9d3"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (incident / "file-classification.csv").write_text("path,classification\n", encoding="utf-8")
    (incident / "original-checksums.sha256").write_text("abc  x\n", encoding="utf-8")
    (incident / "salvaged-artifacts.json").write_text('{"salvaged_facts": []}', encoding="utf-8")
    (incident / "supersession-manifest.json").write_text('{"superseded_by":"V2_FORWARD_ONLY_REMEDIATION","action":"QUARANTINED"}', encoding="utf-8")
    (incident / "invalidated-claims.jsonl").write_text('{"claim":"LARK_CERTIFIED","status":"INVALIDATED"}\n', encoding="utf-8")

    (tmp_path / ".evidence" / "gemini36-v3").mkdir(parents=True)
    (tmp_path / ".evidence" / "gemini36-v3" / "human-gates.reconciled.json").write_text(
        json.dumps(
            {
                "human_gates": {
                    "HG-01": {"status": "BLOCKED_HUMAN"},
                    "HG-02": {"status": "BLOCKED_HUMAN"},
                    "HG-03": {"status": "BLOCKED_HUMAN"},
                    "HG-04": {"status": "BLOCKED_HUMAN"},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (tmp_path / ".orchestration" / "cartorio-super-graph-v2").mkdir(parents=True)
    (tmp_path / ".orchestration" / "cartorio-super-graph-v2" / "completion-report.json").write_text(
        json.dumps({"status": "WAVE_0R_GO", "verdict": "PR_READY_PENDING_HUMANS"}, ensure_ascii=False),
        encoding="utf-8",
    )

    is_pass, violations = verify_sol_v2_completion(overlay, evidence, incident, tmp_path)
    assert is_pass is False
    assert any("Wave 0R nodes not all ACCEPTED" in item for item in violations)
