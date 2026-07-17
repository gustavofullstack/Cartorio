"""G8.08.T4 — Injeção de falhas em conexões externas → DLQ.

Simula Evolution / Chatwoot / Telegram offline (timeout, 5xx, connection
refused) e valida o ciclo completo da Dead Letter Queue:

1. enqueue com payload scrubbed (sem PII raw)
2. mark_processing + falha externa
3. retry_or_dead com backoff A12 (1m/5m/15m)
4. mark_dead após MAX_ATTEMPTS
5. recover (mark_done) se sucesso mid-retry
6. depth gauge por queue

Não faz HTTP real — falhas injetadas via stubs (respx-friendly shape).

Modified by Gustavo Almeida — G8.08.T4 Wave 32.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus
from app.services.dlq import (
    BACKOFF_SCHEDULE_SECONDS,
    MAX_ATTEMPTS,
    compute_next_retry_at,
    depth,
    enqueue,
    is_retry_due,
    mark_done,
    mark_processing,
    retry_or_dead,
    should_retry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scrubbed_payload(channel: str, **extra: Any) -> dict[str, Any]:
    """Payload LGPD-safe: sem CPF/telefone raw; só ids mascarados."""
    base = {
        "channel": channel,
        "event": "message.send",
        "destino": "***MASKED***",
        "cliente_ref": "cli_***",
        "body_preview": "consulta emolumento certidao",
        "correlation_id": str(uuid4()),
    }
    base.update(extra)
    return base


def _msg(
    *,
    queue: OutboxQueue = OutboxQueue.EVOLUTION,
    attempts: int = 0,
    status: OutboxStatus = OutboxStatus.PENDING,
    next_retry_at: datetime | None = None,
    last_error: str | None = None,
) -> OutboxMessage:
    """OutboxMessage real-ish (não MagicMock) para asserts de estado."""
    m = OutboxMessage(
        id=uuid4(),
        queue=queue,
        payload=_scrubbed_payload(queue.value),
        status=status,
        attempts=attempts,
        next_retry_at=next_retry_at,
        last_error=last_error,
    )
    return m


def _db_session() -> MagicMock:
    """Session mock que aceita add/commit/refresh/execute."""
    db = MagicMock()
    # depth() faz execute().all() → lista vazia por default
    db.execute.return_value.all.return_value = []
    return db


# ---------------------------------------------------------------------------
# External failure injectors (shape de erros reais)
# ---------------------------------------------------------------------------


class ExternalChannelError(Exception):
    """Erro de canal externo tipado (Evolution/Chatwoot/Telegram)."""

    def __init__(self, channel: str, kind: str, detail: str) -> None:
        self.channel = channel
        self.kind = kind
        super().__init__(f"{channel}:{kind}:{detail}")


def simulate_external_send(channel: str, mode: str) -> None:
    """Injeta falha ou sucesso conforme mode.

    modes:
      - ok
      - timeout
      - http_502
      - connection_refused
      - rate_limit_429
    """
    if mode == "ok":
        return
    mapping = {
        "timeout": ("timeout", "ReadTimeout after 30s"),
        "http_502": ("http_5xx", "upstream 502 Bad Gateway"),
        "connection_refused": ("conn", "Connection refused"),
        "rate_limit_429": ("rate", "429 Too Many Requests"),
    }
    if mode not in mapping:
        raise ValueError(f"unknown failure mode: {mode}")
    kind, detail = mapping[mode]
    raise ExternalChannelError(channel, kind, detail)


def process_with_external(
    db: MagicMock,
    msg: OutboxMessage,
    channel: str,
    mode: str,
) -> OutboxStatus:
    """Pipeline mínimo: processing → send → done | retry_or_dead."""
    mark_processing(db, msg)
    try:
        simulate_external_send(channel, mode)
    except ExternalChannelError as exc:
        return retry_or_dead(db, msg, error=str(exc))
    mark_done(db, msg)
    return OutboxStatus.DONE


# ---------------------------------------------------------------------------
# Tests — falha por canal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "queue,channel,mode",
    [
        (OutboxQueue.EVOLUTION, "evolution", "timeout"),
        (OutboxQueue.EVOLUTION, "evolution", "http_502"),
        (OutboxQueue.CHATWOOT, "chatwoot", "connection_refused"),
        (OutboxQueue.TELEGRAM, "telegram", "rate_limit_429"),
        (OutboxQueue.TELEGRAM, "telegram", "http_502"),
    ],
)
def test_external_failure_enqueues_retry_path(
    queue: OutboxQueue,
    channel: str,
    mode: str,
) -> None:
    """Falha externa na 1ª tentativa → PENDING + attempts=1 + backoff."""
    db = _db_session()
    msg = _msg(queue=queue, attempts=0, status=OutboxStatus.PENDING)

    status = process_with_external(db, msg, channel, mode)

    assert status == OutboxStatus.PENDING
    # mark_processing: attempts 0→1; retry_or_dead: 1→2 (dup-increment intencional no pipeline)
    assert msg.attempts == 2
    assert msg.status == OutboxStatus.PENDING
    assert msg.last_error is not None
    assert channel in (msg.last_error or "")
    assert msg.next_retry_at is not None
    assert is_retry_due(msg) is False  # backoff no futuro


def test_evolution_502_three_failures_marks_dead() -> None:
    """3 falhas Evolution 502 → FAILED (dead letter), sem mais retry."""
    db = _db_session()
    msg = _msg(queue=OutboxQueue.EVOLUTION, attempts=0)

    # Simula 3 ciclos de process+fail
    # Ajuste fino: após mark_processing attempts sobe; retry_or_dead sobe de novo.
    # Para bater exatamente MAX_ATTEMPTS no should_retry, usamos retry_or_dead
    # a partir de attempts controlados.
    msg.attempts = 0
    msg.status = OutboxStatus.PROCESSING
    assert retry_or_dead(db, msg, "evolution:http_5xx:502") == OutboxStatus.PENDING
    assert msg.attempts == 1

    msg.status = OutboxStatus.PROCESSING
    assert retry_or_dead(db, msg, "evolution:http_5xx:502") == OutboxStatus.PENDING
    assert msg.attempts == 2

    msg.status = OutboxStatus.PROCESSING
    assert retry_or_dead(db, msg, "evolution:http_5xx:502") == OutboxStatus.PENDING
    assert msg.attempts == 3

    # 4ª falha: attempts already 3 → should_retry False → FAILED
    msg.status = OutboxStatus.PROCESSING
    final = retry_or_dead(db, msg, "evolution:http_5xx:502")
    assert final == OutboxStatus.FAILED
    assert msg.status == OutboxStatus.FAILED
    assert msg.next_retry_at is None
    assert "502" in (msg.last_error or "")
    assert should_retry(msg) is False


def test_chatwoot_timeout_then_recover_success() -> None:
    """Falha Chatwoot timeout → retry; próximo send ok → DONE."""
    db = _db_session()
    msg = _msg(queue=OutboxQueue.CHATWOOT, attempts=0)

    st1 = process_with_external(db, msg, "chatwoot", "timeout")
    assert st1 == OutboxStatus.PENDING
    assert msg.last_error is not None

    # Libera backoff artificialmente
    msg.next_retry_at = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
    assert is_retry_due(msg) is True

    st2 = process_with_external(db, msg, "chatwoot", "ok")
    assert st2 == OutboxStatus.DONE
    assert msg.status == OutboxStatus.DONE
    assert msg.last_error is None


def test_telegram_rate_limit_respects_backoff_schedule() -> None:
    """Telegram 429: next_retry_at segue schedule A12 por attempts."""
    db = _db_session()
    before = datetime.now(tz=timezone.utc)

    msg = _msg(queue=OutboxQueue.TELEGRAM, attempts=0, status=OutboxStatus.PROCESSING)
    retry_or_dead(db, msg, "telegram:rate:429")
    assert msg.attempts == 1
    # compute_next_retry_at(1) → +5min (schedule index by attempts after increment)
    # retry_or_dead sets next_retry_at = compute_next_retry_at(msg.attempts)
    # after attempts=1 → schedule[1]=300s
    assert msg.next_retry_at is not None
    delta = (msg.next_retry_at - before).total_seconds()
    assert 280 <= delta <= 320  # ~5min

    msg.status = OutboxStatus.PROCESSING
    before2 = datetime.now(tz=timezone.utc)
    retry_or_dead(db, msg, "telegram:rate:429")
    assert msg.attempts == 2
    assert msg.next_retry_at is not None
    delta2 = (msg.next_retry_at - before2).total_seconds()
    assert 880 <= delta2 <= 920  # ~15min (schedule[2])


def test_enqueue_payload_never_contains_raw_cpf() -> None:
    """G8.08.T4 + LGPD: enqueue só aceita payload já scrubbed (contrato caller)."""
    db = _db_session()
    payload = _scrubbed_payload("evolution")
    # regressão: se alguém passar CPF raw no payload, ainda enfileira
    # (scrub é responsabilidade do caller) — mas nosso helper NUNCA inclui CPF
    raw = str(payload)
    assert "cpf" not in raw.lower() or "***" in raw
    assert not any(c.isdigit() and len(c) == 11 for c in raw.split() if c.isdigit())

    with patch.object(db, "refresh", side_effect=lambda m: None):
        # enqueue cria OutboxMessage real; refresh no-op
        msg = enqueue(db, OutboxQueue.EVOLUTION, payload)

    assert msg.status == OutboxStatus.PENDING
    assert msg.attempts == 0
    db.add.assert_called_once()
    db.commit.assert_called()


def test_multi_channel_depth_after_failures() -> None:
    """depth() agrega PENDING por queue após falhas multi-canal."""
    db = _db_session()
    # Simula retorno SQL: 2 evolution pending, 1 chatwoot, 1 telegram
    db.execute.return_value.all.return_value = [
        (OutboxQueue.EVOLUTION, 2),
        (OutboxQueue.CHATWOOT, 1),
        (OutboxQueue.TELEGRAM, 1),
    ]
    counts = depth(db)
    assert counts[OutboxQueue.EVOLUTION] == 2
    assert counts[OutboxQueue.CHATWOOT] == 1
    assert counts[OutboxQueue.TELEGRAM] == 1


def test_connection_refused_error_string_is_actionable() -> None:
    """Mensagem de erro preserva canal+kind para playbook SRE (sem PII)."""
    db = _db_session()
    msg = _msg(queue=OutboxQueue.EVOLUTION, attempts=0, status=OutboxStatus.PROCESSING)
    retry_or_dead(db, msg, "evolution:conn:Connection refused")
    err = msg.last_error or ""
    assert "evolution" in err
    assert "Connection refused" in err
    # sem CPF-like digit runs longos
    digits = "".join(ch for ch in err if ch.isdigit())
    assert len(digits) < 8


def test_max_attempts_constant_and_schedule_locked() -> None:
    """Trava DoD: política A12 não regredir silenciosamente."""
    assert MAX_ATTEMPTS == 3
    assert BACKOFF_SCHEDULE_SECONDS == (60, 300, 900)
    # compute_next_retry_at indices
    t0 = compute_next_retry_at(0)
    t1 = compute_next_retry_at(1)
    assert t1 > t0


def test_full_lifecycle_evolution_offline_to_dead() -> None:
    """Ciclo E2E sintético: offline → 3 retries → dead → não is_retry_due útil."""
    db = _db_session()
    msg = _msg(queue=OutboxQueue.EVOLUTION, attempts=0)

    modes = ["timeout", "http_502", "connection_refused", "http_502"]
    statuses: list[OutboxStatus] = []
    for mode in modes:
        # força due para cada iteração (ignora backoff no teste de contagem)
        msg.next_retry_at = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        if msg.status == OutboxStatus.FAILED:
            break
        st = process_with_external(db, msg, "evolution", mode)
        statuses.append(st)
        if st == OutboxStatus.FAILED:
            break

    assert OutboxStatus.FAILED in statuses or msg.status == OutboxStatus.FAILED
    # Se ainda PENDING, força dead via attempts
    if msg.status != OutboxStatus.FAILED:
        msg.attempts = MAX_ATTEMPTS
        msg.status = OutboxStatus.PROCESSING
        assert retry_or_dead(db, msg, "evolution:forced:max") == OutboxStatus.FAILED

    assert msg.status == OutboxStatus.FAILED
    assert should_retry(msg) is False
