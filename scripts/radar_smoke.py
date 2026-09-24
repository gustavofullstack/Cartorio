"""Health Radar smoke test CLI (G6.D.T1).

Chama GET /api/v1/health/radar/expanded em prod e gera report binario
[WORK]/[HOLD] com totais por categoria.

Uso:
    python3 scripts/radar_smoke.py                       # default URL
    python3 scripts/radar_smoke.py --url https://api...  # custom
    python3 scripts/radar_smoke.py --report radar_report.md

Exit codes:
    0 = status agregado green ou yellow (UP com warnings)
    1 = status agregado red (algum servico critico DOWN)
    2 = erro pre-requisito (timeout, URL invalida)

Ref: backend/app/api/v1/health_radar_expanded.py (F6 2026-07-15).
Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 3.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

DEFAULT_URL = "https://api.2notasudi.com.br/api/v1/health/radar/expanded"
FALLBACK_URL = "https://api.2notasudi.com.br/api/v1/health/radar"
TIMEOUT = 30.0


def render_markdown(data: dict) -> str:
    """Render radar JSON como markdown."""
    md: list[str] = []
    md.append("# Health Radar Expanded — Smoke Report")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**URL**: {data.get('_url', '?')}")
    md.append(f"**Status agregado**: **{data.get('status', '?')}**")
    md.append("")

    categories = data.get("categories", {})
    totals: dict[str, dict[str, int]] = {}
    for cat_name, checks in categories.items():
        totals[cat_name] = {"up": 0, "warn": 0, "down": 0}
        for ck_name, payload in checks.items():
            s = payload.get("status", "?")
            if s in totals[cat_name]:
                totals[cat_name][s] += 1

    md.append("## Resumo por categoria")
    md.append("")
    md.append("| Categoria | UP | WARN | DOWN | Total |")
    md.append("|---|---|---|---|---|")
    for cat, t in totals.items():
        total = t["up"] + t["warn"] + t["down"]
        md.append(f"| **{cat}** | {t['up']} | {t['warn']} | {t['down']} | {total} |")
    md.append("")

    if data.get("status") == "green":
        md.append("## [WORK] Todos os servicos core UP")
    elif data.get("status") == "yellow":
        md.append("## [HOLD] Algum servico em WARN/DOWN (nao-critico)")
    else:
        md.append("## [CRITICAL] Servico CRITICO (database ou redis) DOWN")
    md.append("")

    md.append("## Detalhes por categoria")
    md.append("")
    for cat_name, checks in categories.items():
        md.append(f"### {cat_name}")
        md.append("")
        md.append("| Check | Status | Latency (ms) | Detail |")
        md.append("|---|---|---|---|")
        for ck_name, payload in checks.items():
            status = payload.get("status", "?")
            emoji = {"up": "✅", "warn": "⚠️", "down": "❌"}.get(status, "?")
            latency = payload.get("latency_ms", "?")
            detail = payload.get("detail", "")[:80].replace("|", "\\|")
            md.append(f"| `{ck_name}` | {emoji} {status} | {latency} | {detail} |")
        md.append("")

    metadata = data.get("metadata", {})
    if metadata:
        md.append("## Metadata")
        md.append("")
        md.append("```json")
        md.append(json.dumps(metadata, indent=2, ensure_ascii=False))
        md.append("```")
        md.append("")

    md.append("---")
    md.append("")
    md.append("**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 3 (auto-gerado)**")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="Health radar smoke CLI")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL do /health/radar/expanded")
    parser.add_argument("--json", action="store_true", help="output JSON puro")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    parser.add_argument("--timeout", type=float, default=TIMEOUT, help="timeout em segundos")
    args = parser.parse_args()

    url_used = args.url
    try:
        resp = httpx.get(args.url, timeout=args.timeout, verify=False)
        # G6.D.T6: prod image pode ainda nao ter /radar/expanded (404) —
        # fallback automatico para /radar classico (7 servicos).
        if resp.status_code == 404 and args.url.rstrip("/").endswith("/expanded"):
            print(
                f"[WARN] {args.url} → HTTP 404; fallback {FALLBACK_URL}",
                file=sys.stderr,
            )
            url_used = FALLBACK_URL
            resp = httpx.get(FALLBACK_URL, timeout=args.timeout, verify=False)
    except Exception as exc:
        print(f"[ERROR] Failed to fetch {args.url}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    if resp.status_code != 200:
        print(f"[ERROR] HTTP {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        return 2

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        print(f"[ERROR] JSON decode failed: {exc}", file=sys.stderr)
        return 2

    # Normaliza shape legado /radar (services: dict) → categories.health
    if "categories" not in data and "services" in data:
        services = data.get("services") or {}
        checks = {
            name: {
                "status": "up" if state == "online" else "down",
                "latency_ms": None,
                "detail": state,
            }
            for name, state in services.items()
        }
        data = {
            "status": data.get("status", "red"),
            "categories": {"health": checks},
            "metadata": {
                "source": "legacy_radar_fallback",
                "note": "Deploy API with /radar/expanded to get DNS/Traefik/SSH/disk",
            },
            "_legacy": True,
        }

    data["_url"] = url_used
    status = data.get("status", "?")

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"Status: {status}")
        cats = data.get("categories", {})
        for cat, checks in cats.items():
            up = sum(1 for p in checks.values() if p.get("status") == "up")
            warn = sum(1 for p in checks.values() if p.get("status") == "warn")
            down = sum(1 for p in checks.values() if p.get("status") == "down")
            print(f"  {cat:12} up={up} warn={warn} down={down} (total={len(checks)})")
        if data.get("_legacy"):
            print("[HOLD] using legacy /radar (expanded not deployed yet)")
        if status == "green":
            print("[WORK] todos up")
        elif status == "yellow":
            print("[HOLD] algum warn/down nao-critico")
        else:
            print("[CRITICAL] servico critico down")

    if args.report:
        args.report.write_text(render_markdown(data))
        print(f"  Report: {args.report}", file=sys.stderr)

    if status == "red":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
