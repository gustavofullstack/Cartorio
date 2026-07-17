"""G7 Wave 17 — dual-format Evolution + WS stress 50 + swagger persist.

Modified by Gustavo Almeida — G7 Wave 17.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.api.v1.whatsapp import parse_evolution_payload
from app.services.websocket_manager import ConnectionManager

ROOT = Path(__file__).resolve().parents[2]


def _nested(jid: str, mid: str, text: str) -> dict:
    return {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {"remoteJid": jid, "fromMe": False, "id": mid},
            "message": {"conversation": text},
            "messageType": "conversation",
            "pushName": "Teste",
        },
    }


def _root(jid: str, mid: str, text: str) -> dict:
    return {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "key": {"remoteJid": jid, "fromMe": False, "id": mid},
        "message": {"conversation": text},
        "pushName": "Legado",
        "messageType": "conversation",
    }


class TestEvolutionDualFormat:
    def test_nested_format(self) -> None:
        msg = parse_evolution_payload(_nested("5511999999999@s.whatsapp.net", "ABC123", "oi"))
        assert msg is not None
        assert msg.text == "oi"
        assert msg.update_id == "ABC123"
        assert msg.extra.get("format") == "nested"

    def test_root_level_legacy(self) -> None:
        msg = parse_evolution_payload(_root("5511888888888@s.whatsapp.net", "LEG1", "emolumento"))
        assert msg is not None
        assert msg.text == "emolumento"
        assert msg.sender_id.startswith("5511")
        assert msg.extra.get("format") == "root"

    def test_extended_text_nested(self) -> None:
        payload = _nested("x@s.whatsapp.net", "E1", "")
        payload["data"]["message"] = {"extendedTextMessage": {"text": "procuração"}}
        msg = parse_evolution_payload(payload)
        assert msg is not None
        assert msg.text == "procuração"

    def test_wrong_event_returns_none(self) -> None:
        p = _nested("a@s.whatsapp.net", "1", "x")
        p["event"] = "connection.update"
        assert parse_evolution_payload(p) is None

    def test_missing_id_returns_none(self) -> None:
        p = _root("a@s.whatsapp.net", "", "x")
        assert parse_evolution_payload(p) is None


_jid = st.from_regex(r"5511[0-9]{8}@s\.whatsapp\.net", fullmatch=True)
_mid = st.text(min_size=8, max_size=24, alphabet="ABCDEF0123456789")
_text = st.text(min_size=1, max_size=80).filter(lambda s: s.strip() != "")


@given(jid=_jid, mid=_mid, text=_text, use_nested=st.booleans())
@settings(max_examples=40, deadline=None)
def test_dual_format_hypothesis(jid: str, mid: str, text: str, use_nested: bool) -> None:
    """G7.04.T3: nested e root produzem update_id e text coerentes."""
    payload = _nested(jid, mid, text) if use_nested else _root(jid, mid, text)
    msg = parse_evolution_payload(payload)
    assert msg is not None
    assert msg.update_id == mid
    assert msg.sender_id == jid
    assert msg.text == text


class TestWsStress50:
    """G7.01.T4 — 50 clients mock na mesma room."""

    def test_register_50_clients_same_room(self) -> None:
        mgr = ConnectionManager()
        room = "cartorio:atendimentos"
        clients = []
        for i in range(50):
            ws = MagicMock()
            ws.client = type("C", (), {"host": f"10.0.0.{i % 250}"})()
            mgr.register(ws, room)  # type: ignore[arg-type]
            clients.append(ws)
        assert mgr.total_connections() == 50
        assert len(mgr.connections[room]) == 50

    @pytest.mark.asyncio
    async def test_broadcast_to_50_mock_ws(self) -> None:
        mgr = ConnectionManager()
        room = "cartorio:stress"
        for _ in range(50):
            ws = MagicMock()
            ws.send_json = AsyncMock()
            mgr.register(ws, room)  # type: ignore[arg-type]
        n = await mgr.broadcast(room, {"evento": "ping", "n": 50})
        assert n == 50
        for ws in mgr.connections[room]:
            ws.send_json.assert_awaited()  # type: ignore[attr-defined]

    def test_unregister_all_50(self) -> None:
        mgr = ConnectionManager()
        room = "cartorio:cleanup"
        clients = []
        for _ in range(50):
            ws = MagicMock()
            mgr.register(ws, room)  # type: ignore[arg-type]
            clients.append(ws)
        for ws in clients:
            mgr.unregister(ws, room)  # type: ignore[arg-type]
        assert mgr.total_connections() == 0


class TestSwaggerPersistAuth:
    """G7.17.T2/T4 — Swagger UI institucional + persistAuthorization."""

    def test_main_has_persist_authorization(self) -> None:
        main_py = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        assert "persistAuthorization: true" in main_py
        assert "tryItOutEnabled: true" in main_py
        assert "2º" in main_py or "Cartorio" in main_py or "Cartório" in main_py
