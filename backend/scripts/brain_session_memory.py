"""brain_session_memory.py - append 1-line em memory/YYYY-MM-DD.md a cada commit (BRAIN7).

Pre-commit hook ou chamado manualmente apos commit:
  uv run python scripts/brain_session_memory.py "CAR-141 done (commit cf80871) - RLS policies"

Cria o arquivo do dia se nao existir, append com timestamp HH:MM.
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

BRAIN_DIR = Path("/Users/gustavoalmeida/projetos/Cartorio/.brain")
MEMORY_DIR = BRAIN_DIR / "memory"


def append_session_line(message: str) -> int:
    """Append 1 line com timestamp na memory de hoje."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    filepath = MEMORY_DIR / f"{today}.md"
    timestamp = datetime.datetime.now().strftime("%H:%M")

    if not filepath.exists():
        filepath.write_text(
            f"# Memory {today}\n\n## Timeline\n\n",
            encoding="utf-8",
        )

    with filepath.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

    print(f"appended: {filepath}: [{timestamp}] {message}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("message", help="1-line para append (sem timestamp)")
    args = parser.parse_args()
    return append_session_line(args.message)


if __name__ == "__main__":
    sys.exit(main())
