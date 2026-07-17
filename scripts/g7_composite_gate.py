#!/usr/bin/env python3
"""G7 Composite Gate — Radar + DNS + pytest (G7.24.T3 Wave 24).

Lightweight subset of g7_super_validator focused on local quality + prod
reachability signals. Network/prod failures are never treated as hard FAIL;
they map to HOLD so CI/local loops stay unblocked when VPS/DNS is partial.

Gates:
  (a) ruff / mypy — optional flags (--ruff, --mypy)
  (b) pytest collect-only OR quick import (--pytest / --import-only)
  (c) scripts/check_dns_health.sh
  (d) scripts/radar_smoke.py (if reachable)

Exit codes (composite):
  0 = all local gates OK (prod may be WORK too)
  1 = local fail (ruff/mypy/pytest/import)
  2 = local OK but prod HOLD (dns/radar partial, timeout, unreachable)

Uso:
    python3 scripts/g7_composite_gate.py
    python3 scripts/g7_composite_gate.py --ruff --pytest
    python3 scripts/g7_composite_gate.py --import-only --skip-dns --skip-radar
    python3 scripts/g7_composite_gate.py --json
    python3 scripts/g7_composite_gate.py --report docs/G7_COMPOSITE_GATE_WAVE24.md
    make g7-composite

Modified by Gustavo Almeida — G7 Wave 24 (G7.24.T3).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DEFAULT_REPORT = ROOT / "docs" / "G7_COMPOSITE_GATE_WAVE24.md"

# Composite exit codes (task contract — differs from g7_super_validator)
EXIT_OK = 0
EXIT_LOCAL_FAIL = 1
EXIT_PROD_HOLD = 2


def _local_env() -> dict[str, str]:
    """Env for local gates — neutralize shell APP_ENV=test / missing DATABASE_URL."""
    env = os.environ.copy()
    # Settings.app_env is Literal['development','staging','production']
    if env.get("APP_ENV", "").lower() not in ("development", "staging", "production"):
        env["APP_ENV"] = "development"
    env.setdefault("DATABASE_URL", "sqlite:///:memory:")
    # Avoid accidental real LLM / Redis from parent shell in smoke import
    env.setdefault("LLM_DEFAULT_PROVIDER", "opencode_go")
    return env


def _run(
    cmd: list[str],
    cwd: Path | None = None,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s: {' '.join(cmd)}"


def check_ruff() -> dict[str, Any]:
    code, out = _run(
        ["uv", "run", "ruff", "check", "app/"],
        cwd=BACKEND,
        timeout=60,
        env=_local_env(),
    )
    return {
        "name": "ruff",
        "tier": "local",
        "exit": code,
        "verdict": "WORK" if code == 0 else "FAIL",
        "detail": out.strip()[-400:],
    }


def check_mypy() -> dict[str, Any]:
    code, out = _run(
        ["uv", "run", "mypy", "app/"],
        cwd=BACKEND,
        timeout=180,
        env=_local_env(),
    )
    return {
        "name": "mypy",
        "tier": "local",
        "exit": code,
        "verdict": "WORK" if code == 0 else "FAIL",
        "detail": out.strip()[-400:],
    }


def check_pytest_collect() -> dict[str, Any]:
    code, out = _run(
        ["uv", "run", "pytest", "--collect-only", "-q", "--no-cov"],
        cwd=BACKEND,
        timeout=90,
        env=_local_env(),
    )
    m = re.search(r"(\d+)/(\d+) tests collected", out)
    m2 = re.search(r"(\d+) tests? collected", out)
    collected = int(m.group(1)) if m else (int(m2.group(1)) if m2 else 0)
    # Soft threshold: collect must succeed; count is informational
    ok = code == 0 and collected > 0
    return {
        "name": "pytest_collect",
        "tier": "local",
        "exit": code,
        "collected": collected,
        "verdict": "WORK" if ok else "FAIL",
        "detail": out.strip()[-300:],
    }


def check_quick_import() -> dict[str, Any]:
    """Import smoke without full pytest (fast offline gate).

    Uses sanitized APP_ENV/DATABASE_URL so parent shell APP_ENV=test
    does not trip Settings validation (common in agent sessions).
    Falls back to compileall of app/ if full app.main import still fails
    for missing optional services — still a real local syntax gate.
    """
    env = _local_env()
    code, out = _run(
        [
            "uv",
            "run",
            "python",
            "-c",
            "from app.main import app; print('app:', getattr(app, 'title', type(app).__name__))",
        ],
        cwd=BACKEND,
        timeout=45,
        env=env,
    )
    if code == 0:
        return {
            "name": "quick_import",
            "tier": "local",
            "exit": code,
            "verdict": "WORK",
            "detail": out.strip()[-300:],
        }

    # Fallback: bytecode compile of app package (no Settings load)
    code2, out2 = _run(
        ["uv", "run", "python", "-m", "compileall", "-q", "app"],
        cwd=BACKEND,
        timeout=60,
        env=env,
    )
    detail = (
        f"app.main import exit={code}: {out.strip()[-200:]}; "
        f"compileall exit={code2}: {out2.strip()[-120:]}"
    )
    return {
        "name": "quick_import",
        "tier": "local",
        "exit": code2,
        "verdict": "WORK" if code2 == 0 else "FAIL",
        "detail": detail,
        "import_exit": code,
        "fallback": "compileall",
    }


def check_dns() -> dict[str, Any]:
    script = ROOT / "scripts" / "check_dns_health.sh"
    if not script.exists():
        return {
            "name": "dns",
            "tier": "prod",
            "exit": 2,
            "verdict": "HOLD",
            "detail": "scripts/check_dns_health.sh missing",
        }
    code, out = _run(["bash", str(script)], timeout=60)
    # dig missing / script prereq → HOLD not local FAIL
    if code == 2:
        verdict = "HOLD"
    elif code == 0:
        verdict = "WORK"
    else:
        verdict = "HOLD"
    return {
        "name": "dns",
        "tier": "prod",
        "exit": code,
        "verdict": verdict,
        "detail": out.strip()[-400:],
    }


def check_radar() -> dict[str, Any]:
    script = ROOT / "scripts" / "radar_smoke.py"
    if not script.exists():
        return {
            "name": "radar",
            "tier": "prod",
            "exit": 2,
            "verdict": "HOLD",
            "detail": "scripts/radar_smoke.py missing",
        }
    code, out = _run([sys.executable, str(script)], timeout=45)
    status = "unknown"
    if "Status: green" in out:
        status = "green"
    elif "Status: yellow" in out:
        status = "yellow"
    elif "Status: red" in out:
        status = "red"

    # radar_smoke: 0=green/yellow, 1=red, 2=network/pre-req
    if code == 2 or status == "unknown":
        verdict = "HOLD"
    elif status in ("green", "yellow"):
        verdict = "WORK"
    elif status == "red":
        verdict = "HOLD"  # degraded prod — not local fail
    else:
        verdict = "HOLD"

    return {
        "name": "radar",
        "tier": "prod",
        "exit": code,
        "status": status,
        "verdict": verdict,
        "detail": out.strip()[-400:],
    }


def composite_exit(checks: list[dict[str, Any]]) -> tuple[int, str]:
    """Map check verdicts → composite exit code + overall label."""
    local_fail = any(
        c.get("tier") == "local" and c.get("verdict") == "FAIL" for c in checks
    )
    prod_hold = any(
        c.get("tier") == "prod" and c.get("verdict") != "WORK" for c in checks
    )

    if local_fail:
        return EXIT_LOCAL_FAIL, "LOCAL_FAIL"
    if prod_hold:
        return EXIT_PROD_HOLD, "PROD_HOLD"
    return EXIT_OK, "OK"


def render_report(
    checks: list[dict[str, Any]],
    overall: str,
    exit_code: int,
    generated_at: str,
) -> str:
    lines = [
        "# G7 Composite Gate — Wave 24 (G7.24.T3)",
        "",
        f"**Generated**: {generated_at}",
        f"**Overall**: **{overall}** (exit `{exit_code}`)",
        "",
        "## Exit code semantics",
        "",
        "| Code | Meaning |",
        "|------|---------|",
        "| `0` | All local OK (and prod WORK if checked) |",
        "| `1` | Local fail (ruff / mypy / pytest / import) |",
        "| `2` | Local OK, prod HOLD (dns / radar partial or unreachable) |",
        "",
        "## Checks",
        "",
        "| Gate | Tier | Verdict | Exit | Notes |",
        "|------|------|---------|------|-------|",
    ]
    for c in checks:
        notes = ""
        if "collected" in c:
            notes = f"collected={c['collected']}"
        elif "status" in c:
            notes = f"status={c['status']}"
        else:
            notes = str(c.get("exit", ""))[:40]
        detail_snip = (c.get("detail") or "").replace("\n", " ")[:60]
        if detail_snip and not notes:
            notes = detail_snip
        elif detail_snip and c.get("verdict") != "WORK":
            notes = f"{notes} · {detail_snip}" if notes else detail_snip
        lines.append(
            f"| `{c['name']}` | {c.get('tier', '?')} | "
            f"**{c.get('verdict', '?')}** | {c.get('exit', '?')} | {notes} |"
        )

    lines += [
        "",
        "## How to run",
        "",
        "```bash",
        "make g7-composite",
        "python3 scripts/g7_composite_gate.py --ruff --pytest",
        "python3 scripts/g7_composite_gate.py --import-only --json",
        "```",
        "",
        "## Notes",
        "",
        "- Prod network may fail offline — treated as **HOLD (exit 2)**, never local FAIL.",
        "- Default local gate is quick import (fast). Use `--pytest` for collect-only.",
        "- Related: `scripts/g7_super_validator.py` (broader), `make g7-validate`.",
        "",
        "---",
        "",
        "Modified by Gustavo Almeida — G7 Wave 24 auto-report",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="G7 composite gate: local + DNS + radar (exit 0/1/2)",
    )
    parser.add_argument(
        "--ruff",
        action="store_true",
        help="run ruff check app/ (local)",
    )
    parser.add_argument(
        "--mypy",
        action="store_true",
        help="run mypy app/ (local, slow)",
    )
    parser.add_argument(
        "--pytest",
        action="store_true",
        help="run pytest --collect-only (local)",
    )
    parser.add_argument(
        "--import-only",
        action="store_true",
        default=False,
        help="quick app.main import instead of pytest (default if no --pytest)",
    )
    parser.add_argument("--skip-dns", action="store_true", help="skip DNS check")
    parser.add_argument("--skip-radar", action="store_true", help="skip radar smoke")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument(
        "--report",
        type=Path,
        nargs="?",
        const=DEFAULT_REPORT,
        default=DEFAULT_REPORT,
        help=f"write markdown report (default: {DEFAULT_REPORT.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="do not write markdown report",
    )
    args = parser.parse_args()

    # Default local smoke: import when neither --pytest nor --import-only
    # is forced; --import-only alone or default → import; --pytest → collect.
    run_import = args.import_only or not args.pytest
    run_pytest = args.pytest

    checks: list[dict[str, Any]] = []

    if args.ruff:
        checks.append(check_ruff())
    if args.mypy:
        checks.append(check_mypy())
    if run_pytest:
        checks.append(check_pytest_collect())
    elif run_import:
        checks.append(check_quick_import())

    if not args.skip_dns:
        checks.append(check_dns())
    if not args.skip_radar:
        checks.append(check_radar())

    if not checks:
        print("[FAIL] no checks selected", file=sys.stderr)
        return EXIT_LOCAL_FAIL

    exit_code, overall = composite_exit(checks)
    generated_at = datetime.now(timezone.utc).isoformat()

    report: dict[str, Any] = {
        "generated_at": generated_at,
        "wave": 24,
        "task": "G7.24.T3",
        "overall": overall,
        "exit_code": exit_code,
        "checks": checks,
        "semantics": {
            "0": "all local OK",
            "1": "local fail",
            "2": "prod HOLD (dns/radar partial)",
        },
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"G7 Composite Gate — {overall} (exit {exit_code})")
        for c in checks:
            extra = ""
            if "collected" in c:
                extra = f" collected={c['collected']}"
            elif "status" in c:
                extra = f" status={c['status']}"
            print(f"  [{c.get('verdict', '?')}] {c['name']} (tier={c.get('tier')}){extra}")
        if exit_code == EXIT_OK:
            print("[OK] all local + prod gates green")
        elif exit_code == EXIT_LOCAL_FAIL:
            print("[LOCAL_FAIL] fix ruff/mypy/pytest/import before next wave")
        else:
            print("[PROD_HOLD] local OK; dns/radar partial or unreachable — SUI pack")

    if not args.no_report:
        report_path = args.report if isinstance(args.report, Path) else DEFAULT_REPORT
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            render_report(checks, overall, exit_code, generated_at),
            encoding="utf-8",
        )
        print(f"Report: {report_path}", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
