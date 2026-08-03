#!/usr/bin/env python3
"""G8 PROGRESS.md audit/persist automation (G8.16.T1).

Given a wave number + agent scope + bullets, generate a canonical
``## YYYY-MM-DD — Wave N REAL COMPLETED ✅ (cartorio-X)`` block and
append/replace it in ``PROGRESS.md``.

Idempotent: re-running with the same ``--date`` + ``--wave`` updates
the existing block in-place instead of appending a duplicate.

Usage:
    python3 scripts/progress_audit.py --wave 46 --agent sre \
        --honest-pre 50 --honest-post 51 --tests 5 \
        --bullet "G8.16.T1 PROGRESS audit helper" \
        --bullet "scripts/progress_audit.py + 5 tests" \
        --bullet "Makefile target progress-audit" \
        --dry-run

    python3 scripts/progress_audit.py --apply          # defaults + append
    make progress-audit                                # runs with --apply

Modified by Gustavo Almeida — cartorio-sre (G8.16.T1 Wave 46).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROGRESS = ROOT / "PROGRESS.md"
DEFAULT_PLANO = (
    (ROOT / "docs" / "plans" / "SUPER_PLANO_G8_100_TASKS.md")
    if (ROOT / "docs" / "plans" / "SUPER_PLANO_G8_100_TASKS.md").exists()
    else (ROOT / "SUPER_PLANO_G8_100_TASKS.md")
)
DEFAULT_LANE_STATE = ROOT / ".brain" / "loop-state.json"

HEADER_RE = re.compile(
    r"^## (?P<date>\d{4}-\d{2}-\d{2})\s+—\s+Wave (?P<wave>\d+)", re.MULTILINE
)
G8_ID_RE = re.compile(r"\bG8\.\d{2}\.T\d+\b")
CHECKBOX_RE = re.compile(
    r"^\|\s*(G8\.\d{2}\.T\d+)\s*\|[^|]*\|\s*\[(?P<mark>[ xX~])\s*\]\s*\|", re.MULTILINE
)
MARK_DONE = "x"


@dataclass
class ProgressEntry:
    """In-memory representation of one wave block."""

    date: str
    wave: int
    agent: str
    honest_pre: int | None
    honest_post: int | None
    tests: int | None
    bullets: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    timestamp: str = ""

    def header_line(self) -> str:
        return f"## {self.date} — Wave {self.wave} REAL COMPLETED ✅ (cartorio-{self.agent})"

    def footer_line(self) -> str:
        ts = self.timestamp or now_iso()
        return f"Modified by Gustavo Almeida — {ts}"

    def render(self) -> str:
        lines: list[str] = ["", self.header_line(), ""]
        if self.honest_pre is not None and self.honest_post is not None:
            delta = self.honest_post - self.honest_pre
            sign = "+" if delta > 0 else ("" if delta == 0 else "")
            lines.append(
                f"- **Honest count:** {self.honest_pre} → **{self.honest_post}/100** ({sign}{delta})"
            )
        elif self.honest_post is not None:
            lines.append(f"- **Honest count:** **{self.honest_post}/100**")
        for bullet in self.bullets:
            lines.append(f"- {bullet}")
        if self.tests is not None:
            lines.append(f"- **Tests:** {self.tests} passed")
        for line in self.extra:
            lines.append(line)
        lines.append(self.footer_line())
        lines.append("")
        return "\n".join(lines)


def now_iso() -> str:
    """Return ISO 8601 UTC timestamp (microsecond precision)."""
    return datetime.now(timezone.utc).isoformat()


def now_brt_date() -> str:
    """Return today's date in BRT (UTC-3). PROGRESS.md uses local date."""
    brt = timezone(timedelta(hours=-3))
    return datetime.now(brt).strftime("%Y-%m-%d")


def detect_latest_wave(limit: int = 50) -> int | None:
    """Scan git log for ``Wave N`` mentions in commit messages; pick max N."""
    try:
        result = subprocess.run(
            ["git", "log", f"-n{limit}", "--pretty=format:%s"],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    waves: list[int] = []
    for line in result.stdout.splitlines():
        m = re.search(r"Wave\s+(\d+)", line, flags=re.IGNORECASE)
        if m:
            waves.append(int(m.group(1)))
    return max(waves) if waves else None


def count_honest_checkmarks(plane_path: Path = DEFAULT_PLANO) -> tuple[int, int]:
    """Return (done, total) honest count from SUPER_PLANO_G8 table rows."""
    if not plane_path.exists():
        return 0, 0
    text = plane_path.read_text(encoding="utf-8")
    rows = CHECKBOX_RE.findall(text)
    if not rows:
        return 0, 0
    done = sum(1 for _, mark in rows if mark.lower() == MARK_DONE)
    return done, len(rows)


def split_existing_blocks(text: str) -> tuple[list[str], list[tuple[int, str]]]:
    """Split PROGRESS.md into (prefix_lines, [(wave, block_text)]).

    ``block_text`` includes the trailing newline so we can rewrite it.
    """
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        return [text], []
    blocks: list[tuple[int, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        wave = int(m.group("wave"))
        blocks.append((wave, text[start:end]))
    prefix = text[: matches[0].start()]
    return prefix.splitlines(keepends=True), blocks


def upsert_block(progress_path: Path, entry: ProgressEntry) -> str:
    """Return new file content with ``entry`` upserted by (date, wave).

    - If a block with same wave exists, replace it in place (preserve position).
    - Otherwise, append at EOF.
    - If a block with same date exists (different wave), still append (history).
    """
    text = progress_path.read_text(encoding="utf-8") if progress_path.exists() else ""
    prefix_lines, blocks = split_existing_blocks(text)
    new_block = entry.render()

    out_blocks: list[tuple[int, str]] = []
    replaced = False
    for wave, block_text in blocks:
        if wave == entry.wave and not replaced:
            out_blocks.append((entry.wave, new_block))
            replaced = True
        else:
            out_blocks.append((wave, block_text))

    if not replaced:
        out_blocks.append((entry.wave, new_block))

    rebuilt = "".join(prefix_lines) + "".join(b for _, b in out_blocks)
    if not rebuilt.endswith("\n"):
        rebuilt += "\n"
    return rebuilt


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="G8 PROGRESS.md append/upsert automation (G8.16.T1)",
    )
    parser.add_argument(
        "--wave",
        type=int,
        default=None,
        help="wave number; default = latest from git log",
    )
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: today BRT)")
    parser.add_argument(
        "--agent",
        default="sre",
        help="agent scope tag, e.g. sre/dev/lgpd/n8n (default sre)",
    )
    parser.add_argument(
        "--honest-pre", type=int, default=None, help="honest count before wave"
    )
    parser.add_argument(
        "--honest-post", type=int, default=None, help="honest count after wave"
    )
    parser.add_argument(
        "--tests", type=int, default=None, help="number of tests passed"
    )
    parser.add_argument(
        "--bullet",
        action="append",
        default=None,
        help="add bullet (repeatable); first occurrence can use **G8.NN.TM** task ID",
    )
    parser.add_argument(
        "--summary", default=None, help="auto-derived first bullet if no --bullet given"
    )
    parser.add_argument(
        "--plano",
        type=Path,
        default=DEFAULT_PLANO,
        help="path to SUPER_PLANO_G8_100_TASKS.md",
    )
    parser.add_argument(
        "--file", type=Path, default=DEFAULT_PROGRESS, help="path to PROGRESS.md"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit JSON envelope to stdout instead of Markdown",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print block to stdout; do not write"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write block to PROGRESS.md (upsert by wave)",
    )
    return parser.parse_args(argv)


def build_entry(args: argparse.Namespace) -> ProgressEntry:
    bullets: list[str] = list(args.bullet or [])
    if not bullets:
        summary = args.summary or f"Wave {args.wave} automation updates"
        bullets.append(summary)

    date = args.date or now_brt_date()
    wave = args.wave if args.wave is not None else (detect_latest_wave() or 0)

    honest_pre = args.honest_pre
    honest_post = args.honest_post
    if honest_post is None and args.plano.exists():
        done, _ = count_honest_checkmarks(args.plano)
        if honest_pre is None:
            honest_pre = done
        honest_post = done

    entry = ProgressEntry(
        date=date,
        wave=wave,
        agent=args.agent,
        honest_pre=honest_pre,
        honest_post=honest_post,
        tests=args.tests,
        bullets=bullets,
        timestamp=now_iso(),
    )
    return entry


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    entry = build_entry(args)
    if entry.wave < 1:
        print(
            "[FAIL] --wave must be >= 1 (and none detected in git log)", file=sys.stderr
        )
        return 1
    if not entry.bullets:
        print("[FAIL] at least one --bullet or --summary required", file=sys.stderr)
        return 1

    progress_path = args.file if args.file.is_absolute() else ROOT / args.file
    block_md = entry.render()

    if args.json:
        print(
            json.dumps(
                {
                    "date": entry.date,
                    "wave": entry.wave,
                    "agent": entry.agent,
                    "honest_pre": entry.honest_pre,
                    "honest_post": entry.honest_post,
                    "tests": entry.tests,
                    "bullets": entry.bullets,
                    "timestamp": entry.timestamp,
                },
                indent=2,
                ensure_ascii=False,
            )
        )

    print(block_md, end="")

    if args.dry_run or not args.apply:
        if not args.apply:
            print("[dry-run] no write (use --apply to persist)", file=sys.stderr)
        return 0

    new_content = upsert_block(progress_path, entry)
    progress_path.write_text(new_content, encoding="utf-8")
    print(f"[OK] upserted Wave {entry.wave} block → {progress_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
