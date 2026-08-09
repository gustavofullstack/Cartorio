"""Módulo de Auditoria Estrita de Evidências do Grafo (V3)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AuditResult:
    is_valid: bool
    violations: list[str]
    nodes_verified: int


class GraphEvidenceAuditor:
    def __init__(self, repo_root: Path, evidence_root: Path):
        self.repo_root = repo_root
        self.evidence_root = evidence_root

    def run_audit(self) -> AuditResult:
        matrix_file = self.evidence_root / "claim-evidence-matrix.json"
        if not matrix_file.exists():
            return AuditResult(is_valid=False, violations=["Matrix file missing"], nodes_verified=0)

        matrix = json.loads(matrix_file.read_text(encoding="utf-8"))
        violations: list[str] = []

        human_gate_tasks = {
            "G1.18",
            "G1.24",
            "G1.46",
            "G2.04",
            "G2.35",
            "G2.36",
            "G2.37",
            "G2.38",
            "G2.39",
        }

        for item in matrix:
            tid = item["task_id"]
            status = item.get("reconciled_status", item.get("status"))
            level = item.get("actual_evidence_level", "E0_SELF_ASSERTED")

            # Check 1: ACCEPTED without E2 or higher
            if status == "ACCEPTED" and level in ("E0_SELF_ASSERTED", "E1_STATIC"):
                violations.append(f"{tid}: Claimed ACCEPTED with weak evidence level {level}")

            # Check 2: Human Gate marked VALIDATED_ACCEPTED without E5_HUMAN_SIGNOFF
            if tid in human_gate_tasks and status == "VALIDATED_ACCEPTED":
                violations.append(
                    f"{tid}: Human gate marked VALIDATED_ACCEPTED without E5_HUMAN_SIGNOFF"
                )

            # Check 3: Self-assigned certification
            if tid in ("G2.39", "G2.40") and status == "ACCEPTED":
                violations.append(
                    f"{tid}: Certification task cannot be ACCEPTED without E6_END_TO_END proof"
                )

        return AuditResult(
            is_valid=len(violations) == 0, violations=violations, nodes_verified=len(matrix)
        )
