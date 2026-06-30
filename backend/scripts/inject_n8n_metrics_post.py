"""inject_n8n_metrics_post.py - injeta POST /api/v1/metrics/n8n no FIM de cada WF.

SQUAD B B10 - metrics Prometheus por WF (3 metrics: count, duration, error_rate).

Para cada WF, adiciona 1 HTTP Request node no FIM:
  POST https://api.2notasudi.com.br/api/v1/metrics/n8n
  Headers: { X-API-Key: <from env>, Content-Type: application/json }
  Body: {wf_name, status: $execution.success ? 'success' : 'error',
         duration_seconds: $now.diff($json.wf_started_at, 'seconds'),
         correlation_id: $json.correlation_id}

Idempotente: checa se ja tem 'Report Metrics N8N' (skip).
DRY-RUN: mostra diff sem salvar.

Uso:
  cd backend
  uv run python scripts/inject_n8n_metrics_post.py --dry-run
  uv run python scripts/inject_n8n_metrics_post.py
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

METRICS_NODE_NAME = "Report Metrics N8N"
DEFAULT_API_URL = "https://api.2notasudi.com.br/api/v1/metrics/n8n"
API_KEY_ENV_NAME = "CARTORIO_API_KEY"  # N8N credential type "Header Auth" env var


def build_metrics_node(api_url: str) -> dict:
    """HTTP Request node que POSTa metricas do WF ao backend."""
    return {
        "id": uuid.uuid4().hex[:12],
        "name": METRICS_NODE_NAME,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1400, 200],
        "parameters": {
            "method": "POST",
            "url": api_url,
            "sendHeaders": True,
            "headerParameters": {
                "parameters": [
                    {"name": "Content-Type", "value": "application/json"},
                    {"name": "X-API-Key", "value": f"={{{{ $env.{API_KEY_ENV_NAME} }}}}"},
                ]
            },
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": (
                "={"
                '"source": "n8n", '
                '"wf_name": $workflow.name, '
                '"wf_id": $workflow.id, '
                '"execution_id": $execution.id, '
                "\"correlation_id\": $json.correlation_id ?? $workflow.id + ':' + $execution.id, "
                "\"status\": $execution.success ? 'success' : 'error', "
                "\"duration_seconds\": $now.diff($json.wf_started_at, 'seconds'), "
                '"counters": {'
                '  "n8n_wf_executions_total": 1'
                "}, "
                '"gauges": {'
                '  "n8n_wf_error_rate": $execution.success ? 0.0 : 1.0'
                "}"
                "}"
            ),
            "options": {
                "timeout": 5000,
                "retry": {"maxTries": 3, "waitBetweenTries": 1000},
            },
        },
    }


def process_workflow(path: Path, dry_run: bool, api_url: str) -> int:
    try:
        wf = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  SKIP {path.name}: parse error {e}")
        return 0

    nodes = wf.get("nodes", [])
    if not isinstance(nodes, list):
        return 0

    if any(n.get("name") == METRICS_NODE_NAME for n in nodes):
        return 0  # ja instrumentado

    new_node = build_metrics_node(api_url)
    # Posiciona entre 'Log Final Correlation' (B09) e o fim
    insert_idx = len(nodes)
    for i, n in enumerate(nodes):
        if n.get("name") == "Log Final Correlation":
            insert_idx = i + 1
            break
    nodes.insert(insert_idx, new_node)

    if not dry_run:
        wf["nodes"] = nodes
        path.write_text(json.dumps(wf, indent=2, ensure_ascii=False), encoding="utf-8")

    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--workflows-dir",
        default=str(Path(__file__).parent.parent.parent / "infra/n8n-workflows"),
    )
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    args = parser.parse_args()

    wf_dir = Path(args.workflows_dir)
    if not wf_dir.exists():
        print(f"ERRO: {wf_dir} nao existe", file=sys.stderr)
        return 1

    json_files = sorted(wf_dir.glob("*.json"))
    if not json_files:
        return 0

    print(f"Processando {len(json_files)} workflows em {wf_dir}")
    print(f"API URL: {args.api_url}")
    if args.dry_run:
        print("DRY-RUN: nada sera salvo\n")

    total_added = 0
    for wf_path in json_files:
        added = process_workflow(wf_path, args.dry_run, args.api_url)
        marker = "*" if added > 0 else " "
        print(f"  {marker} {wf_path.name:50s}  {added} node adicionado")
        total_added += added

    print(f"\nTotal adicionado: {total_added} metric nodes em {len(json_files)} WFs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
