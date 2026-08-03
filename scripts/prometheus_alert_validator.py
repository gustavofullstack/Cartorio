"""Prometheus alerts validator + add 3 LGPD alerts (G6.D.T2).

Valida sintaxe YAML de infra/prometheus/alerts.yml e verifica que TODOS os alerts
tem: name, expr, for, severity, squad, summary, description.

Adiciona 3 alerts novos:
- CartorioLGPDConsentimentoBaixo: consent_granted_ratio < 70% por 1h
- CartorioBackupFalhou: cartorio_backup_last_success_age_seconds > 86400 (24h)
- CartorioCircuitBreakerAberto: circuit_breaker_state{state="open"} > 0 por 5min

Uso:
    python3 scripts/prometheus_alert_validator.py
    python3 scripts/prometheus_alert_validator.py --add-lgpd-alerts  # adiciona 3
    python3 scripts/prometheus_alert_validator.py --report docs/PROMETHEUS_ALERTS_REPORT.md

Exit codes:
    0 = YAML valido + todas alertas tem campos obrigatorios
    1 = algum alerta falta campos
    2 = erro pre-requisito

Modified by Gustavo Almeida + cartorio-sre — G6 wave 8.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "[ERROR] PyYAML nao instalado. uv add pyyaml e rode de novo.", file=sys.stderr
    )
    sys.exit(2)

ALERTS_FILE = Path("infra/prometheus/alerts.yml")

REQUIRED_FIELDS = ["alert", "expr", "labels", "annotations"]
REQUIRED_LABEL_FIELDS = ["severity", "squad"]
REQUIRED_ANNOTATION_FIELDS = ["summary", "description"]


def validate_alerts() -> tuple[bool, list[str]]:
    """Valida todos alerts. Retorna (ok, lista de problemas)."""
    problems: list[str] = []
    if not ALERTS_FILE.exists():
        return False, [f"arquivo nao existe: {ALERTS_FILE}"]

    try:
        data = yaml.safe_load(ALERTS_FILE.read_text())
    except yaml.YAMLError as exc:
        return False, [f"YAML invalido: {exc}"]

    groups = data.get("groups", [])
    if not groups:
        return False, ["nenhum 'groups' definido"]

    total_rules = 0
    for group in groups:
        group_name = group.get("name", "?")
        for rule in group.get("rules", []):
            total_rules += 1
            for field in REQUIRED_FIELDS:
                if field not in rule:
                    problems.append(
                        f"  [{group_name}] rule sem '{field}': {rule.get('alert', '?')}"
                    )
            labels = rule.get("labels", {}) or {}
            for field in REQUIRED_LABEL_FIELDS:
                if field not in labels:
                    problems.append(
                        f"  [{group_name}] {rule.get('alert', '?')} label '{field}' ausente"
                    )
            annotations = rule.get("annotations", {}) or {}
            for field in REQUIRED_ANNOTATION_FIELDS:
                if field not in annotations:
                    problems.append(
                        f"  [{group_name}] {rule.get('alert', '?')} annotation '{field}' ausente"
                    )

    if total_rules == 0:
        problems.append("nenhuma rule definida em nenhum group")

    print(f"Total alerts: {total_rules} (em {len(groups)} groups)")
    return len(problems) == 0, problems


def add_lgpd_alerts() -> int:
    """Adiciona 3 alerts LGPD/produto. Retorna quantos foram adicionados."""
    if not ALERTS_FILE.exists():
        return 0

    data = yaml.safe_load(ALERTS_FILE.read_text())

    new_alerts = [
        {
            "alert": "CartorioLGPDConsentimentoBaixo",
            "expr": "cartorio_consent_granted_ratio < 0.7",
            "for": "1h",
            "labels": {
                "severity": "warning",
                "priority": "P2",
                "squad": "cartorio-lgpd",
            },
            "annotations": {
                "summary": "Taxa de consentimento LGPD baixo",
                "description": "Apenas {{ $value | humanizePercentage }} dos clientes consentiram em {{ $labels.period }}. Esperado >70%. Pode indicar problema no banner de consentimento.",
                "runbook": "https://github.com/gustavofullstack/Cartorio/blob/master/docs/runbook/lgpd-consent-low.md",
            },
        },
        {
            "alert": "CartorioBackupFalhou",
            "expr": "time() - cartorio_backup_last_success_timestamp > 86400",
            "for": "5m",
            "labels": {
                "severity": "critical",
                "priority": "P0",
                "squad": "cartorio-sre",
            },
            "annotations": {
                "summary": "Backup do banco NAO executou em 24h",
                "description": "Ultimo backup bem-sucedido foi ha mais de 24h. Verificar cron pg_basebackup e storage S3.",
                "runbook": "https://github.com/gustavofullstack/Cartorio/blob/master/docs/runbook/backup-failed.md",
            },
        },
        {
            "alert": "CartorioCircuitBreakerAberto",
            "expr": 'circuit_breaker_state{state="open"} > 0',
            "for": "5m",
            "labels": {
                "severity": "warning",
                "priority": "P1",
                "squad": "cartorio-dev",
            },
            "annotations": {
                "summary": "Circuit breaker aberto para {{ $labels.provider }}",
                "description": "Provider {{ $labels.provider }} com circuit breaker aberto ha mais de 5min. Fallback chain pode estar degradado.",
                "runbook": "https://github.com/gustavofullstack/Cartorio/blob/master/docs/runbook/circuit-breaker.md",
            },
        },
    ]

    # Adiciona no grupo cartorio-p2-product (cria se nao existir)
    target_group = None
    for g in data.get("groups", []):
        if g.get("name") == "cartorio-p2-product":
            target_group = g
            break
    if target_group is None:
        target_group = {"name": "cartorio-p2-product", "interval": "5m", "rules": []}
        data.setdefault("groups", []).append(target_group)

    existing_names = {r.get("alert") for r in target_group.get("rules", [])}
    added = 0
    for alert in new_alerts:
        if alert["alert"] in existing_names:
            continue
        target_group["rules"].append(alert)
        added += 1

    if added:
        ALERTS_FILE.write_text(
            yaml.safe_dump(
                data, default_flow_style=False, sort_keys=False, allow_unicode=True
            )
        )
    return added


def render_markdown(problems: list[str], total: int) -> str:
    md: list[str] = []
    md.append("# Prometheus Alerts Report")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Arquivo**: `{ALERTS_FILE}`")
    md.append("")
    if not problems:
        md.append("## [WORK] Todos alerts tem campos obrigatorios")
    else:
        md.append(f"## [HOLD] {len(problems)} problema(s)")
        for p in problems:
            md.append(f"- {p}")
    md.append("")
    md.append("---")
    md.append("")
    md.append(
        "**Modified by Gustavo Almeida + cartorio-sre — G6 wave 8 (auto-gerado)**"
    )
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prometheus alerts validator")
    parser.add_argument(
        "--add-lgpd-alerts", action="store_true", help="adicionar 3 alerts LGPD/produto"
    )
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    if args.add_lgpd_alerts:
        added = add_lgpd_alerts()
        print(f"[FIX] Adicionados {added} alerts LGPD/produto")
        if added == 0:
            print("  (todos ja existem)")

    ok, problems = validate_alerts()

    if ok:
        print("[WORK] Todos alerts validos")
    else:
        print(f"[HOLD] {len(problems)} problemas:")
        for p in problems[:10]:
            print(p)

    if args.report:
        args.report.write_text(render_markdown(problems, total=0))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
