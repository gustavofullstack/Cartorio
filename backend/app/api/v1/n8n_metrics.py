"""N8N Execution Metrics endpoint (G6.B.T9).

Exposicao de metricas N8N em formato Prometheus (complementa scripts/n8n_metrics_exporter.py).

GET /api/v1/n8n/metrics/prometheus:
- Texto formato Prometheus 0.0.4 (scrape-friendly)
- Labels: workflow, status, agent
- Metricas: execution_total, duration_seconds histogram, error_rate

GET /api/v1/n8n/metrics/summary:
- JSON agregado: top WFs por execucoes, error rate, p50/p95/p99 duracao

Auth: X-API-Key (n8n tier 600/min)

Refs:
- infra/prometheus/slo_rules.yml (SLO N8N success)
- scripts/n8n_metrics_exporter.py (CLI exporter)

Modified by Gustavo Almeida + cartorio-n8n — G6 wave 25.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db

router = APIRouter(prefix="/n8n/metrics", tags=["n8n", "metrics"])


def fetch_n8n_executions(
    base_url: str,
    api_key: str,
    hours: int,
    timeout: float,
) -> list[dict[str, Any]]:
    """Busca execucoes N8N das ultimas N horas."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(
                f"{base_url}/api/v1/executions",
                params={"limit": 1000, "includeData": "false"},
                headers={"X-N8N-API-KEY": api_key},
            )
            if r.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail={"erro": "N8N_API_ERROR", "status": r.status_code},
                )
            executions = r.json().get("data", [])
        return [e for e in executions if e.get("startedAt", "") >= cutoff]
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={"erro": "N8N_CONNECTION_ERROR", "mensagem": str(exc)},
        ) from exc


@router.get(
    "/prometheus",
    response_class=__import__(
        "fastapi.responses", fromlist=["PlainTextResponse"]
    ).PlainTextResponse,
    summary="Metricas N8N em formato Prometheus",
)
def prometheus_metrics(
    hours: int = Query(default=24, ge=1, le=168, description="Janela em horas"),
    db: Session = Depends(get_db),  # noqa: ARG001
) -> str:
    """Endpoint scrape-friendly para Prometheus."""
    api_key = settings.n8n_api_key
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail={"erro": "N8N_API_KEY_NOT_CONFIGURED"},
        )
    base_url = settings.n8n_base_url
    executions = fetch_n8n_executions(base_url, api_key, hours, timeout=30.0)

    by_wf: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ex in executions:
        wf_id = ex.get("workflowId", "unknown")
        by_wf[wf_id].append(ex)

    lines: list[str] = [
        f"# N8N metrics (window: {hours}h, generated: {datetime.now(timezone.utc).isoformat()})",
        "",
    ]

    for wf_id, execs in by_wf.items():
        wf_name = execs[0].get("workflow", {}).get("name", wf_id)
        success = sum(1 for e in execs if e.get("status") == "success")
        error = sum(1 for e in execs if e.get("status") in ("error", "failed", "crashed"))
        total = len(execs)
        error_rate = error / total if total > 0 else 0
        lines.append(
            f'n8n_workflow_execution_total{{workflow="{wf_name}",status="success"}} {success}'
        )
        lines.append(f'n8n_workflow_execution_total{{workflow="{wf_name}",status="error"}} {error}')
        lines.append(f'n8n_workflow_error_rate{{workflow="{wf_name}"}} {error_rate:.4f}')

        durations: list[float] = []
        for e in execs:
            started = e.get("startedAt")
            stopped = e.get("stoppedAt")
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
        if durations:
            for bucket in (0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0):
                count = sum(1 for d in durations if d <= bucket)
                lines.append(
                    f'n8n_workflow_execution_duration_seconds_bucket{{workflow="{wf_name}",le="{bucket}"}} {count}'
                )
            lines.append(
                f'n8n_workflow_execution_duration_seconds_count{{workflow="{wf_name}"}} {len(durations)}'
            )
            lines.append(
                f'n8n_workflow_execution_duration_seconds_sum{{workflow="{wf_name}"}} {sum(durations):.3f}'
            )
        lines.append("")

    return "\n".join(lines)


@router.get(
    "/summary",
    summary="Summary agregado de metricas N8N (JSON)",
)
def summary_metrics(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),  # noqa: ARG001
) -> dict[str, Any]:
    """Retorna summary JSON com top WFs e agregacoes."""
    api_key = settings.n8n_api_key
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail={"erro": "N8N_API_KEY_NOT_CONFIGURED"},
        )
    base_url = settings.n8n_base_url
    executions = fetch_n8n_executions(base_url, api_key, hours, timeout=30.0)

    by_wf: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ex in executions:
        wf_id = ex.get("workflowId", "unknown")
        by_wf[wf_id].append(ex)

    top_wfs: list[dict[str, Any]] = []
    all_durations: list[float] = []
    total_success = 0
    total_error = 0

    for wf_id, execs in by_wf.items():
        wf_name = execs[0].get("workflow", {}).get("name", wf_id)
        success = sum(1 for e in execs if e.get("status") == "success")
        error = sum(1 for e in execs if e.get("status") in ("error", "failed", "crashed"))
        total = len(execs)
        total_success += success
        total_error += error

        durations: list[float] = []
        for e in execs:
            started = e.get("startedAt")
            stopped = e.get("stoppedAt")
            if started and stopped:
                try:
                    d_ms = (
                        datetime.fromisoformat(stopped.replace("Z", "+00:00"))
                        - datetime.fromisoformat(started.replace("Z", "+00:00"))
                    ).total_seconds()
                    if d_ms >= 0:
                        durations.append(d_ms)
                        all_durations.append(d_ms)
                except (ValueError, TypeError):
                    pass
        sorted_d = sorted(durations) if durations else [0]
        p50 = sorted_d[len(sorted_d) // 2] if sorted_d else 0
        p95_idx = max(0, int(len(sorted_d) * 0.95) - 1)
        p95 = sorted_d[p95_idx] if sorted_d else 0
        p99_idx = max(0, int(len(sorted_d) * 0.99) - 1)
        p99 = sorted_d[p99_idx] if sorted_d else 0

        top_wfs.append(
            {
                "workflow_id": wf_id,
                "workflow_name": wf_name,
                "total": total,
                "success": success,
                "error": error,
                "error_rate": round(error / total, 4) if total else 0,
                "duration_p50": p50,
                "duration_p95": p95,
                "duration_p99": p99,
            }
        )

    top_wfs.sort(key=lambda x: x["total"], reverse=True)

    sorted_all = sorted(all_durations)
    p50_all = sorted_all[len(sorted_all) // 2] if sorted_all else 0
    p95_all = sorted_all[max(0, int(len(sorted_all) * 0.95) - 1)] if sorted_all else 0
    p99_all = sorted_all[max(0, int(len(sorted_all) * 0.99) - 1)] if sorted_all else 0

    return {
        "window_hours": hours,
        "total_executions": len(executions),
        "total_success": total_success,
        "total_error": total_error,
        "success_rate": round(total_success / len(executions), 4) if executions else 0,
        "duration_p50": p50_all,
        "duration_p95": p95_all,
        "duration_p99": p99_all,
        "workflows": top_wfs[:10],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
