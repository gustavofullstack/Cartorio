"""G8.05.T4 — stress tests for X-Idempotency-Key under high concurrency.

Scenarios:
- concurrent claims of the *same* key (only one setnx wins)
- many unique keys under concurrent load
- pure FakeIdempotencyStore (asyncio) + thread-safe wrapper
- fakeredis-backed RedisIdempotencyStore SET NX
- middleware path with header ``X-Idempotency-Key``

Does not tick SUPER_PLANO.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.middleware.idempotency import (  # noqa: E402
    IdempotencyMiddleware,
    _hash_idempotency_key,
)
from app.services.idempotency_store import RedisIdempotencyStore  # noqa: E402
from app.services.idempotency_store_fake import FakeIdempotencyStore  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class ThreadSafeFakeIdempotencyStore:
    """FakeIdempotencyStore + lock for true multi-thread stress."""

    def __init__(self) -> None:
        self._inner = FakeIdempotencyStore()
        self._lock = threading.Lock()

    async def setnx(self, key: str, value: dict[str, Any], ttl_seconds: int) -> bool:
        with self._lock:
            # setnx/get/delete on Fake are sync under the hood (no await mid-critical)
            return await self._inner.setnx(key, value, ttl_seconds)

    async def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            return await self._inner.get(key)

    async def delete(self, key: str) -> None:
        with self._lock:
            await self._inner.delete(key)

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._inner._store)


def _make_post_request(
    idempotency_key: str | None = None,
    body: dict | None = None,
    *,
    x_header: bool = True,
) -> MagicMock:
    request = MagicMock()
    request.method = "POST"
    request.url.path = "/api/v1/telegram/webhook"
    request.headers = {}
    if idempotency_key is not None:
        header_name = "x-idempotency-key" if x_header else "idempotency-key"
        request.headers[header_name] = idempotency_key
    request.body = AsyncMock(return_value=json.dumps(body or {"event": "message"}).encode())
    return request


async def _ok_response(_req: MagicMock) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {}
    resp.media_type = "application/json"

    async def _iter():
        yield b'{"ok": true}'

    resp.body_iterator = _iter()
    return resp


def _app_with_store(store: Any) -> FastAPI:
    app = FastAPI()
    hits = {"n": 0}
    lock = threading.Lock()

    @app.post("/api/v1/telegram/webhook")
    async def webhook() -> dict:
        with lock:
            hits["n"] += 1
            n = hits["n"]
        return {"ok": True, "handler_hits": n}

    app.state.handler_hits = hits  # type: ignore[attr-defined]
    app.add_middleware(IdempotencyMiddleware, store=store, paths_prefixes=("/api/v1/",))
    return app


# ---------------------------------------------------------------------------
# Pure store — asyncio concurrency (same event loop)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stress_fake_store_same_key_only_one_wins() -> None:
    """N concurrent setnx on the same key → exactly one True."""
    store = FakeIdempotencyStore()
    n = 64
    key = "stress:same-key"

    results = await asyncio.gather(*[store.setnx(key, {"i": i}, ttl_seconds=60) for i in range(n)])
    assert sum(1 for r in results if r is True) == 1
    assert sum(1 for r in results if r is False) == n - 1
    cached = await store.get(key)
    assert cached is not None
    assert "i" in cached


@pytest.mark.asyncio
async def test_stress_fake_store_many_unique_keys_all_win() -> None:
    """N concurrent setnx on unique keys → all True."""
    store = FakeIdempotencyStore()
    n = 128
    results = await asyncio.gather(
        *[store.setnx(f"stress:unique:{i}", {"i": i}, ttl_seconds=60) for i in range(n)]
    )
    assert all(results)
    for i in range(n):
        assert await store.get(f"stress:unique:{i}") == {"i": i}


@pytest.mark.asyncio
async def test_stress_fake_store_mixed_same_and_unique() -> None:
    """Burst: many unique + repeated claims of one contested key."""
    store = FakeIdempotencyStore()
    contested = "stress:contested"
    unique_n = 80
    contested_n = 40

    tasks = [store.setnx(f"stress:u:{i}", {"u": i}, ttl_seconds=60) for i in range(unique_n)]
    tasks += [store.setnx(contested, {"c": j}, ttl_seconds=60) for j in range(contested_n)]
    results = await asyncio.gather(*tasks)

    unique_results = results[:unique_n]
    contested_results = results[unique_n:]
    assert all(unique_results)
    assert sum(1 for r in contested_results if r) == 1
    assert await store.get(contested) is not None


# ---------------------------------------------------------------------------
# Pure store — threaded concurrency (lock-safe wrapper)
# ---------------------------------------------------------------------------


def test_stress_threaded_same_key_only_one_wins() -> None:
    store = ThreadSafeFakeIdempotencyStore()
    n = 48
    key = "thread:same"

    def claim(i: int) -> bool:
        return asyncio.run(store.setnx(key, {"i": i}, ttl_seconds=60))

    wins = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = [pool.submit(claim, i) for i in range(n)]
        for f in as_completed(futs):
            if f.result():
                wins += 1
    assert wins == 1
    assert store.size == 1


def test_stress_threaded_many_unique_keys() -> None:
    store = ThreadSafeFakeIdempotencyStore()
    n = 100

    def claim(i: int) -> bool:
        return asyncio.run(store.setnx(f"thread:u:{i}", {"i": i}, ttl_seconds=60))

    wins = 0
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = [pool.submit(claim, i) for i in range(n)]
        for f in as_completed(futs):
            if f.result():
                wins += 1
    assert wins == n
    assert store.size == n


# ---------------------------------------------------------------------------
# fakeredis — Redis SET NX atomicity under concurrency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stress_fakeredis_same_key_only_one_wins() -> None:
    from fakeredis import aioredis as fakeredis_async

    fake = fakeredis_async.FakeRedis(decode_responses=True)
    store = RedisIdempotencyStore(redis_url="redis://fake/0")
    store._client = fake  # type: ignore[assignment]

    n = 64
    key = "idempotency:fakeredis:same"
    results = await asyncio.gather(
        *[store.setnx(key, {"i": i, "body": "x"}, ttl_seconds=120) for i in range(n)]
    )
    assert sum(1 for r in results if r is True) == 1
    assert sum(1 for r in results if r is False) == n - 1
    got = await store.get(key)
    assert got is not None
    assert "i" in got


@pytest.mark.asyncio
async def test_stress_fakeredis_many_unique_keys() -> None:
    from fakeredis import aioredis as fakeredis_async

    fake = fakeredis_async.FakeRedis(decode_responses=True)
    store = RedisIdempotencyStore(redis_url="redis://fake/0")
    store._client = fake  # type: ignore[assignment]

    n = 100
    results = await asyncio.gather(
        *[store.setnx(f"idempotency:fakeredis:u:{i}", {"i": i}, ttl_seconds=120) for i in range(n)]
    )
    assert all(results)
    for i in range(n):
        assert await store.get(f"idempotency:fakeredis:u:{i}") == {"i": i}


# ---------------------------------------------------------------------------
# Middleware — X-Idempotency-Key concurrent claims (asyncio dispatch)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stress_mw_x_idempotency_same_key_setnx_single_winner() -> None:
    """Concurrent middleware dispatches with same X-Idempotency-Key.

    Middleware can invoke the handler more than once under race (get→handler→setnx),
    but the store setnx must keep a single cached payload (only one insert wins).
    """
    store = FakeIdempotencyStore()
    mw = IdempotencyMiddleware(
        app=MagicMock(),
        store=store,
        paths_prefixes=("/api/v1/",),
    )
    n = 32
    key = "x-stress-same-key"
    body = {"event": "message", "id": "m1"}

    requests = [_make_post_request(idempotency_key=key, body=body, x_header=True) for _ in range(n)]
    responses = await asyncio.gather(*[mw.dispatch(req, _ok_response) for req in requests])
    assert all(r.status_code == 200 for r in responses)

    cache_key = _hash_idempotency_key(key, "/api/v1/telegram/webhook", "POST")
    cached = await store.get(cache_key)
    assert cached is not None
    assert cached.get("status_code") == 200

    # Second wave: all must be pure replays (no new store insert race)
    requests2 = [
        _make_post_request(idempotency_key=key, body=body, x_header=True) for _ in range(16)
    ]
    call_counts: list[int] = []

    async def counting_next(_req: MagicMock) -> MagicMock:
        call_counts.append(1)
        return await _ok_response(_req)

    responses2 = await asyncio.gather(*[mw.dispatch(req, counting_next) for req in requests2])
    assert all(r.status_code == 200 for r in responses2)
    assert call_counts == []  # full cache hit


@pytest.mark.asyncio
async def test_stress_mw_x_idempotency_many_unique_keys() -> None:
    store = FakeIdempotencyStore()
    mw = IdempotencyMiddleware(
        app=MagicMock(),
        store=store,
        paths_prefixes=("/api/v1/",),
    )
    n = 64
    requests = [
        _make_post_request(
            idempotency_key=f"x-unique-{i}",
            body={"event": "message", "id": i},
            x_header=True,
        )
        for i in range(n)
    ]
    responses = await asyncio.gather(*[mw.dispatch(req, _ok_response) for req in requests])
    assert all(r.status_code == 200 for r in responses)

    for i in range(n):
        cache_key = _hash_idempotency_key(f"x-unique-{i}", "/api/v1/telegram/webhook", "POST")
        assert await store.get(cache_key) is not None


# ---------------------------------------------------------------------------
# Middleware — threaded TestClient + X-Idempotency-Key
# ---------------------------------------------------------------------------


def test_stress_http_x_idempotency_same_key_threaded() -> None:
    store = ThreadSafeFakeIdempotencyStore()
    app = _app_with_store(store)
    path = "/api/v1/telegram/webhook"
    key = "http-thread-same"
    headers = {
        "X-Idempotency-Key": key,
        "Content-Type": "application/json",
    }
    body = {"event": "message", "id": "shared"}

    def one() -> int:
        client = TestClient(app)
        r = client.post(path, json=body, headers=headers)
        return r.status_code

    n = 24
    codes: list[int] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = [pool.submit(one) for _ in range(n)]
        for f in as_completed(futs):
            codes.append(f.result())

    assert all(c == 200 for c in codes)
    # After storm, a single follow-up is a clean replay
    client = TestClient(app)
    r = client.post(path, json=body, headers=headers)
    assert r.status_code == 200
    assert r.json().get("ok") is True
    # Only one store entry for this idempotency key
    assert store.size == 1


def test_stress_http_x_idempotency_many_unique_keys_threaded() -> None:
    store = ThreadSafeFakeIdempotencyStore()
    app = _app_with_store(store)
    path = "/api/v1/telegram/webhook"

    def one(i: int) -> tuple[int, dict]:
        client = TestClient(app)
        headers = {
            "X-Idempotency-Key": f"http-u-{i}",
            "Content-Type": "application/json",
        }
        r = client.post(path, json={"event": "message", "id": i}, headers=headers)
        return r.status_code, r.json()

    n = 40
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = [pool.submit(one, i) for i in range(n)]
        results = [f.result() for f in as_completed(futs)]

    assert all(code == 200 for code, _ in results)
    assert all(payload.get("ok") is True for _, payload in results)
    assert store.size == n
    assert app.state.handler_hits["n"] == n  # type: ignore[index]
