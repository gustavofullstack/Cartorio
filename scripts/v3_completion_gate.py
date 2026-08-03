#!/usr/bin/env python3
"""V3 Completion Gate — Validador Final de Conclusão Técnica (V3)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def verify_v3_completion(repo_root: Path, evidence_root: Path, docs_root: Path) -> tuple[bool, list[str]]:
    violations: list[str] = []
    
    # 1. Audit of Audit doc check
    if not (docs_root / "00_V2_AUDIT_OF_AUDIT.md").exists():
        violations.append("00_V2_AUDIT_OF_AUDIT.md missing in docs_root")
        
    # 2. Human gates check
    hg_file = evidence_root / "human-gates.reconciled.json"
    if not hg_file.exists():
        violations.append("human-gates.reconciled.json missing")
    else:
        hg_data = json.loads(hg_file.read_text(encoding="utf-8"))
        gates = hg_data.get("human_gates", {})
        for g_id, g_info in gates.items():
            if g_info.get("status") != "BLOCKED_HUMAN":
                violations.append(f"Human Gate {g_id} is not BLOCKED_HUMAN (got {g_info.get(status)})")
                
    # 3. Gold dataset check
    fixture_file = repo_root / "backend" / "tests" / "fixtures" / "cartorio_eval_v3.jsonl"
    if not fixture_file.exists():
        violations.append("Gold dataset fixture cartorio_eval_v3.jsonl missing")
    else:
        lines = [l for l in fixture_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        if len(lines) < 200:
            violations.append(f"Gold dataset must have at least 200 cases (got {len(lines)})")
            
    # 4. Evals result check
    eval_res = evidence_root / "eval-deterministic-results.json"
    if not eval_res.exists():
        violations.append("eval-deterministic-results.json missing")
        
    return len(violations) == 0, violations


def main() -> int:
    parser = argparse.ArgumentParser(description="V3 Completion Gate")
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--docs-root", required=True, type=Path)
    args = parser.parse_args()
    
    is_pass, violations = verify_v3_completion(args.repo_root, args.evidence_root, args.docs_root)
    
    if not is_pass:
        print(f"[V3 COMPLETION GATE FAIL] Found {len(violations)} violations:")
        for v in violations:
            print(f"  - {v}")
        return 1
        
    print("[V3 COMPLETION GATE PASS] All objective completion gates passed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
