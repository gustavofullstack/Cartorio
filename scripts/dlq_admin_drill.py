#!/usr/bin/env python3
"""DLQ admin drill (G7.10.T2) — dry-run checklist + local policy validation.

Nao toca prod. Valida backoff 1m/5m/15m e imprime curl templates
para endpoints admin (requer X-API-Key em runtime).

Uso:
  python3 scripts/dlq_admin_drill.py
  python3 scripts/dlq_admin_drill.py --json

Modified by Gustavo Almeida — G7 Wave 18.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# Backoff canonical (must match app.services.dlq)
BACKOFF_SECONDS = (60, 300, 900)  # 1m, 5m, 15m
MAX_ATTEMPTS = 3


def compute_next_retry_at_seconds(attempts: int) -> int:
    """Mirror dlq.compute_next_retry_at: index = attempts into (60,300,900)."""
    if attempts >= len(BACKOFF_SECONDS):
        return 0
    return BACKOFF_SECONDS[attempts]


def run_policy_checks() -> list[dict]:
    checks = []
    for attempts in range(0, MAX_ATTEMPTS + 1):
        delay = compute_next_retry_at_seconds(attempts)
        checks.append(
            {
                "attempts": attempts,
                "delay_s": delay,
                "should_retry": attempts < MAX_ATTEMPTS,
            }
        )
    # Import real module if available
    try:
        from app.services.dlq import (  # type: ignore
            BACKOFF_SCHEDULE_SECONDS,
            MAX_ATTEMPTS as REAL_MAX,
            compute_next_retry_at,
        )

        now = datetime.now(timezone.utc)
        for attempts in range(0, 3):
            nxt = compute_next_retry_at(attempts)
            if nxt.tzinfo is None:
                nxt = nxt.replace(tzinfo=timezone.utc)
            delta = (nxt - now).total_seconds()
            expected = float(BACKOFF_SCHEDULE_SECONDS[attempts])
            ok = abs(delta - expected) < 5  # clock skew tolerance
            checks.append(
                {
                    "check": f"real_compute_next_retry_at attempts={attempts}",
                    "ok": ok,
                    "delta_s": round(delta, 1),
                    "expected_s": expected,
                    "max_attempts": REAL_MAX,
                }
            )
    except Exception as exc:
        checks.append({"check": "import_dlq", "ok": False, "error": str(exc)})
    return checks


def curl_templates(base: str = "https://api.2notasudi.com.br") -> list[str]:
    return [
        f'curl -sS -H "X-API-Key: $CARTORIO_API_KEY" {base}/api/v1/metrics/prometheus | rg dlq',
        f'curl -sS -X POST -H "X-API-Key: $CARTORIO_API_KEY" '
        f'-H "Content-Type: application/json" '
        f'-d \'{{"queue":"evolution","payload":{{"drill":true}}}}\' '
        f"{base}/api/v1/dlq/evolution/enqueue",
        "# Apos enqueue: admin list/retry endpoints conforme router (ver OpenAPI /docs)",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    checks = run_policy_checks()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "max_attempts": MAX_ATTEMPTS,
            "backoff_s": list(BACKOFF_SECONDS),
        },
        "checks": checks,
        "curl": curl_templates(),
        "verdict": "WORK"
        if all(c.get("ok", True) for c in checks if "ok" in c)
        else "HOLD",
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"DLQ admin drill — {report['verdict']}")
        print(f"  backoff: {BACKOFF_SECONDS} max_attempts={MAX_ATTEMPTS}")
        for c in checks:
            print(f"  {c}")
        print("  curls:")
        for line in report["curl"]:
            print(f"    {line}")
    return 0 if report["verdict"] == "WORK" else 1


if __name__ == "__main__":
    sys.exit(main())
