"""G8.02.T1 — dialog history token budget tests.

Modified by Gustavo Almeida — Wave 35.
"""

from __future__ import annotations

from app.services.dialog_history import (
    DialogHistoryConfig,
    apply_entry_cap,
    estimate_tokens,
    prepare_history_for_store,
    trim_history_to_token_budget,
)


def test_estimate_tokens_basic() -> None:
    assert estimate_tokens('') == 0
    assert estimate_tokens('abcd') == 1
    assert estimate_tokens('a' * 40) == 10


def test_trim_drops_oldest() -> None:
    hist = [f'user: turn {i} ' + ('x' * 40) for i in range(20)]
    out = trim_history_to_token_budget(hist, max_tokens=30, min_keep=2)
    assert len(out) < len(hist)
    assert out[-1].startswith('user: turn')


def test_min_keep_respected() -> None:
    hist = [f'msg {i}' for i in range(10)]
    out = trim_history_to_token_budget(hist, max_tokens=1, min_keep=3)
    assert len(out) >= 3


def test_empty_ok() -> None:
    assert trim_history_to_token_budget([], 100) == []


def test_entry_cap() -> None:
    hist = [str(i) for i in range(50)]
    assert len(apply_entry_cap(hist, 10)) == 10


def test_prepare_history() -> None:
    cfg = DialogHistoryConfig(max_entries=5, max_tokens=50, min_keep=2)
    hist = [f'user: {i} ' + ('y' * 80) for i in range(20)]
    out = prepare_history_for_store(hist, config=cfg)
    assert len(out) <= 5
