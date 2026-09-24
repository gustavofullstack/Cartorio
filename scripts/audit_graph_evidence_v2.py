#!/usr/bin/env python3
"""Detector automatizado de fraudes de evidência e saltos de estado no Grafo.

Uso: python3 scripts/audit_graph_evidence_v2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_V2_DIR = PROJECT_ROOT / ".evidence" / "gemini36-v2"
CANONICAL_GRAPH = PROJECT_ROOT / "05_GRAPH_STATE_100_TASKS.json"


def audit_evidence() -> int:
    matrix_file = EVIDENCE_V2_DIR / "claim-evidence-matrix.json"
    if not matrix_file.exists():
        print(f"[FAIL] Matrix file not found: {matrix_file}")
        return 1

    matrix = json.loads(matrix_file.read_text(encoding="utf-8"))
    violations: list[str] = []

    human_gate_tasks = {"G1.18", "G1.24", "G1.46", "G2.04", "G2.35", "G2.36", "G2.37", "G2.38", "G2.39"}

    for item in matrix:
        tid = item["task_id"]
        status = item["reconciled_status"]
        level = item["actual_evidence_level"]

        # Check 1: ACCEPTED without E2 or higher
        if status == "ACCEPTED" and level in ("E0_SELF_ASSERTED", "E1_STATIC"):
            violations.append(f"{tid}: Claimed ACCEPTED with weak evidence level {level}")

        # Check 2: Human Gate assigned ACCEPTED without E5_HUMAN_SIGNOFF
        if tid in human_gate_tasks and status == "VALIDATED_ACCEPTED":
            violations.append(f"{tid}: Human gate task marked ACCEPTED without E5_HUMAN_SIGNOFF")

        # Check 3: Invalidated certification
        if tid in ("G2.39", "G2.40") and status == "ACCEPTED":
            violations.append(f"{tid}: Certification task cannot be ACCEPTED without E6_END_TO_END proof")

    if violations:
        print(f"[AUDIT FAIL] Found {len(violations)} evidence violations:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print(f"[AUDIT PASS] All {len(matrix)} tasks pass evidence integrity audit.")
    return 0


if __name__ == "__main__":
    sys.exit(audit_evidence())
