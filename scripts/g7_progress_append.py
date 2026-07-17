#!/usr/bin/env python3
"""G7 Progress append automation (G7.23.T3 Wave 24).

Append-only helper for PROGRESS.md. Writes a dated wave block when given
--wave N and --summary. Never rewrites history; only appends at EOF.

Uso:
    python3 scripts/g7_progress_append.py --wave 24 --summary "composite gate + progress helper"
    python3 scripts/g7_progress_append.py --wave 24 --summary "..." --agents "A4 sre" --tasks "G7.24.T3,G7.23.T3"
    python3 scripts/g7_progress_append.py --wave 24 --summary "..." --dry-run
    make g7-progress WAVE=24 SUMMARY="composite gate"

Modified by Gustavo Almeida — G7 Wave 24 (G7.23.T3).
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROGRESS = ROOT / "PROGRESS.md"


def build_block(
    wave: int,
    summary: str,
    agents: str | None,
    tasks: str | None,
    status: str,
    extra: str | None,
) -> str:
    # Local date for human-facing PROGRESS (BRT-ish: use local date)
    today = datetime.now().strftime("%Y-%m-%d")
    ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mark = "✅" if status.upper() in ("DONE", "OK", "COMPLETE") else "🔄"

    lines = [
        "",
        f"## {today} — Wave {wave} G7 {summary.strip()[:80]} {mark}",
        f"- **When:** {ts_utc}",
        f"- **Status:** {status}",
    ]
    if agents:
        lines.append(f"- **Agents:** {agents}")
    if tasks:
        # Support comma-separated task IDs
        task_list = [t.strip() for t in tasks.split(",") if t.strip()]
        if task_list:
            lines.append("- **Tasks:**")
            for t in task_list:
                lines.append(f"  - [x] {t}")
        else:
            lines.append(f"- **Tasks:** {tasks}")
    lines.append(f"- **Summary:** {summary.strip()}")
    if extra:
        lines.append(f"- **Notes:** {extra.strip()}")
    lines.append("Modified by Gustavo Almeida")
    lines.append("")
    return "\n".join(lines)


def already_has_wave(text: str, wave: int) -> bool:
    """Heuristic: detect an existing Wave N header near EOF to avoid dupes."""
    # Match both "## 2026-07-16 — Wave 24" and "Wave 24 G7"
    pattern = re.compile(rf"^## .+Wave\s+{wave}\b", re.MULTILINE | re.IGNORECASE)
    matches = list(pattern.finditer(text))
    return len(matches) > 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append a dated G7 wave block to PROGRESS.md (append-only)",
    )
    parser.add_argument("--wave", type=int, required=True, help="wave number (e.g. 24)")
    parser.add_argument(
        "--summary",
        required=True,
        help='short summary string, e.g. "composite gate + progress helper"',
    )
    parser.add_argument(
        "--agents",
        default=None,
        help='optional agents line, e.g. "A4 sre / cartorio-brain"',
    )
    parser.add_argument(
        "--tasks",
        default=None,
        help="optional comma-separated task IDs (G7.24.T3,G7.23.T3)",
    )
    parser.add_argument(
        "--status",
        default="IN_PROGRESS",
        help="DONE | IN_PROGRESS | HOLD (default IN_PROGRESS)",
    )
    parser.add_argument(
        "--extra",
        default=None,
        help="optional free-form notes line",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_PROGRESS,
        help="path to PROGRESS.md (default: repo root)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="append even if a Wave N block already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print block to stdout; do not write file",
    )
    args = parser.parse_args()

    if args.wave < 1:
        print("[FAIL] --wave must be >= 1", file=sys.stderr)
        return 1
    if not args.summary.strip():
        print("[FAIL] --summary must be non-empty", file=sys.stderr)
        return 1

    progress_path = args.file if args.file.is_absolute() else ROOT / args.file
    block = build_block(
        wave=args.wave,
        summary=args.summary,
        agents=args.agents,
        tasks=args.tasks,
        status=args.status,
        extra=args.extra,
    )

    if args.dry_run:
        print(block, end="")
        print("[dry-run] no write", file=sys.stderr)
        return 0

    if not progress_path.exists():
        # Create minimal header if missing (still append-only semantics)
        header = (
            "# PROGRESS.md — /goal Auto-save\n\n"
            "> Auto-saved a cada ciclo /goal conforme constraint.\n"
            "> Formato: timestamped events, append-only.\n\n---\n"
        )
        progress_path.write_text(header + block, encoding="utf-8")
        print(f"[OK] created {progress_path} with wave {args.wave} block")
        return 0

    text = progress_path.read_text(encoding="utf-8")
    if already_has_wave(text, args.wave) and not args.force:
        print(
            f"[SKIP] Wave {args.wave} block already present in {progress_path.name} "
            f"(use --force to append anyway)",
            file=sys.stderr,
        )
        return 0

    # Ensure trailing newline before append
    if text and not text.endswith("\n"):
        text += "\n"
    progress_path.write_text(text + block, encoding="utf-8")
    print(f"[OK] appended Wave {args.wave} block → {progress_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
