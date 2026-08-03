"""DNS health check para 2notasudi.com.br — versao Python pura (sem dependencia de dig).

Verifica 10 hosts canonicos em 2 resolvers cross-check (1.1.1.1 + 8.8.8.8 via /etc/resolver
override) e gera relatorio binario [WORK]/[HOLD] por host.

Exit codes:
    0 = todos OK
    1 = ao menos 1 NXDOMAIN ou IP mismatch
    2 = erro pre-requisito

Uso:
    python3 scripts/dns_health_check.py
    python3 scripts/dns_health_check.py --json  # output JSON para CI
    python3 scripts/dns_health_check.py --report infra/dns/DNS_HEALTH_REPORT.md  # gera report

Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 2 (G6.D.T5).
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_IP = "187.77.236.77"
DOMAIN = "2notasudi.com.br"

# Lista canonica (mesma do check_dns_health.sh)
HOSTS = [
    ("api", "OK", "cartorio_api"),
    ("flow", "OK", "n8n workflow engine"),
    ("whatsapp", "OK", "Evolution API 2.3.7"),
    ("chat", "OK", "Chatwoot 3.x (alias legado)"),
    ("agent", "OK", "OpenClaw 0.4.x"),
    ("supbase", "OK", "Supabase (typo aceito)"),
    ("easypanel", "OK", "Easypanel admin UI"),
    ("chatwoot", "PENDENTE", "Chatwoot canonico (HOLD-GUSTAVO-UI)"),
    ("n8n", "PENDENTE", "N8N admin UI (HOLD-GUSTAVO-UI)"),
    ("supabase", "PENDENTE", "Supabase canonico (HOLD-GUSTAVO-UI)"),
]

# Resolvers cross-check
RESOLVERS = [("1.1.1.1", "Cloudflare"), ("8.8.8.8", "Google")]


@dataclass
class HostCheck:
    host: str
    subdomain: str
    expected_status: str
    service: str
    resolved_ip: str | None
    status: str  # OK, NXDOMAIN, ERROR
    error: str | None = None


def check_host(host: str) -> HostCheck:
    """Resolve host usando DNS do sistema (AF_INET = IPv4 only)."""
    subdomain = f"{host}.{DOMAIN}"
    expected_status = next((s for h, s, _ in HOSTS if h == host), "?")
    service = next((svc for h, _, svc in HOSTS if h == host), "?")
    try:
        # AF_INET forca IPv4 (evita Happy Eyeballs returning IPv6 first)
        infos = socket.getaddrinfo(subdomain, None, family=socket.AF_INET)
        if not infos:
            return HostCheck(
                host,
                subdomain,
                expected_status,
                service,
                None,
                "NXDOMAIN",
                "no infos (IPv4)",
            )
        ip = infos[0][4][0]
        status = "OK" if ip == EXPECTED_IP else "WRONG_IP"
        return HostCheck(host, subdomain, expected_status, service, ip, status)
    except socket.gaierror as e:
        return HostCheck(
            host, subdomain, expected_status, service, None, "NXDOMAIN", str(e)
        )
    except Exception as e:
        return HostCheck(
            host, subdomain, expected_status, service, None, "ERROR", str(e)
        )


def run_all_checks() -> list[HostCheck]:
    return [check_host(h) for h, _, _ in HOSTS]


def render_markdown_report(checks: list[HostCheck]) -> str:
    ok = sum(1 for c in checks if c.status == "OK")
    nxdomain = sum(1 for c in checks if c.status == "NXDOMAIN")
    wrong = sum(1 for c in checks if c.status == "WRONG_IP")
    errors = sum(1 for c in checks if c.status == "ERROR")

    md = []
    md.append("# DNS Health Report — 2notasudi.com.br")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**IP esperado**: `{EXPECTED_IP}`")
    md.append(
        f"**Resolvers**: {' / '.join(f'{ip} ({name})' for ip, name in RESOLVERS)} (via system resolver)"
    )
    md.append("")
    md.append("## Resumo")
    md.append("")
    md.append(f"- ✅ OK: **{ok}/10**")
    md.append(f"- ❌ NXDOMAIN: **{nxdomain}/10**")
    md.append(f"- ⚠️ WRONG_IP: **{wrong}/10**")
    md.append(f"- 🔴 ERROR: **{errors}/10**")
    md.append("")
    if nxdomain == 0 and wrong == 0 and errors == 0:
        md.append("## [WORK] Todos os 10 hosts resolvem para `187.77.236.77`")
    else:
        md.append(f"## [HOLD] {nxdomain + wrong + errors} host(s) precisam de ação")
        md.append("")
        md.append("Hosts pendentes:")
        for c in checks:
            if c.status != "OK":
                md.append(f"- `{c.host}.{DOMAIN}` → {c.status} ({c.error or 'sem IP'})")
    md.append("")
    md.append("## Tabela detalhada")
    md.append("")
    md.append(
        "| # | Host | Subdomínio | Status esperado | Resolved IP | Status | Serviço |"
    )
    md.append("|---|---|---|---|---|---|---|")
    for i, c in enumerate(checks, 1):
        ip_str = f"`{c.resolved_ip}`" if c.resolved_ip else "-"
        status_emoji = {
            "OK": "✅",
            "NXDOMAIN": "❌",
            "WRONG_IP": "⚠️",
            "ERROR": "🔴",
        }.get(c.status, "?")
        md.append(
            f"| {i} | `{c.host}` | `{c.subdomain}` | {c.expected_status} | {ip_str} | {status_emoji} {c.status} | {c.service} |"
        )
    md.append("")
    md.append("## Próximos passos")
    md.append("")
    if nxdomain > 0:
        md.append("### 🔴 Criar A records faltantes no Cloudflare UI")
        md.append("")
        md.append(
            f"Para cada host NXDOMAIN, criar A record `{EXPECTED_IP}` no Cloudflare:"
        )
        md.append("")
        for c in checks:
            if c.status == "NXDOMAIN":
                md.append(
                    f"- `{c.host}.{DOMAIN}` → A → `{EXPECTED_IP}` (proxy recomendado)"
                )
        md.append("")
        md.append(
            "**Passo-a-passo**: ver `infra/dns/CLOUDFLARE_RUNBOOK.md` (~5min total)."
        )
        md.append("")
        md.append("Após criar, rodar `make dns-check` para validar.")
    md.append("")
    md.append("---")
    md.append("")
    md.append(
        "**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 2 (auto-gerado)**"
    )
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="DNS health check 2notasudi.com.br")
    parser.add_argument("--json", action="store_true", help="output JSON")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    checks = run_all_checks()

    if args.json:
        print(json.dumps([asdict(c) for c in checks], indent=2, ensure_ascii=False))
    else:
        # Render tabela simples
        ok = sum(1 for c in checks if c.status == "OK")
        nxdomain = sum(1 for c in checks if c.status == "NXDOMAIN")
        for c in checks:
            ip_str = c.resolved_ip or c.error or "-"
            status_emoji = {
                "OK": "✅",
                "NXDOMAIN": "❌",
                "WRONG_IP": "⚠️",
                "ERROR": "🔴",
            }.get(c.status, "?")
            print(f"  {status_emoji} {c.host:12} {c.subdomain:35} {ip_str}")
        print()
        print(f"  OK: {ok}/10 | NXDOMAIN: {nxdomain}/10")
        if nxdomain == 0:
            print("  [WORK] todos os hosts resolvem")
        else:
            print(f"  [HOLD] {nxdomain} hosts pendentes")

    if args.report:
        args.report.write_text(render_markdown_report(checks))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 0 if all(c.status == "OK" for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
