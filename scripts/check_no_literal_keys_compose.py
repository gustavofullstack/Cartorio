#!/usr/bin/env python3
"""Secrets scanner compose — pre-commit + CI wrapper (G8.23.T2).

Wave 52 — orchestrates multiple secret detection tools into a single
gate so that the .pre-commit-config.yaml hook stays simple while
the pipeline covers more ground than any single scanner can:

1. literal_keys — custom regex catalog (lin_api_*, sk-*, sk-proj-*,
   sk-ant-*, rnd_*, AQ.*, gAAAAA*, ghp_*, gh[sur]_*, xox[bpors]-*,
   AKIA*, AIza*, sk-cp-*, JWTs, GCP service-account, Telegram bot
   tokens, ENV_FALLBACK) implemented in backend/scripts/check_no_literal_keys.py.
2. gitleaks — binary scanner (if installed) running on staged changes.
3. trufflehog — optional high-precision scanner (if installed).

Pipeline contract:
    exit 0   — all scanners clean (or skipped when tool absent)
    exit 1   — at least one scanner flagged a critical finding
    exit 2   — internal error (subprocess failure, missing arg)

Cache:
    Re-runs within ``--cache-ttl`` seconds (default 300) reuse a
    sha256 hash of the staged blob (when ``--staged`` is used) or
    the filesystem snapshot (when ``--all-files``). The cache is
    written to ``.cache/secrets_compose/<hash>.json``. Cache entries retain
    result metadata only: scanner output and findings are never persisted,
    because diagnostic output can itself contain a secret.

LGPD Art. 46 — zero credenciais em codigo commitado. P0 incident
se vazar (PII + secrets sao mesma categoria de risco).

Usage:
    python3 scripts/check_no_literal_keys_compose.py
    python3 scripts/check_no_literal_keys_compose.py --no-cache
    python3 scripts/check_no_literal_keys_compose.py --severity high
    python3 scripts/check_no_literal_keys_compose.py --all-files

Modified by Gustavo Almeida + cartorio-sre — Wave 52.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SCRIPT = REPO_ROOT / "backend" / "scripts" / "check_no_literal_keys.py"
CACHE_DIR = REPO_ROOT / ".cache" / "secrets_compose"
CACHE_SCHEMA_VERSION = 2
DEFAULT_TTL = 300  # 5 minutes
SUPPORTED_SCANNERS = ("literal_keys", "gitleaks", "trufflehog")
DEFAULT_SCANNERS = ("literal_keys", "gitleaks")  # trufflehog opt-in (slow)


@dataclass
class ScanResult:
    """Output of a single scanner invocation."""

    name: str
    status: str  # "ok" | "violation" | "skipped" | "error"
    returncode: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    skipped_reason: str = ""
    findings: list[dict[str, str]] = field(default_factory=list)

    @property
    def is_critical(self) -> bool:
        return self.status in {"violation", "error"}


def _tool_exists(name: str) -> bool:
    """Detect binary without invoking it (cheap PATH check)."""
    return shutil.which(name) is not None


def _file_sha256(path: Path) -> str:
    """Stream SHA256 of a file (constant memory)."""
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _staged_blob_hash() -> str:
    """Hash the staged git diff so the cache is content-addressed."""
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--binary"],
            capture_output=True,
            check=True,
            cwd=REPO_ROOT,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "no-git"
    return hashlib.sha256(proc.stdout).hexdigest()


def _all_files_snapshot_hash() -> str:
    """Hash a snapshot of all tracked python + config files."""
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            check=True,
            cwd=REPO_ROOT,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "no-git"
    candidates = [
        line.strip()
        for line in proc.stdout.splitlines()
        if line.endswith((".py", ".yaml", ".yml", ".json", ".env.example", ".toml"))
    ]
    digest = hashlib.sha256()
    for rel in sorted(candidates):
        abspath = REPO_ROOT / rel
        if not abspath.is_file():
            continue
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_file_sha256(abspath).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _cache_key(args: argparse.Namespace) -> str:
    """Compose a stable cache key from scanner inputs + content hash."""
    if args.all_files:
        scope = "all-files"
        content_hash = _all_files_snapshot_hash()
    else:
        scope = "staged"
        content_hash = _staged_blob_hash()
    raw = f"{scope}|{args.severity}|{','.join(args.scanners)}|{content_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_file(key: str) -> Path:
    """Return the versioned cache path; legacy diagnostic caches are never reused."""
    return CACHE_DIR / f"v{CACHE_SCHEMA_VERSION}-{key}.json"


def _read_cache(key: str, ttl: int) -> list[ScanResult] | None:
    """Return cached ScanResults if fresh, else None."""
    cache_file = _cache_file(key)
    if not cache_file.exists():
        return None
    age = time.time() - cache_file.stat().st_mtime
    if age > ttl:
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return [
        ScanResult(
            name=item["name"],
            status=item["status"],
            returncode=item["returncode"],
            stdout=item.get("stdout", ""),
            stderr=item.get("stderr", ""),
            duration_ms=item.get("duration_ms", 0),
            skipped_reason=item.get("skipped_reason", ""),
            findings=item.get("findings", []),
        )
        for item in data
    ]


def _write_cache(key: str, results: Sequence[ScanResult]) -> None:
    """Persist non-sensitive ScanResult metadata (best-effort, fail-open)."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "name": r.name,
                "status": r.status,
                "returncode": r.returncode,
                "duration_ms": r.duration_ms,
                "skipped_reason": r.skipped_reason,
            }
            for r in results
        ]
        _cache_file(key).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        # Cache failures must NEVER block a commit.
        pass


def run_literal_keys(args: argparse.Namespace) -> ScanResult:
    """Invoke the custom regex scanner."""
    if not BACKEND_SCRIPT.exists():
        return ScanResult(
            name="literal_keys",
            status="error",
            returncode=2,
            stderr=f"missing scanner: {BACKEND_SCRIPT}",
        )
    cmd: list[str] = [
        sys.executable,
        str(BACKEND_SCRIPT),
        "--severity",
        args.severity,
    ]
    if args.report_only:
        cmd.append("--report-only")
    started = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    duration_ms = int((time.monotonic() - started) * 1000)
    status = (
        "violation"
        if proc.returncode not in (0, 1)
        else ("ok" if proc.returncode == 0 else "violation")
    )
    # In literal_keys: exit 0 = clean, exit 1 = violations, exit 2 = error.
    if proc.returncode == 0:
        status = "ok"
    elif proc.returncode == 1:
        status = "violation"
    else:
        status = "error"
    return ScanResult(
        name="literal_keys",
        status=status,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        duration_ms=duration_ms,
    )


def run_gitleaks(args: argparse.Namespace) -> ScanResult:
    """Invoke gitleaks if the binary is on PATH."""
    if not _tool_exists("gitleaks"):
        return ScanResult(
            name="gitleaks",
            status="skipped",
            returncode=0,
            skipped_reason="gitleaks binary not installed",
        )
    cmd = ["gitleaks", "protect", "--redact", "--no-banner"]
    if args.all_files:
        cmd.append("--all")
    else:
        cmd.append("--staged")
    started = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    duration_ms = int((time.monotonic() - started) * 1000)
    if proc.returncode == 0:
        status = "ok"
    elif proc.returncode == 1:
        status = "violation"
    else:
        status = "error"
    return ScanResult(
        name="gitleaks",
        status=status,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        duration_ms=duration_ms,
    )


NOISY_PATH_PATTERNS = (
    ".venv",
    "venv",
    ".venv312",
    ".venv311",
    "node_modules",
    ".git",
    ".cache",
    "__pycache__",
    "trae-agent/.venv",
    ".env",  # .env contém secrets e é gitignorado - nunca escanear
)


def _build_trufflehog_excludes() -> list[str]:
    """Translate path patterns into trufflehog --exclude-paths flags."""
    flags: list[str] = []
    for pat in NOISY_PATH_PATTERNS:
        flags.extend(["--exclude-paths", pat])
    return flags


def run_trufflehog(args: argparse.Namespace) -> ScanResult:
    """Invoke trufflehog filesystem scan if available."""
    if not _tool_exists("trufflehog"):
        return ScanResult(
            name="trufflehog",
            status="skipped",
            returncode=0,
            skipped_reason="trufflehog binary not installed",
        )
    cmd = [
        "trufflehog",
        "filesystem",
        str(REPO_ROOT),
        "--no-update",
        "--fail",
    ]
    cmd.extend(_build_trufflehog_excludes())
    started = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    duration_ms = int((time.monotonic() - started) * 1000)
    if proc.returncode == 0:
        status = "ok"
    else:
        status = "violation"
    return ScanResult(
        name="trufflehog",
        status=status,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        duration_ms=duration_ms,
    )


SCANNERS = {
    "literal_keys": run_literal_keys,
    "gitleaks": run_gitleaks,
    "trufflehog": run_trufflehog,
}


def run_pipeline(args: argparse.Namespace) -> list[ScanResult]:
    """Execute the requested scanners in order; fail-fast on first critical."""
    results: list[ScanResult] = []
    for name in args.scanners:
        runner = SCANNERS[name]
        result = runner(args)
        results.append(result)
        if result.is_critical and not args.no_fail_fast:
            break
    return results


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI args with sensible defaults for both humans and hooks."""
    parser = argparse.ArgumentParser(
        prog="check_no_literal_keys_compose",
        description="Compose multiple secret scanners into one gate.",
    )
    parser.add_argument(
        "--severity",
        choices=("critical", "high", "medium", "low"),
        default="low",
        help="Minimum severity forwarded to literal_keys (default: low).",
    )
    parser.add_argument(
        "--scanner",
        action="append",
        dest="scanners",
        choices=SUPPORTED_SCANNERS,
        help="Restrict to a single scanner (repeatable). Default = all.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Forward --report-only to literal_keys (never blocks).",
    )
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Scan the full repo instead of staged changes.",
    )
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Run every scanner even after a critical finding.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass the result cache.",
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=DEFAULT_TTL,
        help=f"Cache TTL in seconds (default: {DEFAULT_TTL}).",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Wipe the cache directory before running.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON on stdout.",
    )
    args = parser.parse_args(argv)
    if not args.scanners:
        args.scanners = list(DEFAULT_SCANNERS)
    return args


def render_text(results: Sequence[ScanResult]) -> str:
    """Human-readable summary for terminal output."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("SECRETS SCANNER COMPOSE (G8.23.T2) — Wave 52")
    lines.append("=" * 72)
    for r in results:
        if r.status == "skipped":
            marker = "SKIP"
        elif r.status == "ok":
            marker = " OK "
        elif r.status == "violation":
            marker = "FAIL"
        else:
            marker = "ERR "
        lines.append(
            f"[{marker}] {r.name:<14} "
            f"rc={r.returncode:<3} "
            f"t={r.duration_ms:<5}ms "
            f"{r.skipped_reason}"
        )
    lines.append("-" * 72)
    failed = [r for r in results if r.is_critical]
    if failed:
        lines.append(f"❌ {len(failed)} scanner(s) flagged critical findings:")
        for r in failed:
            lines.append(f"--- {r.name} (rc={r.returncode}) ---")
            lines.append(
                "diagnostics redacted; rerun the scanner locally to inspect findings"
            )
    else:
        executed = sum(1 for r in results if r.status != "skipped")
        lines.append(f"✓ All {executed} scanner(s) clean.")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point — returns POSIX exit code."""
    args = parse_args(argv)
    if args.clear_cache:
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR, ignore_errors=True)

    if args.no_cache:
        results = run_pipeline(args)
    else:
        key = _cache_key(args)
        cached = _read_cache(key, args.cache_ttl)
        if cached is not None:
            results = cached
        else:
            results = run_pipeline(args)
            _write_cache(key, results)

    if args.json:
        payload = [
            {
                "name": r.name,
                "status": r.status,
                "returncode": r.returncode,
                "duration_ms": r.duration_ms,
                "skipped_reason": r.skipped_reason,
            }
            for r in results
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(results))

    return 1 if any(r.is_critical for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
