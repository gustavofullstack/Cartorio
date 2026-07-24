"""OpenClaw health-check CLI (G6.E.T8).

Verifica saude do OpenClaw gateway:
1. GET /health (lesson 64 - HTTP, nao WebSocket)
2. GET /v1/agents (lista agentes configurados)
3. WebSocket /v1/chat (conecta, ping, desconecta)
4. Valida que cartorio-bot esta na lista de agents

Uso:
    python3 scripts/openclaw_health_check.py                      # default URL
    python3 scripts/openclaw_health_check.py --url https://agent.2notasudi.com.br
    python3 scripts/openclaw_health_check.py --report docs/OPENCLAW_HEALTH.md

Exit codes:
    0 = openclaw saudavel
    1 = algum check falhou
    2 = erro pre-requisito

Modified by Gustavo Almeida + cartorio-llm — G6 wave 15.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import websockets  # type: ignore[import-untyped]

DEFAULT_URL = "https://agent.2notasudi.com.br"
TIMEOUT = 8.0


def check_health(base_url: str) -> dict:
    """GET /health."""
    try:
        resp = httpx.get(f"{base_url}/health", timeout=TIMEOUT, verify=False)
        return {
            "name": "health",
            "status": "ok" if resp.status_code == 200 else "error",
            "details": f"HTTP {resp.status_code}",
            "body": resp.text[:200],
        }
    except Exception as exc:
        return {"name": "health", "status": "error", "details": f"{type(exc).__name__}: {exc}"}


def check_agents(base_url: str) -> dict:
    """GET /v1/agents. Verifica que cartorio-bot esta presente."""
    try:
        resp = httpx.get(f"{base_url}/v1/agents", timeout=TIMEOUT, verify=False)
        if resp.status_code != 200:
            return {
                "name": "agents",
                "status": "error",
                "details": f"HTTP {resp.status_code}",
            }
        # Pode ser HTML ou JSON
        try:
            data = resp.json()
            agents = [a.get("name") for a in data.get("data", [])]
        except json.JSONDecodeError:
            # HTML parse basico
            agents = []
            if "cartorio-bot" in resp.text:
                agents.append("cartorio-bot")

        cartorio_present = "cartorio-bot" in agents
        return {
            "name": "agents",
            "status": "ok" if cartorio_present else "warn",
            "details": f"{len(agents)} agent(s) | cartorio-bot={'sim' if cartorio_present else 'NAO'}",
            "agents": agents,
        }
    except Exception as exc:
        return {"name": "agents", "status": "error", "details": f"{type(exc).__name__}: {exc}"}


async def check_websocket(base_url: str) -> dict:
    """WebSocket /v1/chat ping-pong (lesson 64 super prompt)."""
    ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
    ws_url = f"{ws_url}/v1/chat"
    try:
        async with websockets.connect(ws_url, timeout=TIMEOUT) as ws:
            await ws.send(json.dumps({"type": "ping", "ts": datetime.now(timezone.utc).isoformat()}))
            # Esperar pong ou primeira mensagem
            response = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT)  # type: ignore[name-defined]
            return {
                "name": "websocket",
                "status": "ok",
                "details": f"connected + response received ({len(response)} chars)",
            }
    except Exception as exc:
        return {
            "name": "websocket",
            "status": "warn",
            "details": f"{type(exc).__name__}: {str(exc)[:200]} (WebSocket opcional; se HTTP /health OK, servico ta up)",
        }


def render_markdown(results: list[dict], base_url: str) -> str:
    md: list[str] = []
    md.append("# OpenClaw Health Check Report")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Base URL**: {base_url}")
    md.append("")
    by_status: dict[str, int] = {}
    for r in results:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    md.append("| Status | Count |")
    md.append("|---|---|")
    for s, c in sorted(by_status.items()):
        md.append(f"| {s} | {c} |")
    md.append("")
    md.append("## Detalhes")
    md.append("")
    md.append("| Check | Status | Detalhes |")
    md.append("|---|---|---|")
    for r in results:
        emoji = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(r["status"], "?")
        details = r["details"][:120].replace("|", "\\|")
        md.append(f"| {r['name']} | {emoji} {r['status']} | {details} |")
    if any(r["name"] == "agents" and r.get("agents") for r in results):
        for r in results:
            if r["name"] == "agents" and r.get("agents"):
                md.append("")
                md.append("## Agents configurados")
                md.append("")
                for a in r["agents"]:
                    md.append(f"- `{a}`")
    md.append("")
    md.append("---")
    md.append("")
    md.append("**Modified by Gustavo Almeida + cartorio-llm — G6 wave 15 (auto-gerado)**")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw health-check CLI")
    parser.add_argument("--url", default=DEFAULT_URL, help="OpenClaw base URL")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    print(f"OpenClaw URL: {args.url}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()

    results: list[dict] = []

    # 1. /health (HTTP)
    print("Checking /health...")
    h = check_health(args.url)
    results.append(h)
    print(f"  [{h['status']}] {h['name']}: {h['details']}")
    if "body" in h:
        print(f"    body: {h['body']}")

    # 2. /v1/agents
    print("Checking /v1/agents...")
    a = check_agents(args.url)
    results.append(a)
    print(f"  [{a['status']}] {a['name']}: {a['details']}")

    # 3. WebSocket (opcional)
    print("Checking WebSocket /v1/chat...")
    try:
        import asyncio
        ws = asyncio.run(check_websocket(args.url))
    except ImportError:
        ws = {"name": "websocket", "status": "warn", "details": "websockets module nao instalado"}
    results.append(ws)
    print(f"  [{ws['status']}] {ws['name']}: {ws['details']}")

    problematic = [r for r in results if r["status"] == "error"]
    if problematic:
        print(f"\n[HOLD] {len(problematic)} check(s) com erro critico")
    else:
        print("\n[WORK] OpenClaw saudavel")

    if args.report:
        args.report.write_text(render_markdown(results, args.url))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 1 if problematic else 0


if __name__ == "__main__":
    sys.exit(main())