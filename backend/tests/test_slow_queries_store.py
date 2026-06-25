"""Testes A16 — SlowQueriesStore (Redis sorted set).

Cobertura:
- init com/sem redis_url
- add_slow_query + timestamp auto
- get_slow_queries (todos, filtro duration, filtro path)
- get_slow_queries_count
- clear
- erros: redis_url vazio, add falho, get falho
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.slow_queries import (
    SLOW_QUERIES_KEY,
    SLOW_QUERIES_MAX_ENTRIES,
    SLOW_QUERIES_TTL_SECONDS,
    SlowQueriesError,
    SlowQueriesStore,
    get_slow_queries_store,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reseta o singleton do get_slow_queries_store entre testes."""
    import app.services.slow_queries as sq
    sq._store = None
    yield
    sq._store = None


# ─── Init ───────────────────────────────────────────────────────────────

async def test_init_sem_redis_url_raise_no_call():
    """Init sem url (nem settings) levanta erro ao tentar conectar."""
    with patch("app.services.slow_queries.settings.redis_url", ""):
        store = SlowQueriesStore()
        with pytest.raises(SlowQueriesError, match="redis_url nao configurado"):
            await store._get_client()


async def test_init_com_redis_url_cria_client():
    """Init com URL cria client lazy."""
    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    client = await store._get_client()
    assert client is not None


async def test_close_fecha_client():
    """close() aclose o client interno."""
    mock_redis = AsyncMock()
    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis
    await store.close()
    mock_redis.aclose.assert_awaited_once()
    assert store._client is None


# ─── add_slow_query ─────────────────────────────────────────────────────

async def test_add_slow_query_success():
    """add_slow_query insere no sorted set + seta TTL."""
    mock_redis = AsyncMock()
    mock_redis.zadd = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.zcard = AsyncMock(return_value=5)

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    result = await store.add_slow_query({"event": "slow_request", "duration_ms": 1200.0})
    assert result is True
    mock_redis.zadd.assert_awaited_once()
    mock_redis.expire.assert_awaited_once_with(SLOW_QUERIES_KEY, SLOW_QUERIES_TTL_SECONDS)


async def test_add_slow_query_with_timestamp():
    """add_slow_query usa timestamp fornecido, nao gera novo."""
    mock_redis = AsyncMock()
    mock_redis.zadd = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.zcard = AsyncMock(return_value=5)

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    ts = 1234567890.0
    await store.add_slow_query({"event": "slow", "duration_ms": 500, "timestamp": ts})

    call_args = mock_redis.zadd.call_args
    assert call_args is not None
    # zadd is called as zadd(key, {member: score})
    # The mapping is the second positional arg
    assert len(call_args[0]) >= 2
    mapping = call_args[0][1]
    member_str = list(mapping.keys())[0]
    parsed = json.loads(member_str)
    assert parsed["timestamp"] == ts


async def test_add_slow_query_triggers_lru():
    """add_slow_query faz LRU eviction quando > MAX_ENTRIES."""
    mock_redis = AsyncMock()
    mock_redis.zadd = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.zcard = AsyncMock(return_value=SLOW_QUERIES_MAX_ENTRIES + 10)

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    await store.add_slow_query({"event": "slow", "duration_ms": 500})
    mock_redis.zremrangebyrank.assert_awaited_once()


async def test_add_slow_query_falho_retorna_false():
    """add_slow_query retorna False em caso de excecao."""
    mock_redis = AsyncMock()
    mock_redis.zadd = AsyncMock(side_effect=ConnectionError("redis down"))

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    result = await store.add_slow_query({"event": "slow", "duration_ms": 500})
    assert result is False


# ─── get_slow_queries ───────────────────────────────────────────────────

async def test_get_slow_queries_vazio():
    """get_slow_queries retorna lista vazia quando nao ha dados."""
    mock_redis = AsyncMock()
    mock_redis.zrevrange = AsyncMock(return_value=[])

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    result = await store.get_slow_queries()
    assert result == []


async def test_get_slow_queries_com_dados():
    """get_slow_queries retorna dados parseados corretamente."""
    entry = json.dumps({"event": "slow", "method": "GET", "duration_ms": 1500.0, "path": "/api/v1/test"})
    mock_redis = AsyncMock()
    mock_redis.zrevrange = AsyncMock(return_value=[entry])

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    result = await store.get_slow_queries(limit=10)
    assert len(result) == 1
    assert result[0]["event"] == "slow"
    assert result[0]["duration_ms"] == 1500.0


async def test_get_slow_queries_filtro_duration():
    """get_slow_queries filtra por duracao minima."""
    entries = [
        json.dumps({"event": "a", "duration_ms": 100.0, "path": "/x"}),
        json.dumps({"event": "b", "duration_ms": 500.0, "path": "/y"}),
        json.dumps({"event": "c", "duration_ms": 1000.0, "path": "/z"}),
    ]
    mock_redis = AsyncMock()
    mock_redis.zrevrange = AsyncMock(return_value=entries)

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    result = await store.get_slow_queries(limit=100, min_duration_ms=500.0)
    assert len(result) == 2
    assert all(q["duration_ms"] >= 500.0 for q in result)


async def test_get_slow_queries_filtro_path():
    """get_slow_queries filtra por prefixo de path."""
    entries = [
        json.dumps({"event": "a", "duration_ms": 100.0, "path": "/api/v1/cliente/1"}),
        json.dumps({"event": "b", "duration_ms": 200.0, "path": "/health/live"}),
        json.dumps({"event": "c", "duration_ms": 150.0, "path": "/api/v1/protocolo/2"}),
    ]
    mock_redis = AsyncMock()
    mock_redis.zrevrange = AsyncMock(return_value=entries)

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    result = await store.get_slow_queries(limit=100, path_prefix="/api/v1/")
    assert len(result) == 2


async def test_get_slow_queries_json_invalido_ignorado():
    """get_slow_queries ignora entradas com JSON malformado."""
    mock_redis = AsyncMock()
    mock_redis.zrevrange = AsyncMock(return_value=["{invalid json}", '{"ok": true}'])

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    result = await store.get_slow_queries()
    assert len(result) == 1


async def test_get_slow_queries_falho_retorna_vazio():
    """get_slow_queries retorna [] em caso de excecao."""
    mock_redis = AsyncMock()
    mock_redis.zrevrange = AsyncMock(side_effect=ConnectionError("redis down"))

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    result = await store.get_slow_queries()
    assert result == []


# ─── count / clear ──────────────────────────────────────────────────────

async def test_get_slow_queries_count():
    """get_slow_queries_count retorna total."""
    mock_redis = AsyncMock()
    mock_redis.zcard = AsyncMock(return_value=42)

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    count = await store.get_slow_queries_count()
    assert count == 42


async def test_get_slow_queries_count_falho_retorna_zero():
    """get_slow_queries_count retorna 0 em caso de erro."""
    mock_redis = AsyncMock()
    mock_redis.zcard = AsyncMock(side_effect=ConnectionError("redis down"))

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    count = await store.get_slow_queries_count()
    assert count == 0


async def test_clear():
    """clear deleta a key Redis."""
    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(return_value=1)

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    result = await store.clear()
    assert result is True
    mock_redis.delete.assert_awaited_once_with(SLOW_QUERIES_KEY)


async def test_clear_falho_retorna_false():
    """clear retorna False em caso de erro."""
    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(side_effect=ConnectionError("redis down"))

    store = SlowQueriesStore(redis_url="redis://localhost:6379/0")
    store._client = mock_redis

    result = await store.clear()
    assert result is False


# ─── Constantes ─────────────────────────────────────────────────────────

def test_constants():
    """Constantes do modulo tem valores esperados."""
    assert SLOW_QUERIES_KEY == "cartorio:slow_queries"
    assert SLOW_QUERIES_MAX_ENTRIES == 1000
    assert SLOW_QUERIES_TTL_SECONDS == 86400


# ─── Singleton ──────────────────────────────────────────────────────────

def test_get_slow_queries_store_singleton():
    """get_slow_queries_store retorna mesma instancia."""
    s1 = get_slow_queries_store()
    s2 = get_slow_queries_store()
    assert s1 is s2
