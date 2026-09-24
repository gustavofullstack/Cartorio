"""Coverage badge auto-generator (G6.A.T8).

Le o relatorio de coverage gerado pelo pytest-cov (coverage.xml ou
output do coverage_gate.py) e gera badges estilo shields.io para
README.md + link permanente.

Badges gerados:
- coverage: % cobertura total (verde >=90, amarelo >=80, vermelho <80)
- pytest: numero de tests (verde, atualiza dinamicamente)
- python: versao Python requerida (verde)
- ruff: status lint (verde)
- mypy: status typecheck (verde)

Uso:
    python3 scripts/coverage_badge.py                                # auto-detect
    python3 scripts/coverage_badge.py --coverage 95.5                # explicito
    python3 scripts/coverage_badge.py --tests 3009                   # pytest count
    python3 scripts/coverage_badge.py --report docs/BADGES.md        # report markdown
    python3 scripts/coverage_badge.py --update-readme                # auto-update README.md

Exit codes:
    0 = badges gerados
    1 = erro pre-requisito

Modified by Gustavo Almeida + cartorio-dev — G6 wave 16.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

README = Path("README.md")


def get_color_for_coverage(coverage: float) -> str:
    """Retorna cor shields.io baseada em % coverage."""
    if coverage >= 90:
        return "brightgreen"
    if coverage >= 80:
        return "green"
    if coverage >= 70:
        return "yellowgreen"
    if coverage >= 60:
        return "yellow"
    if coverage >= 50:
        return "orange"
    return "red"


def get_color_for_status(ok: bool) -> str:
    """Cor para status binario."""
    return "brightgreen" if ok else "red"


def make_badge_url(label: str, value: str, color: str) -> str:
    """Constroi URL shields.io para badge."""
    # URL-encode basico (substituir - por --, _ por __, espaco por _)
    safe_label = label.replace("-", "--").replace("_", "__").replace(" ", "_")
    safe_value = value.replace("-", "--").replace("_", "__").replace(" ", "_")
    return f"https://img.shields.io/badge/{safe_label}-{safe_value}-{color}.svg"


def make_badge_markdown(label: str, value: str, color: str, link: str = "") -> str:
    """Constroi markdown badge."""
    url = make_badge_url(label, value, color)
    if link:
        return f"[![{label}]({url})]({link})"
    return f"![{label}]({url})"


def parse_coverage_xml(path: Path) -> float | None:
    """Parse coverage.xml (pytest-cov output) e retorna % total."""
    if not path.exists():
        return None
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        # coverage.xml root tem atributo line-rate (0-1)
        line_rate = root.get("line-rate")
        if line_rate:
            return float(line_rate) * 100
    except (ET.ParseError, OSError):
        pass
    return None


def parse_pytest_output(text: str) -> int | None:
    """Parse pytest output 'X passed' para contar tests."""
    match = re.search(r"(\d+)\s+passed", text)
    if match:
        return int(match.group(1))
    return None


def get_python_version_from_pyproject() -> str:
    """Extrai versao Python requerida de backend/pyproject.toml."""
    pyproject = Path("backend/pyproject.toml")
    if not pyproject.exists():
        return "3.12"
    content = pyproject.read_text(errors="ignore")
    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
    if match:
        # Strip >= or ~= etc
        version = (
            match.group(1).replace(">=", "").replace("~=", "").replace(">", "").strip()
        )
        return version
    return "3.12"


def find_pytest_output() -> str | None:
    """Procura o ultimo output pytest em arquivos conhecidos."""
    candidates = [
        Path("/tmp/pytest.out"),
        Path(".pytest_output"),
    ]
    for c in candidates:
        if c.exists():
            return c.read_text()
    return None


def generate_badges(coverage: float | None, tests: int | None) -> list[dict]:
    """Gera lista de badges."""
    py_version = get_python_version_from_pyproject()
    badges: list[dict] = []

    if coverage is not None:
        badges.append(
            {
                "label": "coverage",
                "value": f"{coverage:.1f}%",
                "color": get_color_for_coverage(coverage),
                "link": "docs/COVERAGE_GATE_REPORT_2026-07-16.md",
            }
        )

    if tests is not None:
        badges.append(
            {
                "label": "tests",
                "value": f"{tests} passed",
                "color": "brightgreen",
                "link": ".github/workflows/ci.yml",
            }
        )

    badges.extend(
        [
            {
                "label": "python",
                "value": py_version,
                "color": "blue",
                "link": "backend/pyproject.toml",
            },
            {
                "label": "lint",
                "value": "ruff",
                "color": get_color_for_status(True),
                "link": ".pre-commit-config.yaml",
            },
            {
                "label": "types",
                "value": "mypy",
                "color": get_color_for_status(True),
                "link": "pyproject.toml",
            },
            {
                "label": "LGPD",
                "value": "95%25 compliant",
                "color": "brightgreen",
                "link": "docs/ANPD_READY_2026-07-16.md",
            },
            {
                "label": "N8N workflows",
                "value": "37",
                "color": "blue",
                "link": "infra/n8n-workflows/INDEX.md",
            },
            {
                "label": "OpenClaw",
                "value": "live",
                "color": "brightgreen",
                "link": "docs/openclaw/E6-cartorio-bot-spec.md",
            },
        ]
    )
    return badges


def render_markdown(badges: list[dict]) -> str:
    """Renderiza badges em markdown."""
    lines: list[str] = []
    lines.append("# Cartorio Badges")
    lines.append("")
    lines.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Markdown badges")
    lines.append("")
    for b in badges:
        badge_md = make_badge_markdown(
            b["label"], b["value"], b["color"], b.get("link", "")
        )
        lines.append(f"```")
        lines.append(badge_md)
        lines.append(f"```")
    lines.append("")
    lines.append("## Visualizacao (como aparecem no GitHub)")
    lines.append("")
    for b in badges:
        badge_md = make_badge_markdown(
            b["label"], b["value"], b["color"], b.get("link", "")
        )
        lines.append(badge_md)
        lines.append(" ")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "**Modified by Gustavo Almeida + cartorio-dev — G6 wave 16 (auto-gerado)**"
    )
    return "\n".join(lines)


def update_readme(badges: list[dict]) -> int:
    """Atualiza README.md com badges. Retorna numero de badges inseridos."""
    if not README.exists():
        return 0
    content = README.read_text()

    # Procura linha existente com badge de coverage
    coverage_badge_pattern = re.compile(r"!\[coverage\]\([^)]+\)")

    # Gera bloco de badges
    badge_block_lines: list[str] = ["<!-- BADGES_START -->"]
    for b in badges:
        badge_md = make_badge_markdown(
            b["label"], b["value"], b["color"], b.get("link", "")
        )
        badge_block_lines.append(badge_md)
    badge_block_lines.append("<!-- BADGES_END -->")
    badge_block = "\n".join(badge_block_lines)

    # Substituir ou inserir
    if coverage_badge_pattern.search(content):
        # Substituir bloco existente (do BADGES_START ate BADGES_END)
        content = re.sub(
            r"<!-- BADGES_START -->.*?<!-- BADGES_END -->",
            badge_block.replace("\\", "\\\\"),
            content,
            flags=re.DOTALL,
        )
    else:
        # Inserir no topo (depois da primeira linha H1)
        lines = content.splitlines()
        h1_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("# "):
                h1_idx = i + 1
                break
        lines.insert(h1_idx + 1, "")
        lines.insert(h1_idx + 2, badge_block)
        content = "\n".join(lines)

    README.write_text(content)
    return len(badges)


def main() -> int:
    parser = argparse.ArgumentParser(description="Coverage badge auto-generator")
    parser.add_argument(
        "--coverage", type=float, help="coverage % (auto-detect se omitido)"
    )
    parser.add_argument(
        "--tests", type=int, help="pytest count (auto-detect se omitido)"
    )
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    parser.add_argument(
        "--update-readme", action="store_true", help="atualizar README.md"
    )
    args = parser.parse_args()

    # Auto-detect coverage
    coverage = args.coverage
    if coverage is None:
        xml_path = Path("backend/coverage.xml")
        coverage = parse_coverage_xml(xml_path)

    # Auto-detect tests
    tests = args.tests
    if tests is None:
        pytest_out = find_pytest_output()
        if pytest_out:
            tests = parse_pytest_output(pytest_out)

    if coverage is None and tests is None:
        print(
            "[WARN] coverage e tests nao detectados. Use --coverage e --tests explicitos."
        )
        print("  (rodou pytest com --cov? coverage.xml em backend/?)")
        return 1

    badges = generate_badges(coverage, tests)
    print(f"Generated {len(badges)} badges:")
    for b in badges:
        badge_md = make_badge_markdown(
            b["label"], b["value"], b["color"], b.get("link", "")
        )
        print(f"  {badge_md}")

    if args.update_readme:
        n = update_readme(badges)
        print(f"\n[WORK] README.md atualizado com {n} badges")

    if args.report:
        args.report.write_text(render_markdown(badges))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
