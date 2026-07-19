"""Contrato do worker de retries vencidos do outbox.

Sem rede real: o dispatcher e injetado para verificar o lifecycle, limite de
lote, lock fail-closed e a ausencia de detalhes sensiveis no erro persistido.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.jobs import outbox_retry
from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus


def _due_message(*, attempts: int = 1, offset_seconds: int = -60) -> OutboxMessage:
    return OutboxMessage(
        id=uuid4(),
        queue=OutboxQueue.OUTBOX,
        payload={"message_id": "masked-event"},
        status=OutboxStatus.FAILED,
        attempts=attempts,
        next_retry_at=datetime.now(timezone.utc) + timedelta(seconds=offset_seconds),
    )


def _grant_lock(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    released: list[tuple[str, str]] = []
    monkeypatch.setattr(outbox_retry, "acquire_lock", lambda _name, ttl_seconds: "owner-token")
    monkeypatch.setattr(
        outbox_retry,
        "release_lock",
        lambda name, token: released.append((name, token)) or True,
    )
    return released


@pytest.mark.asyncio
async def test_due_message_is_delivered_once_and_marked_done(db_session, monkeypatch) -> None:
    message = _due_message()
    db_session.add(message)
    db_session.commit()
    released = _grant_lock(monkeypatch)
    sent: list[tuple[OutboxQueue, dict]] = []

    async def dispatcher(queue: OutboxQueue, payload: dict) -> None:
        sent.append((queue, payload))

    result = await outbox_retry.run_due_outbox_retries(
        db_session,
        dispatcher=dispatcher,
        now=datetime.now(timezone.utc),
    )

    row = db_session.get(OutboxMessage, message.id)
    assert result == outbox_retry.OutboxRetryRunResult(True, 1, 1, 0, 0)
    assert sent == [(OutboxQueue.OUTBOX, {"message_id": "masked-event"})]
    assert row is not None
    assert row.status == OutboxStatus.DONE
    assert row.attempts == 2
    assert row.next_retry_at is None
    assert released == [(outbox_retry.DEFAULT_LOCK_NAME, "owner-token")]


@pytest.mark.asyncio
async def test_failure_is_rescheduled_without_persisting_upstream_detail(
    db_session, monkeypatch
) -> None:
    message = _due_message(attempts=1)
    db_session.add(message)
    db_session.commit()
    _grant_lock(monkeypatch)

    async def failing_dispatcher(_queue: OutboxQueue, _payload: dict) -> None:
        raise RuntimeError("upstream failure with redacted data")

    before = datetime.now(timezone.utc)
    result = await outbox_retry.run_due_outbox_retries(
        db_session,
        dispatcher=failing_dispatcher,
        now=before,
    )

    row = db_session.get(OutboxMessage, message.id)
    assert result == outbox_retry.OutboxRetryRunResult(True, 1, 0, 1, 0)
    assert row is not None
    assert row.status == OutboxStatus.FAILED
    assert row.attempts == 2
    assert row.next_retry_at is not None and row.next_retry_at > before
    assert row.last_error == "dispatch_failed:RuntimeError"


@pytest.mark.asyncio
async def test_final_failure_is_dead_lettered_without_another_retry(
    db_session, monkeypatch
) -> None:
    message = _due_message(attempts=2)
    db_session.add(message)
    db_session.commit()
    _grant_lock(monkeypatch)

    async def failing_dispatcher(_queue: OutboxQueue, _payload: dict) -> None:
        raise TimeoutError("upstream diagnostic")

    result = await outbox_retry.run_due_outbox_retries(
        db_session,
        dispatcher=failing_dispatcher,
        now=datetime.now(timezone.utc),
    )

    row = db_session.get(OutboxMessage, message.id)
    assert result == outbox_retry.OutboxRetryRunResult(True, 1, 0, 0, 1)
    assert row is not None
    assert row.status == OutboxStatus.FAILED
    assert row.attempts == 3
    assert row.next_retry_at is None
    assert row.last_error == "dispatch_failed:TimeoutError"


@pytest.mark.asyncio
async def test_busy_or_unavailable_lock_is_fail_closed(db_session, monkeypatch) -> None:
    message = _due_message()
    db_session.add(message)
    db_session.commit()
    monkeypatch.setattr(outbox_retry, "acquire_lock", lambda _name, ttl_seconds: None)
    invoked = False

    async def dispatcher(_queue: OutboxQueue, _payload: dict) -> None:
        nonlocal invoked
        invoked = True

    result = await outbox_retry.run_due_outbox_retries(db_session, dispatcher=dispatcher)

    row = db_session.get(OutboxMessage, message.id)
    assert result == outbox_retry.OutboxRetryRunResult(False, 0, 0, 0, 0)
    assert invoked is False
    assert row is not None and row.status == OutboxStatus.FAILED


@pytest.mark.asyncio
async def test_batch_limit_only_claims_due_retryable_messages(db_session, monkeypatch) -> None:
    first = _due_message()
    second = _due_message()
    future = _due_message(offset_seconds=300)
    exhausted = _due_message(attempts=3)
    db_session.add_all([first, second, future, exhausted])
    db_session.commit()
    _grant_lock(monkeypatch)
    delivered: list[OutboxQueue] = []

    async def dispatcher(queue: OutboxQueue, _payload: dict) -> None:
        delivered.append(queue)

    result = await outbox_retry.run_due_outbox_retries(
        db_session,
        dispatcher=dispatcher,
        now=datetime.now(timezone.utc),
        batch_limit=1,
    )

    assert result == outbox_retry.OutboxRetryRunResult(True, 1, 1, 0, 0)
    assert delivered == [OutboxQueue.OUTBOX]
    statuses = {item.id: item.status for item in (first, second, future, exhausted)}
    assert list(statuses.values()).count(OutboxStatus.DONE) == 1
    assert future.status == OutboxStatus.FAILED
    assert exhausted.status == OutboxStatus.FAILED


@pytest.mark.asyncio
async def test_invalid_batch_limit_is_rejected_before_lock(db_session) -> None:
    with pytest.raises(ValueError, match="batch_limit"):
        await outbox_retry.run_due_outbox_retries(db_session, batch_limit=0)
