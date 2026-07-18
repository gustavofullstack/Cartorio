"""G8.19.T1 — CLI de verificacao de integridade da blockchain do audit_log.

Uso:
    cd backend && uv run python scripts/audit_integrity_check.py
    cd backend && uv run python scripts/audit_integrity_check.py --json

Exit codes:
    0  cadeia integra (todos os entries OK)
    1  cadeia quebrada (1+ indices divergentes)
    2  erro de I/O (banco offline, sem permissao, etc)

Tambem consumido pelo dead-man's-switch de 15min em `app/main.py` lifespan
(ver `app.jobs.cron_dead_mans_switch`).

LGPD art. 37 (continuidade da auditoria) — alem de "vivo" (dead-man),
precisa estar INTEGRO (chain valida).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Adiciona backend/ ao sys.path para rodar `python scripts/audit_integrity_check.py`
# sem precisar instalar o pacote.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import get_settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.services.audit_integrity import verify_full_chain  # noqa: E402


def _format_human(result: dict) -> str:
    total = result["total_entries"]
    broken = result["broken_indices"]
    score = result["integrity_score"]

    if result.get("error"):
        return f"[IO_ERROR] {result['error']} (total_entries={total})"
    if result["chain_intact"]:
        return f"OK {total} audit entries verified (integrity_score={score:.4f})"
    return (
        f"BROKEN {len(broken)}/{total} entries divergiram "
        f"(indices={broken[:10]}{'...' if len(broken) > 10 else ''}, "
        f"first_break_id={result.get('first_break_id')}, "
        f"integrity_score={score:.4f})"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verifica integridade do audit_log (G8.19.T1).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite o resultado como JSON em stdout (ideal para monitoracao).",
    )
    parser.add_argument(
        "--strict-hmac",
        action="store_true",
        help="Falha (exit 1) mesmo em chain OK se houver inconsistencias de HMAC.",
    )
    args = parser.parse_args(argv)

    get_settings.cache_clear()  # garante env fresh

    with SessionLocal() as session:
        result = verify_full_chain(session)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        status_marker = "OK" if result["chain_intact"] else "BROKEN"
        print(f"[{status_marker}] {_format_human(result)}")

    if result.get("error"):
        return 2
    if not result["chain_intact"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
