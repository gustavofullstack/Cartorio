#!/usr/bin/env python3
"""Offline N8N workflow inventory — JSON parse + count (no network).

Uso (raiz do repo):
    python3 scripts/n8n_wf_inventory.py
    python3 scripts/n8n_wf_inventory.py --json
    python3 scripts/n8n_wf_inventory.py --dir infra/n8n-workflows

Exit codes:
    0 = todos os *.json na raiz do dir parseiam OK
    1 = 1+ JSON quebrado
    2 = diretorio ausente

Modified by Gustavo Almeida — G7 Wave 29 A2 (cartorio-n8n).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_DIR = Path("infra/n8n-workflows")


def inventariar(wf_dir: Path) -> dict:
    if not wf_dir.is_dir():
        return {"ok": False, "error": f"dir missing: {wf_dir}", "count": 0}

    files = sorted(wf_dir.glob("*.json"))
    ok: list[dict] = []
    broken: list[dict] = []

    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            nodes = data.get("nodes") if isinstance(data, dict) else None
            ok.append(
                {
                    "file": path.name,
                    "name": data.get("name", path.stem) if isinstance(data, dict) else path.stem,
                    "active": bool(data.get("active")) if isinstance(data, dict) else False,
                    "nodes": len(nodes) if isinstance(nodes, list) else 0,
                    "bytes": path.stat().st_size,
                }
            )
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            broken.append({"file": path.name, "error": str(exc)[:200]})

    return {
        "ok": len(broken) == 0,
        "dir": str(wf_dir),
        "count": len(files),
        "valid": len(ok),
        "broken": len(broken),
        "active": sum(1 for e in ok if e["active"]),
        "inactive": sum(1 for e in ok if not e["active"]),
        "total_nodes": sum(e["nodes"] for e in ok),
        "workflows": ok,
        "broken_files": broken,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline N8N WF inventory (no network)")
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_DIR,
        help="Directory with workflow JSON exports (default: infra/n8n-workflows)",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args()

    report = inventariar(args.dir)

    if report.get("error"):
        print(f"FAIL: {report['error']}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"=== N8N WF Inventory (offline) ===")
        print(f"dir: {report['dir']}")
        print(f"count: {report['count']}  valid: {report['valid']}  broken: {report['broken']}")
        print(
            f"active: {report['active']}  inactive: {report['inactive']}  "
            f"total_nodes: {report['total_nodes']}"
        )
        print("")
        for e in report["workflows"]:
            flag = "ON " if e["active"] else "OFF"
            print(f"  [{flag}] {e['file']:42s}  nodes={e['nodes']:3d}  {e['name']}")
        if report["broken_files"]:
            print("")
            print("BROKEN JSON:")
            for b in report["broken_files"]:
                print(f"  ✗ {b['file']}: {b['error']}")
        print("")
        status = "PASS" if report["ok"] else "FAIL"
        print(f"status: {status}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
