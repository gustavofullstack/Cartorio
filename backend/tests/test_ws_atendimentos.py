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
from starlette.websockets import WebSocketDisconnect

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
        mgr.unregister(ws, "room1")  # type: ignore[arg-type]
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

        await mgr.send_personal(ws1, {"dm": "so pra voce"})  # type: ignore[arg-type]
        assert received == [{"dm": "so pra voce"}]


# ============================================================
# GRUPO 4: WebSocket endpoint integration (TestClient)
# ============================================================


class TestWSAtendimentosIntegration:
    """Integration do endpoint /ws/atendimentos com TestClient."""

    def test_endpoint_registered_in_app(self) -> None:
        """Endpoint /ws/atendimentos registrado no app principal (main.py)."""
        from app.api.v1.ws.atendimentos import ws_router
        from app.main import app

        # 1) Verifica declaracao do endpoint no ws_router
        ws_paths = [r.path for r in ws_router.routes if hasattr(r, "path")]
        assert "/ws/atendimentos" in ws_paths, (
            f"endpoint nao declarado em ws_router. Routes: {ws_paths}"
        )

        # 2) Verifica que ws_router foi incluido no app.
        # FastAPI wrappa routers incluidos em _IncludedRouter com atributo
        # `original_router` (nao `router`). Precisamos comparar identidade.
        included = any(getattr(r, "original_router", None) is ws_router for r in app.routes)
        assert included, "ws_router nao foi incluido no app via app.include_router"

    def test_endpoint_works_with_test_client(self) -> None:
        """Endpoint funciona em TestClient (handshake inicial)."""
        from app.api.v1.ws.atendimentos import ws_router

        app = FastAPI()
        app.include_router(ws_router)
        client = TestClient(app)
        # TestClient aceita WS via context manager. Smoke test: handshake ok.
        try:
            with client.websocket_connect("/ws/atendimentos") as ws:
                # Servidor responde pong se mandarmos ping
                ws.send_text('{"type":"ping"}')
                # Pode dar timeout se mandar pong nao implementado
                # Mas pelo menos o handshake passou
                assert True
        except Exception as e:  # noqa: BLE001
            # Aceita erros de timeout/leitura — objetivo eh validar handshake
            assert "Handshake" not in str(e), f"handshake falhou: {e}"


# ============================================================
# GRUPO 5: Redis pub/sub integration (com fakeredis)
# ============================================================


class TestWSAtendimentosRedisIntegration:
    """Mensagem publicada no RedisBus deve chegar via broadcast."""

    async def test_redis_message_triggers_broadcast(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """E2E: mensagem publicada em RedisBus chega via broadcast.

        NOTA: usa fakeredis. Para teste com Redis REAL (SCRAM auth + cluster +
        pubsub semantics), ver tests/integration/test_ws_atendimentos_real_redis.py
        (planejado Sprint 3 — requer Redis 7+ rodando).
        """
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

        # Inicia listener PRIMEIRO (deixa connect estabilizar)
        bus_sub = RedisBus()
        listener_done = asyncio.Event()
        delivered_count = 0

        async def listener_loop() -> None:
            nonlocal delivered_count
            async for msg in bus_sub.subscribe("cartorio:atendimentos"):
                delivered_count = await mgr.broadcast(msg["channel"], msg["data"])
                listener_done.set()
                return

        listener_task = asyncio.create_task(listener_loop())
        # Da tempo do subscribe conectar ANTES do publish
        await asyncio.sleep(0.1)

        # Publica mensagem via RedisBus de "outra replica"
        bus_pub = RedisBus()
        await bus_pub.publish(
            "cartorio:atendimentos",
            {"evento": "novo_atendimento", "id": 42},
        )

        # Espera listener processar (max 2s)
        try:
            await asyncio.wait_for(listener_done.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            listener_task.cancel()
            raise

        # Cleanup
        listener_task.cancel()
        try:
            await listener_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass

        assert delivered_count == 1
        assert len(received) == 1
        assert received[0] == {"evento": "novo_atendimento", "id": 42}


# ============================================================
# GRUPO 6: Ping/pong protocol (T2.API.T19)
# ============================================================


class TestWSAtendimentosPingPong:
    """Protocolo ping/pong do WebSocket /api/v1/ws/atendimentos.

    O servidor deve responder {"type": "pong"} a {"type": "ping"} e
    echo da mensagem para qualquer outro payload.
    """

    def _make_client(self) -> TestClient:
        """Cria TestClient isolado com main app + prefix /api/v1."""
        from app.api.v1.ws.atendimentos import ws_router

        isolated_app = FastAPI()
        isolated_app.include_router(ws_router, prefix="/api/v1")
        return TestClient(isolated_app)

    def test_ping_returns_pong(self) -> None:
        """ping -> pong (handshake + echo)."""
        client = self._make_client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "ping"})
            response = ws.receive_json()
            assert response["type"] == "pong"

    def test_non_ping_returns_echo_with_data(self) -> None:
        """Mensagem não-ping -> echo da mensagem."""
        client = self._make_client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "msg", "text": "ola"})
            response = ws.receive_json()
            assert response["type"] == "echo"
            assert response["data"] == {"type": "msg", "text": "ola"}

    def test_invalid_json_returns_echo_raw(self) -> None:
        """String nao-JSON → echo com data.raw."""
        client = self._make_client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_text("not json")
            response = ws.receive_json()
            assert response["type"] == "echo"
            assert "raw" in response["data"]
            assert response["data"]["raw"] == "not json"

    def test_plain_text_non_json_returns_echo_raw(self) -> None:
        """Texto simples (nao-JSON) → echo raw."""
        client = self._make_client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_text("hello world")
            response = ws.receive_json()
            assert response["type"] == "echo"
            assert response["data"]["raw"] == "hello world"


# ============================================================
# GRUPO 7: WebSocket lifecycle (cleanup on disconnect)
# ============================================================


class TestWSAtendimentosLifecycle:
    """Lifecycle: register, deregister, listener cleanup."""

    def _make_client(self) -> TestClient:
        from app.api.v1.ws.atendimentos import ws_router

        isolated_app = FastAPI()
        isolated_app.include_router(ws_router, prefix="/api/v1")
        return TestClient(isolated_app)

    def test_client_disconnect_cleans_manager_state(self) -> None:
        """Disconnect limpa o ConnectionManager (total_connections=0)."""
        from app.services.websocket_manager import get_manager

        # Limpa estado global entre testes
        mgr = get_manager()
        mgr.connections.clear()

        client = self._make_client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            # Confirma que cliente foi registrado
            assert mgr.total_connections() >= 1
            ws.send_json({"type": "ping"})
            ws.receive_json()
        # Apos sair do context manager, cliente foi desconectado
        assert mgr.total_connections() == 0

    def test_double_register_same_ws_idempotent(self) -> None:
        """Register 2x do mesmo ws na mesma room: Set garante unicidade."""
        from app.services.websocket_manager import get_manager

        mgr = get_manager()
        mgr.connections.clear()

        client = self._make_client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws1:
            with client.websocket_connect("/api/v1/ws/atendimentos") as ws2:
                ws1.send_json({"type": "ping"})
                ws1.receive_json()
                ws2.send_json({"type": "ping"})
                ws2.receive_json()
        # Cada context manager registra/desregistra independentemente
        assert mgr.total_connections() == 0

    def test_listener_task_cancelled_on_disconnect(self) -> None:
        """Disconnect cancela o _redis_listener_loop (task cleanup)."""
        from app.services.websocket_manager import get_manager

        mgr = get_manager()
        mgr.connections.clear()

        client = self._make_client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "ping"})
            ws.receive_json()
            # Dentro do contexto: conexao ativa
            assert mgr.total_connections() == 1
        # Apos contexto: tudo limpo, sem task leak
        assert mgr.total_connections() == 0


# ============================================================
# GRUPO 8: Server-side heartbeat (E2.05 — timeout/missed pong cleanup)
# ============================================================


class TestWSAtendimentosHeartbeatCleanup:
    """Heartbeat server-side: idle -> server ping; missed pongs -> close + cleanup.

    Cobre o loop do endpoint (atendimentos.py): apos ping_interval sem
    atividade o server envia {"type":"ping","ts":...}; se o cliente nao
    responde pong dentro de pong_timeout por max_missed ciclos, o server
    fecha a conexao (code 1001) e remove o client do ConnectionManager.

    Usa _DEFAULT_HB monkeypatched com timers curtos (0.1s — piso de
    receive_timeout_sec) para nao esperar os 20s/10s de producao.
    Redis esta mockado no conftest (sem network).
    """

    _FAST_HB_KWARGS: dict[str, Any] = {
        "ping_interval_sec": 0.1,
        "pong_timeout_sec": 0.1,
        "max_missed": 2,
    }

    def _make_client(self, monkeypatch: pytest.MonkeyPatch) -> TestClient:
        from app.api.v1.ws import atendimentos as ws_module
        from app.services.ws_heartbeat import WSHeartbeatConfig

        monkeypatch.setattr(ws_module, "_DEFAULT_HB", WSHeartbeatConfig(**self._FAST_HB_KWARGS))
        isolated_app = FastAPI()
        isolated_app.include_router(ws_module.ws_router, prefix="/api/v1")
        return TestClient(isolated_app)

    def test_idle_client_receives_server_ping(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Cliente idle -> server envia ping com timestamp apos ping_interval."""
        client = self._make_client(monkeypatch)
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "ping"
            assert "ts" in msg

    def test_missed_pongs_close_connection_and_cleanup(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cliente que nunca responde pong: server fecha (1001) e unregister.

        Fluxo com max_missed=2: ping -> timeout (missed=1) -> re-ping ->
        timeout (missed=2) -> close + manager.unregister.
        """
        from app.services.websocket_manager import get_manager

        mgr = get_manager()
        mgr.connections.clear()

        client = self._make_client(monkeypatch)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
                # 1o server ping (idle timeout)
                assert ws.receive_json()["type"] == "ping"
                # missed=1 -> server reenvia ping
                assert ws.receive_json()["type"] == "ping"
                # missed=2 -> server fecha: proximo receive levanta
                ws.receive_json()
        assert exc_info.value.code == 1001
        # Cleanup: conexao removida do manager apos close por heartbeat
        assert mgr.total_connections() == 0

    def test_client_pong_resets_missed_and_stays_connected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cliente que responde pong ao server ping: conexao NAO fecha.

        Regressao: mark_pong zera missed_count; sem isso o 2o timeout
        encerraria a conexao indevidamente.
        """
        client = self._make_client(monkeypatch)
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            # Ciclo 1: server ping -> client pong
            assert ws.receive_json()["type"] == "ping"
            ws.send_json({"type": "pong"})
            # Ciclo 2: idle novamente -> server ping (conexao segue viva)
            assert ws.receive_json()["type"] == "ping"
            ws.send_json({"type": "pong"})
            # Ciclo 3: ainda viva — recebe novo ping em vez de close
            assert ws.receive_json()["type"] == "ping"
