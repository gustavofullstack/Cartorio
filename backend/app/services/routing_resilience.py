"""G8.10.T4 — External routing resilience simulator (packet-loss / retry backoff).

Pure in-process simulation of external HTTP routing under stochastic packet
loss. No network I/O: each attempt is a Bernoulli trial with ``fail_rate``.
On failure, retries follow an exponential backoff schedule until success or
``max_retries`` is exhausted.

Used by unit tests to quantify success_rate and retries_used under controlled
loss conditions (deterministic via RNG seed).

Modified by Gustavo Almeida — G8.10.T4 Wave 38.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

# Default exponential backoff base (seconds). Schedule: base * 2^k for k=0..
DEFAULT_BASE_DELAY_SEC: float = 1.0

# Canonical first delays for docs/tests: 1s → 2s → 4s → 8s …
DEFAULT_BACKOFF_SCHEDULE_SEC: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0, 16.0)


@dataclass(slots=True, frozen=True)
class AttemptRecord:
    """Single simulated attempt outcome."""

    request_id: int
    attempt: int  # 0-based within the request
    success: bool
    backoff_before_sec: float  # delay applied before this attempt (0 for first)


@dataclass(slots=True)
class RoutingResilienceReport:
    """Aggregate report from ``simulate_requests``."""

    n: int
    fail_rate: float
    max_retries: int
    successes: int
    failures: int
    retries_used: int
    success_rate: float
    backoff_schedule_sec: tuple[float, ...] = field(default_factory=tuple)
    total_backoff_sec: float = 0.0
    attempts: list[AttemptRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            'n': self.n,
            'fail_rate': self.fail_rate,
            'max_retries': self.max_retries,
            'successes': self.successes,
            'failures': self.failures,
            'retries_used': self.retries_used,
            'success_rate': self.success_rate,
            'backoff_schedule_sec': list(self.backoff_schedule_sec),
            'total_backoff_sec': self.total_backoff_sec,
            'attempt_count': len(self.attempts),
        }


def exponential_backoff_schedule(
    max_retries: int,
    *,
    base_delay_sec: float = DEFAULT_BASE_DELAY_SEC,
) -> tuple[float, ...]:
    """Build exponential backoff delays for retries after failures.

    After attempt ``k`` fails (k=0 first try), wait ``base * 2^k`` seconds
    before retry ``k+1``. Length equals ``max_retries`` (delays between
    attempts, not including the initial attempt).

    Examples (base=1.0):
      max_retries=0 → ()
      max_retries=3 → (1.0, 2.0, 4.0)
    """
    if max_retries < 0:
        raise ValueError('max_retries must be >= 0')
    if base_delay_sec <= 0:
        raise ValueError('base_delay_sec must be > 0')
    return tuple(base_delay_sec * (2**k) for k in range(max_retries))


def simulate_requests(
    n: int,
    fail_rate: float,
    max_retries: int,
    *,
    seed: int | None = None,
    base_delay_sec: float = DEFAULT_BASE_DELAY_SEC,
    record_attempts: bool = False,
) -> RoutingResilienceReport:
    """Simulate ``n`` external routed requests under packet loss.

    Each attempt fails independently with probability ``fail_rate`` (Bernoulli).
    A request may retry up to ``max_retries`` times after the first attempt
    (total attempts per request ≤ ``max_retries + 1``). Backoff delays are
    accumulated (no real sleep).

    Args:
        n: Number of logical requests to simulate (must be >= 0).
        fail_rate: Packet-loss / fail probability in [0.0, 1.0].
        max_retries: Max retries after the first attempt (must be >= 0).
        seed: Optional RNG seed for deterministic runs (tests).
        base_delay_sec: Base of exponential backoff (seconds).
        record_attempts: If True, attach per-attempt records (heavier).

    Returns:
        RoutingResilienceReport with success_rate, retries_used, schedule, etc.

    Raises:
        ValueError: On invalid n / fail_rate / max_retries / base_delay_sec.
    """
    if n < 0:
        raise ValueError('n must be >= 0')
    if not 0.0 <= fail_rate <= 1.0:
        raise ValueError('fail_rate must be in [0.0, 1.0]')
    if max_retries < 0:
        raise ValueError('max_retries must be >= 0')
    if base_delay_sec <= 0:
        raise ValueError('base_delay_sec must be > 0')

    schedule = exponential_backoff_schedule(max_retries, base_delay_sec=base_delay_sec)
    rng = random.Random(seed)

    successes = 0
    failures = 0
    retries_used = 0
    total_backoff = 0.0
    attempts: list[AttemptRecord] = []

    for req_id in range(n):
        succeeded = False
        for attempt in range(max_retries + 1):
            backoff = 0.0
            if attempt > 0:
                # schedule[attempt-1] is delay before this retry
                backoff = schedule[attempt - 1]
                total_backoff += backoff
                retries_used += 1

            # Independent packet-loss trial for this attempt
            ok = rng.random() >= fail_rate
            if record_attempts:
                attempts.append(
                    AttemptRecord(
                        request_id=req_id,
                        attempt=attempt,
                        success=ok,
                        backoff_before_sec=backoff,
                    )
                )
            if ok:
                succeeded = True
                break

        if succeeded:
            successes += 1
        else:
            failures += 1

    success_rate = (successes / n) if n > 0 else 1.0

    return RoutingResilienceReport(
        n=n,
        fail_rate=fail_rate,
        max_retries=max_retries,
        successes=successes,
        failures=failures,
        retries_used=retries_used,
        success_rate=success_rate,
        backoff_schedule_sec=schedule,
        total_backoff_sec=total_backoff,
        attempts=attempts if record_attempts else [],
    )
