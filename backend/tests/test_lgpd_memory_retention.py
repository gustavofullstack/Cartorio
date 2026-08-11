"""Regressoes de retencao/erasure dos stores de memoria por titular."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.jobs.retencao import RetencaoConfig, run_retencao
from app.services.lgpd_memory_retention import (
    erase_subject_memory,
    purge_expired_memory,
)
from app.core.redis_keys import RedisKey
from app.models.cliente import Cliente
from app.services.channel_identity import bind_channel_identity


TELEFONE_HASH = "a" * 64
OUTRO_HASH = "b" * 64


class FakeRedis:
    def __init__(self, keys: list[str]) -> None:
        self.keys = set(keys)
        self.last_match = ""

    def scan_iter(self, *, match: str, count: int) -> list[str]:
        self.last_match = match
        prefix = match.removesuffix("*")
        return [key for key in self.keys if key.startswith(prefix)]

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.keys:
                self.keys.remove(key)
                deleted += 1
        return deleted


def _create_memory_tables(db_session) -> None:
    db_session.execute(
        text(
            "CREATE TABLE memoria_conversa ("
            "telefone_hash TEXT NOT NULL, session_id TEXT NOT NULL, "
            "content TEXT NOT NULL, created_at DATETIME NOT NULL)"
        )
    )
    db_session.execute(
        text(
            "CREATE TABLE session_state ("
            "telefone_hash TEXT NOT NULL, session_id TEXT NOT NULL, "
            "expires_at DATETIME NOT NULL)"
        )
    )
    db_session.commit()


def test_purge_expired_memory_respects_365_days_and_state_expiry(db_session) -> None:
    _create_memory_tables(db_session)
    now = datetime(2026, 8, 11, tzinfo=timezone.utc)
    old = now - timedelta(days=366)
    recent = now - timedelta(days=364)
    db_session.execute(
        text(
            "INSERT INTO memoria_conversa "
            "(telefone_hash, session_id, content, created_at) "
            "VALUES (:tel, :sid, :content, :created_at)"
        ),
        [
            {"tel": TELEFONE_HASH, "sid": "old", "content": "scrubbed", "created_at": old},
            {"tel": TELEFONE_HASH, "sid": "new", "content": "scrubbed", "created_at": recent},
        ],
    )
    db_session.execute(
        text(
            "INSERT INTO session_state (telefone_hash, session_id, expires_at) "
            "VALUES (:tel, :sid, :expires_at)"
        ),
        [
            {"tel": TELEFONE_HASH, "sid": "expired", "expires_at": now - timedelta(seconds=1)},
            {"tel": TELEFONE_HASH, "sid": "active", "expires_at": now + timedelta(seconds=1)},
        ],
    )

    result = purge_expired_memory(db_session, now=now, conversation_days=365)

    assert result.memoria_conversa_deleted == 1
    assert result.session_state_deleted == 1
    assert db_session.execute(text("SELECT session_id FROM memoria_conversa")).scalar_one() == "new"
    assert db_session.execute(text("SELECT session_id FROM session_state")).scalar_one() == "active"


def test_erase_subject_memory_is_exact_and_clears_redis_namespace(db_session) -> None:
    _create_memory_tables(db_session)
    now = datetime.now(timezone.utc)
    for telefone_hash in (TELEFONE_HASH, OUTRO_HASH):
        db_session.execute(
            text(
                "INSERT INTO memoria_conversa "
                "(telefone_hash, session_id, content, created_at) "
                "VALUES (:tel, :sid, :content, :created_at)"
            ),
            {"tel": telefone_hash, "sid": "s1", "content": "scrubbed", "created_at": now},
        )
        db_session.execute(
            text(
                "INSERT INTO session_state (telefone_hash, session_id, expires_at) "
                "VALUES (:tel, :sid, :expires_at)"
            ),
            {"tel": telefone_hash, "sid": "s1", "expires_at": now + timedelta(minutes=30)},
        )

    target_key = f"pietra:session:{TELEFONE_HASH}:s1"
    target_state = f"{target_key}:state"
    other_key = f"pietra:session:{OUTRO_HASH}:s1"
    redis_client = FakeRedis([target_key, target_state, other_key])

    result = erase_subject_memory(
        db_session,
        telefone_hash=TELEFONE_HASH,
        redis_client=redis_client,
    )

    assert result.memoria_conversa_deleted == 1
    assert result.session_state_deleted == 1
    assert result.redis_keys_deleted == 2
    assert result.redis_available is True
    assert "chat_pipeline:unbound_identity" in result.uncovered_stores
    assert "external:vector" in result.uncovered_stores
    assert redis_client.last_match == f"pietra:session:{TELEFONE_HASH}:*"
    assert redis_client.keys == {other_key}
    assert (
        db_session.execute(text("SELECT telefone_hash FROM memoria_conversa")).scalar_one()
        == OUTRO_HASH
    )
    assert (
        db_session.execute(text("SELECT telefone_hash FROM session_state")).scalar_one()
        == OUTRO_HASH
    )


def test_bound_identity_erases_all_exact_chat_pipeline_keys(db_session) -> None:
    pseudonym = "c" * 64
    other_pseudonym = "d" * 64
    cliente = Cliente(
        cpf_hash="e" * 64,
        nome="Cliente Sintetico",
        telefone_hash=TELEFONE_HASH,
        consentimento_lgpd=True,
    )
    db_session.add(cliente)
    db_session.flush()
    bind_channel_identity(
        db_session,
        cliente_id=cliente.id,
        channel="whatsapp",
        conversation_pseudonym=pseudonym,
        hmac_kid="test-v1",
    )
    target_keys = {
        f"queue:whatsapp:{pseudonym}",
        f"tg:hist:whatsapp:{pseudonym}",
        RedisKey.rate_limit("chat", f"whatsapp_{pseudonym}"),
        RedisKey.bot_mute("whatsapp", pseudonym),
        f"consent:wa:{pseudonym}",
        f"consent:wa:notice:{pseudonym}",
        f"cartorio:idem:chat_pipeline:{pseudonym}.abc123",
    }
    unrelated_key = f"tg:hist:whatsapp:{other_pseudonym}"
    redis_client = FakeRedis([*target_keys, unrelated_key])

    result = erase_subject_memory(
        db_session,
        telefone_hash=TELEFONE_HASH,
        cliente_id=cliente.id,
        redis_client=redis_client,
    )

    assert result.redis_available is True
    assert result.redis_keys_deleted == len(target_keys)
    assert result.channel_bindings_deleted == 1
    assert result.uncovered_stores == ("external:vector", "external:graph")
    assert redis_client.keys == {unrelated_key}


def test_redis_failure_preserves_binding_and_database_memory(db_session) -> None:
    _create_memory_tables(db_session)
    cliente = Cliente(
        cpf_hash="f" * 64,
        nome="Cliente Sintetico",
        telefone_hash=TELEFONE_HASH,
        consentimento_lgpd=True,
    )
    db_session.add(cliente)
    db_session.flush()
    bind_channel_identity(
        db_session,
        cliente_id=cliente.id,
        channel="whatsapp",
        conversation_pseudonym="c" * 64,
        hmac_kid="test-v1",
    )
    db_session.execute(
        text(
            "INSERT INTO memoria_conversa "
            "(telefone_hash, session_id, content, created_at) "
            "VALUES (:tel, :sid, :content, :created_at)"
        ),
        {
            "tel": TELEFONE_HASH,
            "sid": "s1",
            "content": "scrubbed",
            "created_at": datetime.now(timezone.utc),
        },
    )

    class BrokenRedis:
        def scan_iter(self, *, match: str, count: int):
            raise ConnectionError("synthetic redis failure")

    from app.models.cliente_channel_identity import ClienteChannelIdentity
    from app.services.lgpd_memory_retention import MemoryErasureUnavailableError

    with pytest.raises(MemoryErasureUnavailableError):
        erase_subject_memory(
            db_session,
            telefone_hash=TELEFONE_HASH,
            cliente_id=cliente.id,
            redis_client=BrokenRedis(),
        )

    assert db_session.get(Cliente, cliente.id) is not None
    assert db_session.query(ClienteChannelIdentity).filter_by(cliente_id=cliente.id).count() == 1
    assert (
        db_session.execute(
            text("SELECT COUNT(*) FROM memoria_conversa WHERE telefone_hash = :telefone_hash"),
            {"telefone_hash": TELEFONE_HASH},
        ).scalar_one()
        == 1
    )


def test_binding_without_phone_hash_is_still_erased_by_cliente_id(db_session) -> None:
    pseudonym = "c" * 64
    cliente = Cliente(
        cpf_hash="f" * 64,
        nome="Cliente Legado",
        telefone_hash=None,
        consentimento_lgpd=True,
    )
    db_session.add(cliente)
    db_session.flush()
    bind_channel_identity(
        db_session,
        cliente_id=cliente.id,
        channel="whatsapp",
        conversation_pseudonym=pseudonym,
        hmac_kid="test-v1",
    )
    target_key = f"queue:whatsapp:{pseudonym}"
    redis_client = FakeRedis([target_key])

    result = erase_subject_memory(
        db_session,
        telefone_hash=None,
        cliente_id=cliente.id,
        redis_client=redis_client,
    )

    assert result.redis_available is True
    assert result.redis_keys_deleted == 1
    assert result.channel_bindings_deleted == 1
    assert target_key not in redis_client.keys


@pytest.mark.parametrize("invalid_hash", ["", "abc", "a" * 63, "a" * 64 + "*"])
def test_erase_subject_memory_rejects_invalid_or_wildcard_hash(
    db_session,
    invalid_hash: str,
) -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        erase_subject_memory(
            db_session,
            telefone_hash=invalid_hash,
            redis_client=FakeRedis([]),
        )


def test_purge_is_noop_when_optional_memory_tables_are_absent(db_session) -> None:
    result = purge_expired_memory(
        db_session,
        now=datetime.now(timezone.utc),
    )
    assert result.memoria_conversa_deleted == 0
    assert result.session_state_deleted == 0


def test_daily_retention_job_reports_memory_deletions(db_session) -> None:
    _create_memory_tables(db_session)
    now = datetime(2026, 8, 11, tzinfo=timezone.utc)
    db_session.execute(
        text(
            "INSERT INTO memoria_conversa "
            "(telefone_hash, session_id, content, created_at) "
            "VALUES (:tel, :sid, :content, :created_at)"
        ),
        {
            "tel": TELEFONE_HASH,
            "sid": "expired",
            "content": "scrubbed",
            "created_at": now - timedelta(days=366),
        },
    )
    db_session.execute(
        text(
            "INSERT INTO session_state (telefone_hash, session_id, expires_at) "
            "VALUES (:tel, :sid, :expires_at)"
        ),
        {
            "tel": TELEFONE_HASH,
            "sid": "expired",
            "expires_at": now - timedelta(seconds=1),
        },
    )

    result = run_retencao(
        db_session,
        config=RetencaoConfig(retencao_conversa_dias=365),
        now=now,
    )

    assert result.memoria_conversa_deleted == 1
    assert result.session_state_deleted == 1
