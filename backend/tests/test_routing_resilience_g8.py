"""G8.10.T4 — External routing resilience (packet-loss / retry backoff) unit tests.

Pure simulation: no network. Deterministic via fixed RNG seed.

Modified by Gustavo Almeida — G8.10.T4 Wave 38.
"""

from __future__ import annotations

import pytest

from app.services.routing_resilience import (
    DEFAULT_BACKOFF_SCHEDULE_SEC,
    RoutingResilienceReport,
    exponential_backoff_schedule,
    simulate_requests,
)

# Fixed seed for all stochastic assertions in this module
SEED = 42


# ---------------------------------------------------------------------------
# Backoff schedule
# ---------------------------------------------------------------------------


def test_exponential_backoff_schedule_canonical() -> None:
    assert exponential_backoff_schedule(0) == ()
    assert exponential_backoff_schedule(3) == (1.0, 2.0, 4.0)
    assert exponential_backoff_schedule(5) == DEFAULT_BACKOFF_SCHEDULE_SEC


def test_exponential_backoff_custom_base() -> None:
    assert exponential_backoff_schedule(3, base_delay_sec=0.5) == (0.5, 1.0, 2.0)


def test_exponential_backoff_rejects_invalid() -> None:
    with pytest.raises(ValueError, match='max_retries'):
        exponential_backoff_schedule(-1)
    with pytest.raises(ValueError, match='base_delay'):
        exponential_backoff_schedule(1, base_delay_sec=0)


# ---------------------------------------------------------------------------
# simulate_requests — validation
# ---------------------------------------------------------------------------


def test_simulate_rejects_bad_params() -> None:
    with pytest.raises(ValueError, match='n must'):
        simulate_requests(-1, 0.1, 1)
    with pytest.raises(ValueError, match='fail_rate'):
        simulate_requests(1, 1.5, 1)
    with pytest.raises(ValueError, match='fail_rate'):
        simulate_requests(1, -0.01, 1)
    with pytest.raises(ValueError, match='max_retries'):
        simulate_requests(1, 0.1, -1)


def test_simulate_zero_requests() -> None:
    report = simulate_requests(0, 0.5, 3, seed=SEED)
    assert report.n == 0
    assert report.successes == 0
    assert report.failures == 0
    assert report.retries_used == 0
    assert report.success_rate == 1.0
    assert report.backoff_schedule_sec == (1.0, 2.0, 4.0)


# ---------------------------------------------------------------------------
# Determinism + extremes
# ---------------------------------------------------------------------------


def test_deterministic_same_seed() -> None:
    a = simulate_requests(200, 0.4, 3, seed=SEED)
    b = simulate_requests(200, 0.4, 3, seed=SEED)
    assert a.successes == b.successes
    assert a.failures == b.failures
    assert a.retries_used == b.retries_used
    assert a.success_rate == b.success_rate
    assert a.total_backoff_sec == b.total_backoff_sec


def test_different_seeds_may_differ() -> None:
    a = simulate_requests(100, 0.5, 2, seed=1)
    b = simulate_requests(100, 0.5, 2, seed=2)
    # Extremely unlikely to match on all counters with different seeds
    assert (a.successes, a.retries_used) != (b.successes, b.retries_used)


def test_zero_fail_rate_perfect_success() -> None:
    report = simulate_requests(50, 0.0, 3, seed=SEED)
    assert report.successes == 50
    assert report.failures == 0
    assert report.success_rate == 1.0
    assert report.retries_used == 0
    assert report.total_backoff_sec == 0.0


def test_full_fail_rate_no_retries_all_fail() -> None:
    report = simulate_requests(20, 1.0, 0, seed=SEED)
    assert report.successes == 0
    assert report.failures == 20
    assert report.success_rate == 0.0
    assert report.retries_used == 0


def test_full_fail_rate_with_retries_still_fails() -> None:
    """fail_rate=1.0 → every attempt fails; retries_used = n * max_retries."""
    n, max_retries = 10, 3
    report = simulate_requests(n, 1.0, max_retries, seed=SEED)
    assert report.successes == 0
    assert report.failures == n
    assert report.retries_used == n * max_retries
    # Backoff sum per request: 1+2+4 = 7
    assert report.total_backoff_sec == n * (1.0 + 2.0 + 4.0)
    assert report.backoff_schedule_sec == (1.0, 2.0, 4.0)


def test_retries_improve_success_under_loss() -> None:
    """Same seed + fail_rate: more retries ⇒ success_rate >= with fewer retries."""
    low = simulate_requests(500, 0.5, 0, seed=SEED)
    high = simulate_requests(500, 0.5, 5, seed=SEED)
    assert high.success_rate >= low.success_rate
    assert high.retries_used >= low.retries_used


# ---------------------------------------------------------------------------
# Report shape + attempt recording
# ---------------------------------------------------------------------------


def test_report_to_dict_keys() -> None:
    report = simulate_requests(5, 0.2, 2, seed=SEED)
    d = report.to_dict()
    assert d['n'] == 5
    assert d['fail_rate'] == 0.2
    assert d['max_retries'] == 2
    assert 'success_rate' in d
    assert 'retries_used' in d
    assert d['backoff_schedule_sec'] == [1.0, 2.0]
    assert d['successes'] + d['failures'] == 5


def test_record_attempts_shape() -> None:
    report = simulate_requests(3, 1.0, 2, seed=SEED, record_attempts=True)
    # 3 requests × (1 initial + 2 retries) = 9 attempts, all fail
    assert len(report.attempts) == 9
    assert all(not a.success for a in report.attempts)
    # First attempt of each request has zero backoff
    firsts = [a for a in report.attempts if a.attempt == 0]
    assert len(firsts) == 3
    assert all(a.backoff_before_sec == 0.0 for a in firsts)
    # Retry attempts follow schedule
    retries = [a for a in report.attempts if a.attempt > 0]
    for a in retries:
        assert a.backoff_before_sec == report.backoff_schedule_sec[a.attempt - 1]


def test_seeded_known_success_count() -> None:
    """Lock a known outcome for seed=42 so regressions are visible."""
    report = simulate_requests(100, 0.3, 2, seed=SEED)
    assert isinstance(report, RoutingResilienceReport)
    assert 0 <= report.success_rate <= 1.0
    assert report.successes + report.failures == 100
    # With fail_rate=0.3 and 2 retries, success should be high but not perfect
    assert report.successes >= 90
    # Pin exact counters for seed=42 (regression lock — current RNG path)
    assert report.successes == 96
    assert report.failures == 4
    assert report.retries_used == 47
