"""N8N Idempotency Injector (G6.B.T6).

Injeta automaticamente nos de Redis SETNX nos 20 WFs SEM idempotencia
detectados pelo n8n_idempotency_audit.py.

Adiciona APOS o Webhook node (e ANTES de qualquer processing):
1. Redis SETNX com TTL 86400s (24h) + key webhook:${webhook_id}
2. Code node com JS para dedup (lesson 22)
3. Branch para "if duplicate, throw DUPLICATE_WEBHOOK"

Uso:
    python3 scripts/n8n_idempotency_injector.py               # dry-run (mostra)
    python3 scripts/n8n_idempotency_injector.py --apply       # aplica alteracoes
    python3 scripts/n8n_idempotency_injector.py --report doc.md

Exit codes:
    0 = nada a injetar OU aplicado com sucesso
    1 = WFs sem idempotencia detectados (mostra o que precisa)
    2 = erro pre-requisito

Modified by Gustavo Almeida + cartorio-n8n — G6 wave 13.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WF_DIR = Path("infra/n8n-workflows")
AUDIT_SCRIPT = Path("scripts/n8n_idempotency_audit.py")

IDEMPOTENCY_MARKERS = ["SETNX", "setnx", "redis.SETNX", "idempotencia", "idempotent"]


def has_idempotency(wf_path: Path) -> bool:
    """Detecta se WF ja tem idempotencia."""
    data = json.loads(wf_path.read_text())
    text = json.dumps(data.get("nodes", []))
    return any(marker.lower() in text.lower() for marker in IDEMPOTENCY_MARKERS)


def get_webhook_node(wf_path: Path) -> dict | None:
    """Retorna o primeiro webhook node do WF."""
    data = json.loads(wf_path.read_text())
    for node in data.get("nodes", []):
        if node.get("type") == "n8n-nodes-base.webhook":
            return node
    return None


def build_dedup_code_node(webhook_path: str) -> dict:
    """Constroi Code node com JS para dedup Redis SETNX."""
    return {
        "parameters": {
            "jsCode": (
                "// Idempotency via Redis SETNX TTL 24h (lesson 22 super-prompt).\n"
                "const webhookId = $input.item.json.headers?.['x-webhook-id']\n"
                "  || $input.item.json.body?.id\n"
                "  || $input.item.json.body?.messageId\n"
                "  || crypto.randomUUID();\n"
                "\n"
                "const dedupKey = `webhook:${webhookPath}:${webhookId}`;\n"
                "\n"
                "// SETNX retorna 'OK' se inserido, null se ja existe\n"
                "const result = await this.helpers.redis.set(dedupKey, '1', 'EX', 86400, 'NX');\n"
                "\n"
                "if (!result) {\n"
                "  throw new Error('DUPLICATE_WEBHOOK');\n"
                "}\n"
                "\n"
                "return [{ json: { ...$input.item.json, _dedup_key: dedupKey } }];\n"
            ).replace("${webhookPath}", webhook_path),
        },
        "name": "Dedup Webhook (SETNX)",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [0, 0],  # Sera ajustado pelo injector
        "id": "dedup-webhook-idempotency",
    }


def build_redis_node() -> dict:
    """Constroi Redis SETNX node (configuracao centralizada)."""
    return {
        "parameters": {
            "operation": "set",
            "key": "={{$json._dedup_key}}",
            "value": "1",
            "expire": True,
            "ttl": 86400,
            "options": {"NX": True},
        },
        "name": "Redis SETNX 24h",
        "type": "n8n-nodes-base.redis",
        "typeVersion": 1,
        "position": [0, 0],
        "id": "redis-setnx-24h",
    }


def inject_idempotency(wf_path: Path) -> bool:
    """Injeta Redis SETNX apos webhook. Retorna True se modificou."""
    if has_idempotency(wf_path):
        return False

    data = json.loads(wf_path.read_text())
    nodes = data.get("nodes", [])
    connections = data.get("connections", {}) or {}

    webhook = get_webhook_node(wf_path)
    if webhook is None:
        return False
    webhook_path = webhook.get("parameters", {}).get("path", "unknown")

    # Posicionar webhook + dedup code + redis
    base_x = webhook.get("position", [0, 0])[0]
    base_y = webhook.get("position", [0, 0])[1] + 100

    code_node = build_dedup_code_node(webhook_path)
    code_node["position"] = [base_x + 200, base_y]
    redis_node = build_redis_node()
    redis_node["position"] = [base_x + 400, base_y]

    # Inserir apos webhook
    new_nodes: list[dict] = []
    inserted = False
    for node in nodes:
        new_nodes.append(node)
        if node.get("id") == webhook.get("id"):
            new_nodes.append(code_node)
            new_nodes.append(redis_node)
            inserted = True
    if not inserted:
        # Fallback: append no fim
        new_nodes.append(code_node)
        new_nodes.append(redis_node)

    # Adicionar connections: webhook -> code -> redis
    webhook_id = webhook.get("id", "webhook")
    code_id = code_node["id"]
    redis_id = redis_node["id"]
    connections[webhook_id] = {
        "main": [[{"node": code_id, "type": "main", "index": 0}]],
    }
    connections[code_id] = {
        "main": [[{"node": redis_id, "type": "main", "index": 0}]],
    }

    data["nodes"] = new_nodes
    data["connections"] = connections
    wf_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="N8N idempotency injector")
    parser.add_argument(
        "--apply", action="store_true", help="aplicar injecao (sem isso, dry-run)"
    )
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    if not WF_DIR.exists():
        print(f"[ERROR] {WF_DIR} nao existe", file=sys.stderr)
        return 2

    wfs = sorted(WF_DIR.glob("*.json"))
    missing: list[Path] = [
        w for w in wfs if not has_idempotency(w) and get_webhook_node(w)
    ]
    applied: list[Path] = []

    print(f"Total WFs: {len(wfs)}")
    print(f"Sem idempotencia: {len(missing)}")

    if not missing:
        print("[WORK] Todos WFs com webhook ja tem idempotencia")
        return 0

    if not args.apply:
        print("[HOLD] DRY-RUN (rode com --apply para injetar):")
        for w in missing:
            print(f"  - {w.name}")
        if args.report:
            md = ["# N8N Idempotency Injector - Dry Run\n"]
            md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
            md.append(f"**Total sem idempotencia**: {len(missing)}")
            md.append("\n## WFs pendentes\n")
            for w in missing:
                md.append(f"- `{w.name}`")
            md.append("\n## Para aplicar:\n")
            md.append(
                "```bash\npython3 scripts/n8n_idempotency_injector.py --apply\n```\n"
            )
            args.report.write_text("\n".join(md))
            print(f"  Report: {args.report}", file=sys.stderr)
        return 1

    for w in missing:
        try:
            if inject_idempotency(w):
                applied.append(w)
                print(f"  [INJECTED] {w.name}")
            else:
                print(f"  [SKIP] {w.name} (sem webhook?)")
        except Exception as exc:
            print(f"  [ERROR] {w.name}: {type(exc).__name__}: {exc}", file=sys.stderr)

    print(f"\n{len(applied)}/{len(missing)} WFs injetados com idempotencia")
    print("[WORK] Re-validar com scripts/n8n_idempotency_audit.py")

    if args.report:
        md = ["# N8N Idempotency Injector - Report\n"]
        md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
        md.append(f"**Aplicado**: {len(applied)} WFs")
        md.append("\n## WFs injetados\n")
        for w in applied:
            md.append(f"- `{w.name}`")
        md.append("\n## Padrao aplicado\n")
        md.append("1. Webhook -> Code (Dedup JS) -> Redis SETNX 24h -> processing")
        md.append("2. Dedup key: `webhook:{path}:{webhook_id}`")
        md.append("3. Throw `DUPLICATE_WEBHOOK` se ja existir")
        md.append("\n---\n")
        md.append(
            "**Modified by Gustavo Almeida + cartorio-n8n — G6 wave 13 (auto-gerado)**"
        )
        args.report.write_text("\n".join(md))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
