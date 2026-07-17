#!/usr/bin/env python3
"""G7 Super Orquestrador — status do SUPER_PLANO_G7_100_TASKS.md (Wave 17+).

Comandos:
  python3 scripts/g7_orchestrator.py status
  python3 scripts/g7_orchestrator.py next
  python3 scripts/g7_orchestrator.py validate

Modified by Gustavo Almeida + Pietra — G7 Wave 17.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLANO = ROOT / "SUPER_PLANO_G7_100_TASKS.md"
GOALS = ROOT / "SUPER_GOALS_G7.md"
STATE = ROOT / ".brain" / "loop-state.json"


def parse_tasks() -> list[dict]:
    if not PLANO.exists():
        return []
    text = PLANO.read_text(encoding="utf-8")
    tasks: list[dict] = []
    # | G7.xx.Ty | desc | [x] or [ ] or [~]
    for m in re.finditer(
        r"\|\s*(G7\.\d+\.T\d+)\s*\|\s*([^|]+)\|\s*(\[[ x~X]\][^\|]*)\|",
        text,
    ):
        tid, desc, status = m.group(1), m.group(2).strip(), m.group(3).strip()
        done = status.lower().startswith("[x]")
        partial = "[~]" in status
        tasks.append(
            {
                "id": tid,
                "desc": desc,
                "status_raw": status,
                "done": done,
                "partial": partial and not done,
            }
        )
    return tasks


def status_cmd() -> int:
    tasks = parse_tasks()
    done = sum(1 for t in tasks if t["done"])
    partial = sum(1 for t in tasks if t["partial"])
    total = len(tasks) or 100
    pct = round(100.0 * done / total, 1) if total else 0.0
    print(f"G7 Super Orquestrador — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Plan: {PLANO.name}")
    print(f"  Tasks parsed: {total} | done: {done} | partial: {partial} | open: {total - done - partial}")
    print(f"  Progress: {pct}%")
    if STATE.exists():
        try:
            st = json.loads(STATE.read_text())
            print(f"  loop-state: {st.get('status')} wave={st.get('metrics', {}).get('g7_wave')}")
        except json.JSONDecodeError:
            print("  loop-state: (invalid json)")
    open_tasks = [t for t in tasks if not t["done"]]
    print("  Next 8 open:")
    for t in open_tasks[:8]:
        mark = "~" if t["partial"] else " "
        print(f"    [{mark}] {t['id']} — {t['desc'][:60]}")
    return 0


def next_cmd() -> int:
    """Emite 4 tasks abertas para a próxima wave (1 por 'bucket' se possível)."""
    tasks = parse_tasks()
    open_tasks = [t for t in tasks if not t["done"]]
    # Prefer diversity by second number (squad)
    picked: list[dict] = []
    seen_squad: set[str] = set()
    for t in open_tasks:
        squad = t["id"].split(".")[1]  # 01, 02, ...
        if squad in seen_squad and len(picked) < 4:
            continue
        picked.append(t)
        seen_squad.add(squad)
        if len(picked) >= 4:
            break
    if len(picked) < 4:
        for t in open_tasks:
            if t not in picked:
                picked.append(t)
            if len(picked) >= 4:
                break
    print("NEXT WAVE (4 tasks / 4 agents):")
    reins = ["cartorio-dev", "cartorio-n8n", "cartorio-lgpd", "cartorio-sre"]
    for i, t in enumerate(picked[:4]):
        print(f"  [{reins[i % 4]}] {t['id']}: {t['desc']}")
    return 0


def validate_cmd() -> int:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "g7_super_validator.py"), "--skip-ruff"],
        cwd=str(ROOT),
    )
    return r.returncode


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        return status_cmd()
    if cmd == "next":
        return next_cmd()
    if cmd in ("validate", "val"):
        return validate_cmd()
    print("Usage: g7_orchestrator.py [status|next|validate]")
    return 2


if __name__ == "__main__":
    sys.exit(main())
