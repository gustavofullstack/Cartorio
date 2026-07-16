"""LGPD Data Inventory scanner (G6.C.T6).

Mapeia TODOS os campos PII (Pessoalmente Identificaveis) em:
- backend/app/models/*.py (SQLAlchemy models)
- backend/app/schemas/*.py (Pydantic schemas)
- backend/app/services/pii.py (campos protegidos)

Gera report consolidado mostrando onde cada tipo de PII aparece,
LGPD base legal, e retencao.

Uso:
    python3 scripts/lgpd_data_inventory.py
    python3 scripts/lgpd_data_inventory.py --json
    python3 scripts/lgpd_data_inventory.py --report docs/LGPD_DATA_INVENTORY.md

Exit codes:
    0 = inventory gerado OK
    1 = erro ao processar

LGPD art. 37 + art. 18 IV (direito a portabilidade).
Modified by Gustavo Almeida + cartorio-lgpd — G6 wave 11.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("backend/app")
MODELS_DIR = ROOT / "models"
SCHEMAS_DIR = ROOT / "schemas"
PII_SERVICE = ROOT / "services" / "pii.py"

# Categorias LGPD art. 5 I (dados pessoais)
PII_CATEGORIES: dict[str, dict] = {
    "identificacao_direta": {
        "patterns": [
            re.compile(r"\bcpf\b", re.IGNORECASE),
            re.compile(r"\bcnpj\b", re.IGNORECASE),
            re.compile(r"\brg\b", re.IGNORECASE),
            re.compile(r"\bcnh\b", re.IGNORECASE),
            re.compile(r"\bpassaporte\b", re.IGNORECASE),
            re.compile(r"nome_completo"),
            re.compile(r"\bnome\b"),
        ],
        "base_legal": "art. 7 II (obrigacao legal cartoraria)",
        "retencao": "5 anos (Provimento 74/2018)",
    },
    "contato": {
        "patterns": [
            re.compile(r"\bemail\b", re.IGNORECASE),
            re.compile(r"\btelefone\b", re.IGNORECASE),
            re.compile(r"\bcelular\b", re.IGNORECASE),
            re.compile(r"\bendereco\b", re.IGNORECASE),
            re.compile(r"\bcep\b", re.IGNORECASE),
        ],
        "base_legal": "art. 7 V (execucao do servico)",
        "retencao": "5 anos",
    },
    "navegacao": {
        "patterns": [
            re.compile(r"\bip\b", re.IGNORECASE),
            re.compile(r"user_agent"),
            re.compile(r"cookies"),
        ],
        "base_legal": "art. 7 IX (interesse legitimo, seguranca)",
        "retencao": "6 meses",
    },
    "financeiro": {
        "patterns": [
            re.compile(r"\bvalor\b", re.IGNORECASE),
            re.compile(r"\bpix\b", re.IGNORECASE),
            re.compile(r"\bconta\b", re.IGNORECASE),
            re.compile(r"emolumento"),
            re.compile(r"cartao"),
        ],
        "base_legal": "art. 7 V (execucao do servico)",
        "retencao": "5 anos (Provimento 74/2018)",
    },
    "biometrico": {
        "patterns": [
            re.compile(r"biometric"),
            re.compile(r"fingerprint"),
            re.compile(r"face_id"),
            re.compile(r"foto"),
        ],
        "base_legal": "art. 11 I (consentimento especifico + destacado)",
        "retencao": "ate revogacao do consentimento",
    },
    "saude": {
        "patterns": [
            re.compile(r"saude"),
            re.compile(r"cid"),
            re.compile(r"deficiencia"),
            re.compile(r"medic"),
        ],
        "base_legal": "art. 11 II (politica publica / saude)",
        "retencao": "20 anos (CF art. 5 LXXIX)",
    },
    "criptografado_hash": {
        "patterns": [
            re.compile(r"_hash\b"),
            re.compile(r"hashed_"),
        ],
        "base_legal": "art. 46 (medidas de seguranca)",
        "retencao": "mesma do dado original",
    },
}


def categorize_field(field_name: str) -> tuple[str, str] | None:
    """Retorna (categoria, descricao) se o field eh PII, None caso contrario."""
    for category, info in PII_CATEGORIES.items():
        for pat in info["patterns"]:
            if pat.search(field_name):
                return category, info["base_legal"]
    return None


def scan_models() -> list[dict]:
    """Scan SQLAlchemy models em backend/app/models/*.py."""
    findings: list[dict] = []
    if not MODELS_DIR.exists():
        return findings

    for py_file in sorted(MODELS_DIR.glob("*.py")):
        content = py_file.read_text(errors="ignore")
        # Match: field: Mapped[...] = mapped_column(...) ou Column(...)
        # Pattern simples: line starts with whitespace, has nome + :
        for line_no, line in enumerate(content.splitlines(), start=1):
            # Match `name: Mapped` or `name = Column`
            match = re.match(r"\s+(\w+):\s*(Mapped|Optional|Column|=\s*Column)", line)
            if not match:
                continue
            field_name = match.group(1)
            if field_name.startswith("_"):
                continue
            cat = categorize_field(field_name)
            if cat:
                category, base_legal = cat
                findings.append({
                    "file": str(py_file.relative_to(ROOT)),
                    "line": line_no,
                    "field": field_name,
                    "category": category,
                    "base_legal": base_legal,
                })

    return findings


def scan_schemas() -> list[dict]:
    """Scan Pydantic schemas em backend/app/schemas/*.py."""
    findings: list[dict] = []
    if not SCHEMAS_DIR.exists():
        return findings

    for py_file in sorted(SCHEMAS_DIR.glob("*.py")):
        content = py_file.read_text(errors="ignore")
        # Match: field: str = ... ou field: Optional[str]
        for line_no, line in enumerate(content.splitlines(), start=1):
            match = re.match(r"\s+(\w+):\s*(str|int|Optional\[|List\[|EmailStr)", line)
            if not match:
                continue
            field_name = match.group(1)
            if field_name.startswith("_"):
                continue
            cat = categorize_field(field_name)
            if cat:
                category, base_legal = cat
                findings.append({
                    "file": str(py_file.relative_to(ROOT)),
                    "line": line_no,
                    "field": field_name,
                    "category": category,
                    "base_legal": base_legal,
                })

    return findings


def scan_pii_service() -> list[dict]:
    """Scan backend/app/services/pii.py para funcoes de protecao."""
    findings: list[dict] = []
    if not PII_SERVICE.exists():
        return findings

    content = PII_SERVICE.read_text(errors="ignore")
    # Match def funcao_pii(...)
    for line_no, line in enumerate(content.splitlines(), start=1):
        match = re.match(r"def (\w*pii\w*|\w*scrub\w*|\w*mask\w*|\w*hash\w*)", line)
        if not match:
            continue
        findings.append({
            "file": str(PII_SERVICE.relative_to(ROOT)),
            "line": line_no,
            "field": match.group(1),
            "category": "protecao",
            "base_legal": "art. 46",
        })
    return findings


def render_markdown(model_findings: list[dict], schema_findings: list[dict], pii_findings: list[dict]) -> str:
    md: list[str] = []
    md.append("# LGPD Data Inventory")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Total fields PII**: {len(model_findings) + len(schema_findings)}")
    md.append(f"**Funcoes protecao**: {len(pii_findings)}")
    md.append("")

    # Categoria count
    cat_count: dict[str, int] = {}
    for f in model_findings + schema_findings:
        cat_count[f["category"]] = cat_count.get(f["category"], 0) + 1

    md.append("## Resumo por categoria")
    md.append("")
    md.append("| Categoria | Total | Base legal | Retencao |")
    md.append("|---|---|---|---|")
    for cat, count in sorted(cat_count.items()):
        info = PII_CATEGORIES.get(cat, {})
        base_legal = info.get("base_legal", "?")
        retencao = info.get("retencao", "?")
        md.append(f"| {cat} | {count} | {base_legal} | {retencao} |")
    md.append("")

    # Models
    if model_findings:
        md.append(f"## Models SQLAlchemy ({len(model_findings)})")
        md.append("")
        md.append("| File | Line | Field | Categoria | Base legal |")
        md.append("|---|---|---|---|---|")
        for f in model_findings:
            md.append(f"| `{f['file']}` | {f['line']} | `{f['field']}` | {f['category']} | {f['base_legal']} |")
        md.append("")

    # Schemas
    if schema_findings:
        md.append(f"## Schemas Pydantic ({len(schema_findings)})")
        md.append("")
        md.append("| File | Line | Field | Categoria | Base legal |")
        md.append("|---|---|---|---|---|")
        for f in schema_findings:
            md.append(f"| `{f['file']}` | {f['line']} | `{f['field']}` | {f['category']} | {f['base_legal']} |")
        md.append("")

    # Protection
    if pii_findings:
        md.append(f"## Funcoes de Protecao ({len(pii_findings)})")
        md.append("")
        md.append("| File | Line | Funcao |")
        md.append("|---|---|---|")
        for f in pii_findings:
            md.append(f"| `{f['file']}` | {f['line']} | `{f['field']}` |")
        md.append("")

    md.append("---")
    md.append("")
    md.append("**Compliance**: LGPD art. 37 (registro das operacoes) + art. 18 IV (portabilidade).")
    md.append("")
    md.append("**Modified by Gustavo Almeida + cartorio-lgpd — G6 wave 11 (auto-gerado)**")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="LGPD data inventory scanner")
    parser.add_argument("--json", action="store_true", help="output JSON")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    model_findings = scan_models()
    schema_findings = scan_schemas()
    pii_findings = scan_pii_service()

    total = len(model_findings) + len(schema_findings)

    if args.json:
        print(json.dumps({
            "models": model_findings,
            "schemas": schema_findings,
            "protection": pii_findings,
            "total_pii": total,
        }, indent=2, ensure_ascii=False))
    else:
        print(f"PII em models: {len(model_findings)}")
        print(f"PII em schemas: {len(schema_findings)}")
        print(f"Funcoes protecao: {len(pii_findings)}")
        print(f"Total: {total}")

    if args.report:
        args.report.write_text(render_markdown(model_findings, schema_findings, pii_findings))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())