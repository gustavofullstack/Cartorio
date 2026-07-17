"""G7.10.T4 — WebSocket app-level ping/pong (proxy keep-alive contract).

Valida o contrato que o cliente deve usar ATRÁS do Traefik/reverse proxy:
- {"type":"ping"} -> {"type":"pong"}
- keep-alive em sequência (simula pings periódicos sob idle proxy)
- não-ping continua em echo (não quebra o loop)

Não simula idleTimeout do Traefik (isso é smoke wss:// em docs/WS_PING_PONG_PROXY_G7.md).
TestClient + Starlette WS é suficiente para o protocol app.
"""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.ws.atendimentos import ws_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(ws_router, prefix="/api/v1")
    return TestClient(app)


class TestWSPingPongG7:
    """Contrato keep-alive documentado em docs/WS_PING_PONG_PROXY_G7.md."""

    def test_ping_json_returns_pong(self) -> None:
        client = _client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "ping"})
            assert ws.receive_json() == {"type": "pong"}

    def test_ping_text_frame_returns_pong(self) -> None:
        """Cliente pode mandar text frame com JSON string (browser WebSocket)."""
        client = _client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            assert ws.receive_json() == {"type": "pong"}

    def test_sequential_pings_under_proxy_keepalive_pattern(self) -> None:
        """3 pings seguidos (padrão cliente a cada ~25s; aqui sem sleep).

        Garante que o loop receive_text não quebra após o primeiro pong —
        regressão típica se alguém 'return' após o primeiro keep-alive.
        """
        client = _client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            for _ in range(3):
                ws.send_json({"type": "ping"})
                assert ws.receive_json()["type"] == "pong"

    def test_ping_then_echo_then_ping(self) -> None:
        """Mistura keep-alive + tráfego normal (broadcast simulado via echo)."""
        client = _client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "ping"})
            assert ws.receive_json() == {"type": "pong"}

            ws.send_json({"type": "client_hello", "n": 1})
            echo = ws.receive_json()
            assert echo["type"] == "echo"
            assert echo["data"]["type"] == "client_hello"

            ws.send_json({"type": "ping"})
            assert ws.receive_json() == {"type": "pong"}

    def test_ping_extra_fields_still_pong(self) -> None:
        """Campos extras no ping não devem impedir pong (forward-compat cliente)."""
        client = _client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "ping", "ts": 1_721_000_000, "src": "dashboard"})
            assert ws.receive_json() == {"type": "pong"}

    def test_case_sensitive_type_ping(self) -> None:
        """type deve ser exatamente 'ping' (não 'Ping' / 'PING') — contrato estrito."""
        client = _client()
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "PING"})
            resp = ws.receive_json()
            assert resp["type"] == "echo"
            assert resp["data"]["type"] == "PING"
