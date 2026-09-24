#!/usr/bin/env python3
"""
Super Orquestrador do Cartório 2º Notas — default **G7**.

Fonte canônica de progresso: `SUPER_PLANO_G7_100_TASKS.md`
(via `scripts/g7_orchestrator.py`).

Comandos:
  python3 scripts/super_loop_orchestrator.py status
  python3 scripts/super_loop_orchestrator.py next
  python3 scripts/super_loop_orchestrator.py validate
  python3 scripts/super_loop_orchestrator.py run next   # alias de next
  python3 scripts/super_loop_orchestrator.py legacy-status  # plano v25 (arquivo)

Notas:
  - Lesson 208: o script antigo lia v25 e reportava 20/100 incorreto.
  - Loop harness + make g7-status usam G7.
  - Plano v25 permanece no repo como histórico; não é a fonte de verdade.

Modified by Gustavo Almeida — G7 Wave 29 A1.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
G7_ORCH = ROOT / "scripts" / "g7_orchestrator.py"
G7_PLANO = (
    (ROOT / "docs" / "plans" / "SUPER_PLANO_G7_100_TASKS.md")
    if (ROOT / "docs" / "plans" / "SUPER_PLANO_G7_100_TASKS.md").exists()
    else (ROOT / "SUPER_PLANO_G7_100_TASKS.md")
)
G7_STATE = ROOT / ".brain" / "loop-state.json"
V25_PLANO = (
    (ROOT / "docs" / "plans" / "SUPER_PLANO_100_TASKS_25_SQUADS_v25.md")
    if (ROOT / "docs" / "plans" / "SUPER_PLANO_100_TASKS_25_SQUADS_v25.md").exists()
    else (ROOT / "SUPER_PLANO_100_TASKS_25_SQUADS_v25.md")
)
V25_STATE = ROOT / ".brain" / "loop-state-v25.json"


def _run_g7(args: list[str]) -> int:
    if not G7_ORCH.exists():
        print(f"ERROR: missing {G7_ORCH}", file=sys.stderr)
        return 2
    cmd = [sys.executable, str(G7_ORCH), *args]
    return subprocess.call(cmd, cwd=str(ROOT))


def _legacy_v25_status() -> int:
    """Status read-only do plano v25 (histórico). Não conta para G7."""
    print("=" * 56)
    print("  SUPER PLANO v25 — LEGACY STATUS (não canônico)")
    print("=" * 56)
    if not V25_PLANO.exists():
        print(f"  Plano v25 ausente: {V25_PLANO.name}")
        return 1
    text = V25_PLANO.read_text(encoding="utf-8", errors="replace")
    # Rough checkbox counts if present
    done = len(re.findall(r"\[x\]", text, flags=re.I))
    open_ = len(re.findall(r"\[ \]", text))
    partial = len(re.findall(r"\[~\]", text))
    print(f"  File: {V25_PLANO.name}")
    print(f"  Rough marks: [x]={done} [~]={partial} [ ]={open_}")
    if V25_STATE.exists():
        try:
            st = json.loads(V25_STATE.read_text(encoding="utf-8"))
            print(
                f"  loop-state-v25: last_wave={st.get('last_wave')} "
                f"completed={len(st.get('completed_waves') or [])}"
            )
        except json.JSONDecodeError:
            print("  loop-state-v25: invalid JSON")
    else:
        print("  loop-state-v25: (missing)")
    print()
    print("  Fonte de verdade atual: SUPER_PLANO_G7_100_TASKS.md")
    print("  Use: python3 scripts/super_loop_orchestrator.py status")
    return 0


def _banner_status() -> int:
    print(
        f"Super Loop Orchestrator (G7 default) — "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    print(f"  Canonical plan: {G7_PLANO.name}")
    print(
        f"  State: {G7_STATE.relative_to(ROOT) if G7_STATE.exists() else '(missing)'}"
    )
    print()
    return _run_g7(["status"])


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["status"]

    cmd = argv[0].lower().replace("_", "-")
    rest = argv[1:]

    if cmd in ("status", "st"):
        return _banner_status()
    if cmd in ("next", "run"):
        # `run next` or bare `next` → g7 next wave suggestion
        if rest and rest[0].isdigit():
            print(
                "NOTE: G7 waves are tracked in SUPER_PLANO_G7_100_TASKS.md "
                "(not numeric S0–S24 v25). Emitting next open tasks:"
            )
        return _run_g7(["next"])
    if cmd in ("validate", "val", "gates"):
        return _run_g7(["validate"])
    if cmd in ("legacy-status", "v25", "legacy"):
        return _legacy_v25_status()
    if cmd in ("help", "-h", "--help"):
        print(__doc__)
        return 0

    print(f"Unknown command: {cmd}", file=sys.stderr)
    print("Usage: super_loop_orchestrator.py [status|next|validate|legacy-status]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
