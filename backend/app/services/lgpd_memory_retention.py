"""Retencao e eliminacao focal da memoria conversacional da Pietra.

Este modulo cobre stores vinculados por ``telefone_hash`` e, quando existe o
binding pseudonimo-only ``cliente_channel_identities``, tambem queue, history,
rate limit, idempotencia, mute e consentimento Redis do canal.

O dump Supabase contem ``agents_memory_entries`` com embedding, mas essa tabela
nao possui ``cliente_id`` ou ``telefone_hash`` e nao e acessada pelo backend.
Portanto vector/graph externos NAO sao declarados como apagados aqui: precisam
de um contrato de subject binding no sistema proprietario antes de integrarem
DSAR/erasure. Fazer delete por heuristica seria destrutivo e nao auditavel.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, inspect, text
from sqlalchemy.orm import Session


_TELEFONE_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")
UNCOVERED_SUBJECT_STORES = ("external:vector", "external:graph")


class MemoryErasureUnavailableError(RuntimeError):
    """Redis indisponivel: nenhuma mutacao DB de erasure pode prosseguir."""


@dataclass(frozen=True)
class MemoryRetentionResult:
    """Contagens de linhas removidas pelo job de retencao."""

    memoria_conversa_deleted: int = 0
    session_state_deleted: int = 0


@dataclass(frozen=True)
class SubjectMemoryErasureResult:
    """Contagens sem identificador do titular, seguras para audit log."""

    memoria_conversa_deleted: int = 0
    session_state_deleted: int = 0
    redis_keys_deleted: int = 0
    channel_bindings_deleted: int = 0
    redis_available: bool = False
    uncovered_stores: tuple[str, ...] = UNCOVERED_SUBJECT_STORES


def _has_table(db: Session, table_name: str) -> bool:
    # Inspecionar a connection da Session preserva o mesmo SQLite in-memory e
    # a mesma transacao; inspecionar apenas o Engine pode abrir outra conexao.
    return bool(inspect(db.connection()).has_table(table_name))


def _rowcount(result: Any) -> int:
    return int(getattr(result, "rowcount", 0) or 0)


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def purge_expired_memory(
    db: Session,
    *,
    now: datetime,
    conversation_days: int = 365,
) -> MemoryRetentionResult:
    """Remove memoria conversacional vencida sem executar ``commit``.

    ``memoria_conversa`` e dado de atendimento baseado em consentimento e tem
    retencao de 365 dias. ``session_state`` e cache operacional e vence pelo
    proprio ``expires_at``. O caller controla a transacao e o audit do batch.
    """
    if conversation_days < 1:
        raise ValueError("conversation_days deve ser positivo")

    now_naive = _utc_naive(now)
    cutoff = now_naive - timedelta(days=conversation_days)
    memoria_deleted = 0
    state_deleted = 0

    if _has_table(db, "memoria_conversa"):
        memoria_deleted = _rowcount(
            db.execute(
                text("DELETE FROM memoria_conversa WHERE created_at < :cutoff"),
                {"cutoff": cutoff},
            )
        )

    if _has_table(db, "session_state"):
        state_deleted = _rowcount(
            db.execute(
                text("DELETE FROM session_state WHERE expires_at <= :now"),
                {"now": now_naive},
            )
        )

    return MemoryRetentionResult(
        memoria_conversa_deleted=memoria_deleted,
        session_state_deleted=state_deleted,
    )


def erase_subject_memory(
    db: Session,
    *,
    telefone_hash: str | None,
    cliente_id: int | None = None,
    redis_client: Any | None = None,
) -> SubjectMemoryErasureResult:
    """Elimina memoria ligada exatamente a um ``telefone_hash``.

    O hash e validado antes de compor o pattern Redis para impedir wildcard ou
    exclusao transversal. O caller controla a transacao PostgreSQL. Redis nao
    participa dessa transacao; indisponibilidade e retornada explicitamente e
    nunca convertida em falsa confirmacao de apagamento.
    """
    normalized_hash = (telefone_hash or "").strip().lower()
    if normalized_hash and not _TELEFONE_HASH_RE.fullmatch(normalized_hash):
        raise ValueError("telefone_hash deve ser SHA-256 hexadecimal")
    if not normalized_hash and cliente_id is None:
        raise ValueError("telefone_hash deve ser SHA-256 hexadecimal ou informar cliente_id")

    identities: list[Any] = []
    if cliente_id is not None and _has_table(db, "cliente_channel_identities"):
        from app.services.channel_identity import list_channel_identities

        identities = list_channel_identities(db, cliente_id=cliente_id)

    has_redis_targets = bool(normalized_hash or identities)
    if redis_client is None and has_redis_targets:
        from app.services.pietra_memoria import get_redis

        redis_client = get_redis()

    if redis_client is None and has_redis_targets:
        raise MemoryErasureUnavailableError("Redis indisponivel para erasure LGPD")

    redis_deleted = 0
    if has_redis_targets:
        redis_store: Any = redis_client
        keys: list[Any] = []
        try:
            if normalized_hash:
                keys.extend(
                    redis_store.scan_iter(
                        match=f"pietra:session:{normalized_hash}:*",
                        count=100,
                    )
                )
            from app.core.redis_keys import RedisKey

            for identity in identities:
                channel = identity.channel
                pseudonym = identity.conversation_pseudonym
                keys.extend(
                    (
                        f"queue:{channel}:{pseudonym}",
                        f"tg:hist:{channel}:{pseudonym}",
                        RedisKey.rate_limit("chat", f"{channel}_{pseudonym}"),
                        RedisKey.bot_mute(channel, pseudonym),
                    )
                )
                keys.extend(
                    redis_store.scan_iter(
                        match=f"cartorio:idem:chat_pipeline:{pseudonym}.*",
                        count=100,
                    )
                )
                if channel == "whatsapp":
                    keys.append(f"consent:wa:{pseudonym}")
                    keys.append(f"consent:wa:notice:{pseudonym}")
            redis_deleted = int(redis_store.delete(*set(keys)) or 0) if keys else 0
        except Exception as exc:  # noqa: BLE001 - fail-closed, binding permite retry
            raise MemoryErasureUnavailableError("Falha ao eliminar memoria Redis") from exc

    # Mutacoes DB so comecam depois que o store externo confirmou acesso.
    # Permanecem pendentes na mesma Session ate o audit duravel fazer commit.
    memoria_deleted = 0
    state_deleted = 0
    if normalized_hash and _has_table(db, "memoria_conversa"):
        memoria_deleted = _rowcount(
            db.execute(
                text("DELETE FROM memoria_conversa WHERE telefone_hash = :telefone_hash"),
                {"telefone_hash": normalized_hash},
            )
        )
    if normalized_hash and _has_table(db, "session_state"):
        state_deleted = _rowcount(
            db.execute(
                text("DELETE FROM session_state WHERE telefone_hash = :telefone_hash"),
                {"telefone_hash": normalized_hash},
            )
        )

    bindings_deleted = 0
    if identities:
        from app.models.cliente_channel_identity import ClienteChannelIdentity

        delete_result = db.execute(
            delete(ClienteChannelIdentity).where(
                ClienteChannelIdentity.cliente_id == cliente_id,
            )
        )
        bindings_deleted = _rowcount(delete_result)

    uncovered_stores = list(UNCOVERED_SUBJECT_STORES)
    if cliente_id is None or not identities:
        uncovered_stores.append("chat_pipeline:unbound_identity")

    return SubjectMemoryErasureResult(
        memoria_conversa_deleted=memoria_deleted,
        session_state_deleted=state_deleted,
        redis_keys_deleted=redis_deleted,
        channel_bindings_deleted=bindings_deleted,
        redis_available=True,
        uncovered_stores=tuple(uncovered_stores),
    )


__all__ = [
    "MemoryRetentionResult",
    "MemoryErasureUnavailableError",
    "SubjectMemoryErasureResult",
    "UNCOVERED_SUBJECT_STORES",
    "erase_subject_memory",
    "purge_expired_memory",
]
