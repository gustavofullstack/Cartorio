"""Auto-gera infra/n8n-workflows/INDEX.md a partir dos JSON exports.

Uso:
    cd /Users/gustavoalmeida/projetos/Cartorio
    python3 scripts/n8n_index_gen.py

Output:
    infra/n8n-workflows/INDEX.md (registro markdown de todos WFs)

Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 2.
"""
from __future__ import annotations

import json
from pathlib import Path

WF_DIR = Path("infra/n8n-workflows")
OUT_FILE = WF_DIR / "INDEX.md"

# Mapeamento WF file prefix -> squad owner
SQUAD_MAP = {
    "00-error-handler": "B (N8N infra)",
    "01-consulta-emolumento": "B (consulta)",
    "02-criar-protocolo": "B (protocolo)",
    "03-handoff-human": "B (handoff)",
    "04-boas-vindas": "B+C (LGPD consent)",
    "04-consulta-protocolo": "B (consulta)",
    "05-agendamento": "B (agendamento)",
    "06-2-via-protocolo": "B (2ª via)",
    "07-pesquisa-satisfacao": "B (NPS)",
    "08-audit-verify-diario": "A (audit)",
    "10-faq-bot": "B (FAQ)",
    "11-monitor-cartorio": "A (monitor)",
    "12-chatbot-llm-end-to-end": "E (LLM)",
    "14-opencode-go-fallback": "E (LLM)",
    "16-prospeccao-enrichment": "B (prospecção)",
    "18-prospeccao-followup": "B (prospecção)",
    "21-backup-status": "A (backup)",
    "22-audit-verify": "A (audit)",
    "22-mcp-server": "A (MCP)",
    "23-cron-stale-detector": "A (cron)",
    "23-lgpd-esqueci": "D (LGPD)",
    "24-daily-cleanup": "A (cron)",
    "24-retencao-diaria": "D (retenção)",
    "25-metrics-collector": "A (observability)",
    "25-protocolo-concluido-pdf": "B (PDF)",
    "26-alerta-critico": "A (alertas)",
    "27-welcome-first-time": "B+C (onboarding)",
    "28-audit-snapshot": "D (LGPD audit)",
    "29-rate-limit-reset": "A (rate limit)",
    "30-health-deep-check": "A (health)",
    "31-telegram-listener": "B (Telegram)",
}


def main() -> None:
    wfs = sorted(WF_DIR.glob("*.json"))
    entries: list[dict] = []
    for wf in wfs:
        try:
            data = json.loads(wf.read_text())
            nodes = data.get("nodes", [])
            triggers = [
                n.get("type", "").split(".")[-1]
                for n in nodes
                if "trigger" in str(n.get("type", "")).lower()
                or "webhook" in str(n.get("type", "")).lower()
            ]
            entries.append({
                "file": wf.name,
                "name": data.get("name", wf.stem),
                "active": "✅" if data.get("active") else "❌",
                "n_nodes": len(nodes),
                "triggers": triggers[:3],
                "first_nodes": [n.get("name", "?") for n in nodes[:5]],
            })
        except Exception as e:
            entries.append({"file": wf.name, "name": wf.stem, "error": str(e)[:60]})

    total_active = sum(1 for e in entries if e.get("active") == "✅")
    total_nodes = sum(e.get("n_nodes", 0) for e in entries)
    trigger_counts: dict[str, int] = {}
    for e in entries:
        for t in e.get("triggers", []):
            trigger_counts[t] = trigger_counts.get(t, 0) + 1

    md: list[str] = []
    md.append("# N8N Workflows Registry — INDEX")
    md.append("")
    md.append("**Auto-gerado**: rodar `python3 scripts/n8n_index_gen.py`.")
    md.append(f"**Total WFs**: {len(entries)} | **Ativos**: {total_active} | **Total nodes**: {total_nodes}")
    md.append("")
    md.append("## Tabela de workflows")
    md.append("")
    md.append("| # | Arquivo | Nome | Ativo | Nodes | Triggers | Primeiros 5 nodes |")
    md.append("|---|---|---|---|---|---|---|")
    for i, e in enumerate(entries, 1):
        if "error" in e:
            md.append(f"| {i} | `{e['file']}` | {e['name']} | ⚠️ | - | - | `{e['error']}` |")
            continue
        triggers_str = ", ".join(e["triggers"]) if e["triggers"] else "manual"
        first_nodes = ", ".join(f"`{n}`" for n in e["first_nodes"])
        md.append(f"| {i} | `{e['file']}` | {e['name']} | {e['active']} | {e['n_nodes']} | {triggers_str} | {first_nodes} |")
    md.append("")
    md.append("## Por trigger")
    md.append("")
    for t, c in sorted(trigger_counts.items(), key=lambda x: -x[1]):
        md.append(f"- **{t}**: {c} workflow(s)")
    md.append("")
    md.append("## Por squad")
    md.append("")
    md.append("| Squad | WFs | Detalhes |")
    md.append("|---|---|---|")
    squads: dict[str, list[str]] = {}
    for fn, squad in SQUAD_MAP.items():
        squads.setdefault(squad, []).append(fn)
    for squad, wfs in sorted(squads.items()):
        md.append(f"| **{squad}** | {len(wfs)} | {', '.join(wfs)} |")
    md.append("")
    md.append(f"## Stats finais")
    md.append(f"- Total: {len(entries)} workflows")
    md.append(f"- Ativos: {total_active} ({100 * total_active // len(entries)}%)")
    md.append(f"- Total nodes: {total_nodes}")
    if trigger_counts:
        top = max(trigger_counts, key=trigger_counts.get)
        md.append(f"- Trigger mais comum: {top} ({max(trigger_counts.values())} WFs)")
    md.append("")
    md.append("---")
    md.append("")
    md.append("**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 2 (auto-gerado)**")

    OUT_FILE.write_text("\n".join(md))
    print(f"OK {OUT_FILE} ({len(entries)} WFs, {total_active} ativos)")


if __name__ == "__main__":
    main()
