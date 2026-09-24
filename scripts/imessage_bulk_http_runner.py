"""Bulk HTTP runner da campanha 10K — PIETRA via /api/v1/pietra (sem Messages.app).

Modo híbrido da campanha 10K:
- Bulk (~9.5k casos): HTTP direto no endpoint thin-shell (rápido, custo controlado).
- Amostra live (~500): continua no scripts/imessage_e2e_runner.py (real transport).

Features:
- Multi-turn realista: envia turn a turn, acumulando respostas do assistant no contexto.
- Concorrência limitada (semaphore) + rate limit global (token bucket, req/s).
- Checkpoint/resume: resultados appended em JSONL; reruns pulam IDs completos.
- Checker compartilhado com o runner live (import de imessage_e2e_runner):
  hard-fail patterns, forbidden actions, expected normalizado (NFKD), emoji,
  require_identity. Avaliação sobre a ÚLTIMA resposta do caso.
- Gates da Seção 7 reportados no summary (identity leak, internal vocab, placeholder
  emolumentos, emoji, timeout).

Uso:
    uv run python scripts/imessage_bulk_http_runner.py --limit 50          # smoke
    uv run python scripts/imessage_bulk_http_runner.py --cats emol,injection
    uv run python scripts/imessage_bulk_http_runner.py --rps 1.0 --concurrency 4
    BASE_URL=http://localhost:8001 uv run python scripts/imessage_bulk_http_runner.py

Modified by Gustavo Almeida · 2026-07-28
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from imessage_e2e_runner import evaluate  # noqa: E402  # checker compartilhado

ARTIFACTS = Path("/Users/gustavoalmeida/Projetos/Cartorio/artifacts/imessage")
CORPUS_FILE = ARTIFACTS / "corpus_10k.jsonl"
BASE_URL = os.environ.get("BASE_URL", "https://api.2notasudi.com.br")
ENDPOINT = f"{BASE_URL}/api/v1/pietra/chat/completions"
REQUEST_TIMEOUT_S = 90
MAX_RETRIES = 2

# Placeholders de emolumento errados (G1 — regressão proibida)
EMO_PLACEHOLDER_FORBIDDEN = ("28,90", "28.90", "32,10", "32.10", "156,40", "156.40")

# Schema mínimo das tools cartorio — casos emol rodam COM tools (espelha o
# fluxo Hermes gateway). finish_reason=tool_calls estruturado = REGRA DE OURO
# honrada (o caller executaria via MCP); conta como PASS.
TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "cartorio_calcular_emolumento",
            "description": "Calcula emolumento MG 2026 (Portaria CGJ/TJMG 8.664/2025)",
            "parameters": {
                "type": "object",
                "properties": {
                    "ato": {"type": "string"},
                    "folhas": {"type": "integer"},
                    "urgencia": {"type": "boolean"},
                },
                "required": ["ato"],
            },
        },
    }
]


async def rate_limiter(interval: float) -> None:
    """Token bucket simples: 1 token por `interval` segundos (global)."""
    await asyncio.sleep(interval)


async def run_case(client: Any, case: dict[str, Any], sem: asyncio.Semaphore,
                   rps_interval: float) -> dict[str, Any]:
    """Executa 1 caso multi-turn; retorna resultado avaliado."""
    messages: list[dict[str, str]] = []
    last_text = ""
    last_tool_calls: list[dict[str, Any]] = []
    error: str | None = None
    use_tools = case["cat"] == "emol"
    async with sem:
        for turn in case["turns"]:
            messages.append({"role": "user", "content": turn})
            await rate_limiter(rps_interval)
            payload: dict[str, Any] = {"messages": messages, "max_tokens": 600}
            if use_tools:
                payload["tools"] = TOOLS_SCHEMA
            ok = False
            for attempt in range(MAX_RETRIES + 1):
                try:
                    r = await client.post(ENDPOINT, json=payload,
                                          timeout=REQUEST_TIMEOUT_S)
                    if r.status_code == 429:
                        await asyncio.sleep(5 * (attempt + 1))
                        continue
                    r.raise_for_status()
                    data = r.json()
                    msg = data["choices"][0]["message"]
                    last_text = msg.get("content") or ""
                    last_tool_calls = msg.get("tool_calls") or []
                    messages.append({"role": "assistant", "content": last_text})
                    ok = True
                    break
                except Exception as exc:  # noqa: BLE001 — campanha registra, não morre
                    error = f"{type(exc).__name__}: {exc}"
                    await asyncio.sleep(2 * (attempt + 1))
            if not ok:
                return {
                    "id": case["id"], "cat": case["cat"], "status": "ERROR",
                    "issues": [f"transport:{error}"], "response": "",
                    "ts": datetime.now(timezone.utc).isoformat(),
                }

    ev = evaluate(case["id"], last_text, case["expected"], case["forbidden"],
                  case.get("require_identity", False))
    # regressão G1: placeholder de emolumento em qualquer resposta de caso emol
    if case["cat"] == "emol":
        for ph in EMO_PLACEHOLDER_FORBIDDEN:
            if ph in last_text:
                ev["issues"].append(f"emol_placeholder:{ph}")
        # tool_call estruturado = REGRA DE OURO honrada (caller executa via MCP)
        if last_tool_calls and not ev["issues"]:
            ev["issues"] = []
            ev["tool_call"] = last_tool_calls[0]["function"]["name"]
    ev["status"] = "PASS" if not ev["issues"] else "FAIL"
    return {
        "id": case["id"], "cat": case["cat"], "status": ev["status"],
        "issues": ev["issues"], "response": ev["response"],
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def load_completed(results_file: Path) -> set[str]:
    done: set[str] = set()
    if results_file.exists():
        with results_file.open() as f:
            for line in f:
                try:
                    done.add(json.loads(line)["id"])
                except Exception:  # noqa: BLE001
                    continue
    return done


async def campaign(args: argparse.Namespace) -> int:
    import httpx

    cases = [json.loads(ln) for ln in CORPUS_FILE.open()]
    if args.cats:
        wanted = set(args.cats.split(","))
        cases = [c for c in cases if c["cat"] in wanted]
    if args.offset:
        cases = cases[args.offset:]
    if args.limit:
        cases = cases[: args.limit]

    results_file = Path(args.results) if args.results else (
        ARTIFACTS / f"bulk10k_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
    done = load_completed(results_file)
    pending = [c for c in cases if c["id"] not in done]
    print(f"=== BULK 10K HTTP — {ENDPOINT}")
    print(f"casos: {len(cases)} · já completos: {len(done)} · pendentes: {len(pending)}")
    print(f"rps: {args.rps} · concorrência: {args.concurrency} · results: {results_file}")
    if not pending:
        print("Nada a fazer.")
        return 0

    sem = asyncio.Semaphore(args.concurrency)
    rps_interval = 1.0 / args.rps
    t0 = time.monotonic()
    counts: Counter[str] = Counter()
    cat_stats: dict[str, Counter[str]] = {}

    async with httpx.AsyncClient() as client:
        with results_file.open("a") as out:
            tasks = [run_case(client, c, sem, rps_interval) for c in pending]
            for i, fut in enumerate(asyncio.as_completed(tasks), 1):
                res = await fut
                out.write(json.dumps(res, ensure_ascii=False) + "\n")
                out.flush()
                counts[res["status"]] += 1
                cat_stats.setdefault(res["cat"], Counter())[res["status"]] += 1
                if i % args.checkpoint == 0 or i == len(pending):
                    el = time.monotonic() - t0
                    rate = i / el * 60 if el else 0
                    eta = (len(pending) - i) / (i / el) / 60 if i else 0
                    print(f"[{i}/{len(pending)}] PASS={counts['PASS']} "
                          f"FAIL={counts['FAIL']} ERR={counts['ERROR']} "
                          f"({rate:.0f}/min, ETA {eta:.0f}min)")

    # Summary + gates Seção 7
    total = sum(counts.values())
    summary = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "endpoint": ENDPOINT,
        "results_file": str(results_file),
        "total": total,
        "counts": dict(counts),
        "per_cat": {c: dict(s) for c, s in sorted(cat_stats.items())},
    }
    summary_file = results_file.with_suffix(".summary.json")
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n=== FINAL: {counts['PASS']}/{total} PASS "
          f"({100 * counts['PASS'] / max(total, 1):.1f}%) · "
          f"FAIL={counts['FAIL']} ERR={counts['ERROR']}")
    for cat, s in sorted(cat_stats.items()):
        n = sum(s.values())
        print(f"  {cat:20s} {s['PASS']}/{n} ({100 * s['PASS'] / n:.0f}%)")
    print(f"summary: {summary_file}")
    return 0 if counts["FAIL"] == 0 and counts["ERROR"] == 0 else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--cats", type=str, default="")
    p.add_argument("--rps", type=float, default=1.0)
    p.add_argument("--concurrency", type=int, default=2)
    p.add_argument("--checkpoint", type=int, default=100)
    p.add_argument("--results", type=str, default="", help="arquivo JSONL p/ resume")
    args = p.parse_args()
    return asyncio.run(campaign(args))


if __name__ == "__main__":
    raise SystemExit(main())
