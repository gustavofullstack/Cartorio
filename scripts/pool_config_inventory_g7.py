#!/usr/bin/env python3
"""G7.08.T4 — inventário offline do connection pool (sem DB, sem secrets).

Uso (repo root ou qualquer cwd):
  python scripts/pool_config_inventory_g7.py
  python scripts/pool_config_inventory_g7.py --workers 4 --pool-size 25

Não importa app.config (evita exigir DATABASE_URL / AUDIT_HMAC_KEY).
Lê defaults documentados no código e imprime capacidade teórica.

Modified by Gustavo Almeida
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CONFIG_PY = REPO / "backend" / "app" / "config.py"
DB_PY = REPO / "backend" / "app" / "db.py"
ENV_BACKEND = REPO / "backend" / ".env.example"
ENV_ROOT = REPO / ".env.example"

# Defaults canônicos A15 (fallback se parse AST falhar)
_FALLBACK = {
    "db_pool_size": 20,
    "db_max_overflow": 10,
    "db_pool_recycle": 3600,
    "db_pool_timeout": 30,
    "db_pool_pre_ping": True,
}


def _parse_settings_defaults(path: Path) -> dict[str, object]:
    """Extrai defaults de db_pool_* do AST de config.py (sem importar o módulo)."""
    out: dict[str, object] = dict(_FALLBACK)
    if not path.is_file():
        return out
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        name = node.target.id
        if not name.startswith("db_pool") and name != "db_max_overflow":
            continue
        if node.value is None:
            continue
        try:
            out[name] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
    return out


def _grep_env_example(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    if not path.is_file():
        return found
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.startswith("DB_POOL") or key == "DB_MAX_OVERFLOW":
            found[key] = val.strip()
    return found


def _db_py_notes(path: Path) -> list[str]:
    notes: list[str] = []
    if not path.is_file():
        return ["db.py não encontrado"]
    text = path.read_text(encoding="utf-8")
    for needle, label in (
        ("pool_use_lifo=True", "pool_use_lifo=True (Postgres)"),
        ("pool_size=settings.db_pool_size", "pool_size ← settings"),
        ("max_overflow=settings.db_max_overflow", "max_overflow ← settings"),
        ("create_engine", "create_engine presente"),
        ("get_pool_stats", "get_pool_stats presente"),
    ):
        notes.append(f"{'OK' if needle in text else 'MISS'}: {label}")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(description="G7 pool config inventory (offline)")
    parser.add_argument(
        "--workers", type=int, default=4, help="uvicorn workers (default 4)"
    )
    parser.add_argument(
        "--pool-size",
        type=int,
        default=None,
        help="override pool_size para simular cenário (ex.: 25)",
    )
    parser.add_argument(
        "--max-overflow",
        type=int,
        default=None,
        help="override max_overflow para simular cenário",
    )
    args = parser.parse_args()

    defaults = _parse_settings_defaults(CONFIG_PY)
    pool_size = int(
        args.pool_size if args.pool_size is not None else defaults["db_pool_size"]
    )  # type: ignore[arg-type]
    max_overflow = int(
        args.max_overflow
        if args.max_overflow is not None
        else defaults["db_max_overflow"]  # type: ignore[arg-type]
    )
    cap = pool_size + max_overflow
    multi = cap * args.workers

    print("=== G7.08.T4 Connection pool inventory (offline) ===")
    print(f"config.py: {CONFIG_PY}")
    print()
    print("Defaults em backend/app/config.py (AST):")
    for k in sorted(defaults):
        print(f"  {k} = {defaults[k]!r}")
    print()
    print("backend/.env.example:")
    for k, v in sorted(_grep_env_example(ENV_BACKEND).items()):
        print(f"  {k}={v}")
    print()
    print("raiz .env.example:")
    root_env = _grep_env_example(ENV_ROOT)
    if root_env:
        for k, v in sorted(root_env.items()):
            print(f"  {k}={v}")
    else:
        print("  (sem DB_POOL_* ou arquivo ausente)")
    print()
    print("db.py checks:")
    for n in _db_py_notes(DB_PY):
        print(f"  {n}")
    print()
    print("Capacidade teórica:")
    print(f"  pool_size={pool_size} max_overflow={max_overflow} → cap/worker={cap}")
    print(f"  workers={args.workers} → cap multi-worker saturado={multi}")
    print()
    rec = 25
    print(f"Recomendação G7 (simulação pool_size={rec}):")
    print(
        f"  cap/worker={rec + max_overflow} multi={(rec + max_overflow) * args.workers}"
    )
    print()
    print("Load test live: HOLD (este script não gera carga).")
    print("Ver docs/CONNECTION_POOL_REPORT_G7.md")
    print("Modified by Gustavo Almeida")
    return 0


if __name__ == "__main__":
    sys.exit(main())
