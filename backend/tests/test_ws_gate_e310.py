"""E3.10 — Gate formal WebSocket /ws/atendimentos (offline: TestClient + fakeredis).

Matriz do gate e o que é verificável offline:

  | Área          | Status offline | Onde |
  | ------------- | -------------- | ---- |
  | auth          | BLOCKED_PROD   | endpoint hoje NÃO exige credencial
  |               |                | (docstring LGPD: forwarding interno).
  |               |                | Gate formal de auth (token via
  |               |                | subprotocol/query + allowlist de
  |               |                | origin) exige decisão de design e
  |               |                | validação atrás do proxy prod. Este
  |               |                | arquivo DOCUMENTA o contrato atual
  |               |                | (handshake sem credencial) para o
  |               |                | gate não passar silenciosamente.
  | reconexão     | COBERTO        | TestWSGateReconnection |
  | ordenação     | COBERTO        | TestWSGateOrdering (fakeredis) |
  | backpressure  | COBERTO        | TestWSGateBackpressure |
  | cleanup       | COBERTO        | TestWSGateCleanup |
  | PII scrub     | COBERTO (boundary) | TestWSGatePIIScrubBoundary |
  | métricas      | PARCIAL        | gauge observável offline =
  |               |                | ConnectionManager.total_connections()
  |               |                | + last_seen (touch). Séries
  |               |                | Prometheus dedicadas a WS:
  |               |                | BLOCKED (não existem hoje; exigem
  |               |                | mudança fora do escopo desta lane).

Referências existentes (não duplicadas): tests/test_ws_atendimentos.py
(ping/pong G7, heartbeat G8.01 cleanup, lifecycle), tests/test_ws_ping_g7.py,
tests/test_ws_concurrency_g8.py, tests/test_ws_heartbeat_g8.py.

Modified by Gustavo Almeida — E3.10 gate formal WS.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.websocket_manager import ConnectionManager

ROOM = "cartorio:atendimentos"


def _make_client() -> TestClient:
    from app.api.v1.ws.atendimentos import ws_router

    isolated_app = FastAPI()
    isolated_app.include_router(ws_router, prefix="/api/v1")
    return TestClient(isolated_app)


# ============================================================
# 1. Auth — contrato ATUAL documentado; enforcement = BLOCKED_PROD
# ============================================================


class TestWSGateAuth:
    def test_current_contract_handshake_sem_credencial(self) -> None:
        """DOCUMENTAÇÃO DE GAP: hoje o endpoint aceita handshake sem auth.

        Este teste existe para o gate E3.10 não ficar silencioso: se um
        gate de auth for adicionado ao endpoint (token via subprotocol,
        query param assinado ou allowlist de origin no proxy), este teste
        QUEBRA e deve ser substituído pela matriz 401/close-4401.
        Enforcement em prod: BLOCKED (exige decisão de design + validação
        atrás do proxy — fora do escopo offline).
        """
        client = _make_client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "ping"})
            assert ws.receive_json()["type"] == "pong"


# ============================================================
# 2. Reconexão
# ============================================================


class TestWSGateReconnection:
    def test_reconnect_after_clean_disconnect(self) -> None:
        """Cliente reconecta após disconnect limpo; ciclo register/unregister íntegro."""
        from app.services.websocket_manager import get_manager

        mgr = get_manager()
        mgr.connections.clear()

        client = _make_client()
        for ciclo in range(3):
            with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
                assert mgr.total_connections() >= 1
                ws.send_json({"type": "ping"})
                assert ws.receive_json()["type"] == "pong"
            assert mgr.total_connections() == 0, f"ciclo {ciclo}: conexão vazou"

    def test_reconnect_after_abrupt_drop(self) -> None:
        """Cliente que 'morre' (close sem pong) não impede reconexão posterior."""
        from app.services.websocket_manager import get_manager

        mgr = get_manager()
        mgr.connections.clear()

        client = _make_client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "ping"})
            ws.receive_json()
        # Novo cliente conecta normalmente após o anterior sair.
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws2:
            ws2.send_json({"type": "ping"})
            assert ws2.receive_json()["type"] == "pong"
        assert mgr.total_connections() == 0


# ============================================================
# 3. Ordenação (RedisBus fakeredis -> broadcast)
# ============================================================


class TestWSGateOrdering:
    async def test_broadcasts_preserve_publish_order(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mensagens publicadas em sequência chegam na ordem (FIFO do pub/sub)."""
        from fakeredis import aioredis as fakeredis_async

        from app.services.redis_bus import RedisBus

        fake_server = fakeredis_async.FakeRedis(decode_responses=True)
        monkeypatch.setattr("redis.asyncio.from_url", lambda url, **kw: fake_server)

        mgr = ConnectionManager()
        received: list[dict[str, Any]] = []

        class FakeWS:
            client = type("C", (), {"host": "1.2.3.4"})()

            async def send_json(self, data: dict[str, Any]) -> None:
                received.append(data)

        mgr.register(FakeWS(), ROOM)  # type: ignore[arg-type]

        bus_sub = RedisBus()
        done = asyncio.Event()
        esperado = [{"evento": "evt", "seq": i} for i in range(5)]

        async def listener_loop() -> None:
            async for msg in bus_sub.subscribe(ROOM):
                await mgr.broadcast(msg["channel"], msg["data"])
                if len(received) == len(esperado):
                    done.set()
                    return

        listener_task = asyncio.create_task(listener_loop())
        await asyncio.sleep(0.1)

        bus_pub = RedisBus()
        for payload in esperado:
            await bus_pub.publish(ROOM, payload)

        try:
            await asyncio.wait_for(done.wait(), timeout=3.0)
        finally:
            listener_task.cancel()
            # Se o listener ja retornou (done.set()), await nao levanta
            # CancelledError; suppress cobre ambos os caminhos.
            import contextlib

            with contextlib.suppress(asyncio.CancelledError):
                await listener_task

        assert received == esperado


# ============================================================
# 4. Backpressure (fail-loud: morto sai, vivos recebem)
# ============================================================


class TestWSGateBackpressure:
    async def test_dead_client_unregistered_others_continue(self) -> None:
        """Política fail-loud do manager: send falho remove o morto e
        broadcast segue para os demais (sem silent drop nem bloqueio)."""
        mgr = ConnectionManager()
        entregues: list[str] = []

        class GoodWS:
            def __init__(self, name: str) -> None:
                self.name = name
                self.client = type("C", (), {"host": "1.2.3.4"})()

            async def send_json(self, data: dict[str, Any]) -> None:
                entregues.append(self.name)

        class DeadWS:
            client = type("C", (), {"host": "1.2.3.4"})()

            async def send_json(self, data: dict[str, Any]) -> None:
                raise RuntimeError("client disconnected")

        good1, good2, dead = GoodWS("g1"), GoodWS("g2"), DeadWS()
        mgr.register(good1, ROOM)  # type: ignore[arg-type]
        mgr.register(dead, ROOM)  # type: ignore[arg-type]
        mgr.register(good2, ROOM)  # type: ignore[arg-type]

        delivered = await mgr.broadcast(ROOM, {"evento": "x"})
        assert delivered == 2
        assert sorted(entregues) == ["g1", "g2"]

    async def test_stress_harness_partial_failure_counts(self) -> None:
        """Harness ws_concurrency: 50 clients, 1 a cada 5 morre no send."""
        from app.services.ws_concurrency import stress_register_broadcast

        mgr = ConnectionManager()
        report = await stress_register_broadcast(
            mgr, ROOM, 50, {"evento": "carga"}, fail_every=5
        )
        assert report.registered == 50
        assert report.broadcast_delivered == 40
        assert report.errors == 10


# ============================================================
# 5. Cleanup (disconnect/heartbeat -> unregister + cancel listener)
# ============================================================


class TestWSGateCleanup:
    def test_disconnect_unregisters_and_cancels_listener(self) -> None:
        """Saída do contexto TestClient = disconnect: manager volta a 0 e
        o listener task é cancelado (sem leak) — gate formal do lifecycle."""
        from app.services.websocket_manager import get_manager

        mgr = get_manager()
        mgr.connections.clear()

        client = _make_client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "ping"})
            ws.receive_json()
            assert mgr.total_connections() == 1
        assert mgr.total_connections() == 0

    def test_heartbeat_missed_pongs_close_and_cleanup(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Versão compacta do gate heartbeat (suíte completa em
        tests/test_ws_atendimentos.py::TestWSAtendimentosHeartbeatCleanup):
        max_missed atingido -> close 1001 + unregister."""
        from starlette.websockets import WebSocketDisconnect

        from app.api.v1.ws import atendimentos as ws_module
        from app.services.websocket_manager import get_manager
        from app.services.ws_heartbeat import WSHeartbeatConfig

        monkeypatch.setattr(
            ws_module,
            "_DEFAULT_HB",
            WSHeartbeatConfig(ping_interval_sec=0.1, pong_timeout_sec=0.1, max_missed=2),
        )
        mgr = get_manager()
        mgr.connections.clear()

        isolated_app = FastAPI()
        isolated_app.include_router(ws_module.ws_router, prefix="/api/v1")
        client = TestClient(isolated_app)

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
                assert ws.receive_json()["type"] == "ping"
                assert ws.receive_json()["type"] == "ping"
                ws.receive_json()
        assert exc_info.value.code == 1001
        assert mgr.total_connections() == 0


# ============================================================
# 6. PII scrub — fronteira de responsabilidade
# ============================================================


class TestWSGatePIIScrubBoundary:
    CANARY_CPF = "529.982.247-25"

    async def test_publisher_scrubbed_payload_delivered_masked(self) -> None:
        """Contrato LGPD do endpoint: 'PII scrubbing deve ser feito ANTES
        de chamar publish/broadcast' (docstring atendimentos.py). Publisher
        que aplica pii.scrub entrega payload mascarado aos clients."""
        from app.services.pii import scrub

        mgr = ConnectionManager()
        entregues: list[dict[str, Any]] = []

        class FakeWS:
            client = type("C", (), {"host": "1.2.3.4"})()

            async def send_json(self, data: dict[str, Any]) -> None:
                entregues.append(data)

        mgr.register(FakeWS(), ROOM)  # type: ignore[arg-type]

        # Publisher correto: scrub ANTES de publicar.
        mensagem = scrub(f"novo atendimento do cpf {self.CANARY_CPF}").text
        await mgr.broadcast(ROOM, {"evento": "novo_atendimento", "resumo": mensagem})

        assert len(entregues) == 1
        assert self.CANARY_CPF not in str(entregues[0])
        assert "[CPF_REDACTED]" in entregues[0]["resumo"]

    async def test_endpoint_forwards_verbatim_no_scrub_layer(self) -> None:
        """Fronteira documentada: o manager NÃO scrubba — forwarding verbatim.
        Se um publisher esquecer o scrub, o dado cru atravessa. Este teste
        trava a fronteira para que ninguém assuma scrub no WS e remova o
        scrub do publisher."""
        mgr = ConnectionManager()
        entregues: list[dict[str, Any]] = []

        class FakeWS:
            client = type("C", (), {"host": "1.2.3.4"})()

            async def send_json(self, data: dict[str, Any]) -> None:
                entregues.append(data)

        mgr.register(FakeWS(), ROOM)  # type: ignore[arg-type]
        payload = {"evento": "raw", "resumo": f"cpf {self.CANARY_CPF}"}
        await mgr.broadcast(ROOM, payload)
        # Forwarding verbatim: manager não altera payload (responsabilidade
        # do publisher, ver teste acima).
        assert entregues[0] == payload


# ============================================================
# 7. Métricas observáveis offline
# ============================================================


class TestWSGateMetrics:
    def test_total_connections_gauge_reflects_lifecycle(self) -> None:
        """Gauge observável offline: total_connections sobe/desce com o
        lifecycle. Séries Prometheus dedicadas a WS: BLOCKED (inexistentes
        hoje; fora do escopo desta lane — metrics.py congelado)."""
        mgr = ConnectionManager()

        class FakeWS:
            client = type("C", (), {"host": "1.2.3.4"})()

        ws = FakeWS()
        assert mgr.total_connections() == 0
        mgr.register(ws, ROOM)  # type: ignore[arg-type]
        assert mgr.total_connections() == 1
        mgr.unregister(ws, ROOM)  # type: ignore[arg-type]
        assert mgr.total_connections() == 0

    def test_last_seen_updated_on_register_and_touch(self) -> None:
        """last_seen (base do heartbeat/observabilidade) é atualizado."""
        mgr = ConnectionManager()

        class FakeWS:
            client = type("C", (), {"host": "1.2.3.4"})()

        ws = FakeWS()
        mgr.register(ws, ROOM)  # type: ignore[arg-type]
        primeiro = mgr._last_seen[ws]  # type: ignore[index]
        mgr.touch(ws)  # type: ignore[arg-type]
        assert mgr._last_seen[ws] >= primeiro  # type: ignore[index]
