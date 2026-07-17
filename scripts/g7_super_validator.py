#!/usr/bin/env python3
"""G7 Super Teste Validador (G7.24.T1).

Composite exit-code gate for integração total:
  1. ruff (optional if uv available)
  2. pytest collect / optional fast subset
  3. radar smoke (prod)
  4. DNS health (optional script)
  5. N8N workflow count + idempotency audit
  6. MCP tool count from mcp_server.py
  7. Secrets scan quick (optional)

Uso:
    python3 scripts/g7_super_validator.py
    python3 scripts/g7_super_validator.py --skip-pytest --json
    python3 scripts/g7_super_validator.py --report docs/G7_VALIDATOR_REPORT.md

Exit codes:
    0 = all hard checks WORK
    1 = soft HOLD (prod degraded but local gates OK)
    2 = hard FAIL (local gates broken)

Modified by Gustavo Almeida + Pietra orquestrador — G7 Wave 14.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER = ROOT / "backend" / "mcp_server.py"
WF_DIR = ROOT / "infra" / "n8n-workflows"


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s: {' '.join(cmd)}"


def count_mcp_tools() -> int:
    if not MCP_SERVER.exists():
        return 0
    text = MCP_SERVER.read_text(encoding="utf-8", errors="replace")
    return len(re.findall(r"@mcp\.tool\s*\(", text))


def count_n8n_workflows() -> tuple[int, int]:
    if not WF_DIR.exists():
        return 0, 0
    files = list(WF_DIR.glob("*.json"))
    with_webhook = 0
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            nodes = data.get("nodes") or []
            if any(n.get("type") == "n8n-nodes-base.webhook" for n in nodes):
                with_webhook += 1
        except (json.JSONDecodeError, OSError):
            continue
    return len(files), with_webhook


def check_radar() -> dict:
    code, out = _run([sys.executable, str(ROOT / "scripts" / "radar_smoke.py")], timeout=45)
    status = "unknown"
    if "Status: green" in out:
        status = "green"
    elif "Status: yellow" in out:
        status = "yellow"
    elif "Status: red" in out:
        status = "red"
    return {
        "exit": code,
        "status": status,
        "detail": out.strip()[-500:],
        "verdict": "WORK" if status in ("green", "yellow") else ("HOLD" if status == "red" else "FAIL"),
    }


def check_pytest_collect() -> dict:
    code, out = _run(
        ["uv", "run", "pytest", "--collect-only", "-q", "--no-cov"],
        cwd=ROOT / "backend",
        timeout=90,
    )
    m = re.search(r"(\d+)/(\d+) tests collected", out)
    # also "N tests collected"
    m2 = re.search(r"(\d+) tests? collected", out)
    collected = int(m.group(1)) if m else (int(m2.group(1)) if m2 else 0)
    return {
        "exit": code,
        "collected": collected,
        "verdict": "WORK" if code == 0 and collected >= 2500 else "FAIL",
        "detail": out.strip()[-300:],
    }


def check_ruff() -> dict:
    code, out = _run(
        ["uv", "run", "ruff", "check", "app/"],
        cwd=ROOT / "backend",
        timeout=60,
    )
    return {
        "exit": code,
        "verdict": "WORK" if code == 0 else "FAIL",
        "detail": out.strip()[-300:],
    }


def check_idempotency_audit() -> dict:
    script = ROOT / "scripts" / "n8n_idempotency_audit.py"
    if not script.exists():
        return {"verdict": "HOLD", "detail": "script missing"}
    code, out = _run([sys.executable, str(script)], timeout=30)
    # exit 0 = all protected
    return {
        "exit": code,
        "verdict": "WORK" if code == 0 else "HOLD",
        "detail": out.strip()[-400:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="G7 Super Validator")
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-ruff", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    checks: dict[str, dict] = {}
    hard_fail = False
    soft_hold = False

    mcp_n = count_mcp_tools()
    wf_n, wh_n = count_n8n_workflows()
    checks["mcp_tools"] = {
        "count": mcp_n,
        "verdict": "WORK" if mcp_n >= 10 else "FAIL",
    }
    checks["n8n_workflows"] = {
        "json_files": wf_n,
        "with_webhook": wh_n,
        "verdict": "WORK" if wf_n >= 30 else "HOLD",
    }

    openclaw_bot = ROOT / "infra" / "openclaw" / "cartorio-bot.openclaw.json"
    checks["openclaw_bot_json"] = {
        "exists": openclaw_bot.is_file(),
        "verdict": "WORK" if openclaw_bot.is_file() else "HOLD",
    }
    matrix = ROOT / "docs" / "INTEGRATION_MATRIX_G7.md"
    checks["integration_matrix"] = {
        "exists": matrix.is_file(),
        "verdict": "WORK" if matrix.is_file() else "HOLD",
    }

    if not args.skip_ruff:
        checks["ruff"] = check_ruff()
        if checks["ruff"]["verdict"] == "FAIL":
            hard_fail = True

    if not args.skip_pytest:
        checks["pytest_collect"] = check_pytest_collect()
        if checks["pytest_collect"]["verdict"] == "FAIL":
            hard_fail = True

    checks["radar"] = check_radar()
    if checks["radar"]["verdict"] == "HOLD":
        soft_hold = True
    elif checks["radar"]["verdict"] == "FAIL":
        soft_hold = True

    checks["n8n_idempotency"] = check_idempotency_audit()
    if checks["n8n_idempotency"]["verdict"] != "WORK":
        soft_hold = True

    dns_script = ROOT / "scripts" / "check_dns_health.sh"
    if dns_script.exists():
        code, out = _run(["bash", str(dns_script)], timeout=60)
        checks["dns"] = {
            "exit": code,
            "verdict": "WORK" if code == 0 else "HOLD",
            "detail": out.strip()[-300:],
        }
        if code != 0:
            soft_hold = True


    code_be, out_be = _run([sys.executable, str(ROOT / "scripts" / "check_no_bare_exception.py")], timeout=30)
    checks["bare_exception"] = {
        "exit": code_be,
        "verdict": "WORK" if code_be == 0 else "FAIL",
        "detail": (out_be or "")[-200:],
    }
    if checks["bare_exception"]["verdict"] == "FAIL":
        hard_fail = True


    inv = ROOT / "scripts" / "pii_pre_llm_inventory.py"
    if inv.exists():
        code_i, out_i = _run([sys.executable, str(inv), "--strict"], timeout=30)
        checks["pii_pre_llm"] = {
            "exit": code_i,
            "verdict": "WORK" if code_i == 0 else "FAIL",
            "detail": (out_i or "")[-200:],
        }
        if checks["pii_pre_llm"]["verdict"] == "FAIL":
            hard_fail = True

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "hard_fail": hard_fail,
        "soft_hold": soft_hold,
        "overall": "FAIL" if hard_fail else ("HOLD" if soft_hold else "WORK"),
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"G7 Super Validator — {report['overall']}")
        print(f"  MCP tools: {mcp_n}")
        print(f"  N8N WFs: {wf_n} ({wh_n} webhooks)")
        for name, payload in checks.items():
            print(f"  [{payload.get('verdict', '?')}] {name}")
        if report["overall"] == "WORK":
            print("[WORK] all hard checks green")
        elif report["overall"] == "HOLD":
            print("[HOLD] local OK, prod/SUI gaps remain — see CANAL_HEALTH_MATRIX")
        else:
            print("[FAIL] fix local gates before next wave")

    if args.report:
        lines = [
            "# G7 Super Validator Report",
            "",
            f"**Generated**: {report['generated_at']}",
            f"**Overall**: **{report['overall']}**",
            "",
            "| Check | Verdict | Notes |",
            "|---|---|---|",
        ]
        for name, payload in checks.items():
            notes = str(payload.get("count", payload.get("status", payload.get("exit", ""))))[:80]
            lines.append(f"| {name} | {payload.get('verdict')} | {notes} |")
        lines += [
            "",
            "---",
            "Modified by Gustavo Almeida — G7 Wave 14 auto-report",
        ]
        args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Report: {args.report}", file=sys.stderr)

    if hard_fail:
        return 2
    if soft_hold:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
