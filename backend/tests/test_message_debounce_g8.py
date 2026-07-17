"""G8.02.T3 — Unit tests for message_debounce pure helpers.

Cobre:
  - should_start_debounce: só queue_len == 1 dispara janela
  - merge_burst_texts: empty / 1-2 / burst 3+ / whitespace / truncate
  - is_duplicate_update: first vs replay, falsy ids, mutates set

Modified by Gustavo Almeida — G8.02.T3.
"""

from __future__ import annotations

from app.services.message_debounce import (
    BURST_JOIN_MAX_CHARS,
    BURST_RESUME_THRESHOLD,
    DEBOUNCE_WINDOW_SEC,
    is_duplicate_update,
    merge_burst_texts,
    should_start_debounce,
)


class TestConstants:
    def test_window_matches_pipeline(self) -> None:
        assert DEBOUNCE_WINDOW_SEC == 1.2

    def test_burst_threshold_is_two(self) -> None:
        assert BURST_RESUME_THRESHOLD == 2

    def test_join_cap(self) -> None:
        assert BURST_JOIN_MAX_CHARS == 600


class TestShouldStartDebounce:
    def test_first_message_starts(self) -> None:
        assert should_start_debounce(1) is True

    def test_second_message_does_not_restart(self) -> None:
        assert should_start_debounce(2) is False

    def test_longer_queue_does_not_restart(self) -> None:
        assert should_start_debounce(10) is False

    def test_empty_queue_does_not_start(self) -> None:
        assert should_start_debounce(0) is False

    def test_negative_does_not_start(self) -> None:
        assert should_start_debounce(-1) is False

    def test_string_one_coerces(self) -> None:
        assert should_start_debounce("1") is True  # type: ignore[arg-type]

    def test_invalid_type_false(self) -> None:
        assert should_start_debounce(None) is False  # type: ignore[arg-type]
        assert should_start_debounce("x") is False  # type: ignore[arg-type]


class TestMergeBurstTexts:
    def test_none_and_empty(self) -> None:
        assert merge_burst_texts(None) == ""
        assert merge_burst_texts([]) == ""

    def test_only_whitespace(self) -> None:
        assert merge_burst_texts(["  ", "", "\n"]) == ""

    def test_single_text(self) -> None:
        assert merge_burst_texts(["ola"]) == "ola"

    def test_two_texts_returns_last(self) -> None:
        # espelha resume_burst: <=2 → último
        assert merge_burst_texts(["oi", "quero certidao"]) == "quero certidao"

    def test_three_plus_summarizes(self) -> None:
        out = merge_burst_texts(["a", "b", "c"])
        assert out.startswith("[3 mensagens] ")
        assert "a | b | c" in out

    def test_strips_and_skips_empty_in_burst(self) -> None:
        out = merge_burst_texts([" a ", "", "  b  ", "c"])
        assert out.startswith("[3 mensagens] ")
        assert out.endswith("a | b | c") or "a | b | c" in out

    def test_truncates_long_join(self) -> None:
        long_parts = [f"msg{i}-{'x' * 50}" for i in range(20)]
        out = merge_burst_texts(long_parts)
        assert out.startswith(f"[{len(long_parts)} mensagens] ")
        body = out.split("] ", 1)[1]
        assert len(body) <= BURST_JOIN_MAX_CHARS

    def test_preserves_order(self) -> None:
        out = merge_burst_texts(["primeiro", "segundo", "terceiro"])
        assert "primeiro | segundo | terceiro" in out


class TestIsDuplicateUpdate:
    def test_first_seen_not_duplicate(self) -> None:
        seen: set[int] = set()
        assert is_duplicate_update(seen, 1001) is False
        assert 1001 in seen

    def test_second_time_is_duplicate(self) -> None:
        seen: set[int] = set()
        assert is_duplicate_update(seen, 1001) is False
        assert is_duplicate_update(seen, 1001) is True
        assert seen == {1001}

    def test_different_ids_independent(self) -> None:
        seen: set[int] = set()
        assert is_duplicate_update(seen, 1) is False
        assert is_duplicate_update(seen, 2) is False
        assert is_duplicate_update(seen, 1) is True
        assert is_duplicate_update(seen, 2) is True

    def test_falsy_ids_never_duplicate(self) -> None:
        seen: set[object] = set()
        assert is_duplicate_update(seen, None) is False
        assert is_duplicate_update(seen, 0) is False
        assert is_duplicate_update(seen, "") is False
        assert seen == set()  # não polui o set

    def test_string_update_ids(self) -> None:
        seen: set[str] = set()
        assert is_duplicate_update(seen, "upd-9") is False
        assert is_duplicate_update(seen, "upd-9") is True

    def test_burst_window_simulation(self) -> None:
        """Simula webhook redelivery na mesma janela de debounce."""
        seen: set[int] = set()
        # 3 updates distintos + 1 replay do primeiro
        incoming = [10, 11, 10, 12]
        accepted: list[int] = []
        for uid in incoming:
            if not is_duplicate_update(seen, uid):
                accepted.append(uid)
        assert accepted == [10, 11, 12]
        assert should_start_debounce(len(accepted[:1])) is True
        # após 1º aceito, próximos enqueues não re-disparam
        assert should_start_debounce(2) is False
        assert should_start_debounce(3) is False


class TestWorkflowIntegration:
    """Fluxo mínimo: dedupe → enqueue decision → merge."""

    def test_duplicate_then_burst_merge(self) -> None:
        seen: set[int] = set()
        queue: list[str] = []
        started = 0

        events = [
            (501, "oi"),
            (502, "preciso de certidao"),
            (501, "oi"),  # redelivery
            (503, "nascimento"),
        ]
        for uid, text in events:
            if is_duplicate_update(seen, uid):
                continue
            queue.append(text)
            if should_start_debounce(len(queue)):
                started += 1

        assert started == 1
        assert queue == ["oi", "preciso de certidao", "nascimento"]
        merged = merge_burst_texts(queue)
        assert merged.startswith("[3 mensagens]")
        assert "nascimento" in merged
