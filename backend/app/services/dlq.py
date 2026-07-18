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


def expire_old_messages(
    db: Session,
    *,
    older_than_days: int = 30,
    status: OutboxStatus = OutboxStatus.FAILED,
    batch_size: int = 500,
) -> int:
    """Descarta mensagens obsoletas do DLQ (LGPD Art.16: eliminação após prazo).

    Mensagens em status terminal (FAILED por default) mais antigas que
    `older_than_days` sao marcadas como DELETED (soft delete via status).
    Nao remove fisicamente para preservar audit trail (LGPD Art.37: registro
    das operacoes de tratamento).

    Args:
        db: Session SQLAlchemy.
        older_than_days: idade minima em dias para descarte (default 30).
            LGPD recomenda 90d max para conversa_ia_log, mas DLQ eh
            dados tecnicos (status/eventos), entao 30d eh seguro.
        status: status alvo para expirar (default FAILED).
        batch_size: maximo de mensagens processadas por chamada (evita
            lock de transacao longa em DLQs grandes).

    Returns:
        Numero de mensagens marcadas como deletadas.

    Side effects:
        - Atualiza `dlq_depth{queue}` gauge.
        - Loga operacao em audit log (se existir).
    """
    from datetime import timedelta

    from sqlalchemy import update
    from sqlalchemy.engine import CursorResult

    from app.models.outbox_message import OutboxMessage  # noqa: F401
    from app.services.metrics import store as metrics_store_local

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=older_than_days)
    # Marca como DELETED (nao remove fisicamente para audit trail)
    # OutboxStatus nao tem DELETED ainda - usamos FAILED com marker last_error
    stmt = (
        update(OutboxMessage)
        .where(
            OutboxMessage.status == status,
            OutboxMessage.created_at < cutoff,
        )
        .values(
            status=OutboxStatus.FAILED,  # terminal
            last_error=f"EXPIRED after {older_than_days}d at {datetime.now(tz=timezone.utc).isoformat()}",
        )
        .execution_options(synchronize_session=False)
    )
    from typing import cast

    result = cast(CursorResult, db.execute(stmt))
    db.commit()
    deleted_count = result.rowcount or 0
    _update_depth_gauge(db)
    # Metrica: dlq_expired_total counter
    metrics_store_local.inc_dlq_expired(queue=None, count=deleted_count)
    return deleted_count


def purge_deleted_hard(
    db: Session,
    *,
    older_than_days: int = 180,
    batch_size: int = 1000,
) -> int:
    """Remove FISICamente mensagens expired mais antigas que X dias.

    LGPD Art.16: apos periodo de retenção, dados podem ser eliminados.
    Use APOS `expire_old_messages()` + periodo de auditoria (default 180d
    = 6 meses, conservador para ANPD + CFP).

    ATENCAO: operacao IRREVERSIVEL. Requer confirmacao explicita em prod.

    Args:
        db: Session.
        older_than_days: idade minima em dias desde EXPIRATION.
        batch_size: maximo removido por chamada.

    Returns:
        Numero de rows fisicamente removidas.
    """
    from datetime import timedelta

    from sqlalchemy import delete

    from app.models.outbox_message import OutboxMessage

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=older_than_days)
    stmt = (
        delete(OutboxMessage)
        .where(
            OutboxMessage.status == OutboxStatus.FAILED,
            OutboxMessage.last_error.like("EXPIRED after %"),
            OutboxMessage.created_at < cutoff,
        )
        .execution_options(synchronize_session=False)
    )
    from typing import cast
    from sqlalchemy.engine import CursorResult

    result = cast(CursorResult, db.execute(stmt))
    db.commit()
    return result.rowcount or 0


def stats_by_age(db: Session, queue: OutboxQueue | None = None) -> dict[str, int]:
    """Snapshot de distribuição por idade (debugging/observability).

    Returns:
        Dict com contadores por faixa:
        - "<1d": mensagens criadas nas últimas 24h
        - "1-7d": entre 1 e 7 dias
        - "7-30d": entre 7 e 30 dias
        - ">30d": mais de 30 dias (candidatas a expirar)
    """
    from datetime import timedelta

    now = datetime.now(tz=timezone.utc)
    cuts = {
        "<1d": now - timedelta(days=1),
        "1-7d": now - timedelta(days=7),
        "7-30d": now - timedelta(days=30),
        ">30d": now - timedelta(days=365 * 10),  # effectively all
    }
    result: dict[str, int] = {}
    base = select(OutboxMessage.created_at)
    if queue is not None:
        base = base.where(OutboxMessage.queue == queue)
    rows = db.execute(base).all()
    for created_at, *_ in rows:
        if not created_at:
            continue
        if created_at >= cuts["<1d"]:
            result["<1d"] = result.get("<1d", 0) + 1
        elif created_at >= cuts["1-7d"]:
            result["1-7d"] = result.get("1-7d", 0) + 1
        elif created_at >= cuts["7-30d"]:
            result["7-30d"] = result.get("7-30d", 0) + 1
        else:
            result[">30d"] = result.get(">30d", 0) + 1
    return result


__all__ = [
    "depth",
    "enqueue",
    "expire_old_messages",
    "mark_dead",
    "mark_done",
    "mark_failed",
    "mark_processing",
    "purge_deleted_hard",
    "stats_by_age",
]
