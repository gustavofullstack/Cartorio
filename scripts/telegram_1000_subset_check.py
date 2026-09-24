#!/usr/bin/env python3
"""G7.24.T2 — Subset auto-check do guia Telegram 1000 pontos.

Valida que artefatos locais (docs, endpoints no source, testes, scripts)
existem para os cenários top do guia 1000 pts — SEM bater rede/Telegram
em produção (safe offline / CI).

Fontes canônicas:
  - docs/GUIA_VALIDACAO_TELEGRAM_1000_PONTOS.md
  - docs/RUNBOOK_VALIDACAO_1000_PONTOS.md
  - docs/GUIA_TESTES_TELEGRAM.md

Uso:
    python3 scripts/telegram_1000_subset_check.py
    python3 scripts/telegram_1000_subset_check.py --json
    python3 scripts/telegram_1000_subset_check.py --report docs/TELEGRAM_1000_SUBSET_REPORT_G7.md

Exit:
    0 = todos os checks WORK
    1 = um ou mais FAIL (artefato ausente / comando não encontrado no source)

Modified by Gustavo Almeida — G7 Wave 26 (G7.24.T2).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "docs" / "TELEGRAM_1000_SUBSET_REPORT_G7.md"
TELEGRAM_PY = ROOT / "backend" / "app" / "api" / "v1" / "telegram.py"

# 7 comandos canônicos (guia + telegram.py header)
CANONICAL_COMMANDS = (
    "/start",
    "/menu",
    "/agendar",
    "/protocolo",
    "/humano",
    "/cancelar",
    "/lgpd",
)

# Endpoints documentados no guia 1000 pts (paths relativos ao router /telegram)
ENDPOINT_MARKERS: dict[str, str] = {
    "GET /health": r'@router\.(get|api_route)\("/health"',
    "GET /metrics": r'@router\.(get|api_route)\("/metrics"',
    "GET /webhook/info": r'@router\.(get|api_route)\("/webhook/info"',
    # FastAPI decorators are commonly formatted over multiple lines.
    "POST /webhook": r'@router\.(?:post|api_route)\(\s*["\']/?webhook["\']',
    "POST /set-commands": r'@router\.(post|api_route)\("/set-commands"',
    "GET /debug/last-updates": r'@router\.(get|api_route)\("/debug/last-updates"',
}

# Docs / scripts / testes top do subset
PATH_CHECKS: list[tuple[str, Path, str]] = [
    (
        "doc_guia_1000",
        ROOT / "docs" / "GUIA_VALIDACAO_TELEGRAM_1000_PONTOS.md",
        "Guia validação 1000 pontos",
    ),
    (
        "doc_runbook_1000",
        ROOT / "docs" / "RUNBOOK_VALIDACAO_1000_PONTOS.md",
        "Runbook 1000 pontos (curl health/metrics)",
    ),
    (
        "doc_guia_testes",
        ROOT / "docs" / "GUIA_TESTES_TELEGRAM.md",
        "Guia 20 cenários E2E Telegram",
    ),
    (
        "doc_telegram_guide",
        ROOT / "docs" / "TELEGRAM_GUIDE.md",
        "Telegram guide ops",
    ),
    (
        "doc_webhook_reregister",
        ROOT / "docs" / "TELEGRAM_WEBHOOK_REREGISTER_G7.md",
        "Webhook re-register G7",
    ),
    (
        "src_telegram_router",
        TELEGRAM_PY,
        "Router FastAPI telegram.py",
    ),
    (
        "script_diagnose",
        ROOT / "scripts" / "diagnose_vps_and_bot.sh",
        "Diagnose 1-command (score 7/7)",
    ),
    (
        "script_set_webhook",
        ROOT / "scripts" / "telegram_set_webhook.py",
        "Helper setWebhook",
    ),
    (
        "script_e2e_sh",
        ROOT / "scripts" / "test_telegram_e2e.sh",
        "Shell E2E Telegram",
    ),
    (
        "test_commands",
        ROOT / "backend" / "tests" / "test_telegram_commands.py",
        "Pytest comandos canônicos",
    ),
    (
        "test_webhook",
        ROOT / "backend" / "tests" / "test_telegram_webhook.py",
        "Pytest webhook",
    ),
    (
        "test_webhook_e2e",
        ROOT / "backend" / "tests" / "test_telegram_webhook_e2e.py",
        "Pytest webhook e2e",
    ),
    (
        "test_state_machine",
        ROOT / "backend" / "tests" / "test_telegram_state_machine.py",
        "Pytest state machine",
    ),
    (
        "test_e2e",
        ROOT / "backend" / "tests" / "test_telegram_e2e.py",
        "Pytest telegram e2e",
    ),
    (
        "test_send",
        ROOT / "backend" / "tests" / "test_telegram_send.py",
        "Pytest send helpers",
    ),
]


@dataclass
class CheckResult:
    id: str
    category: str
    title: str
    verdict: str  # WORK | FAIL
    detail: str


def _file_exists(path: Path) -> CheckResult:
    ok = path.is_file()
    return CheckResult(
        id=f"path:{path.relative_to(ROOT)}",
        category="artifact",
        title=str(path.relative_to(ROOT)),
        verdict="WORK" if ok else "FAIL",
        detail="exists" if ok else "MISSING",
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_paths() -> list[CheckResult]:
    out: list[CheckResult] = []
    for cid, path, title in PATH_CHECKS:
        ok = path.is_file()
        out.append(
            CheckResult(
                id=cid,
                category="artifact",
                title=title,
                verdict="WORK" if ok else "FAIL",
                detail=str(path.relative_to(ROOT)) if ok else f"MISSING {path}",
            )
        )
    return out


def check_commands() -> list[CheckResult]:
    out: list[CheckResult] = []
    if not TELEGRAM_PY.is_file():
        for cmd in CANONICAL_COMMANDS:
            out.append(
                CheckResult(
                    id=f"cmd:{cmd}",
                    category="command",
                    title=f"Handler {cmd}",
                    verdict="FAIL",
                    detail="telegram.py missing",
                )
            )
        return out

    src = _read(TELEGRAM_PY)
    for cmd in CANONICAL_COMMANDS:
        # Match string literal "/start" etc. in source (allow list + handlers)
        pattern = re.escape(cmd)
        found = re.search(rf'["\']{pattern}["\']', src) is not None
        # Also require handler branch when present as cmd == "/x"
        branch = re.search(rf'cmd\s*==\s*["\']{pattern}["\']', src) is not None
        ok = found and branch
        out.append(
            CheckResult(
                id=f"cmd:{cmd}",
                category="command",
                title=f"Handler {cmd}",
                verdict="WORK" if ok else "FAIL",
                detail=(
                    "literal+branch OK" if ok else f"literal={found} branch={branch}"
                ),
            )
        )
    return out


def check_endpoints() -> list[CheckResult]:
    out: list[CheckResult] = []
    if not TELEGRAM_PY.is_file():
        for name in ENDPOINT_MARKERS:
            out.append(
                CheckResult(
                    id=f"ep:{name}",
                    category="endpoint",
                    title=name,
                    verdict="FAIL",
                    detail="telegram.py missing",
                )
            )
        return out

    src = _read(TELEGRAM_PY)
    for name, pattern in ENDPOINT_MARKERS.items():
        ok = re.search(pattern, src) is not None
        out.append(
            CheckResult(
                id=f"ep:{name}",
                category="endpoint",
                title=name,
                verdict="WORK" if ok else "FAIL",
                detail="router decorator found" if ok else "decorator NOT found",
            )
        )
    return out


def check_guide_mentions_commands() -> list[CheckResult]:
    """Guia 1000 deve listar os 7 comandos canônicos."""
    out: list[CheckResult] = []
    guide = ROOT / "docs" / "GUIA_VALIDACAO_TELEGRAM_1000_PONTOS.md"
    if not guide.is_file():
        return [
            CheckResult(
                id="guide:commands",
                category="doc_content",
                title="Guia lista 7 comandos",
                verdict="FAIL",
                detail="guide missing",
            )
        ]
    text = _read(guide)
    missing = [c for c in CANONICAL_COMMANDS if c not in text]
    ok = not missing
    out.append(
        CheckResult(
            id="guide:commands",
            category="doc_content",
            title="Guia lista 7 comandos",
            verdict="WORK" if ok else "FAIL",
            detail="all 7 present" if ok else f"missing {missing}",
        )
    )
    # Runbook health curls
    runbook = ROOT / "docs" / "RUNBOOK_VALIDACAO_1000_PONTOS.md"
    if runbook.is_file():
        rtext = _read(runbook)
        needles = (
            "/api/v1/telegram/health",
            "/api/v1/telegram/metrics",
            "/api/v1/telegram/webhook",
        )
        miss_r = [n for n in needles if n not in rtext]
        out.append(
            CheckResult(
                id="runbook:endpoints",
                category="doc_content",
                title="Runbook cita health/metrics/webhook",
                verdict="WORK" if not miss_r else "FAIL",
                detail="ok" if not miss_r else f"missing {miss_r}",
            )
        )
    return out


def check_tests_cover_commands() -> list[CheckResult]:
    """test_telegram_commands.py deve referenciar a maioria dos comandos."""
    path = ROOT / "backend" / "tests" / "test_telegram_commands.py"
    if not path.is_file():
        return [
            CheckResult(
                id="test:commands_coverage",
                category="test",
                title="test_telegram_commands cobre comandos",
                verdict="FAIL",
                detail="file missing",
            )
        ]
    text = _read(path)
    present = [c for c in CANONICAL_COMMANDS if c in text]
    # Require at least 6/7 (ajuda may not be in allowlist tests)
    ok = len(present) >= 6
    return [
        CheckResult(
            id="test:commands_coverage",
            category="test",
            title="test_telegram_commands cobre ≥6/7 comandos",
            verdict="WORK" if ok else "FAIL",
            detail=f"{len(present)}/7 present: {present}",
        )
    ]


def run_all() -> list[CheckResult]:
    results: list[CheckResult] = []
    results.extend(check_paths())
    results.extend(check_commands())
    results.extend(check_endpoints())
    results.extend(check_guide_mentions_commands())
    results.extend(check_tests_cover_commands())
    return results


def summarize(results: list[CheckResult]) -> dict[str, Any]:
    work = sum(1 for r in results if r.verdict == "WORK")
    fail = sum(1 for r in results if r.verdict == "FAIL")
    total = len(results)
    by_cat: dict[str, dict[str, int]] = {}
    for r in results:
        bucket = by_cat.setdefault(r.category, {"WORK": 0, "FAIL": 0})
        bucket[r.verdict] = bucket.get(r.verdict, 0) + 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "work": work,
        "fail": fail,
        "score": f"{work}/{total}",
        "overall": "OK" if fail == 0 else "FAIL",
        "exit_code": 0 if fail == 0 else 1,
        "by_category": by_cat,
        "checks": [asdict(r) for r in results],
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Telegram 1000-point subset check — G7.24.T2",
        "",
        f"**Generated**: {summary['generated_at']}",
        f"**Overall**: **{summary['overall']}** (exit `{summary['exit_code']}`)",
        f"**Score**: {summary['score']} checks WORK",
        "",
        "## Scope",
        "",
        "Offline subset of `docs/GUIA_VALIDACAO_TELEGRAM_1000_PONTOS.md` + runbook:",
        "- 7 comandos canônicos no source `telegram.py`",
        "- Endpoints health/metrics/webhook/set-commands/debug",
        "- Docs + scripts diagnose/setWebhook + testes pytest chave",
        "",
        "**Does not** call Telegram API, prod webhook, or live VPS.",
        "",
        "## By category",
        "",
        "| Category | WORK | FAIL |",
        "|----------|------|------|",
    ]
    for cat, counts in sorted(summary["by_category"].items()):
        lines.append(f"| `{cat}` | {counts.get('WORK', 0)} | {counts.get('FAIL', 0)} |")
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Verdict | ID | Title | Detail |",
            "|---------|----|-------|--------|",
        ]
    )
    for c in summary["checks"]:
        flag = "**WORK**" if c["verdict"] == "WORK" else "**FAIL**"
        detail = str(c["detail"]).replace("|", "\\|")
        title = str(c["title"]).replace("|", "\\|")
        lines.append(f"| {flag} | `{c['id']}` | {title} | {detail} |")
    lines.extend(
        [
            "",
            "## How to run",
            "",
            "```bash",
            "python3 scripts/telegram_1000_subset_check.py",
            "python3 scripts/telegram_1000_subset_check.py --json",
            "python3 scripts/telegram_1000_subset_check.py --report docs/TELEGRAM_1000_SUBSET_REPORT_G7.md",
            "```",
            "",
            "## Related",
            "",
            "- `docs/GUIA_VALIDACAO_TELEGRAM_1000_PONTOS.md`",
            "- `docs/RUNBOOK_VALIDACAO_1000_PONTOS.md`",
            "- `scripts/diagnose_vps_and_bot.sh` (live score 7/7 — precisa rede)",
            "- `scripts/g7_composite_gate.py` (composite local+prod HOLD)",
            "",
            "---",
            "",
            "Modified by Gustavo Almeida — G7 Wave 26 (G7.24.T2) auto-report",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    parser.add_argument(
        "--report",
        type=Path,
        nargs="?",
        const=DEFAULT_REPORT,
        default=None,
        help=f"Write markdown report (default path: {DEFAULT_REPORT})",
    )
    args = parser.parse_args(argv)

    results = run_all()
    summary = summarize(results)

    if args.report is not None:
        report_path = args.report if args.report.is_absolute() else ROOT / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_report(summary), encoding="utf-8")
        print(f"report_written={report_path}")

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(
            f"telegram_1000_subset: {summary['overall']} "
            f"{summary['score']} exit={summary['exit_code']}"
        )
        for c in results:
            mark = "OK" if c.verdict == "WORK" else "FAIL"
            print(f"  [{mark}] {c.id}: {c.title} — {c.detail}")

    return int(summary["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
