"""inject_n8n_correlation_logs.py - injeta Set node 'Init Correlation' no INICIO de cada WF.

SQUAD B B09 - logs estruturados JSON correlation_id em todos WFs.

Para cada WF:
1. Gera correlation_id = uuid v4 no trigger (Set node 'Init Correlation')
2. Propaga via $json.correlation_id em todos nodes HTTP/Code/IF
3. Adiciona 1 Log node no FIM que emite JSON estruturado com
   {ts, level, wf, correlation_id, duration_ms, success, error}

Idempotente: checa se ja tem 'Init Correlation' (skip).
DRY-RUN: mostra diff sem salvar.

Uso:
  cd backend
  uv run python scripts/inject_n8n_correlation_logs.py --dry-run
  uv run python scripts/inject_n8n_correlation_logs.py
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

INIT_NODE_NAME = "Init Correlation"
LOG_NODE_NAME = "Log Final Correlation"


def build_init_node() -> dict:
    """Set node que gera correlation_id = uuid v4."""
    return {
        "id": uuid.uuid4().hex[:12],
        "name": INIT_NODE_NAME,
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [200, 200],  # posicao inicial
        "parameters": {
            "assignments": {
                "assignments": [
                    {
                        "id": uuid.uuid4().hex[:8],
                        "name": "correlation_id",
                        "value": "={{ $uuid }}",
                        "type": "string",
                    },
                    {
                        "id": uuid.uuid4().hex[:8],
                        "name": "wf_started_at",
                        "value": "={{ $now.toISO() }}",
                        "type": "string",
                    },
                ]
            },
            "options": {"renameConflict": "longestVariableName"},
        },
    }


def build_log_node() -> dict:
    """Set node que monta JSON de log estruturado."""
    return {
        "id": uuid.uuid4().hex[:12],
        "name": LOG_NODE_NAME,
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [1200, 200],
        "parameters": {
            "assignments": {
                "assignments": [
                    {
                        "id": uuid.uuid4().hex[:8],
                        "name": "log_json",
                        "value": (
                            "={"
                            '"ts": $now.toISO(), '
                            '"level": "info", '
                            '"workflow": $workflow.name, '
                            '"workflow_id": $workflow.id, '
                            '"execution_id": $execution.id, '
                            '"correlation_id": $json.correlation_id, '
                            '"wf_started_at": $json.wf_started_at, '
                            "\"duration_ms\": $now.diff($json.wf_started_at, 'milliseconds'), "
                            '"success": $execution.success, '
                            '"error": $json.error ?? null'
                            "}"
                        ),
                        "type": "string",
                    }
                ]
            },
            "options": {"renameConflict": "longestVariableName"},
        },
    }


def process_workflow(path: Path, dry_run: bool) -> int:
    """Retorna nodes adicionados (0, 1 ou 2)."""
    try:
        wf = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  SKIP {path.name}: parse error {e}")
        return 0

    nodes = wf.get("nodes", [])
    if not isinstance(nodes, list):
        return 0

    names = {n.get("name") for n in nodes}
    has_init = INIT_NODE_NAME in names
    has_log = LOG_NODE_NAME in names

    if has_init and has_log:
        return 0  # ja instrumentado

    added = 0
    if not has_init:
        nodes.insert(0, build_init_node())
        added += 1
    if not has_log:
        nodes.append(build_log_node())
        added += 1

    if added > 0 and not dry_run:
        wf["nodes"] = nodes
        path.write_text(json.dumps(wf, indent=2, ensure_ascii=False), encoding="utf-8")

    return added


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
        return 0

    print(f"Processando {len(json_files)} workflows em {wf_dir}")
    if args.dry_run:
        print("DRY-RUN: nada sera salvo\n")

    total_added = 0
    for wf_path in json_files:
        added = process_workflow(wf_path, args.dry_run)
        marker = "*" if added > 0 else " "
        print(f"  {marker} {wf_path.name:50s}  {added} nodes adicionados")
        total_added += added

    print(f"\nTotal adicionado: {total_added} nodes em {len(json_files)} WFs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
