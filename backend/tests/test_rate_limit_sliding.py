"""Testes do sliding window rate limit (A7).

A7: MELHORA o rate limit existente com sliding window real (log algorithm).
Usa Redis ZADD/ZCOUNT/ZREMRANGEBYSCORE.
- 60 requests em 60s = OK
- 61a request em 60s = 429
- Apos janela passar, contador reseta
- Redis offline = fail-open
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import time  # noqa: E402
# AsyncMock/MagicMock not needed for this test (uses FakeSlidingWindowStore)

import pytest  # noqa: E402

from app.services.sliding_window import (  # noqa: E402
    SlidingWindowResult,  # noqa: F401  (re-exported for tests)
    sliding_window_check,
)


# ============================================================================
# SlidingWindowStore (fake) — base behavior
# ============================================================================


class FakeSlidingWindowStore:
    """In-memory store simulando Redis ZSET (sliding window log)."""

    def __init__(self) -> None:
        self._store: dict[str, list[tuple[float, str]]] = {}

    async def zadd(self, key: str, score: float, member: str) -> int:
        if key not in self._store:
            self._store[key] = []
        self._store[key].append((score, member))
        return 1

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        if key not in self._store:
            return 0
        before = len(self._store[key])
        self._store[key] = [
            (s, m) for s, m in self._store[key] if s < min_score or s > max_score
        ]
        return before - len(self._store[key])

    async def zcount(self, key: str, min_score: float, max_score: float) -> int:
        if key not in self._store:
            return 0
        return sum(1 for s, _ in self._store[key] if min_score <= s <= max_score)


@pytest.mark.asyncio
async def test_sliding_window_60_requests_em_60s_passa() -> None:
    """60 requests em 60s = OK (no limite)."""
    store = FakeSlidingWindowStore()
    now = time.time()
    for i in range(60):
        result = await sliding_window_check(
            store, key="ip:1.2.3.4", limit=60, window_s=60, now=now + i * 0.1
        )
        assert result.allowed, f"Request {i+1} deveria ser allowed"


@pytest.mark.asyncio
async def test_sliding_window_61a_request_em_60s_bloqueia() -> None:
    """61a request em 60s = 429."""
    store = FakeSlidingWindowStore()
    now = time.time()
    for i in range(60):
        await sliding_window_check(
            store, key="ip:1.2.3.4", limit=60, window_s=60, now=now + i * 0.1
        )
    result = await sliding_window_check(
        store, key="ip:1.2.3.4", limit=60, window_s=60, now=now + 7.0
    )
    assert not result.allowed
    assert result.current == 60  # count ANTES de tentar adicionar
    assert result.limit == 60
    assert result.retry_after > 0


@pytest.mark.asyncio
async def test_sliding_window_apos_janela_reseta() -> None:
    """Apos 60s passarem, contador zera e permite novamente."""
    store = FakeSlidingWindowStore()
    now = time.time()
    # Estoura limite
    for i in range(60):
        await sliding_window_check(
            store, key="ip:1.2.3.4", limit=60, window_s=60, now=now + i * 0.01
        )
    # Apos 60s (janela passou)
    result = await sliding_window_check(
        store, key="ip:1.2.3.4", limit=60, window_s=60, now=now + 65.0
    )
    assert result.allowed
    assert result.current == 1


@pytest.mark.asyncio
async def test_sliding_window_keys_independentes() -> None:
    """Keys diferentes tem contadores independentes."""
    store = FakeSlidingWindowStore()
    now = time.time()
    for i in range(60):
        await sliding_window_check(
            store, key="ip:1.1.1.1", limit=60, window_s=60, now=now + i * 0.01
        )
    # IP diferente: ainda tem 60 reqs disponiveis
    result = await sliding_window_check(
        store, key="ip:2.2.2.2", limit=60, window_s=60, now=now + 0.05
    )
    assert result.allowed
    assert result.current == 1


@pytest.mark.asyncio
async def test_sliding_window_retry_after_eh_ate_expirar_mais_antigo() -> None:
    """retry_after indica quanto esperar ate a request mais antiga expirar."""
    store = FakeSlidingWindowStore()
    now = time.time()
    for i in range(60):
        await sliding_window_check(
            store, key="ip:1.2.3.4", limit=60, window_s=60, now=now + i * 0.01
        )
    # 61a request: bloqueada, retry_after ~= window_s
    result = await sliding_window_check(
        store, key="ip:1.2.3.4", limit=60, window_s=60, now=now + 1.0
    )
    assert not result.allowed
    # retry_after deve ser ~ window_s (60s) - tempo desde a primeira request
    assert 50 < result.retry_after <= 60


# ============================================================================
# sliding_window_check com store Redis (fail-open)
# ============================================================================


@pytest.mark.asyncio
async def test_sliding_window_redis_offline_faz_fail_open() -> None:
    """Se Redis offline (raise exception), sliding_window_check retorna allowed=True."""

    class BrokenStore:
        async def zadd(self, *args, **kwargs):
            raise ConnectionError("Redis down")

        async def zremrangebyscore(self, *args, **kwargs):
            raise ConnectionError("Redis down")

        async def zcount(self, *args, **kwargs):
            raise ConnectionError("Redis down")

    result = await sliding_window_check(
        BrokenStore(),  # type: ignore[arg-type]
        key="ip:1.2.3.4",
        limit=60,
        window_s=60,
        now=time.time(),
    )
    # Fail-open: permite request
    assert result.allowed
    assert result.current == 0
    assert result.retry_after == 0
