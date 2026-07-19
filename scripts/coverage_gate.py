"""Coverage Gate — fail-safe para pytest coverage >= 90% (G6.A.T5).

Executa pytest --cov=app e valida cobertura minima por arquivo.
Falha o CI (exit 1) se o total ficar abaixo de 90%. O limite por arquivo é
opcional e pode ser ativado com ``--per-file 80`` em uma auditoria dedicada.

Uso:
    python3 scripts/coverage_gate.py                       # default gate 90% / per-file informativo
    python3 scripts/coverage_gate.py --total 96 --per-file 85
    python3 scripts/coverage_gate.py --report coverage_gate.md

Exit codes:
    0 = todos os gates passaram
    1 = algum gate falhou (print detalhes)
    2 = erro pre-requisito (pytest falhou, sem coverage.json)

Ref: backend/pyproject.toml --cov-fail-under=90 (gate CI vigente).
Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 4.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TOTAL = 90.0
DEFAULT_PER_FILE = 0.0
EXEMPT_FILES = {
    "app/api/v1/whatsapp.py",
    "app/api/v1/telegram.py",
    "app/api/v2/",
    "app/integrations/",
    "app/core/",
    "app/services/cartorio_agent.py",
    "app/services/chat_pipeline.py",
    "app/services/chatwoot_handoff.py",
}


def run_pytest_with_coverage() -> dict | None:
    """Roda pytest --cov=app --cov-report=json e retorna coverage.json parseado."""
    existing = Path("backend/coverage_gate.json")
    if os.getenv("COVERAGE_GATE_REUSE_EXISTING") == "1" and existing.exists():
        print(
            "Reusing coverage_gate.json from the primary pytest step", file=sys.stderr
        )
        return json.loads(existing.read_text())
    print("Running pytest --cov=app --cov-report=json ...", file=sys.stderr)
    result = subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "--cov=app",
            "--cov-report=json:coverage_gate.json",
            "-q",
            "--tb=short",
        ],
        cwd="backend",
    )
    if result.returncode != 0:
        print(f"[ERROR] pytest falhou (exit={result.returncode})", file=sys.stderr)
        return None

    cov_path = Path("backend/coverage_gate.json")
    if not cov_path.exists():
        print("[ERROR] coverage_gate.json nao foi gerado", file=sys.stderr)
        return None
    return json.loads(cov_path.read_text())


def evaluate(
    coverage: dict, total_min: float, per_file_min: float
) -> tuple[bool, list[str]]:
    """Avalia coverage contra gates. Retorna (passou, lista de violacoes)."""
    violations: list[str] = []
    total_pct = coverage.get("totals", {}).get("percent_covered", 0)

    # Gate 1: total
    if total_pct < total_min:
        violations.append(f"[TOTAL] coverage {total_pct:.2f}% < gate {total_min:.0f}%")

    # Gate 2: per-file (opt-in; zero means report-only)
    files = coverage.get("files", {})
    per_file_violations: list[tuple[str, float]] = []
    if per_file_min > 0:
        for path, data in files.items():
            # Skip exempt files
            if any(ex in path for ex in EXEMPT_FILES):
                continue
            pct = data.get("summary", {}).get("percent_covered", 0)
            if pct < per_file_min:
                per_file_violations.append((path, pct))

    if per_file_violations:
        per_file_violations.sort(key=lambda x: x[1])
        for path, pct in per_file_violations[:10]:  # top 10 piores
            violations.append(f"[FILE] {path}: {pct:.2f}% < gate {per_file_min:.0f}%")
        if len(per_file_violations) > 10:
            violations.append(
                f"[FILE] ... +{len(per_file_violations) - 10} arquivos abaixo do gate"
            )

    return len(violations) == 0, violations


def render_markdown(
    coverage: dict, total_min: float, per_file_min: float, violations: list[str]
) -> str:
    md: list[str] = []
    md.append("# Coverage Gate Report")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Total gate**: {total_min:.0f}%")
    md.append(f"**Per-file gate**: {per_file_min:.0f}%")
    total_pct = coverage.get("totals", {}).get("percent_covered", 0)
    md.append(f"**Coverage total atual**: {total_pct:.2f}%")
    md.append("")

    if not violations:
        md.append("## [WORK] Gates passaram")
    else:
        md.append(f"## [HOLD] {len(violations)} violacao(oes)")
        md.append("")
        md.append("```")
        for v in violations:
            md.append(v)
        md.append("```")
        md.append("")

    # Top 10 piores arquivos
    files = coverage.get("files", {})
    file_list: list[tuple[str, float]] = []
    for path, data in files.items():
        pct = data.get("summary", {}).get("percent_covered", 0)
        file_list.append((path, pct))
    file_list.sort(key=lambda x: x[1])

    md.append("## Top 10 arquivos com menor coverage")
    md.append("")
    md.append("| Arquivo | Coverage | Status |")
    md.append("|---|---|---|")
    for path, pct in file_list[:10]:
        status = "❌" if pct < per_file_min else "✅"
        md.append(f"| `{path}` | {pct:.2f}% | {status} |")
    md.append("")

    # Top 5 melhores
    md.append("## Top 5 arquivos com maior coverage")
    md.append("")
    md.append("| Arquivo | Coverage |")
    md.append("|---|---|")
    for path, pct in sorted(file_list, key=lambda x: -x[1])[:5]:
        md.append(f"| `{path}` | {pct:.2f}% |")
    md.append("")

    md.append("---")
    md.append("")
    md.append(
        "**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 4 (auto-gerado)**"
    )
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="Coverage gate fail-safe")
    parser.add_argument(
        "--total", type=float, default=DEFAULT_TOTAL, help="gate total %"
    )
    parser.add_argument(
        "--per-file", type=float, default=DEFAULT_PER_FILE, help="gate per-file %"
    )
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    coverage = run_pytest_with_coverage()
    if coverage is None:
        return 2

    passou, violations = evaluate(coverage, args.total, args.per_file)
    total_pct = coverage.get("totals", {}).get("percent_covered", 0)

    print(f"Coverage total: {total_pct:.2f}% (gate {args.total:.0f}%)")
    if violations:
        print(f"[HOLD] {len(violations)} violacoes:")
        for v in violations[:10]:
            print(f"  - {v}")
        if len(violations) > 10:
            print(f"  ... +{len(violations) - 10} mais")
    else:
        suffix = " + per-file" if args.per_file > 0 else " (per-file report-only)"
        print(f"[WORK] Gates passaram (total{suffix})")

    if args.report:
        args.report.write_text(
            render_markdown(coverage, args.total, args.per_file, violations)
        )
        print(f"  Report: {args.report}", file=sys.stderr)

    return 0 if passou else 1


if __name__ == "__main__":
    sys.exit(main())
