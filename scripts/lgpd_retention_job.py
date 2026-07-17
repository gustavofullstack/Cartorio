"""LGPD retention job (G6.C.T12).

Job que anonimiza registros conforme regras de retencao LGPD art. 16:

| Entity | Retencao | Acao |
|---|---|---|
| conversa_ia_log | 90 dias | DELETE |
| audit_log | 6 meses | DELETE (LGPD art. 37 - hash chain preservado) |
| session_temp | 24h | DELETE |
| LGPDConsentLog | 5 anos | MANTEM (LGPD art. 37) |
| audit_log_hash | permanente | MANTEM (apenas hash SHA256 chain) |

Uso:
    python3 scripts/lgpd_retention_job.py --dry-run
    python3 scripts/lgpd_retention_job.py --apply
    python3 scripts/lgpd_retention_job.py --entity conversa_ia --apply

Exit codes:
    0 = OK (0 deleted ou dry-run)
    1 = erro durante delete
    2 = erro pre-requisito

Modified by Gustavo Almeida + cartorio-lgpd — G6 wave 28.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import httpx

# Database URL (Postgres only - SQLite nao suporta DELETE com regra de tempo)
RETENTION_RULES = {
    "conversa_ia_log": {"days": 90, "action": "delete", "lgpd_article": "art. 16"},
    "audit_log": {"days": 180, "action": "delete", "lgpd_article": "art. 37 (somente logs nao-hash)"},
    "session_temp": {"days": 1, "action": "delete", "lgpd_article": "art. 16"},
}


def get_db_config() -> tuple[str, str]:
    """Retorna (database_url, api_internal_key)."""
    return (
        os.environ.get("DATABASE_URL", ""),
        os.environ.get("CARTORIO_API_KEY", ""),
    )


def query_count_eligible(entity: str, days: int, base_url: str, api_key: str, timeout: float) -> int:
    """Busca contagem de items elegiveis via API interna."""
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(
                f"{base_url}/api/v1/admin/retention/preview",
                params={"entity": entity, "days": days},
                headers={"X-API-Key": api_key},
            )
            if r.status_code != 200:
                print(f"[ERROR] preview {entity}: HTTP {r.status_code}", file=sys.stderr)
                return 0
            return r.json().get("count", 0)
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 0


def execute_delete(entity: str, days: int, base_url: str, api_key: str, timeout: float) -> tuple[bool, int]:
    """Executa DELETE via API interna."""
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(
                f"{base_url}/api/v1/admin/retention/apply",
                json={"entity": entity, "days": days},
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            )
            if r.status_code == 200:
                deleted = r.json().get("deleted", 0)
                return (True, deleted)
            print(f"[ERROR] apply {entity}: HTTP {r.status_code} - {r.text[:200]}", file=sys.stderr)
            return (False, 0)
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return (False, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="LGPD retention job")
    parser.add_argument("--entity", help="entity especifica (default: todas)")
    parser.add_argument("--apply", action="store_true", help="aplicar (default: dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="so mostra (default)")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    dry_run = not args.apply
    database_url, api_key = get_db_config()

    if not database_url:
        print("[ERROR] DATABASE_URL nao definido", file=sys.stderr)
        return 2
    if not api_key:
        print("[ERROR] CARTORIO_API_KEY nao definido", file=sys.stderr)
        return 2

    base_url = os.environ.get("CARTORIO_API_URL", "http://localhost:8000")

    print(f"Mode: {'DRY-RUN' if dry_run else 'APPLY'}")
    print(f"Database: {database_url[:50]}...")
    print(f"API base: {base_url}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()

    rules_to_apply = RETENTION_RULES
    if args.entity:
        if args.entity not in RETENTION_RULES:
            print(f"[ERROR] Entity desconhecida: {args.entity}", file=sys.stderr)
            return 2
        rules_to_apply = {args.entity: RETENTION_RULES[args.entity]}

    total_eligible = 0
    total_deleted = 0
    failed = 0

    for entity, rule in rules_to_apply.items():
        days = rule["days"]
        print(f"[{entity}] retencao {days}d ({rule['lgpd_article']})")
        eligible = query_count_eligible(entity, days, base_url, api_key, args.timeout)
        total_eligible += eligible
        print(f"  elegiveis: {eligible}")

        if not dry_run and eligible > 0:
            ok, deleted = execute_delete(entity, days, base_url, api_key, args.timeout)
            if ok:
                total_deleted += deleted
                print(f"  deleted: {deleted}")
            else:
                failed += 1
                print(f"  [HOLD] delete falhou", file=sys.stderr)
        print()

    print(f"Total elegiveis: {total_eligible}")
    print(f"Total deleted: {total_deleted}")
    print(f"Failed entities: {failed}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())