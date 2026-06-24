#!/usr/bin/env python3
"""Test runner para workflows N8N do projeto Cartorio.

Faz:
1. Lista todos os workflows via N8N API
2. Para cada workflow, dispara execucao (POST /execute)
3. Coleta resultado (sucesso/falha) + tempo de execucao
4. Salva relatorio em docs/n8n-workflows-test-report.md

Uso:
    export N8N_API_KEY="n8n-..."  # ou user:owner
    export N8N_BASE_URL="https://flow.2notasudi.com.br"
    python3 scripts/n8n_workflow_test.py

Ou via Makefile:
    make n8n-test
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import httpx


def get_workflows(base_url: str, api_key: str) -> list[dict[str, Any]]:
    """Lista todos workflows do N8N."""
    headers = {"X-N8N-API-KEY": api_key}
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{base_url}/api/v1/workflows?limit=100", headers=headers)
        resp.raise_for_status()
        return resp.json().get("data", [])


def execute_workflow(
    base_url: str, api_key: str, workflow_id: str, payload: dict | None = None
) -> dict[str, Any]:
    """Dispara execucao de um workflow."""
    headers = {"X-N8N-API-KEY": api_key}
    data = payload or {}
    with httpx.Client(timeout=60.0) as client:
        start = time.time()
        resp = client.post(
            f"{base_url}/api/v1/workflows/{workflow_id}/execute",
            headers=headers,
            json=data,
        )
        elapsed = time.time() - start
        return {
            "status_code": resp.status_code,
            "elapsed_s": round(elapsed, 3),
            "response": resp.json() if resp.status_code < 500 else None,
            "error": resp.text if resp.status_code >= 500 else None,
        }


def main() -> int:
    """Funcao principal."""
    base_url = os.environ.get("N8N_BASE_URL", "https://flow.2notasudi.com.br")
    api_key = os.environ.get("N8N_API_KEY", "")

    if not api_key:
        print("ERROR: N8N_API_KEY nao definido")
        print("Exporte: export N8N_API_KEY=n8n-...")
        return 1

    print(f"Listando workflows em {base_url}...")
    try:
        workflows = get_workflows(base_url, api_key)
    except Exception as e:
        print(f"ERROR ao listar: {e}")
        return 1

    print(f"Encontrados {len(workflows)} workflows.\n")

    if not workflows:
        print("Nenhum workflow encontrado.")
        return 0

    # Resultados
    results: list[dict[str, Any]] = []
    for wf in workflows:
        wf_id = wf.get("id")
        wf_name = wf.get("name", "?")
        wf_active = wf.get("active", False)
        print(f"  [{wf_id}] {wf_name} (active={wf_active})")

        if not wf_active:
            print(f"    SKIP: workflow inativo")
            results.append({"id": wf_id, "name": wf_name, "status": "skipped", "reason": "inactive"})
            continue

        # Tenta executar (sem payload - usa default)
        try:
            r = execute_workflow(base_url, api_key, wf_id)
            if r["status_code"] < 300:
                print(f"    OK em {r['elapsed_s']}s (status={r['status_code']})")
                results.append(
                    {
                        "id": wf_id,
                        "name": wf_name,
                        "status": "ok",
                        "elapsed_s": r["elapsed_s"],
                    }
                )
            else:
                print(f"    FAIL status={r['status_code']}")
                results.append(
                    {
                        "id": wf_id,
                        "name": wf_name,
                        "status": "fail",
                        "http_status": r["status_code"],
                    }
                )
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"id": wf_id, "name": wf_name, "status": "error", "error": str(e)})

    # Relatorio
    ok = sum(1 for r in results if r["status"] == "ok")
    fail = sum(1 for r in results if r["status"] == "fail")
    error = sum(1 for r in results if r["status"] == "error")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    print("\n=== Resumo ===")
    print(f"  Total: {len(workflows)}")
    print(f"  OK: {ok}")
    print(f"  FAIL: {fail}")
    print(f"  ERROR: {error}")
    print(f"  SKIPPED: {skipped}")

    # Salva relatorio
    report_path = "docs/n8n-workflows-test-report.md"
    with open(report_path, "w") as f:
        f.write("# N8N Workflows Test Report\n\n")
        f.write(f"Data: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"- Total: {len(workflows)}\n")
        f.write(f"- OK: {ok}\n")
        f.write(f"- FAIL: {fail}\n")
        f.write(f"- ERROR: {error}\n")
        f.write(f"- SKIPPED: {skipped}\n\n")
        f.write("## Detalhes\n\n")
        f.write("| ID | Nome | Status | Detalhes |\n")
        f.write("|---|---|---|---|\n")
        for r in results:
            det = r.get("elapsed_s") or r.get("http_status") or r.get("reason") or r.get("error", "")
            f.write(f"| {r['id']} | {r['name']} | {r['status']} | {det} |\n")

    print(f"\nRelatorio salvo em {report_path}")
    return 0 if (fail == 0 and error == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
