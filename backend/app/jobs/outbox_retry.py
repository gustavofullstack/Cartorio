"""Retry seguro e limitado para mensagens vencidas do outbox.

O job retoma apenas mensagens que ja falharam e cujo ``next_retry_at`` venceu.
Ele nao consome mensagens novas: a primeira entrega continua sendo responsabilidade
do webhook Supabase. Isso evita competir com o fluxo primario e preserva o HITL dos
adaptadores de canal (em especial, Chatwoot aceita somente contexto ``incoming``).

O lock Redis e *fail-closed*: sem uma exclusao mutua confirmada o job nao envia
nenhuma mensagem, pois uma entrega externa pode ter efeito observavel. A transicao
``FAILED -> PROCESSING`` e persistida antes do I/O; portanto, a garantia e
at-least-once, nunca exactly-once. Mensagens interrompidas em ``PROCESSING`` devem
ser investigadas pelo operador, em vez de serem reenviadas automaticamente.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus
from app.services.dlq import MAX_ATTEMPTS, compute_next_retry_at
from app.services.redlock import acquire_lock, release_lock

logger = logging.getLogger(__name__)

DEFAULT_BATCH_LIMIT = 25
MAX_BATCH_LIMIT = 100
DEFAULT_LOCK_NAME = "outbox-retry-worker"
DEFAULT_LOCK_TTL_SECONDS = 600

OutboxDispatcher = Callable[[OutboxQueue, dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class OutboxRetryRunResult:
    """Contadores observaveis de uma execucao do worker."""

    lock_acquired: bool
    claimed: int
    delivered: int
    rescheduled: int
    dead_lettered: int


async def dispatch_due_outbox_message(queue: OutboxQueue, payload: dict[str, Any]) -> None:
    """Despacha por meio dos adaptadores oficiais, que ja aplicam as regras HITL.

    O import e tardio para manter jobs independentes do bootstrap HTTP. O mapa de
    adaptadores e a mesma fronteira usada pelo webhook primario; nenhum endpoint
    HTTP e chamado pelo worker.
    """
    from app.api.v1.integrations import _DISPATCHERS

    await _DISPATCHERS[queue](payload)


def _validate_batch_limit(batch_limit: int) -> None:
    if not 1 <= batch_limit <= MAX_BATCH_LIMIT:
        raise ValueError(f"batch_limit deve estar entre 1 e {MAX_BATCH_LIMIT}")


def _due_messages_statement(now: datetime, batch_limit: int) -> Select[tuple[OutboxMessage]]:
    """Retorna mensagens transitórias vencidas, com lock por linha no Postgres."""
    due = and_(
        OutboxMessage.status == OutboxStatus.FAILED,
        OutboxMessage.attempts < MAX_ATTEMPTS,
        OutboxMessage.next_retry_at.is_not(None),
        OutboxMessage.next_retry_at <= now,
    )
    return (
        select(OutboxMessage)
        .where(due)
        .order_by(OutboxMessage.next_retry_at, OutboxMessage.created_at)
        .limit(batch_limit)
        .with_for_update(skip_locked=True)
    )


def _claim_due_messages(db: Session, *, now: datetime, batch_limit: int) -> list[UUID]:
    """Reserva um lote e persiste ``PROCESSING`` antes de qualquer chamada externa."""
    messages = list(db.execute(_due_messages_statement(now, batch_limit)).scalars())
    for message in messages:
        message.status = OutboxStatus.PROCESSING
    db.commit()
    return [message.id for message in messages]


def _mark_delivered(db: Session, message_id: UUID) -> bool:
    """Fecha uma reserva ainda pertencente a este worker."""
    message = db.get(OutboxMessage, message_id)
    if message is None or message.status != OutboxStatus.PROCESSING:
        return False
    message.status = OutboxStatus.DONE
    message.attempts += 1
    message.last_error = None
    message.next_retry_at = None
    db.commit()
    return True


def _mark_retry_failure(db: Session, message_id: UUID, error: Exception) -> OutboxStatus | None:
    """Registra uma falha sem serializar payload, URL ou detalhes upstream."""
    message = db.get(OutboxMessage, message_id)
    if message is None or message.status != OutboxStatus.PROCESSING:
        return None

    message.attempts += 1
    # Mensagens externas podem ecoar PII/segredos em sua mensagem de erro. Somente
    # o tipo e persistido; o payload nunca aparece em logs do worker.
    message.last_error = f"dispatch_failed:{type(error).__name__}"
    if message.attempts >= MAX_ATTEMPTS:
        message.status = OutboxStatus.FAILED
        message.next_retry_at = None
        result = OutboxStatus.FAILED
    else:
        message.status = OutboxStatus.FAILED
        # ``compute_next_retry_at`` recebe o indice da falha (0, 1, 2).
        message.next_retry_at = compute_next_retry_at(message.attempts - 1)
        result = OutboxStatus.PENDING
    db.commit()
    return result


async def run_due_outbox_retries(
    db: Session,
    *,
    dispatcher: OutboxDispatcher = dispatch_due_outbox_message,
    now: datetime | None = None,
    batch_limit: int = DEFAULT_BATCH_LIMIT,
    lock_name: str = DEFAULT_LOCK_NAME,
    lock_ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
) -> OutboxRetryRunResult:
    """Reprocessa no maximo um lote de falhas vencidas com exclusao mutua.

    O job e propositalmente uma funcao invocavel por cron/N8N/CronJob. Ele nao e
    registrado no lifespan ate que a operacao aprove frequencia e observabilidade
    de producao. Se Redis nao confirmar o lock, retorna ``lock_acquired=False`` e
    nao toca no banco nem em integracoes externas.
    """
    _validate_batch_limit(batch_limit)
    if lock_ttl_seconds <= 0:
        raise ValueError("lock_ttl_seconds deve ser positivo")

    token = acquire_lock(lock_name, ttl_seconds=lock_ttl_seconds)
    if token is None:
        logger.warning("OUTBOX_RETRY_SKIPPED: distributed lock unavailable_or_busy")
        return OutboxRetryRunResult(False, 0, 0, 0, 0)

    effective_now = now or datetime.now(timezone.utc)
    delivered = 0
    rescheduled = 0
    dead_lettered = 0
    try:
        message_ids = _claim_due_messages(db, now=effective_now, batch_limit=batch_limit)
        for message_id in message_ids:
            message = db.get(OutboxMessage, message_id)
            if message is None or message.status != OutboxStatus.PROCESSING:
                continue
            try:
                await dispatcher(message.queue, message.payload)
            except Exception as exc:  # noqa: BLE001 - retry boundary externa
                outcome = _mark_retry_failure(db, message_id, exc)
                logger.warning(
                    "OUTBOX_RETRY_FAILED: id=%s queue=%s error_type=%s",
                    message_id,
                    message.queue.value,
                    type(exc).__name__,
                )
                if outcome == OutboxStatus.FAILED:
                    dead_lettered += 1
                elif outcome is not None:
                    rescheduled += 1
            else:
                if _mark_delivered(db, message_id):
                    delivered += 1
        logger.info(
            "OUTBOX_RETRY_COMPLETED: claimed=%d delivered=%d rescheduled=%d dead_lettered=%d",
            len(message_ids),
            delivered,
            rescheduled,
            dead_lettered,
        )
        return OutboxRetryRunResult(True, len(message_ids), delivered, rescheduled, dead_lettered)
    finally:
        release_lock(lock_name, token)


__all__ = [
    "DEFAULT_BATCH_LIMIT",
    "DEFAULT_LOCK_NAME",
    "DEFAULT_LOCK_TTL_SECONDS",
    "MAX_BATCH_LIMIT",
    "OutboxRetryRunResult",
    "dispatch_due_outbox_message",
    "run_due_outbox_retries",
]
