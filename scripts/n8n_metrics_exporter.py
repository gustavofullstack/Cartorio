"""N8N Metrics Exporter for Prometheus (G6.B.T8).

Conecta no N8N API, busca ultimas execucoes de workflows, e expoe
metricas formato Prometheus textfile (para node_exporter) OU HTTP.

Metricas exportadas:
- n8n_workflow_execution_total{workflow, status}
- n8n_workflow_execution_duration_seconds{workflow} (histogram)
- n8n_workflow_active{workflow} (gauge)
- n8n_workflow_error_rate{workflow} (gauge)

Uso:
    python3 scripts/n8n_metrics_exporter.py --output /var/lib/node_exporter/textfile_collector/n8n.prom
    python3 scripts/n8n_metrics_exporter.py --http-port 9099

Exit codes:
    0 = OK
    1 = erro API N8N
    2 = erro pre-requisito

Modified by Gustavo Almeida + cartorio-n8n — G6 wave 19.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

DEFAULT_N8N_URL = "https://flow.2notasudi.com.br"
DEFAULT_TIMEOUT = 30.0
HISTOGRAM_BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)


def get_n8n_config() -> tuple[str, str | None]:
    """Retorna (base_url, api_key)."""
    return os.environ.get("N8N_BASE_URL", DEFAULT_N8N_URL), os.environ.get("N8N_API_KEY")


def fetch_workflows(base_url: str, api_key: str, timeout: float) -> list[dict]:
    """Lista todos workflows via API."""
    try:
        resp = httpx.get(
            f"{base_url}/api/v1/workflows",
            headers={"X-N8N-API-KEY": api_key},
            timeout=timeout,
        )
        if resp.status_code != 200:
            print(f"[ERROR] API N8N retornou {resp.status_code}", file=sys.stderr)
            return []
        return resp.json().get("data", [])
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return []


def fetch_executions(base_url: str, api_key: str, workflow_id: str, limit: int, timeout: float) -> list[dict]:
    """Busca ultimas N execucoes de um workflow."""
    try:
        resp = httpx.get(
            f"{base_url}/api/v1/executions",
            params={"workflowId": workflow_id, "limit": limit, "includeData": "false"},
            headers={"X-N8N-API-KEY": api_key},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("data", [])
    except Exception:
        return []


def compute_workflow_metrics(workflows: list[dict], executions: dict[str, list[dict]]) -> list[str]:
    """Calcula metricas em formato Prometheus."""
    lines: list[str] = []
    lines.append(f"# N8N metrics exported at {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    for wf in workflows:
        wf_id = wf.get("id", "?")
        wf_name = wf.get("name", wf_id)
        wf_active = 1 if wf.get("active") else 0
        lines.append(f'n8n_workflow_active{{workflow="{wf_name}"}} {wf_active}')

        execs = executions.get(wf_id, [])
        if not execs:
            lines.append(f'n8n_workflow_execution_total{{workflow="{wf_name}",status="success"}} 0')
            lines.append(f'n8n_workflow_execution_total{{workflow="{wf_name}",status="error"}} 0')
            lines.append(f'n8n_workflow_error_rate{{workflow="{wf_name}"}} 0')
            continue

        by_status: dict[str, int] = defaultdict(int)
        durations: list[float] = []
        for ex in execs:
            status = ex.get("finished") and (ex.get("status") or "unknown")
            # Normalizar: success/error/unknown
            if status == "success":
                by_status["success"] += 1
            elif status in ("error", "failed", "crashed"):
                by_status["error"] += 1
            else:
                by_status["unknown"] += 1
            # Duracao (startedAt -> stoppedAt em ms)
            started = ex.get("startedAt")
            stopped = ex.get("stoppedAt")
            if started and stopped:
                try:
                    d_ms = (
                        datetime.fromisoformat(stopped.replace("Z", "+00:00"))
                        - datetime.fromisoformat(started.replace("Z", "+00:00"))
                    ).total_seconds()
                    if d_ms >= 0:
                        durations.append(d_ms)
                except (ValueError, TypeError):
                    pass

        total = sum(by_status.values())
        success = by_status.get("success", 0)
        error = by_status.get("error", 0)
        error_rate = error / total if total > 0 else 0

        lines.append(f'n8n_workflow_execution_total{{workflow="{wf_name}",status="success"}} {success}')
        lines.append(f'n8n_workflow_execution_total{{workflow="{wf_name}",status="error"}} {error}')
        lines.append(f'n8n_workflow_error_rate{{workflow="{wf_name}"}} {error_rate:.4f}')

        # Histogram-like (cumulative buckets)
        if durations:
            sorted_d = sorted(durations)
            for bucket in HISTOGRAM_BUCKETS:
                count = sum(1 for d in sorted_d if d <= bucket)
                lines.append(f'n8n_workflow_execution_duration_seconds_bucket{{workflow="{wf_name}",le="{bucket}"}} {count}')
            lines.append(f'n8n_workflow_execution_duration_seconds_bucket{{workflow="{wf_name}",le="+Inf"}} {len(sorted_d)}')
            lines.append(f'n8n_workflow_execution_duration_seconds_count{{workflow="{wf_name}"}} {len(sorted_d)}')
            avg = sum(sorted_d) / len(sorted_d)
            lines.append(f'n8n_workflow_execution_duration_seconds_sum{{workflow="{wf_name}"}} {sum(sorted_d):.3f}')
            lines.append(f'# n8n_workflow_execution_duration_seconds_avg{{workflow="{wf_name}"}} {avg:.3f}')

        lines.append("")

    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="N8N metrics exporter")
    parser.add_argument("--output", type=Path, help="textfile output path")
    parser.add_argument("--http-port", type=int, help="start HTTP server (prometheus format)")
    parser.add_argument("--limit", type=int, default=100, help="execucoes por WF (default 100)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    base_url, api_key = get_n8n_config()
    if not api_key:
        print("[ERROR] N8N_API_KEY nao definido", file=sys.stderr)
        return 2

    print(f"N8N URL: {base_url}")
    print(f"Limit: {args.limit} executions per workflow")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()

    workflows = fetch_workflows(base_url, api_key, args.timeout)
    if not workflows:
        print("[HOLD] 0 workflows encontrados", file=sys.stderr)
        return 1

    print(f"Total workflows: {len(workflows)}")

    # Fetch executions para cada WF (limit 100)
    executions: dict[str, list[dict]] = {}
    for wf in workflows:
        wf_id = wf.get("id")
        if wf_id:
            execs = fetch_executions(base_url, api_key, wf_id, args.limit, args.timeout)
            executions[wf_id] = execs
    print(f"Total executions fetched: {sum(len(v) for v in executions.values())}")

    metrics_lines = compute_workflow_metrics(workflows, executions)
    metrics_text = "\n".join(metrics_lines)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(metrics_text)
        print(f"[WORK] Metricas salvas em {args.output} ({len(metrics_lines)} linhas)")

    if args.http_port:
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.end_headers()
                self.wfile.write(metrics_text.encode())

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                pass

        server = HTTPServer(("0.0.0.0", args.http_port), Handler)
        print(f"[WORK] HTTP server em :{args.http_port}/metrics")
        server.serve_forever()

    if not args.output and not args.http_port:
        print(metrics_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())