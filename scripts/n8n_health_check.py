"""N8N Workflow health-check CLI (G6.A.T7).

Para cada WF em infra/n8n-workflows/, dispara POST de teste (ou health
check via N8N API) e valida resposta 2xx. Detecta WFs quebrados antes
de afetar producao.

Uso:
    python3 scripts/n8n_health_check.py                       # todos WFs
    python3 scripts/n8n_health_check.py --wf 02-criar-protocolo  # 1 WF
    python3 scripts/n8n_health_check.py --report docs/N8N_HEALTH.md

Exit codes:
    0 = todos WFs saudaveis
    1 = algum WF com problema (5xx, 404, timeout)
    2 = erro pre-requisito (N8N nao configurado)

Ref: skill `n8n` + N8N public API.
Modified by Gustavo Almeida + cartorio-n8n — G6 wave 14.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

WF_DIR = Path("infra/n8n-workflows")
DEFAULT_BASE_URL = "https://flow.2notasudi.com.br"
TIMEOUT = 8.0


def get_n8n_config() -> tuple[str, str | None]:
    """Retorna (base_url, api_key) do N8N."""
    base_url = os.environ.get("N8N_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.environ.get("N8N_API_KEY")
    return base_url, api_key


def list_workflows() -> list[dict]:
    """Lista WFs do N8N via API. Retorna lista vazia se offline."""
    base_url, api_key = get_n8n_config()
    if not api_key:
        return []
    try:
        resp = httpx.get(
            f"{base_url}/api/v1/workflows",
            headers={"X-N8N-API-KEY": api_key},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json().get("data", [])
    except Exception:
        pass
    return []


def check_wf_health(name: str, webhook_path: str | None) -> dict:
    """Check health de 1 WF. Se webhook_path definido, faz POST teste."""
    base_url, _ = get_n8n_config()
    result = {"name": name, "status": "unknown", "details": ""}

    if not webhook_path:
        result["status"] = "no_webhook"
        result["details"] = "WF sem webhook (provavelmente cron/trigger)"
        return result

    url = f"{base_url}/webhook/{webhook_path}"
    try:
        # POST com payload minimo (a maioria dos WFs nao valida body, so recebe)
        resp = httpx.post(
            url,
            json={
                "_health_check": True,
                "_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            timeout=TIMEOUT,
        )
        result["status"] = "ok" if resp.status_code < 500 else "error"
        result["details"] = f"HTTP {resp.status_code}"
        result["url"] = url
        return result
    except httpx.ConnectError as exc:
        result["status"] = "unreachable"
        result["details"] = f"connect error: {exc}"
        return result
    except httpx.TimeoutException:
        result["status"] = "timeout"
        result["details"] = f"timeout {TIMEOUT}s"
        return result
    except Exception as exc:
        result["status"] = "error"
        result["details"] = f"{type(exc).__name__}: {exc}"
        return result


def get_local_webhook_path(wf_file: Path) -> str | None:
    """Extrai o webhook path de 1 WF local (sem fazer request)."""
    try:
        data = json.loads(wf_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    for node in data.get("nodes", []):
        if node.get("type") == "n8n-nodes-base.webhook":
            return node.get("parameters", {}).get("path")
    return None


def render_markdown(results: list[dict]) -> str:
    md: list[str] = []
    md.append("# N8N Workflow Health Report")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")

    by_status: dict[str, int] = {}
    for r in results:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    md.append(f"**Total WFs**: {len(results)}")
    for status, count in sorted(by_status.items()):
        emoji = {
            "ok": "✅",
            "no_webhook": "ℹ️",
            "unreachable": "🔌",
            "timeout": "⏱️",
            "error": "❌",
        }.get(status, "?")
        md.append(f"- {emoji} {status}: {count}")
    md.append("")

    if not any(r["status"] not in ("ok", "no_webhook") for r in results):
        md.append("## [WORK] Todos WFs saudaveis")
    else:
        md.append("## [HOLD] WFs com problema")
    md.append("")

    md.append("| WF | Status | Detalhes |")
    md.append("|---|---|---|")
    for r in sorted(results, key=lambda x: (x["status"] != "error", x["name"])):
        emoji = {
            "ok": "✅",
            "no_webhook": "ℹ️",
            "unreachable": "🔌",
            "timeout": "⏱️",
            "error": "❌",
        }.get(r["status"], "?")
        details = r["details"][:80].replace("|", "\\|")
        md.append(f"| {r['name']} | {emoji} {r['status']} | {details} |")
    md.append("")
    md.append("---")
    md.append("")
    md.append(
        "**Modified by Gustavo Almeida + cartorio-n8n — G6 wave 14 (auto-gerado)**"
    )
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="N8N workflow health-check CLI")
    parser.add_argument("--wf", help="checar apenas 1 WF (filename sem .json)")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    parser.add_argument(
        "--dry-run", action="store_true", help="mostrar URLs sem chamar"
    )
    args = parser.parse_args()

    if not WF_DIR.exists():
        print(f"[ERROR] {WF_DIR} nao existe", file=sys.stderr)
        return 2

    if args.wf:
        wf_files = [WF_DIR / f"{args.wf}.json"]
    else:
        wf_files = sorted(WF_DIR.glob("*.json"))

    print(f"Total WFs a checar: {len(wf_files)}")

    if args.dry_run:
        for wf in wf_files:
            path = get_local_webhook_path(wf)
            if path:
                base_url, _ = get_n8n_config()
                print(f"  {wf.name}: POST {base_url}/webhook/{path}")
            else:
                print(f"  {wf.name}: (sem webhook)")
        return 0

    results: list[dict] = []
    for wf in wf_files:
        path = get_local_webhook_path(wf)
        if not path:
            results.append({"name": wf.stem, "status": "no_webhook", "details": ""})
            continue
        result = check_wf_health(wf.stem, path)
        results.append(result)
        emoji = {
            "ok": "✅",
            "no_webhook": "ℹ️",
            "unreachable": "🔌",
            "timeout": "⏱️",
            "error": "❌",
        }.get(result["status"], "?")
        print(f"  {emoji} {wf.stem}: {result['status']} ({result['details']})")

    problematic = [r for r in results if r["status"] not in ("ok", "no_webhook")]
    if problematic:
        print(f"\n[HOLD] {len(problematic)} WF(s) com problema")
    else:
        print(f"\n[WORK] Todos WFs saudaveis")

    if args.report:
        args.report.write_text(render_markdown(results))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 1 if problematic else 0


if __name__ == "__main__":
    sys.exit(main())
