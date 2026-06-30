"""apply_n8n_timeouts.py - força timeout=5000ms em todos HTTP nodes N8N.

SQUAD B B08 - timeout 5s em todos HTTP requests.

Le todos os *.json em infra/n8n-workflows/ e ajusta o campo
options.timeout para 5000ms em qualquer node do tipo:
- n8n-nodes-base.httpRequest (HTTP Request v1)
- n8n-nodes-base.httpRequestV2 (HTTP Request v2 novo)
- @n8n/n8n-nodes-base.httpRequest (mesmo, formato package)
- n8n-nodes-base.telegram (telegram tbm faz HTTP)

Idempotente: se ja eh 5000, nao muda.
DRY-RUN: mostra diff sem salvar.

Uso:
  cd backend
  uv run python scripts/apply_n8n_timeouts.py --dry-run
  uv run python scripts/apply_n8n_timeouts.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HTTP_NODE_TYPES = (
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.httpRequestV2",
    "@n8n/n8n-nodes-base.httpRequest",
    "n8n-nodes-base.telegram",
    "n8n-nodes-base.chatwoot",
    "n8n-nodes-base.evolutionApi",
)
DEFAULT_TIMEOUT_MS = 5000


def process_workflow(path: Path, dry_run: bool) -> tuple[int, int]:
    """Retorna (changed_count, total_http_nodes) para este WF."""
    try:
        wf = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  SKIP {path.name}: parse error {e}")
        return 0, 0

    nodes = wf.get("nodes", [])
    if not isinstance(nodes, list):
        return 0, 0

    changed = 0
    total = 0
    for node in nodes:
        ntype = node.get("type", "")
        if not any(t in ntype for t in HTTP_NODE_TYPES):
            continue
        total += 1
        opts = node.setdefault("options", {})
        cur = opts.get("timeout")
        if cur == DEFAULT_TIMEOUT_MS:
            continue
        opts["timeout"] = DEFAULT_TIMEOUT_MS
        node["options"] = opts
        changed += 1

    if changed > 0 and not dry_run:
        path.write_text(json.dumps(wf, indent=2, ensure_ascii=False), encoding="utf-8")

    return changed, total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--workflows-dir",
        default=str(Path(__file__).parent.parent.parent / "infra/n8n-workflows"),
    )
    args = parser.parse_args()

    wf_dir = Path(args.workflows_dir)
    if not wf_dir.exists():
        print(f"ERRO: {wf_dir} nao existe", file=sys.stderr)
        return 1

    json_files = sorted(wf_dir.glob("*.json"))
    if not json_files:
        print(f"Nenhum .json em {wf_dir}")
        return 0

    print(f"Processando {len(json_files)} workflows em {wf_dir}")
    if args.dry_run:
        print("DRY-RUN: nada sera salvo\n")

    total_changed = 0
    total_nodes = 0
    for wf_path in json_files:
        changed, total = process_workflow(wf_path, args.dry_run)
        marker = "*" if changed > 0 else " "
        print(f"  {marker} {wf_path.name:50s}  {total:3d} HTTP nodes  ({changed} alterados)")
        total_changed += changed
        total_nodes += total

    print(f"\nTotal: {total_nodes} HTTP nodes em {len(json_files)} WFs")
    print(f"Alterados: {total_changed}")
    if args.dry_run:
        print("(DRY-RUN - nada foi salvo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
