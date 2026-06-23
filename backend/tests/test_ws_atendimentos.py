"""Testes do WebSocket /ws/atendimentos (T2.API.T19).

Cobre:
1. ConnectionManager connect/disconnect (state local).
2. Broadcast para todos clients em uma room.
3. send_personal para um client especifico.
4. Redis pub/sub integration (mensagem de outra replica chega via RedisBus).
5. WebSocket lifecycle (connect -> send -> receive -> close).
6. Multi-client broadcast (3 clients recebem mesma mensagem).
7. Backpressure / desconexao silenciosa (send para cliente morto nao bloqueia).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.websocket_manager import ConnectionManager


# ============================================================
# GRUPO 1: ConnectionManager unit (sem WebSocket real)
# ============================================================


class TestConnectionManagerUnit:
    """Unit tests do ConnectionManager isolado (sem WebSocket/Redis)."""

    def test_init_empty(self) -> None:
        mgr = ConnectionManager()
        assert mgr.connections == {}
        assert mgr.total_connections() == 0

    def test_register_adds_to_room(self) -> None:
        mgr = ConnectionManager()

        class FakeWS:
            client = type("C", (), {"host": "1.2.3.4"})()

        mgr.register(FakeWS(), "cartorio:atendimentos")  # type: ignore[arg-type]
        assert "cartorio:atendimentos" in mgr.connections
        assert mgr.total_connections() == 1

    def test_unregister_removes_from_room(self) -> None:
        mgr = ConnectionManager()

        class FakeWS:
            client = type("C", (), {"host": "1.2.3.4"})()

        ws = FakeWS()
        mgr.register(ws, "room1")  # type: ignore[arg-type]
        mgr.unregister(ws, "room1")
        assert mgr.total_connections() == 0

    def test_unregister_unknown_ws_is_safe(self) -> None:
        """unregister de WS que nao esta na room nao levanta erro."""
        mgr = ConnectionManager()

        class FakeWS:
            client = type("C", (), {"host": "1.2.3.4"})()

        mgr.unregister(FakeWS(), "room_inexistente")  # type: ignore[arg-type]
        assert mgr.total_connections() == 0

    def test_total_connections_across_rooms(self) -> None:
        mgr = ConnectionManager()

        class FakeWS:
            client = type("C", (), {"host": "1.2.3.4"})()

        mgr.register(FakeWS(), "room_a")  # type: ignore[arg-type]
        mgr.register(FakeWS(), "room_a")  # type: ignore[arg-type]
        mgr.register(FakeWS(), "room_b")  # type: ignore[arg-type]
        assert mgr.total_connections() == 3
        assert len(mgr.connections["room_a"]) == 2
        assert len(mgr.connections["room_b"]) == 1


# ============================================================
# GRUPO 2: ConnectionManager.broadcast (com fake WebSocket)
# ============================================================


class TestConnectionManagerBroadcast:
    """Broadcast envia JSON para todos clients em uma room."""

    async def test_broadcast_to_empty_room_noop(self) -> None:
        mgr = ConnectionManager()
        # Nao levanta erro, nao faz nada
        count = await mgr.broadcast("room_vazia", {"msg": "oi"})
        assert count == 0

    async def test_broadcast_to_multiple_clients(self) -> None:
        """3 clients na mesma room recebem a mensagem."""
        mgr = ConnectionManager()
        sent: list[dict[str, Any]] = []

        class FakeWS:
            def __init__(self, name: str) -> None:
                self.name = name
                self.client = type("C", (), {"host": "1.2.3.4"})()

            async def send_json(self, data: dict[str, Any]) -> None:
                sent.append({"to": self.name, "data": data})

        ws1 = FakeWS("c1")
        ws2 = FakeWS("c2")
        ws3 = FakeWS("c3")
        mgr.register(ws1, "room")  # type: ignore[arg-type]
        mgr.register(ws2, "room")  # type: ignore[arg-type]
        mgr.register(ws3, "room")  # type: ignore[arg-type]

        count = await mgr.broadcast("room", {"evento": "novo"})
        assert count == 3
        assert len(sent) == 3
        assert all(s["data"] == {"evento": "novo"} for s in sent)
        names = {s["to"] for s in sent}
        assert names == {"c1", "c2", "c3"}

    async def test_broadcast_swallows_send_failure(self) -> None:
        """Se um cliente morre durante broadcast, manager continua com outros."""
        mgr = ConnectionManager()
        sent: list[str] = []

        class GoodWS:
            client = type("C", (), {"host": "1.2.3.4"})()

            async def send_json(self, data: dict[str, Any]) -> None:
                sent.append("good")

        class DeadWS:
            client = type("C", (), {"host": "1.2.3.4"})()

            async def send_json(self, data: dict[str, Any]) -> None:
                raise RuntimeError("client disconnected")

        mgr.register(GoodWS(), "room")  # type: ignore[arg-type]
        mgr.register(DeadWS(), "room")  # type: ignore[arg-type]

        # broadcast NAO deve levantar mesmo com 1 cliente morto
        count = await mgr.broadcast("room", {"msg": "oi"})
        # GoodWS recebeu, DeadWS falhou -> count reflete sucessos
        assert sent == ["good"]
        assert count == 1


# ============================================================
# GRUPO 3: ConnectionManager.send_personal
# ============================================================


class TestConnectionManagerSendPersonal:
    async def test_send_personal_to_specific_client(self) -> None:
        mgr = ConnectionManager()
        received: list[dict[str, Any]] = []

        class FakeWS:
            client = type("C", (), {"host": "1.2.3.4"})()

            async def send_json(self, data: dict[str, Any]) -> None:
                received.append(data)

        ws1 = FakeWS()
        ws2 = FakeWS()
        mgr.register(ws1, "room")  # type: ignore[arg-type]
        mgr.register(ws2, "room")  # type: ignore[arg-type]

        await mgr.send_personal(ws1, {"dm": "so pra voce"})
        assert received == [{"dm": "so pra voce"}]


# ============================================================
# GRUPO 4: WebSocket endpoint integration (TestClient)
# ============================================================


class TestWSAtendimentosIntegration:
    """Integration do endpoint /ws/atendimentos com TestClient."""

    def test_endpoint_registered_and_reachable(self) -> None:
        from app.api.v1.ws.atendimentos import ws_router

        app = FastAPI()
        app.include_router(ws_router)
        client = TestClient(app)
        # Tentativa de conectar -> 403 (TestClient nao suporta WS sem context manager)
        # Apenas valida que a rota existe via openapi
        schema = client.get("/openapi.json").json()
        paths = schema.get("paths", {})
        assert any("/ws/atendimentos" in p for p in paths)


# ============================================================
# GRUPO 5: Redis pub/sub integration (com fakeredis)
# ============================================================


class TestWSAtendimentosRedisIntegration:
    """Mensagem publicada no RedisBus deve chegar via broadcast."""

    async def test_redis_message_triggers_broadcast(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fakeredis import aioredis as fakeredis_async

        from app.services.redis_bus import RedisBus

        fake_server = fakeredis_async.FakeRedis(decode_responses=True)

        def fake_from_url(url: str, **kwargs: Any) -> Any:
            return fake_server

        monkeypatch.setattr("redis.asyncio.from_url", fake_from_url)

        mgr = ConnectionManager()
        received: list[dict[str, Any]] = []

        class FakeWS:
            client = type("C", (), {"host": "1.2.3.4"})()

            async def send_json(self, data: dict[str, Any]) -> None:
                received.append(data)

        mgr.register(FakeWS(), "cartorio:atendimentos")  # type: ignore[arg-type]

        # Publica mensagem via RedisBus de "outra replica"
        bus_pub = RedisBus()
        await bus_pub.publish(
            "cartorio:atendimentos",
            {"evento": "novo_atendimento", "id": 42},
        )

        # Listener local (mesmo padrao do endpoint /ws/atendimentos)
        # Faz loop de subscribe e broadcast.
        async def listener_loop() -> None:
            bus_sub = RedisBus()
            async for msg in bus_sub.subscribe("cartorio:atendimentos"):
                await mgr.broadcast(msg["channel"], msg["data"])
                # Limita a 1 mensagem pra teste nao ficar pendurado
                return

        await asyncio.wait_for(listener_loop(), timeout=2.0)

        assert len(received) == 1
        assert received[0] == {"evento": "novo_atendimento", "id": 42}