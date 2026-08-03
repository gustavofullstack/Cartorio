#!/usr/bin/env python3
"""Completion Gate do SOL V2 — Validador de Orquestração e Qualidade (V2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def verify_sol_v2_completion(overlay_path: Path, evidence_path: Path, incident_dir: Path, repo_root: Path) -> tuple[bool, list[str]]:
    violations: list[str] = []

    # 1. Check incident folder
    if not incident_dir.exists():
        violations.append(f"Incident directory missing: {incident_dir}")
    else:
        if not (incident_dir / "commit-inventory.json").exists():
            violations.append("Incident commit-inventory.json missing")

    # 2. Check overlay
    if not overlay_path.exists():
        violations.append(f"Overlay file missing: {overlay_path}")

    # 3. Check evidence
    if not evidence_path.exists():
        violations.append(f"Evidence ledger missing: {evidence_path}")

    # 4. Check human gates
    hg_file = repo_root / ".evidence" / "gemini36-v3" / "human-gates.reconciled.json"
    if hg_file.exists():
        hg_data = json.loads(hg_file.read_text(encoding="utf-8"))
        for gid, ginfo in hg_data.get("human_gates", {}).items():
            if ginfo.get("status") != "BLOCKED_HUMAN":
                violations.append(f"Human gate {gid} is not BLOCKED_HUMAN")
    else:
        violations.append("Human gates file missing")

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
