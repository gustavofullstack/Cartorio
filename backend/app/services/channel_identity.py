"""Subject binding pseudonimo-only para stores conversacionais."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cliente_channel_identity import ClienteChannelIdentity


_PSEUDONYM_RE = re.compile(r"^[0-9a-f]{64}$")
_CHANNEL_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
_KID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def bind_channel_identity(
    db: Session,
    *,
    cliente_id: int,
    channel: str,
    conversation_pseudonym: str,
    hmac_kid: str,
) -> ClienteChannelIdentity:
    """Cria binding idempotente; nunca recebe nem persiste identificador bruto."""

    normalized_channel = channel.strip().lower()
    normalized_pseudonym = conversation_pseudonym.strip().lower()
    normalized_kid = hmac_kid.strip()
    if cliente_id < 1:
        raise ValueError("cliente_id must be positive")
    if not _CHANNEL_RE.fullmatch(normalized_channel):
        raise ValueError("invalid channel")
    if not _PSEUDONYM_RE.fullmatch(normalized_pseudonym):
        raise ValueError("invalid conversation pseudonym")
    if not _KID_RE.fullmatch(normalized_kid):
        raise ValueError("invalid conversation HMAC key id")

    stmt = select(ClienteChannelIdentity).where(
        ClienteChannelIdentity.channel == normalized_channel,
        ClienteChannelIdentity.conversation_pseudonym == normalized_pseudonym,
    )
    existing = db.execute(stmt).scalar_one_or_none()
    if existing is not None:
        if existing.cliente_id != cliente_id:
            raise RuntimeError("conversation pseudonym is bound to another client")
        return existing

    candidate = ClienteChannelIdentity(
        cliente_id=cliente_id,
        channel=normalized_channel,
        conversation_pseudonym=normalized_pseudonym,
        hmac_kid=normalized_kid,
    )
    try:
        with db.begin_nested():
            db.add(candidate)
            db.flush()
    except IntegrityError:
        existing = db.execute(stmt).scalar_one_or_none()
        if existing is None or existing.cliente_id != cliente_id:
            raise
        return existing
    return candidate


def find_cliente_id_by_channel_identity(
    db: Session,
    *,
    channel: str,
    conversation_pseudonym: str,
) -> int | None:
    """Resolve o titular pelo pseudonimo do canal, sem expor identificador bruto."""

    normalized_channel = channel.strip().lower()
    normalized_pseudonym = conversation_pseudonym.strip().lower()
    if not _CHANNEL_RE.fullmatch(normalized_channel):
        return None
    if not _PSEUDONYM_RE.fullmatch(normalized_pseudonym):
        return None
    existing = db.execute(
        select(ClienteChannelIdentity).where(
            ClienteChannelIdentity.channel == normalized_channel,
            ClienteChannelIdentity.conversation_pseudonym == normalized_pseudonym,
        )
    ).scalar_one_or_none()
    if existing is None:
        return None
    return existing.cliente_id


def list_channel_identities(db: Session, *, cliente_id: int) -> list[ClienteChannelIdentity]:
    """Lista bindings do titular sem expor identificadores originais."""

    return list(
        db.execute(
            select(ClienteChannelIdentity).where(
                ClienteChannelIdentity.cliente_id == cliente_id,
            )
        ).scalars()
    )


__all__ = [
    "bind_channel_identity",
    "find_cliente_id_by_channel_identity",
    "list_channel_identities",
]
