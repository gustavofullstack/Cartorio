#!/usr/bin/env python3
"""Completion Gate do SOL V2 — Validador de Orquestração e Qualidade (V2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


BASE_TRUSTED_SHA = "d5427b42ff998005fdef12b9b5a8f764033eeca7"
CONCURRENT_COMMITS = {
    "a06c8c19b7a3bf548df92689e51f4d59581b02a2",
    "60f801bfb03b695348dec5b837a3a48a39e5c9d3",
}
REQUIRED_NODES = [f"V2.R{i:02d}" for i in range(1, 31)]
REQUIRED_HUMAN_GATES = {"HG-01", "HG-02", "HG-03", "HG-04"}


def _json_or_fail(path: Path, violations: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        violations.append(f"JSON file missing: {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        violations.append(f"Invalid JSON in {path}: {exc}")
        return None


def _jsonl_lines(path: Path, violations: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        violations.append(f"JSONL file missing: {path}")
        return []
    entries: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        raw = line.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            violations.append(f"Invalid JSONL in {path}:{index} -> {exc}")
            continue
        if isinstance(data, dict):
            entries.append(data)
    return entries


def _read_non_empty_file(path: Path, violations: list[str]) -> bool:
    if not path.exists():
        violations.append(f"Required file missing: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        violations.append(f"Required file is empty: {path}")
        return False
    return True


def _load_json_lines(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in text if line.strip()}


def verify_sol_v2_completion(
    overlay_path: Path,
    evidence_path: Path,
    incident_dir: Path,
    repo_root: Path,
) -> tuple[bool, list[str]]:
    violations: list[str] = []

    if not overlay_path.exists():
        violations.append(f"Overlay file missing: {overlay_path}")
        return False, violations
    if not evidence_path.exists():
        violations.append(f"Evidence ledger missing: {evidence_path}")
        return False, violations
    if not incident_dir.exists():
        violations.append(f"Incident directory missing: {incident_dir}")
        return False, violations

    overlay = _json_or_fail(overlay_path, violations)
    if overlay is None:
        return False, violations

    nodes = overlay.get("nodes")
    if not isinstance(nodes, dict):
        violations.append("Overlay.nodes is missing or not a dict")
    else:
        missing = [node for node in REQUIRED_NODES if nodes.get(node) != "ACCEPTED"]
        if missing:
            violations.append(f"Wave 0R nodes not all ACCEPTED: {missing}")

    wave_status = overlay.get("wave0_status")
    if wave_status != "WAVE_0R_GO":
        violations.append(f"Unexpected wave0_status: {wave_status}")

    if overlay.get("version") not in {"2", 2, "state.v2.overlay.json"}:
        violations.append(f"Unexpected overlay version: {overlay.get('version')}")

    commits = _json_or_fail(incident_dir / "commit-inventory.json", violations)
    if commits is not None:
        concurrent_commits: Iterable[str] = []
        try:
            concurrent_commits = [entry["sha"] for entry in commits.get("concurrent_commits", [])]
        except AttributeError:
            violations.append("commit-inventory.json does not have expected shape")
        for sha in CONCURRENT_COMMITS:
            if sha not in concurrent_commits:
                violations.append(f"Concurrent commit missing from inventory: {sha}")
        base_sha = commits.get("base_trusted")
        if base_sha != BASE_TRUSTED_SHA:
            violations.append(f"Unexpected base_trusted in commit inventory: {base_sha}")

    incident_files = [
        "commit-inventory.json",
        "file-classification.csv",
        "original-checksums.sha256",
        "salvaged-artifacts.json",
        "supersession-manifest.json",
        "invalidated-claims.jsonl",
    ]
    for name in incident_files:
        file_path = incident_dir / name
        if not _read_non_empty_file(file_path, violations) and name != "original-checksums.sha256":
            continue
        if name == "original-checksums.sha256":
            lines = _load_json_lines(file_path)
            if len(lines) < 2:
                violations.append("original-checksums.sha256 has insufficient entries")

    evidence_entries = _jsonl_lines(evidence_path, violations)
    if not evidence_entries:
        violations.append("Evidence ledger has no valid entries")
    else:
        task_ids = {entry.get("task_id") for entry in evidence_entries if isinstance(entry, dict)}
        missing = [node for node in REQUIRED_NODES if node not in task_ids]
        if missing:
            violations.append(f"Evidence ledger missing task_ids: {missing}")

    hg_path = repo_root / ".evidence" / "gemini36-v3" / "human-gates.reconciled.json"
    hg_data = _json_or_fail(hg_path, violations)
    if hg_data is not None:
        gates = hg_data.get("human_gates", {})
        for gate_id in REQUIRED_HUMAN_GATES:
            if gate_id not in gates:
                violations.append(f"Human gate missing: {gate_id}")
                continue
            if gates[gate_id].get("status") != "BLOCKED_HUMAN":
                violations.append(f"Human gate {gate_id} is not BLOCKED_HUMAN")

    for required_file in (
        Path(".evidence") / "incidents" / "INC-GRAPH-EVIDENCE-2026-08-03" / "invalidated-claims.jsonl",
        Path("scripts/sol_v2_completion_gate.py"),
        Path("backend/tests/test_sol_v2_completion_gate.py"),
    ):
        if not _read_non_empty_file(repo_root / required_file, violations):
            continue

    completion_report = repo_root / ".orchestration" / "cartorio-super-graph-v2" / "completion-report.json"
    report_data = _json_or_fail(completion_report, violations)
    if report_data is not None:
        if report_data.get("status") not in {"WAVE_0R_GO", "WAVE_0R_NO_GO", "PR_READY_PENDING_HUMANS"}:
            violations.append(f"Unexpected completion status: {report_data.get('status')}")

    return len(violations) == 0, violations


def main() -> int:
    parser = argparse.ArgumentParser(description="SOL V2 Completion Gate")
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--incident", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()

    is_pass, violations = verify_sol_v2_completion(args.overlay, args.evidence, args.incident, args.repo_root)

    if not is_pass:
        print(f"[SOL V2 COMPLETION GATE FAIL] Found {len(violations)} violations:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("[SOL V2 COMPLETION GATE PASS] All SOL V2 criteria passed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
