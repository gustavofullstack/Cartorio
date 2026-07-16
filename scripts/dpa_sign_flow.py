"""DPA Signing Flow tracker (G6.C.T2).

Rastreia status de assinatura de TODOS os DPAs do projeto Cartorio.
Detecta DPAs vencidos, expirados em <90 dias, ou pendentes Gustavo.
Exit code 1 se algum DPA nao assinado que deveria estar.

Uso:
    python3 scripts/dpa_sign_flow.py                        # status todos
    python3 scripts/dpa_sign_flow.py --dpa MiniMax          # 1 DPA especifico
    python3 scripts/dpa_sign_flow.py --report docs/DPA_FLOW.md

Exit codes:
    0 = todos DPAs ativos OK
    1 = DPA pendente assinatura ou expirado
    2 = erro pre-requisito

Ref: docs/lgpd/DPA_INDEX.md, docs/lgpd/dpa_*_template.md.
Modified by Gustavo Almeida + cartorio-lgpd — G6 wave 7.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

DPA_DIR = Path("docs/lgpd")
DPA_INDEX = DPA_DIR / "DPA_INDEX.md"


@dataclass
class DPAStatus:
    name: str
    template_path: Path
    status: str  # signed, template, pending_gustavo, pending_provider, expired, missing
    signed_date: datetime | None = None
    renewal_due: datetime | None = None
    days_to_renewal: int | None = None
    notes: str = ""


# Cadastro de DPAs conhecido (status manual, atualizado em DPA_INDEX.md)
KNOWN_DPAS: dict[str, dict] = {
    "MiniMax": {
        "template": "dpa_minimax_template.md",
        "status": "pending_gustavo",
        "signed_date": None,
        "renewal_due": "2027-01-01",
        "notes": "LGPD-015. Pendente Gustavo assinar (Mavis reune com MiniMax Corp)",
    },
    "opencode-go": {
        "template": "dpa_opencode_go_template.md",
        "status": "signed",
        "signed_date": "2026-01-15",
        "renewal_due": "2027-01-15",
        "notes": "LGPD-008. Assinado Gustavo + opencode-go Inc.",
    },
    "DeepSeek": {
        "template": "dpa_deepseek_template.md",
        "status": "signed",
        "signed_date": "2026-02-20",
        "renewal_due": "2027-02-20",
        "notes": "LGPD-014. Assinado via DocuSign.",
    },
    "Cloudflare": {
        "template": "dpa_cloudflare_template.md",
        "status": "signed",
        "signed_date": "2026-01-10",
        "renewal_due": "2027-01-10",
        "notes": "Cloudflare DPA publico ja vigente.",
    },
    "Hostinger": {
        "template": "dpa_hostinger_template.md",
        "status": "signed",
        "signed_date": "2026-01-05",
        "renewal_due": "2027-01-05",
        "notes": "Contrato master Hostinger + addendum DPA.",
    },
    "mimo": {
        "template": None,
        "status": "pending_provider",
        "signed_date": None,
        "renewal_due": None,
        "notes": "mimo Corp sem DPA publico. Bloqueado ate assinar.",
    },
    "mistral-free": {
        "template": None,
        "status": "pending_provider",
        "signed_date": None,
        "renewal_due": None,
        "notes": "Mistral.ai DPA tier free limitado. Bloqueado.",
    },
    "openrouter-free": {
        "template": None,
        "status": "pending_provider",
        "signed_date": None,
        "renewal_due": None,
        "notes": "OpenRouter free tier. Bloqueado.",
    },
    "gemini-free": {
        "template": None,
        "status": "pending_provider",
        "signed_date": None,
        "renewal_due": None,
        "notes": "Gemini free tier. Bloqueado.",
    },
}


def parse_dpa_status(name: str) -> DPAStatus:
    """Parse DPA status do cadastro."""
    cfg = KNOWN_DPAS.get(name, {})
    template_path = DPA_DIR / cfg["template"] if cfg.get("template") else Path("(no template)")
    signed_date = None
    if cfg.get("signed_date"):
        signed_date = datetime.fromisoformat(cfg["signed_date"]).replace(tzinfo=timezone.utc)
    renewal_due = None
    days_to_renewal = None
    if cfg.get("renewal_due"):
        renewal_due = datetime.fromisoformat(cfg["renewal_due"]).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_to_renewal = (renewal_due - now).days
    return DPAStatus(
        name=name,
        template_path=template_path,
        status=cfg.get("status", "missing"),
        signed_date=signed_date,
        renewal_due=renewal_due,
        days_to_renewal=days_to_renewal,
        notes=cfg.get("notes", ""),
    )


def render_markdown(DPAs: list[DPAStatus]) -> str:
    md: list[str] = []
    md.append("# DPA Signing Flow Tracker")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append("")

    # Resumo
    by_status: dict[str, int] = {}
    for d in DPAs:
        by_status[d.status] = by_status.get(d.status, 0) + 1
    md.append("## Resumo")
    md.append("")
    md.append("| Status | Count |")
    md.append("|---|---|")
    for s, c in sorted(by_status.items()):
        md.append(f"| {s} | {c} |")
    md.append("")

    # Tabela
    md.append("## DPA Matrix")
    md.append("")
    md.append("| DPA | Status | Assinado | Renewal | Dias | Notes |")
    md.append("|---|---|---|---|---|---|")
    for d in sorted(DPAs, key=lambda x: x.days_to_renewal if x.days_to_renewal is not None else 99999):
        signed = d.signed_date.date() if d.signed_date else "-"
        renewal = d.renewal_due.date() if d.renewal_due else "-"
        days = f"{d.days_to_renewal}d" if d.days_to_renewal is not None else "-"
        status_emoji = {
            "signed": "✅",
            "template": "📝",
            "pending_gustavo": "⏳",
            "pending_provider": "🚧",
            "expired": "❌",
            "missing": "❌",
        }.get(d.status, "?")
        notes = d.notes.replace("|", "\\|")[:60]
        md.append(f"| {d.name} | {status_emoji} {d.status} | {signed} | {renewal} | {days} | {notes} |")
    md.append("")

    # Alertas
    alerts: list[str] = []
    for d in DPAs:
        if d.status == "expired":
            alerts.append(f"❌ **{d.name}**: EXPIRADO em {d.renewal_due.date() if d.renewal_due else '?'}")
        elif d.status == "pending_gustavo":
            alerts.append(f"⏳ **{d.name}**: Pendente Gustavo assinar")
        elif d.status == "pending_provider":
            alerts.append(f"🚧 **{d.name}**: Aguardando provider (mimo/mistral/openrouter/gemini)")
        elif d.status == "signed" and d.days_to_renewal is not None and d.days_to_renewal < 90:
            alerts.append(f"⚠️ **{d.name}**: Renewal em {d.days_to_renewal} dias (renovar antes)")
    if alerts:
        md.append("## Alertas")
        md.append("")
        for a in alerts:
            md.append(f"- {a}")
        md.append("")
    else:
        md.append("## [WORK] Todos DPAs ativos OK")
        md.append("")

    md.append("---")
    md.append("")
    md.append("**Modified by Gustavo Almeida + cartorio-lgpd — G6 wave 7 (auto-gerado)**")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="DPA signing flow tracker")
    parser.add_argument("--dpa", help="mostrar apenas 1 DPA")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    DPAs = [parse_dpa_status(name) for name in KNOWN_DPAS]

    if args.dpa:
        DPAs = [d for d in DPAs if d.name.lower() == args.dpa.lower()]
        if not DPAs:
            print(f"[ERROR] DPA '{args.dpa}' nao encontrado", file=sys.stderr)
            return 2

    print(f"DPAs: {len(DPAs)}")
    blocking = 0
    for d in DPAs:
        emoji = {
            "signed": "✅",
            "template": "📝",
            "pending_gustavo": "⏳",
            "pending_provider": "🚧",
            "expired": "❌",
            "missing": "❌",
        }.get(d.status, "?")
        days = f"{d.days_to_renewal}d" if d.days_to_renewal is not None else "-"
        print(f"  {emoji} {d.name:18} {d.status:20} renewal={days}")
        if d.status in ("expired", "pending_gustavo"):
            blocking += 1
    if blocking:
        print(f"[HOLD] {blocking} DPA(s) bloqueando uso em prod")
    else:
        print("[WORK] Todos DPAs ativos OK")

    if args.report:
        args.report.write_text(render_markdown(DPAs))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())