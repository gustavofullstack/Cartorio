"""Secrets scanner (G6.A.T6) — pre-commit hook.

Detecta provaveis secrets hardcoded em arquivos commitados:
- AWS keys (AKIA*)
- GitHub tokens (ghp_*)
- OpenAI/MiniMax/Coding Plan keys (sk-*, sk-cp-*)
- Linear API keys (lin_api_*)
- Render tokens (rnd_*)
- Generic API keys (api_key=...)

Exit codes:
    0 = nenhum secret encontrado
    1 = secret detectado (BLOQUEIA commit)

Uso:
    python3 scripts/secrets_scan.py                 # scan git diff staged
    python3 scripts/secrets_scan.py --all-files     # scan repo todo
    python3 scripts/secrets_scan.py --report secrets_report.md

Modified by Gustavo Almeida + cartorio-security — G6 wave 10.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(".")

# Patterns de secrets comuns
SECRET_PATTERNS: dict[str, re.Pattern] = {
    "AWS_ACCESS_KEY": re.compile(r"AKIA[0-9A-Z]{16}"),
    "GITHUB_TOKEN": re.compile(r"ghp_[A-Za-z0-9]{36}"),
    "OPENAI_KEY": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "MINIMAX_KEY": re.compile(r"sk-cp-[A-Za-z0-9]{20,}"),
    "LINEAR_KEY": re.compile(r"lin_api_[A-Za-z0-9]{20,}"),
    "RENDER_TOKEN": re.compile(r"rnd_[A-Za-z0-9]{20,}"),
    "GOOGLE_TOKEN": re.compile(r"AQ\.[A-Za-z0-9_-]{20,}"),
    "SLACK_TOKEN": re.compile(r"xox[baprs]-[A-Za-z0-9-]+"),
    "GOOGLE_API": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "GENERIC_API_KEY": re.compile(r"api_key\s*[:=]\s*['\"][A-Za-z0-9_-]{16,}['\"]", re.IGNORECASE),
    "GENERIC_PASSWORD": re.compile(r"password\s*[:=]\s*['\"][^'\"\s]{8,}['\"]", re.IGNORECASE),
}

# Diretorios a ignorar
IGNORE_DIRS = {".venv", ".git", "node_modules", "__pycache__", ".mypy_cache", ".ruff_cache", "snapshots", ".brain"}
IGNORE_FILE_PATTERNS = [
    "*.lock",
    "*.svg",
    "*.png",
    "*.jpg",
    "*.woff*",
    "*.ttf",
    ".secrets/",
    "*-lock.json",
    "coverage_gate.json",
]


def scan_file(path: Path) -> list[tuple[str, int, str, str]]:
    """Scan 1 arquivo. Retorna lista de (kind, line_no, line_text, pattern)."""
    matches: list[tuple[str, int, str, str]] = []
    try:
        content = path.read_text(errors="ignore")
    except (UnicodeDecodeError, OSError):
        return matches

    for line_no, line in enumerate(content.splitlines(), start=1):
        # Comentarios explicitos sobre o pattern (mas NAO o valor real)
        if "EXAMPLE" in line or "FAKE" in line or "PLACEHOLDER" in line or "TEST_TOKEN" in line:
            continue
        for kind, pattern in SECRET_PATTERNS.items():
            if pattern.search(line):
                matches.append((kind, line_no, line.strip()[:120], pattern.pattern[:50]))

    return matches


def get_files_to_scan(all_files: bool) -> list[Path]:
    """Retorna lista de arquivos para scan."""
    if all_files:
        result = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False
        )
        files = [ROOT / f for f in result.stdout.splitlines() if f]
    else:
        # Scan apenas staged (pre-commit default)
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"], cwd=ROOT, capture_output=True, text=True, check=False
        )
        files = [ROOT / f for f in result.stdout.splitlines() if f]

    filtered: list[Path] = []
    for f in files:
        # Skip dirs
        if any(part in IGNORE_DIRS for part in f.parts):
            continue
        # Skip file patterns
        if any(f.match(p) for p in IGNORE_FILE_PATTERNS):
            continue
        if f.is_file() and f.exists():
            filtered.append(f)

    return filtered


def main() -> int:
    parser = argparse.ArgumentParser(description="Secrets scanner pre-commit")
    parser.add_argument("--all-files", action="store_true", help="scan repo todo")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    files = get_files_to_scan(args.all_files)
    total_matches = 0
    all_findings: list[tuple[Path, str, int, str, str]] = []

    for f in files:
        matches = scan_file(f)
        for m in matches:
            all_findings.append((f, m[0], m[1], m[2], m[3]))
            total_matches += 1

    print(f"Files scanned: {len(files)}")
    print(f"Secrets found: {total_matches}")
    if total_matches:
        print("[HOLD] SECRET(S) DETECTED(S) — BLOQUEIA COMMIT:")
        for path, kind, line_no, line, pattern in all_findings[:20]:
            print(f"  - {path}:{line_no} [{kind}]")
            print(f"    line: {line}")
        if len(all_findings) > 20:
            print(f"  ... +{len(all_findings) - 20} mais")
    else:
        print("[WORK] Nenhum secret detectado")

    if args.report:
        md: list[str] = []
        md.append("# Secrets Scan Report")
        md.append("")
        md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
        md.append(f"**Files scanned**: {len(files)}")
        md.append(f"**Secrets found**: {total_matches}")
        md.append("")
        if total_matches:
            md.append("## [HOLD] Secret(s) detectado(s)")
            md.append("")
            for path, kind, line_no, line, pattern in all_findings:
                md.append(f"- `{path}:{line_no}` [{kind}]")
                md.append(f"  ```\n  {line}\n  ```")
            md.append("")
        else:
            md.append("## [WORK] Nenhum secret detectado")
        md.append("---")
        md.append("")
        md.append("**Modified by Gustavo Almeida + cartorio-security — G6 wave 10 (auto-gerado)**")
        args.report.write_text("\n".join(md))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 1 if total_matches else 0


if __name__ == "__main__":
    sys.exit(main())