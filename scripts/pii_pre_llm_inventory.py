#!/usr/bin/env python3
"""PII pre-LLM call-site inventory (G7.02.T3).

Lista caminhos que DEVEM scrubbar antes de LLM/public output e verifica
presenca de scrub() / pii_scrub / sanitize no source.

Uso:
  python3 scripts/pii_pre_llm_inventory.py
  python3 scripts/pii_pre_llm_inventory.py --json
  python3 scripts/pii_pre_llm_inventory.py --strict   # exit 1 se gap

Modified by Gustavo Almeida — G7 Wave 19.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "backend" / "app"

# Paths that must contain a scrub call (relative to backend/app)
REQUIRED_SCRUB_SITES: tuple[tuple[str, str], ...] = (
    ("services/chat_pipeline.py", "inbound pipeline pre-LLM"),
    ("services/cartorio_agent.py", "agent user text pre-LLM"),
    ("integrations/opencode_go.py", "OpenCode-Go provider"),
    ("integrations/openclaw.py", "OpenClaw gateway"),
    ("integrations/opencode_generic.py", "generic opencode"),
    ("integrations/antigravity.py", "Antigravity bridge"),
    ("utils/output_safety.py", "output safety layer"),
    ("api/v1/telegram.py", "telegram inbound/outbound"),
)

SCRUB_MARKERS = re.compile(
    r"\bscrub\s*\(|\bpii_scrub\s*\(|sanitize_bot_output\s*\(|sanitize_pii\s*\(",
    re.M,
)


def check_site(rel: str) -> dict:
    path = APP / rel
    if not path.is_file():
        return {"path": rel, "ok": False, "error": "missing file", "hits": 0}
    text = path.read_text(encoding="utf-8", errors="replace")
    hits = len(SCRUB_MARKERS.findall(text))
    return {
        "path": rel,
        "ok": hits >= 1,
        "hits": hits,
        "bytes": path.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    sites = []
    for rel, purpose in REQUIRED_SCRUB_SITES:
        row = check_site(rel)
        row["purpose"] = purpose
        sites.append(row)

    gaps = [s for s in sites if not s["ok"]]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sites_total": len(sites),
        "sites_ok": len(sites) - len(gaps),
        "gaps": gaps,
        "sites": sites,
        "verdict": "WORK" if not gaps else "FAIL",
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"PII pre-LLM inventory — {report['verdict']}")
        print(f"  {report['sites_ok']}/{report['sites_total']} sites scrubbed")
        for s in sites:
            mark = "WORK" if s["ok"] else "FAIL"
            print(f"  [{mark}] {s['path']} hits={s.get('hits')} — {s['purpose']}")
        if gaps:
            print(f"  GAPS: {len(gaps)}")

    if args.strict and gaps:
        return 1
    return 0 if not gaps else (1 if args.strict else 0)


if __name__ == "__main__":
    sys.exit(main())
