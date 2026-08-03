#!/usr/bin/env python3
"""CLI para auditoria estrita de evidências V3."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.graph_evidence_audit import GraphEvidenceAuditor


def main() -> int:
    evidence_dir = PROJECT_ROOT / ".evidence" / "gemini36-v3"
    if not evidence_dir.exists():
        evidence_dir = PROJECT_ROOT / ".evidence" / "gemini36-v2"
        
    auditor = GraphEvidenceAuditor(PROJECT_ROOT, evidence_dir)
    res = auditor.run_audit()
    
    if not res.is_valid:
        print(f"[FAIL V3 AUDIT] Found {len(res.violations)} violations:")
        for v in res.violations:
            print(f"  - {v}")
        return 1
        
    print(f"[PASS V3 AUDIT] Verified {res.nodes_verified} nodes cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
