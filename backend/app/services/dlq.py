"""Services DLQ - Dead Letter Queue para integracoes externas.

Permite enfileirar mensagens que falharam ao enviar (WhatsApp offline,
Chatwoot rate limit, etc) para reprocessamento assincrono.

Instrumentacao A2:
- `dlq_depth{queue}` gauge - atualizado em cada enqueue/mark_done/mark_failed
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus
from app.services.metrics import store as metrics_store


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
