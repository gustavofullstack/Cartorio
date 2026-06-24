"""Services DLQ - Dead Letter Queue para integracoes externas.

Permite enfileirar mensagens que falharam ao enviar (WhatsApp offline,
Chatwoot rate limit, etc) para reprocessamento assincrono.

Instrumentacao A2:
- `dlq_depth{queue}` gauge - atualizado em cada enqueue/mark_done/mark_failed

Retry policy A12:
- 3 tentativas max com exponential backoff: 1min, 5min, 15min.
- Apos 3 falhas, mensagem vai para FAILED (mark_dead).
- next_retry_at eh timestamp UTC ate quando NAO deve reprocessar.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus
from app.services.metrics import store as metrics_store


# A12: retry policy — 3 tentativas, backoff 1min/5min/15min
MAX_ATTEMPTS = 3
BACKOFF_SCHEDULE_SECONDS: tuple[int, ...] = (60, 300, 900)  # 1min, 5min, 15min


def should_retry(msg: OutboxMessage) -> bool:
    """Retorna True se a mensagem ainda pode ser reprocessada.

    Logica: attempts < MAX_ATTEMPTS. Caller deve checar tambem next_retry_at
    para respeitar o backoff schedule.
    """
    return msg.attempts < MAX_ATTEMPTS


def compute_next_retry_at(attempts: int) -> datetime:
    """Calcula proximo timestamp permitido pra retry (UTC).

    attempts=0 (acabou de falhar a 1a vez) -> +1min
    attempts=1 (acabou de falhar a 2a vez) -> +5min
    attempts=2 (acabou de falhar a 3a vez) -> +15min
    attempts>=3 -> retorna timestamp atual (ja passou de tudo, caller deve
    chamar mark_dead).
    """
    if attempts >= len(BACKOFF_SCHEDULE_SECONDS):
        return datetime.now(tz=timezone.utc)
    delta = BACKOFF_SCHEDULE_SECONDS[attempts]
    return datetime.now(tz=timezone.utc) + timedelta(seconds=delta)


def is_retry_due(msg: OutboxMessage, now: datetime | None = None) -> bool:
    """Verifica se o backoff schedule permite retry agora.

    Returns:
        True se (next_retry_at IS NULL) OR (next_retry_at <= now).
    """
    if msg.next_retry_at is None:
        return True
    now = now or datetime.now(tz=timezone.utc)
    return msg.next_retry_at <= now


def retry_or_dead(
    db: Session,
    msg: OutboxMessage,
    error: str,
) -> OutboxStatus:
    """Decide entre retry (mark_failed) ou dead (mark_dead) baseado em attempts.

    Returns:
        Novo status (PENDING se vai retry, FAILED se morreu).

    Side effects:
        - Se retry: msg.attempts += 1, next_retry_at = compute_next_retry_at(attempts).
        - Se dead: msg.status = FAILED.
        - Atualiza gauge dlq_depth.
    """
    if should_retry(msg):
        # Ainda da pra tentar
        msg.attempts += 1
        msg.last_error = error
        msg.next_retry_at = compute_next_retry_at(msg.attempts)
        msg.status = OutboxStatus.PENDING
        db.commit()
    else:
        # Esgotou tentativas
        msg.status = OutboxStatus.FAILED
        msg.last_error = error
        msg.next_retry_at = None
        db.commit()
    _update_depth_gauge(db)
    return msg.status


def enqueue(
    db: Session,
    queue: OutboxQueue,
    payload: dict[str, Any],
) -> OutboxMessage:
    """Enfileira mensagem para reprocessamento.

    Args:
        db: Session SQLAlchemy.
        queue: enum (evolution|chatwoot|telegram|outbox).
        payload: dict JSON-serializavel. DEVE estar scrubbed (LGPD-by-design)
                 antes de chamar esta funcao. Caller eh responsavel pelo scrub.

    Returns:
        OutboxMessage criada (id UUID, status=PENDING).
    """
    msg = OutboxMessage(
        id=uuid.uuid4(),
        queue=queue,
        payload=payload,
        status=OutboxStatus.PENDING,
        attempts=0,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    _update_depth_gauge(db)
    return msg


def mark_processing(db: Session, msg: OutboxMessage) -> None:
    """Marca mensagem como em processamento."""
    msg.status = OutboxStatus.PROCESSING
    msg.attempts += 1
    db.commit()
    _update_depth_gauge(db)


def mark_done(db: Session, msg: OutboxMessage) -> None:
    """Marca mensagem como entregue com sucesso."""
    msg.status = OutboxStatus.DONE
    msg.last_error = None
    db.commit()
    _update_depth_gauge(db)


def mark_failed(db: Session, msg: OutboxMessage, error: str) -> None:
    """Marca mensagem como falha (volta para PENDING para retry).

    Attempts counter eh incrementado. Apos 3 tentativas, status = FAILED
    (caller decide retry policy).
    """
    msg.last_error = error
    msg.status = OutboxStatus.PENDING  # volta para retry
    db.commit()
    _update_depth_gauge(db)


def mark_dead(db: Session, msg: OutboxMessage, error: str) -> None:
    """Marca mensagem como dead letter (NAO tentar mais).

    Apos max_attempts (3), chama isto. Status = FAILED.
    """
    msg.status = OutboxStatus.FAILED
    msg.last_error = error
    db.commit()
    _update_depth_gauge(db)


def depth(db: Session, queue: OutboxQueue | None = None) -> dict[OutboxQueue, int]:
    """Retorna profundidade (count de pending) por queue.

    Args:
        db: Session.
        queue: se None, retorna todas as queues. Se especificado, so essa.

    Returns:
        dict {queue_enum: count_pending}.
    """
    stmt = select(OutboxMessage.queue, func.count(OutboxMessage.id)).where(
        OutboxMessage.status == OutboxStatus.PENDING
    )
    if queue is not None:
        stmt = stmt.where(OutboxMessage.queue == queue)
    stmt = stmt.group_by(OutboxMessage.queue)

    rows = db.execute(stmt).all()
    return {q: cnt for q, cnt in rows}


def _update_depth_gauge(db: Session) -> None:
    """Atualiza gauge dlq_depth{queue} baseado em SELECT COUNT.

    Chamado apos cada enqueue/mark_done/mark_failed para manter o gauge
    atualizado em tempo real (sem precisar scrape-time query).
    """
    counts = depth(db)
    for q in OutboxQueue:
        metrics_store.set_dlq_depth(queue=q.value, depth=counts.get(q, 0))


__all__ = [
    "depth",
    "enqueue",
    "mark_dead",
    "mark_done",
    "mark_failed",
    "mark_processing",
]
