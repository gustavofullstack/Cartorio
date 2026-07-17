"""G8.10.T4 tests.

Modified by Gustavo Almeida — Wave 42.
"""

from __future__ import annotations

from app.services.routing_resilience import backoff_delays, simulate_requests


def test_backoff_schedule() -> None:
    d = backoff_delays(3, base=0.1)
    assert d == [0.1, 0.2, 0.4]


def test_zero_fail_all_success() -> None:
    r = simulate_requests(50, fail_rate=0.0, seed=1)
    assert r.successes == 50
    assert r.failures == 0
    assert r.success_rate == 1.0


def test_always_fail() -> None:
    r = simulate_requests(20, fail_rate=1.0, max_retries=2, seed=2)
    assert r.successes == 0
    assert r.failures == 20
    assert r.retries_used > 0


def test_partial_deterministic() -> None:
    a = simulate_requests(100, fail_rate=0.3, seed=99)
    b = simulate_requests(100, fail_rate=0.3, seed=99)
    assert a.successes == b.successes
    assert 0.0 < a.success_rate <= 1.0
