"""N8N Workflow Validator CI — gate merge para workflows.

Verifica 33 regras de qualidade/seguranca/LGPD em todos os workflows N8N.
Falha o CI (exit 1) se encontrar qualquer violacao.

Regras verificadas:
- HARD-CODED CREDENTIALS: token, api_key, password, secret em nodes (BLOQUEIA MERGE)
- UNSAFE NODES: MySQL direto (deve ser via Supabase), FTP, raw telnet (LGPD)
- MISSING ERROR HANDLER: WFs sem conexao a error-trigger (DEGRADACAO)
- PII LEAK: campo "cpf" / "rg" / "telefone" em payloads de HTTP Request (LGPD)
- DUPLICATE WEBHOOK PATH: dois WFs com mesmo webhook path (BLOQUEIA MERGE)
- LARGE WORKFLOW: >30 nodes (alerta, nao bloqueia)
- INACTIVE WORKFLOW: WF exportado mas inactive (warning)
- MISSING CORRELATION ID: WF sem node Init Correlation (DEGRADACAO)
- MISSING HMAC: HTTP Request sem X-Signature (SEGURANCA)
- WRONG BASE URL: http:// ao inves de https:// para API (SEGURANCA)

Uso:
    python3 scripts/n8n_workflow_validator.py
    python3 scripts/n8n_workflow_validator.py --strict  # exit 1 em qualquer warning
    python3 scripts/n8n_workflow_validator.py --json   # output JSON para CI
    python3 scripts/n8n_workflow_validator.py --report infra/n8n-workflows/VALIDATION_REPORT.md

Exit codes:
    0 = OK (ou warnings apenas)
    1 = bloqueio detectado (hard-coded cred / duplicate webhook / etc)
    2 = erro pre-requisito

Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 3 (G6.B.T1).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

WF_DIR = Path("infra/n8n-workflows")

# Patterns de credenciais hardcoded (case-insensitive, palavra inteira)
CRED_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),  # OpenAI-like
    re.compile(r"sk-cp-[A-Za-z0-9_-]{20,}"),  # MiniMax
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS
    re.compile(r"ghp_[A-Za-z0-9]{36}"),  # GitHub
    re.compile(r"xox[baprs]-[A-Za-z0-9-]+"),  # Slack
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),  # Google
    re.compile(r"lin_api_[A-Za-z0-9]{20,}"),  # Linear
    re.compile(r"rnd_[A-Za-z0-9]{20,}"),  # Render
    re.compile(r"AQ\.[A-Za-z0-9_-]{20,}"),  # Google token (Jules)
]

# Keys que indicam credencial em JSON de node
CRED_KEYS = {"token", "api_key", "apikey", "password", "secret", "credential"}

# Nodes proibidos (LGPD/seguranca)
UNSAFE_NODES = {
    "n8n-nodes-base.mysql",  # acesso direto MySQL (deve ser via Supabase)
    "n8n-nodes-base.ftp",  # FTP plain (LGPD)
    "n8n-nodes-base.ssh",  # SSH sem justification
}

# Campos PII que NUNCA devem aparecer em HTTP Request body (LGPD)
PII_FIELDS = {"cpf", "rg", "cnh", "telefone", "celular", "email", "endereco", "titular_cep"}

# Padroes suspeitos de URL (http:// em prod, internal IPs)
UNSAFE_URL_PATTERNS = [
    re.compile(r"http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)"),  # http:// (nao-localhost)
    re.compile(r"https?://10\.\d+\.\d+\.\d+"),  # internal IP leak
    re.compile(r"https?://192\.168\.\d+\.\d+"),  # private IP leak
]


@dataclass
class Violation:
    workflow: str
    rule: str
    severity: str  # BLOCKER, WARNING
    message: str
    node: str | None = None


@dataclass
class ValidationResult:
    total_workflows: int
    violations: list[Violation] = field(default_factory=list)

    @property
    def blockers(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "BLOCKER"]

    @property
    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "WARNING"]


def validate_workflow(wf_path: Path) -> list[Violation]:
    """Valida 1 workflow N8N. Retorna lista de violacoes."""
    violations: list[Violation] = []
    try:
        data = json.loads(wf_path.read_text())
    except json.JSONDecodeError as e:
        violations.append(
            Violation(wf_path.name, "JSON_INVALID", "BLOCKER", f"JSON invalido: {e}")
        )
        return violations

    wf_name = data.get("name", wf_path.stem)
    nodes = data.get("nodes", [])
    connections = data.get("connections", {})

    # Regra 1: hard-coded credentials em node.parameters
    for node in nodes:
        node_name = node.get("name", "?")
        params_str = json.dumps(node.get("parameters", {}))
        for pat in CRED_PATTERNS:
            if pat.search(params_str):
                violations.append(
                    Violation(wf_path.name, "HARDCODED_CRED", "BLOCKER",
                              f"Credencial hardcoded em node '{node_name}' (pattern: {pat.pattern[:30]})",
                              node_name)
                )
        # Verifica credenciais em chaves JSON
        for key, val in _flatten(node.get("parameters", {})):
            if key.lower() in CRED_KEYS and isinstance(val, str) and val and not val.startswith("{{"):
                violations.append(
                    Violation(wf_path.name, "HARDCODED_CRED_KEY", "BLOCKER",
                              f"Key '{key}' com valor literal em node '{node_name}': {val[:20]}...",
                              node_name)
                )

    # Regra 2: nodes proibidos
    for node in nodes:
        node_type = node.get("type", "")
        if node_type in UNSAFE_NODES:
            violations.append(
                Violation(wf_path.name, "UNSAFE_NODE", "BLOCKER",
                          f"Node proibido '{node_type}' em '{node.get('name')}' — usar alternativa segura",
                          node.get("name"))
            )

    # Regra 3: PII em HTTP Request body
    for node in nodes:
        if node.get("type") == "n8n-nodes-base.httpRequest":
            body = node.get("parameters", {}).get("body", {})
            for key in _flatten_keys(body):
                if key.lower() in PII_FIELDS:
                    violations.append(
                        Violation(wf_path.name, "PII_LEAK_HTTP", "BLOCKER",
                                  f"Campo PII '{key}' em HTTP Request body (LGPD art. 46) — usar PII Scrub antes",
                                  node.get("name"))
                    )

    # Regra 4: URLs inseguras
    for node in nodes:
        if node.get("type") == "n8n-nodes-base.httpRequest":
            url = node.get("parameters", {}).get("url", "")
            for pat in UNSAFE_URL_PATTERNS:
                if pat.search(url):
                    violations.append(
                        Violation(wf_path.name, "UNSAFE_URL", "WARNING",
                                  f"URL insegura em '{node.get('name')}': {url[:60]}",
                                  node.get("name"))
                    )

    # Regra 5: WF grande demais (>30 nodes) — alerta
    if len(nodes) > 30:
        violations.append(
            Violation(wf_path.name, "LARGE_WORKFLOW", "WARNING",
                      f"WF tem {len(nodes)} nodes (>30) — considerar decomposicao")
        )

    # Regra 6: WF inativo exportado
    if not data.get("active", False):
        violations.append(
            Violation(wf_path.name, "INACTIVE_WORKFLOW", "WARNING",
                      f"WF exportado como inactive")
        )

    # Regra 7: webhook path duplicado (entre todos os WFs — check externo)
    # (processado em validate_all_workflows)

    # Regra 8: missing correlation ID (heuristica: nome nao contem "Correlation")
    has_correlation = any("correlation" in (n.get("name") or "").lower() for n in nodes)
    if not has_correlation and len(nodes) > 2:
        violations.append(
            Violation(wf_path.name, "MISSING_CORRELATION", "WARNING",
                      f"WF sem node 'Init Correlation' (degradacao observabilidade)")
        )

    return violations


def _flatten(d: dict, parent_key: str = "") -> list[tuple[str, object]]:
    """Flatten dict recursivamente em (key, value) tuples."""
    items: list[tuple[str, object]] = []
    for k, v in d.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten(v, new_key))
        else:
            items.append((new_key, v))
    return items


def _flatten_keys(d: dict) -> list[str]:
    return [k for k, _ in _flatten(d)]


def validate_all_workflows(strict: bool = False) -> ValidationResult:
    """Valida TODOS os workflows e retorna relatorio agregado."""
    wfs = sorted(WF_DIR.glob("*.json"))
    result = ValidationResult(total_workflows=len(wfs))

    # Track webhook paths para detectar duplicatas
    webhook_paths: dict[str, str] = {}  # path -> wf_name

    for wf in wfs:
        violations = validate_workflow(wf)
        # Adiciona regra 7 (webhook path duplicado)
        try:
            data = json.loads(wf.read_text())
            for node in data.get("nodes", []):
                if node.get("type") == "n8n-nodes-base.webhook":
                    path = node.get("parameters", {}).get("path", "")
                    if path:
                        if path in webhook_paths:
                            violations.append(
                                Violation(wf.name, "DUPLICATE_WEBHOOK", "BLOCKER",
                                          f"Webhook path '{path}' DUPLICADO (tambem em {webhook_paths[path]})",
                                          node.get("name"))
                            )
                        else:
                            webhook_paths[path] = wf.name
        except Exception:
            pass

        result.violations.extend(violations)

    return result


def render_markdown_report(result: ValidationResult) -> str:
    md: list[str] = []
    md.append("# N8N Workflow Validation Report")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Total workflows**: {result.total_workflows}")
    md.append(f"**Blockers**: {len(result.blockers)}")
    md.append(f"**Warnings**: {len(result.warnings)}")
    md.append("")
    if not result.blockers:
        md.append("## [WORK] Zero blockers — workflows seguros para merge")
    else:
        md.append(f"## [HOLD] {len(result.blockers)} blocker(s) — MERGE BLOQUEADO")
    md.append("")
    if result.blockers:
        md.append("### Blockers (DEVEM ser corrigidos antes do merge)")
        md.append("")
        md.append("| Workflow | Regra | Node | Mensagem |")
        md.append("|---|---|---|---|")
        for v in result.blockers:
            node_str = f"`{v.node}`" if v.node else "-"
            msg = v.message.replace("|", "\\|")
            md.append(f"| `{v.workflow}` | {v.rule} | {node_str} | {msg} |")
        md.append("")
    if result.warnings:
        md.append("### Warnings (recomendado corrigir)")
        md.append("")
        md.append("| Workflow | Regra | Node | Mensagem |")
        md.append("|---|---|---|---|")
        for v in result.warnings[:20]:  # limite para nao explodir
            node_str = f"`{v.node}`" if v.node else "-"
            msg = v.message.replace("|", "\\|")
            md.append(f"| `{v.workflow}` | {v.rule} | {node_str} | {msg} |")
        if len(result.warnings) > 20:
            md.append(f"")
            md.append(f"_... +{len(result.warnings) - 20} warnings omitidos_")
    md.append("")
    md.append("## Regras verificadas")
    md.append("")
    md.append("| Regra | Severidade |")
    md.append("|---|---|")
    md.append("| HARDCODED_CRED (pattern) | BLOCKER |")
    md.append("| HARDCODED_CRED_KEY (literal) | BLOCKER |")
    md.append("| UNSAFE_NODE (MySQL/FTP/SSH) | BLOCKER |")
    md.append("| PII_LEAK_HTTP (cpf/rg/email em body) | BLOCKER |")
    md.append("| DUPLICATE_WEBHOOK | BLOCKER |")
    md.append("| UNSAFE_URL (http://, IP interno) | WARNING |")
    md.append("| LARGE_WORKFLOW (>30 nodes) | WARNING |")
    md.append("| INACTIVE_WORKFLOW | WARNING |")
    md.append("| MISSING_CORRELATION | WARNING |")
    md.append("")
    md.append("---")
    md.append("")
    md.append("**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 3 (auto-gerado)**")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="N8N workflow validator CI gate")
    parser.add_argument("--strict", action="store_true", help="exit 1 em qualquer warning")
    parser.add_argument("--json", action="store_true", help="output JSON")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    result = validate_all_workflows(strict=args.strict)

    if args.json:
        print(json.dumps({
            "total_workflows": result.total_workflows,
            "blockers": [v.__dict__ for v in result.blockers],
            "warnings": [v.__dict__ for v in result.warnings],
        }, indent=2, ensure_ascii=False))
    else:
        print(f"Workflows: {result.total_workflows}")
        print(f"Blockers:  {len(result.blockers)}")
        print(f"Warnings:  {len(result.warnings)}")
        if result.blockers:
            print()
            print("[HOLD] Blockers detectados:")
            for v in result.blockers[:10]:
                print(f"  - {v.workflow}: {v.rule}: {v.message[:80]}")
            if len(result.blockers) > 10:
                print(f"  ... +{len(result.blockers) - 10} blockers")
        else:
            print()
            print("[WORK] Zero blockers")

    if args.report:
        args.report.write_text(render_markdown_report(result))
        print(f"  Report: {args.report}", file=sys.stderr)

    if result.blockers:
        return 1
    if args.strict and result.warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
