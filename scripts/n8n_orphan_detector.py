#!/usr/bin/env python3
"""Offline detector for unreferenced N8N JSON exports."""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

DEFAULT_WORKFLOW_DIR = Path("infra/n8n-workflows")
ARCHIVE_DIR_NAME = "archive-2026-07-18"
TEXT_SUFFIXES = {".md", ".py", ".sh"}
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


@dataclass(frozen=True)
class AuditEntry:
    path: Path
    referenced_by_count: int

    @property
    def is_orphan(self) -> bool:
        return self.referenced_by_count == 0


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def reference_sources(root: Path) -> list[Path]:
    sources: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or is_excluded(path):
            continue
        if path.name == "Makefile" or path.suffix in TEXT_SUFFIXES:
            sources.append(path)
    return sorted(sources)


def source_references_json(source: Path, terms: tuple[str, str]) -> bool:
    try:
        content = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return any(term in content for term in terms)


def audit_json(path: Path, root: Path, sources: list[Path]) -> AuditEntry:
    relative_path = path.relative_to(root).as_posix()
    terms = (relative_path, path.name)
    referenced_by_count = sum(
        source_references_json(source, terms) for source in sources
    )
    return AuditEntry(path=path, referenced_by_count=referenced_by_count)


def audit_workflows(workflow_dir: Path, root: Path) -> list[AuditEntry]:
    json_files = sorted(workflow_dir.rglob("*.json"))
    sources = reference_sources(root)
    worker_count = min(32, max(1, len(json_files)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        entries = executor.map(
            lambda path: audit_json(path, root, sources),
            json_files,
        )
        return list(entries)


def is_tracked(path: Path, root: Path) -> bool:
    relative_path = path.relative_to(root)
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", str(relative_path)],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.returncode == 0


def move_to_archive(
    path: Path, workflow_dir: Path, archive_dir: Path, root: Path
) -> Path:
    relative_path = path.relative_to(workflow_dir)
    destination = archive_dir / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if is_tracked(path, root):
        subprocess.run(
            [
                "git",
                "mv",
                str(path.relative_to(root)),
                str(destination.relative_to(root)),
            ],
            cwd=root,
            check=True,
        )
    else:
        shutil.move(str(path), str(destination))
    return destination


def apply_archive(
    entries: list[AuditEntry], workflow_dir: Path, root: Path
) -> list[Path]:
    archive_dir = workflow_dir / ARCHIVE_DIR_NAME
    candidates = [
        entry.path
        for entry in entries
        if entry.is_orphan and archive_dir not in entry.path.parents
    ]
    if not candidates:
        return []

    sys.stderr.write(
        f"Found {len(candidates)} orphan JSON file(s). "
        f"Type ARCHIVE to move them to {archive_dir.relative_to(root)}: "
    )
    try:
        confirmation = input().strip()
    except EOFError:
        confirmation = ""
    if confirmation != "ARCHIVE":
        sys.stderr.write("Archive canceled.\n")
        return []

    return [
        move_to_archive(path, workflow_dir, archive_dir, root) for path in candidates
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan N8N JSON exports for offline text references."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Report CSV only; this is the default.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Ask for confirmation and archive orphan JSON files.",
    )
    return parser.parse_args()


def write_csv(entries: list[AuditEntry], root: Path) -> None:
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("path", "referenced_by_count", "is_orphan"))
    for entry in entries:
        writer.writerow(
            (
                entry.path.relative_to(root).as_posix(),
                entry.referenced_by_count,
                str(entry.is_orphan).lower(),
            )
        )


def main() -> int:
    args = parse_args()
    root = repository_root()
    workflow_dir = root / DEFAULT_WORKFLOW_DIR
    if not workflow_dir.is_dir():
        sys.stderr.write(f"Missing workflow directory: {workflow_dir}\n")
        return 2

    entries = audit_workflows(workflow_dir, root)
    write_csv(entries, root)
    if args.apply:
        moved = apply_archive(entries, workflow_dir, root)
        if moved:
            sys.stderr.write(f"Archived {len(moved)} file(s).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
