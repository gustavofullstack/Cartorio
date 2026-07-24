"""N8N retry policy config (G6.B.T10).

Aplica retry policy global em todos N8N workflows via API.
Configura: maxTries, waitBetweenTries (ms), retryOnFail.

Padrao (Google SRE retry):
- maxTries: 3 (inicial + 2 retries)
- waitBetweenTries: 5000ms (5s)
- retryOnFail: true

Uso:
    python3 scripts/n8n_retry_policy.py --dry-run
    python3 scripts/n8n_retry_policy.py --apply
    python3 scripts/n8n_retry_policy.py --max-tries 5 --wait 10000

Exit codes:
    0 = OK
    1 = erro API
    2 = erro pre-requisito

Modified by Gustavo Almeida + cartorio-n8n — G6 wave 26.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import httpx

DEFAULT_N8N_URL = "https://flow.2notasudi.com.br"
DEFAULT_MAX_TRIES = 3
DEFAULT_WAIT_MS = 5000
DEFAULT_RETRY_ON_FAIL = True


def get_n8n_config() -> tuple[str, str]:
    """Retorna (base_url, api_key)."""
    return (
        os.environ.get("N8N_BASE_URL", DEFAULT_N8N_URL),
        os.environ.get("N8N_API_KEY"),
    )


def fetch_workflows(base_url: str, api_key: str, timeout: float) -> list[dict]:
    """Lista todos workflows via API."""
    try:
        r = httpx.get(
            f"{base_url}/api/v1/workflows",
            headers={"X-N8N-API-KEY": api_key},
            timeout=timeout,
        )
        if r.status_code != 200:
            print(f"[ERROR] N8N API retornou {r.status_code}", file=sys.stderr)
            return []
        return r.json().get("data", [])
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return []


def build_retry_settings(max_tries: int, wait_ms: int, retry_on_fail: bool) -> dict:
    """Constroi settings block para aplicacao de retry."""
    return {
        "errorWorkflow": None,
        "saveDataErrorExecution": "all",
        "saveDataSuccessExecution": "all",
        "saveManualExecutions": True,
        "saveExecutionProgress": True,
        "timezone": "America/Sao_Paulo",
        "executionTimeout": 300,
        "maxTries": max_tries,
        "retryOnFail": retry_on_fail,
        "waitBetweenTries": wait_ms,
    }


def apply_retry_policy(
    base_url: str,
    api_key: str,
    workflow_id: str,
    settings: dict,
    dry_run: bool,
    timeout: float,
) -> bool:
    """Aplica retry policy em 1 workflow."""
    if dry_run:
        print(f"[DRY-RUN] Aplicaria em {workflow_id}: {json.dumps(settings, ensure_ascii=False)}")
        return True

    try:
        # GET workflow atual
        r = httpx.get(
            f"{base_url}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": api_key},
            timeout=timeout,
        )
        if r.status_code != 200:
            print(f"[ERROR] GET workflow {workflow_id}: {r.status_code}", file=sys.stderr)
            return False

        wf = r.json()
        # Merge settings (preserva outros campos)
        if "settings" not in wf:
            wf["settings"] = {}
        wf["settings"].update(settings)

        # PUT workflow com settings atualizadas
        r = httpx.put(
            f"{base_url}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": api_key},
            json=wf,
            timeout=timeout,
        )
        if r.status_code in (200, 201):
            print(f"[WORK] {wf.get('name', workflow_id)}: maxTries={settings['maxTries']}, wait={settings['waitBetweenTries']}ms")
            return True
        print(f"[ERROR] PUT workflow {workflow_id}: {r.status_code} - {r.text[:200]}", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="N8N retry policy config")
    parser.add_argument("--max-tries", type=int, default=DEFAULT_MAX_TRIES, help="max tentativas (default 3)")
    parser.add_argument("--wait", type=int, default=DEFAULT_WAIT_MS, help="wait entre tentativas em ms (default 5000)")
    parser.add_argument("--no-retry-on-fail", action="store_true", help="desabilitar retryOnFail")
    parser.add_argument("--apply", action="store_true", help="aplicar (default: dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="so mostra o que faria (default)")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    base_url, api_key = get_n8n_config()
    if not api_key:
        print("[ERROR] N8N_API_KEY nao definido", file=sys.stderr)
        return 2

    dry_run = not args.apply

    settings_block = build_retry_settings(
        max_tries=args.max_tries,
        wait_ms=args.wait,
        retry_on_fail=not args.no_retry_on_fail,
    )

    print(f"N8N URL: {base_url}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Settings: maxTries={settings_block['maxTries']}, wait={settings_block['waitBetweenTries']}ms, retryOnFail={settings_block['retryOnFail']}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()

    workflows = fetch_workflows(base_url, api_key, args.timeout)
    if not workflows:
        print("[HOLD] 0 workflows encontrados", file=sys.stderr)
        return 1

    print(f"Total workflows: {len(workflows)}")

    success = 0
    failed = 0
    for wf in workflows:
        wf_id = wf.get("id", "?")
        if apply_retry_policy(base_url, api_key, wf_id, settings_block, dry_run, args.timeout):
            success += 1
        else:
            failed += 1
        # Rate limit: 10 req/s
    print()
    print(f"Resultado: {success} OK, {failed} falharam")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())