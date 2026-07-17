"""G8.10.T4 — Simulador de resiliência de roteamento (packet loss + retry).

Modified by Gustavo Almeida — Wave 42.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(slots=True)
class ResilienceReport:
    attempts: int
    successes: int
    failures: int
    retries_used: int
    success_rate: float


def backoff_delays(max_retries: int, base: float = 0.05) -> list[float]:
    return [base * (2**i) for i in range(max_retries)]


def simulate_requests(
    n: int,
    fail_rate: float,
    max_retries: int = 3,
    *,
    seed: int = 42,
) -> ResilienceReport:
    """Simula n requests com fail_rate e retries (determinístico via seed)."""
    rng = random.Random(seed)
    successes = 0
    failures = 0
    retries_used = 0
    attempts = 0
    for _ in range(max(0, n)):
        ok = False
        for attempt in range(max_retries + 1):
            attempts += 1
            if attempt > 0:
                retries_used += 1
            if rng.random() >= fail_rate:
                ok = True
                break
        if ok:
            successes += 1
        else:
            failures += 1
    total = successes + failures
    rate = (successes / total) if total else 0.0
    return ResilienceReport(
        attempts=attempts,
        successes=successes,
        failures=failures,
        retries_used=retries_used,
        success_rate=rate,
    )


__all__ = ['ResilienceReport', 'backoff_delays', 'simulate_requests']
