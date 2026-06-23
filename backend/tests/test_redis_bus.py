"""Testes do RedisBus (T2.API.T20).

Usa fakeredis pra nao depender de Redis rodando em testes locais.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fakeredis import aioredis as fakeredis_async

from app.services.redis_bus import (
    CHANNEL_ALERTAS,
    CHANNEL_ATENDIMENTOS,
    CHANNEL_PROTOCOLOS,
    RedisBus,
    RedisBusError,
    get_bus,
)


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Substitui o redis client por fakeredis async.

    Monkeypatcha o construtor redis_async.from_url pra retornar fakeredis.
    """
    fake_server = fakeredis_async.FakeRedis(decode_responses=True)

    def fake_from_url(url: str, **kwargs: Any) -> Any:
        return fake_server

    monkeypatch.setattr("redis.asyncio.from_url", fake_from_url)


class TestRedisBusInit:
    def test_init_default(self) -> None:
        bus = RedisBus()
        assert bus._url  # default de settings

    def test_init_custom_url(self) -> None:
        bus = RedisBus(redis_url="redis://other:6379/1")
        assert bus._url == "redis://other:6379/1"


class TestRedisBusPing:
    async def test_ping_ok(self, fake_redis: None) -> None:
        bus = RedisBus()
        assert await bus.ping() is True

    async def test_ping_no_url(self, fake_redis: None) -> None:
        bus = RedisBus(redis_url="")
        # Forca a config para vazia (nao herda de settings)
        bus._url = ""
        print(f"DEBUG url={bus._url!r} client={bus._client!r}")
        try:
            result = await bus.ping()
            print(f"DEBUG ping returned {result}")
        except Exception as e:
            print(f"DEBUG got exception {type(e).__name__}: {e}")
        with pytest.raises(RedisBusError):
            await bus.ping()


class TestRedisBusPublish:
    async def test_publish_returns_count(self, fake_redis: None) -> None:
        bus = RedisBus()
        count = await bus.publish(CHANNEL_ATENDIMENTOS, {"evento": "novo", "id": 1})
        # Sem subscribers = 0
        assert count == 0

    async def test_publish_rejects_empty_channel(self, fake_redis: None) -> None:
        bus = RedisBus()
        with pytest.raises(RedisBusError):
            await bus.publish("", {"x": 1})

    async def test_publish_rejects_non_dict(self, fake_redis: None) -> None:
        bus = RedisBus()
        with pytest.raises(RedisBusError):
            await bus.publish("cartorio:x", "string nao-dict")  # type: ignore[arg-type]

    async def test_publish_serializes_datetime(self, fake_redis: None) -> None:
        bus = RedisBus()
        from datetime import datetime

        # Deve serializar sem erro (default=str)
        count = await bus.publish(
            "cartorio:x",
            {"ts": datetime(2026, 6, 23, 14, 0, 0)},
        )
        assert count == 0


class TestRedisBusSubscribe:
    async def test_subscribe_receives_message(self, fake_redis: None) -> None:
        bus_pub = RedisBus()
        bus_sub = RedisBus()

        received: list[dict[str, Any]] = []

        async def reader() -> None:
            async for msg in bus_sub.subscribe(CHANNEL_ATENDIMENTOS):
                received.append(msg)
                if len(received) >= 1:
                    return

        # Inicia reader em background
        task = asyncio.create_task(reader())
        await asyncio.sleep(0.1)  # da tempo do subscribe conectar

        await bus_pub.publish(CHANNEL_ATENDIMENTOS, {"evento": "novo"})

        try:
            await asyncio.wait_for(task, timeout=2.0)
        except asyncio.TimeoutError:
            task.cancel()
            raise

        assert len(received) == 1
        assert received[0]["channel"] == CHANNEL_ATENDIMENTOS
        assert received[0]["data"] == {"evento": "novo"}

    async def test_subscribe_requires_channel(self, fake_redis: None) -> None:
        bus = RedisBus()
        gen = bus.subscribe()
        with pytest.raises(RedisBusError):
            async for _ in gen:
                pass


class TestRedisBusPatternSubscribe:
    async def test_psubscribe_receives_matching_channels(
        self, fake_redis: None
    ) -> None:
        bus_pub = RedisBus()
        bus_sub = RedisBus()

        received: list[dict[str, Any]] = []

        async def reader() -> None:
            async for msg in bus_sub.pattern_subscribe("cartorio:*"):
                received.append(msg)
                if len(received) >= 2:
                    return

        task = asyncio.create_task(reader())
        await asyncio.sleep(0.1)

        await bus_pub.publish(CHANNEL_ATENDIMENTOS, {"e": 1})
        await bus_pub.publish(CHANNEL_PROTOCOLOS, {"e": 2})

        try:
            await asyncio.wait_for(task, timeout=2.0)
        except asyncio.TimeoutError:
            task.cancel()
            raise

        assert len(received) == 2
        channels = {r["channel"] for r in received}
        assert CHANNEL_ATENDIMENTOS in channels
        assert CHANNEL_PROTOCOLOS in channels

    async def test_psubscribe_requires_pattern(self, fake_redis: None) -> None:
        bus = RedisBus()
        gen = bus.pattern_subscribe("")
        with pytest.raises(RedisBusError):
            async for _ in gen:
                pass


class TestRedisBusSingleton:
    def test_get_bus_returns_singleton(self) -> None:
        a = get_bus()
        b = get_bus()
        assert a is b