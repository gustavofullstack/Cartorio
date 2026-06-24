"""Testes A12 — DLQ retry policy 3x exp backoff (1min/5min/15min)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.models.outbox_message import OutboxMessage, OutboxStatus
from app.services.dlq import (
    BACKOFF_SCHEDULE_SECONDS,
    MAX_ATTEMPTS,
    compute_next_retry_at,
    is_retry_due,
    retry_or_dead,
    should_retry,
)


def test_should_retry_true_quando_attempts_lt_max() -> None:
    """should_retry True para attempts < 3."""
    msg = MagicMock(spec=OutboxMessage)
    msg.attempts = 0
    assert should_retry(msg) is True
    msg.attempts = 1
    assert should_retry(msg) is True
    msg.attempts = 2
    assert should_retry(msg) is True


def test_should_retry_false_quando_attempts_gte_max() -> None:
    """should_retry False para attempts >= 3."""
    msg = MagicMock(spec=OutboxMessage)
    msg.attempts = 3
    assert should_retry(msg) is False
    msg.attempts = 5
    assert should_retry(msg) is False


def test_compute_next_retry_at_segue_backoff_schedule() -> None:
    """compute_next_retry_at retorna 1min, 5min, 15min para attempts 0,1,2."""
    before = datetime.now(tz=timezone.utc)
    t0 = compute_next_retry_at(0)
    assert (t0 - before).total_seconds() >= 58  # ~1min, tolerancia
    assert (t0 - before).total_seconds() <= 62

    t1 = compute_next_retry_at(1)
    assert (t1 - before).total_seconds() >= 298  # ~5min
    assert (t1 - before).total_seconds() <= 302

    t2 = compute_next_retry_at(2)
    assert (t2 - before).total_seconds() >= 898  # ~15min
    assert (t2 - before).total_seconds() <= 902


def test_compute_next_retry_at_passa_limite_retorna_now() -> None:
    """Apos 3 tentativas, compute_next_retry_at retorna timestamp atual."""
    before = datetime.now(tz=timezone.utc)
    t = compute_next_retry_at(3)
    assert (t - before).total_seconds() < 1


def test_is_retry_due_sem_next_retry_at() -> None:
    """Se next_retry_at eh None, esta pronto pra retry."""
    msg = MagicMock(spec=OutboxMessage)
    msg.next_retry_at = None
    assert is_retry_due(msg) is True


def test_is_retry_due_com_next_retry_at_futuro() -> None:
    """Se next_retry_at no futuro, NAO esta pronto."""
    msg = MagicMock(spec=OutboxMessage)
    msg.next_retry_at = datetime.now(tz=timezone.utc) + timedelta(minutes=10)
    assert is_retry_due(msg) is False


def test_is_retry_due_com_next_retry_at_passado() -> None:
    """Se next_retry_at no passado, esta pronto pra retry."""
    msg = MagicMock(spec=OutboxMessage)
    msg.next_retry_at = datetime.now(tz=timezone.utc) - timedelta(minutes=1)
    assert is_retry_due(msg) is True


def test_retry_or_dead_incrementa_attempts_e_set_next_retry_at() -> None:
    """retry_or_dead com attempts<3: vai pra PENDING + next_retry_at futuro."""
    db = MagicMock()
    msg = MagicMock(spec=OutboxMessage)
    msg.attempts = 0
    msg.status = OutboxStatus.PROCESSING
    result = retry_or_dead(db, msg, error="connection timeout")
    assert result == OutboxStatus.PENDING
    assert msg.attempts == 1
    assert msg.last_error == "connection timeout"
    assert msg.next_retry_at is not None
    db.commit.assert_called_once()


def test_retry_or_dead_marca_failed_apos_max_attempts() -> None:
    """retry_or_dead com attempts=3 (ja excedeu max): vai pra FAILED."""
    db = MagicMock()
    msg = MagicMock(spec=OutboxMessage)
    msg.attempts = 3
    msg.status = OutboxStatus.PROCESSING
    result = retry_or_dead(db, msg, error="connection refused")
    assert result == OutboxStatus.FAILED
    assert msg.last_error == "connection refused"
    assert msg.next_retry_at is None
    db.commit.assert_called_once()


def test_backoff_schedule_canonico() -> None:
    """Schedule canonico: 1min, 5min, 15min (60/300/900 segundos)."""
    assert MAX_ATTEMPTS == 3
    assert BACKOFF_SCHEDULE_SECONDS == (60, 300, 900)
