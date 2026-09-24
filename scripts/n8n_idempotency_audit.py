"""N8N Idempotency Audit (G6.B.T5).

Identifica workflows N8N que tem webhooks SEM protecao de idempotencia.
Padrao obrigatorio (lesson 22 super-prompt): cada webhook deve usar Redis SETNX
com TTL 24h para evitar duplicacao em retries (N8N runner faz ate 5 retries).

Detecta por:
- Presenca de nos Redis/SETNX nos nodes
- Comentarios markdown com "idempot" / "setnx"

Uso:
    python3 scripts/n8n_idempotency_audit.py
    python3 scripts/n8n_idempotency_audit.py --report docs/N8N_IDEMPOTENCY_AUDIT.md

Exit codes:
    0 = todos webhooks tem idempotencia
    1 = webhook(s) SEM idempotencia (risco duplicacao em retry)

Modified by Gustavo Almeida + cartorio-n8n — G6 wave 12.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WF_DIR = Path("infra/n8n-workflows")

IDEMPOTENCY_MARKERS = [
    "SETNX",
    "setnx",
    "redis.SETNX",
    "redis.setnx",
    "idempotencia",
    "idempotent",
    "idempotency",
    "deduplica",
    "deduplication",
    "webhook_id",
    "x-webhook-id",
]

REDIS_NODE_TYPES = {
    "n8n-nodes-base.redis",
    "n8n-nodes-base.redisCommand",
}


def audit_workflow(wf_path: Path) -> dict:
    """Audita 1 workflow. Retorna dict com findings."""
    data = json.loads(wf_path.read_text())
    name = data.get("name", wf_path.stem)

    # Webhooks
    webhooks: list[str] = []
    for node in data.get("nodes", []):
        if node.get("type") == "n8n-nodes-base.webhook":
            path = node.get("parameters", {}).get("path", "?")
            webhooks.append(path)

    if not webhooks:
        return {
            "file": wf_path.name,
            "name": name,
            "webhooks": [],
            "has_redis": False,
            "has_idempotency_marker": False,
            "missing": [],
        }

    # Idempotency check
    nodes_json = json.dumps(data.get("nodes", []))
    has_redis = any(
        node.get("type") in REDIS_NODE_TYPES for node in data.get("nodes", [])
    )
    has_idempotency_marker = any(
        marker.lower() in nodes_json.lower() for marker in IDEMPOTENCY_MARKERS
    )

    missing = []
    if not (has_redis or has_idempotency_marker):
        missing = webhooks

    return {
        "file": wf_path.name,
        "name": name,
        "webhooks": webhooks,
        "has_redis": has_redis,
        "has_idempotency_marker": has_idempotency_marker,
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="N8N idempotency audit")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    wfs = sorted(WF_DIR.glob("*.json"))
    findings = [audit_workflow(w) for w in wfs]

    missing_total = sum(len(f["missing"]) for f in findings)
    wfs_with_webhooks = [f for f in findings if f["webhooks"]]

    print(f"Total workflows: {len(findings)}")
    print(f"WFs com webhook: {len(wfs_with_webhooks)}")
    print(f"Webhooks SEM idempotencia: {missing_total}")

    if missing_total:
        print("[HOLD] Webhooks SEM protecao SETNX (risco duplicacao em retry):")
        for f in findings:
            if f["missing"]:
                print(f"  - {f['file']}: {f['missing']}")
        print()
        print("Fix: adicionar Redis SETNX node antes do processing com TTL 24h")
    else:
        print("[WORK] Todos webhooks tem protecao de idempotencia")

    if args.report:
        md: list[str] = []
        md.append("# N8N Idempotency Audit")
        md.append("")
        md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
        md.append(f"**Total workflows**: {len(findings)}")
        md.append(f"**WFs com webhook**: {len(wfs_with_webhooks)}")
        md.append(f"**Webhooks SEM idempotencia**: {missing_total}")
        md.append("")
        if missing_total:
            md.append(f"## [HOLD] {missing_total} webhook(s) sem protecao SETNX")
        else:
            md.append("## [WORK] Todos webhooks protegidos")
        md.append("")
        md.append("## Detalhes por WF")
        md.append("")
        md.append("| WF | name | Webhooks | Redis? | Marker? | Missing |")
        md.append("|---|---|---|---|---|---|")
        for f in findings:
            if not f["webhooks"]:
                continue
            redis_icon = "✅" if f["has_redis"] else "❌"
            marker_icon = "✅" if f["has_idempotency_marker"] else "❌"
            webhooks_str = ", ".join(f["webhooks"][:3])
            if len(f["webhooks"]) > 3:
                webhooks_str += f" (+{len(f['webhooks']) - 3})"
            missing_str = ", ".join(f["missing"]) if f["missing"] else "nenhum"
            md.append(
                f"| `{f['file']}` | {f['name']} | {webhooks_str} | {redis_icon} | {marker_icon} | {missing_str} |"
            )
        md.append("")
        md.append("## Padrao obrigatorio (lesson 22)")
        md.append("")
        md.append("```javascript")
        md.append("// Antes do processing principal:")
        md.append(
            "const webhookId = $input.item.json.headers['x-webhook-id'] || $input.item.json.body.id;"
        )
        md.append("const dedupKey = `webhook:${webhookId}`;")
        md.append("const isNew = await redis.set(dedupKey, '1', 'EX', 86400, 'NX');")
        md.append("if (!isNew) {")
        md.append("  throw new Error('DUPLICATE_WEBHOOK');")
        md.append("}")
        md.append("```")
        md.append("")
        md.append("---")
        md.append("")
        md.append(
            "**Modified by Gustavo Almeida + cartorio-n8n — G6 wave 12 (auto-gerado)**"
        )
        args.report.write_text("\n".join(md))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 1 if missing_total else 0


if __name__ == "__main__":
    sys.exit(main())
