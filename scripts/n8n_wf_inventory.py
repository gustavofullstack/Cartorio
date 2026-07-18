#!/usr/bin/env python3
"""Offline N8N workflow inventory — JSON parse + count (no network).

Modos:
- padrao: parse JSON basico (estrutura minima)
- --strict: validacao Pydantic strict schema (G8.13.T2 cartorio-n8n)
- --md-out FILE: escreve relatorio Markdown (combina com --strict)
- --workers N: paralelismo para --strict (default 8)

Uso (raiz do repo):
    python3 scripts/n8n_wf_inventory.py
    python3 scripts/n8n_wf_inventory.py --json
    python3 scripts/n8n_wf_inventory.py --dir infra/n8n-workflows
    python3 scripts/n8n_wf_inventory.py --strict
    python3 scripts/n8n_wf_inventory.py --strict --md-out docs/N8N_STRICT_VALIDATION_2026-07-18.md

Exit codes:
    0 = todos os *.json validos (strict ou basico)
    1 = 1+ JSON quebrado ou violacao schema
    2 = diretorio ausente

Modified by Gustavo Almeida — G7 Wave 29 A2 (cartorio-n8n).
Extended by G8.13.T2 (cartorio-n8n).
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

DEFAULT_DIR = Path("infra/n8n-workflows")


def _resolve_repo_root(start: Path) -> Path:
    """Sobe diretorios ate encontrar marcador de repo (Makefile + backend/)."""
    current = start.resolve()
    for parent in [current, *current.parents]:
        if (parent / "Makefile").is_file() and (parent / "backend").is_dir():
            return parent
    return start


def _parse_basic(path: Path) -> dict[str, Any]:
    """Parse JSON basico (legado — sem schema strict)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        return {
            "file": path.name,
            "ok": False,
            "valid": False,
            "validation_status": "broken_json",
            "validation_errors": [str(exc)[:200]],
            "bytes": path.stat().st_size if path.exists() else 0,
        }

    if not isinstance(data, dict):
        return {
            "file": path.name,
            "ok": False,
            "valid": False,
            "validation_status": "broken_json",
            "validation_errors": ["top-level not a dict"],
            "bytes": path.stat().st_size,
        }

    nodes = data.get("nodes")
    return {
        "file": path.name,
        "ok": True,
        "valid": True,
        "validation_status": "basic_ok",
        "validation_errors": [],
        "name": data.get("name", path.stem),
        "active": bool(data.get("active")),
        "nodes": len(nodes) if isinstance(nodes, list) else 0,
        "bytes": path.stat().st_size,
    }


def _parse_strict(path: Path) -> dict[str, Any]:
    """Parse com schema Pydantic strict (G8.13.T2)."""
    import contextlib

    entry = _parse_basic(path)
    if not entry["ok"]:
        return entry

    try:
        from pydantic import ValidationError as _PydVE
        from app.schemas.n8n_workflow import N8nWorkflow  # type: ignore[import-not-found]

        payload = json.loads(path.read_text(encoding="utf-8"))
        wf = N8nWorkflow.model_validate(payload)
        entry["validation_status"] = "valid"
        entry["validation_errors"] = []
        entry["strict_name"] = wf.name
        entry["strict_nodes"] = len(wf.nodes)
        entry["strict_timezone"] = wf.settings.timezone
        entry["name"] = wf.name
        entry["active"] = wf.active
        entry["nodes"] = len(wf.nodes)
        return entry
    except ImportError as exc:
        entry["validation_status"] = "schema_unavailable"
        entry["validation_errors"] = [
            f"schema nao importavel: {exc}. Rode via 'make -C backend shell'."
        ]
        return entry
    except Exception as exc:  # noqa: BLE001
        with contextlib.suppress(NameError):
            if isinstance(exc, _PydVE):
                entry["validation_status"] = "invalid"
                entry["valid"] = False
                entry["ok"] = False
                errs: list[str] = []
                for err in exc.errors()[:5]:  # type: ignore[attr-defined]
                    loc = ".".join(str(x) for x in err.get("loc", ()))
                    errs.append(f"{loc}: {err['msg'][:120]}")
                entry["validation_errors"] = errs
                entry["validation_error_count"] = len(exc.errors())  # type: ignore[attr-defined]
                return entry
        entry["validation_status"] = "schema_error"
        entry["valid"] = False
        entry["ok"] = False
        entry["validation_errors"] = [str(exc)[:200]]
        return entry


def inventariar(wf_dir: Path, strict: bool = False, workers: int = 8) -> dict:
    if not wf_dir.is_dir():
        return {"ok": False, "error": f"dir missing: {wf_dir}", "count": 0}

    files = sorted(wf_dir.glob("*.json"))
    parse_fn = _parse_strict if strict else _parse_basic

    worker_count = max(1, min(workers, len(files))) if files else 1
    if worker_count > 1:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            entries = list(executor.map(parse_fn, files))
    else:
        entries = [parse_fn(f) for f in files]

    valid_count = sum(1 for e in entries if e.get("validation_status") == "valid")
    invalid_count = sum(1 for e in entries if e.get("validation_status") == "invalid")
    broken_count = sum(1 for e in entries if e.get("validation_status") == "broken_json")
    basic_ok_count = sum(1 for e in entries if e.get("validation_status") == "basic_ok")

    return {
        "ok": (invalid_count == 0 and broken_count == 0),
        "strict": strict,
        "dir": str(wf_dir),
        "count": len(files),
        "valid": valid_count if strict else (broken_count == 0),
        "invalid": invalid_count,
        "broken": broken_count,
        "basic_ok": basic_ok_count,
        "active": sum(1 for e in entries if e.get("active")),
        "inactive": sum(1 for e in entries if not e.get("active")),
        "total_nodes": sum(e.get("nodes", 0) for e in entries),
        "workflows": entries,
    }


def render_markdown(report: dict, generated_at: str) -> str:
    """Renderiza relatorio estrito em Markdown (LGPD-friendly: so stats)."""
    lines: list[str] = []
    lines.append("# N8N Strict Validation Report")
    lines.append("")
    lines.append(f"- generated_at: {generated_at}")
    lines.append(f"- dir: `{report['dir']}`")
    lines.append(f"- strict_mode: {report['strict']}")
    lines.append(f"- total: {report['count']}")
    lines.append(f"- valid: {report.get('valid', 0)}")
    lines.append(f"- invalid: {report.get('invalid', 0)}")
    lines.append(f"- broken_json: {report.get('broken', 0)}")
    lines.append(f"- basic_ok_only: {report.get('basic_ok', 0)}")
    lines.append(f"- active: {report.get('active', 0)}")
    lines.append(f"- inactive: {report.get('inactive', 0)}")
    lines.append(f"- total_nodes: {report.get('total_nodes', 0)}")
    lines.append("")
    lines.append("## Workflows")
    lines.append("")
    lines.append("| file | status | nodes | name | first_error |")
    lines.append("|------|--------|-------|------|-------------|")
    for e in report["workflows"]:
        status = e.get("validation_status", "?")
        err = "; ".join(e.get("validation_errors", [])[:1])
        if len(err) > 80:
            err = err[:77] + "..."
        lines.append(
            f"| `{e['file']}` | {status} | {e.get('nodes', 0)} | "
            f"{e.get('name', '?')} | {err or '-'} |"
        )
    lines.append("")
    lines.append("## Schema")
    lines.append("")
    lines.append("- Validator: `app.schemas.n8n_workflow.N8nWorkflow` (Pydantic v2 strict)")
    lines.append("- `ConfigDict(strict=True, extra='forbid')` em todos os modelos")
    lines.append(
        "- LGPD Art. 46: regex anti-PII (CPF/CNPJ/RG/tel/email) em `name`, "
        "`description`, `tags`, `webhookId`"
    )
    lines.append("- IANA timezone via `zoneinfo` (stdlib)")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline N8N WF inventory (no network)")
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Directory with workflow JSON exports (default: <repo>/infra/n8n-workflows)",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Pydantic strict schema validation (G8.13.T2)",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        help="Escreve relatorio Markdown (combina com --strict)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Numero de threads paralelas (default 8)",
    )
    args = parser.parse_args()

    if args.dir is None:
        repo_root = _resolve_repo_root(Path(__file__).parent)
        args.dir = repo_root / DEFAULT_DIR

    if args.strict:
        repo_root = _resolve_repo_root(Path(__file__).parent)
        backend_dir = repo_root / "backend"
        if backend_dir.is_dir() and str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        import os
        os.environ.setdefault("APP_ENV", "development")

    report = inventariar(args.dir, strict=args.strict, workers=args.workers)

    if report.get("error"):
        print(f"FAIL: {report['error']}", file=sys.stderr)
        return 2

    if args.md_out:
        from datetime import datetime, timezone
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_markdown(report, generated_at), encoding="utf-8")
        print(f"[md] wrote {args.md_out}", file=sys.stderr)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== N8N WF Inventory (offline) ===")
        print(f"dir: {report['dir']}")
        print(f"mode: {'strict' if report['strict'] else 'basic'}")
        print(
            f"count: {report['count']}  valid: {report.get('valid', 0)}  "
            f"invalid: {report.get('invalid', 0)}  broken: {report['broken']}"
        )
        print(
            f"active: {report['active']}  inactive: {report['inactive']}  "
            f"total_nodes: {report['total_nodes']}"
        )
        print("")
        for e in report["workflows"]:
            status = e.get("validation_status", "?")
            flag = "ON " if e.get("active") else "OFF"
            err = ""
            if status == "invalid" and e.get("validation_errors"):
                err = f"  ERR: {e['validation_errors'][0][:60]}"
            print(
                f"  [{flag}] {e['file']:42s}  status={status:18s}  "
                f"nodes={e.get('nodes', 0):3d}  {e.get('name', '?')}{err}"
            )
        print("")
        status = "PASS" if report["ok"] else "FAIL"
        print(f"status: {status}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
