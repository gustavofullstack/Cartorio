"""G8.01.T3 — testes heartbeat WS.

Modified by Gustavo Almeida — Wave 35.
"""

from __future__ import annotations

import time

from app.services.ws_heartbeat import (
    WSHeartbeatConfig,
    build_ping_payload,
    is_pong_message,
    is_stale,
    mark_missed,
    mark_pong,
    mark_server_ping_sent,
    new_heartbeat_state,
    receive_timeout_sec,
)


def test_fresh_not_stale() -> None:
    st = new_heartbeat_state(WSHeartbeatConfig(pong_timeout_sec=10))
    assert is_stale(st) is False
    assert st.should_disconnect() is False


def test_after_pong_not_stale() -> None:
    st = new_heartbeat_state()
    mark_missed(st)
    mark_pong(st, now=time.monotonic())
    assert st.missed_count == 0
    assert st.awaiting_pong is False
    assert is_stale(st) is False


def test_max_missed_disconnect() -> None:
    cfg = WSHeartbeatConfig(max_missed=2)
    st = new_heartbeat_state(cfg)
    mark_missed(st)
    assert st.should_disconnect() is False
    mark_missed(st)
    assert st.should_disconnect() is True


def test_stale_by_timeout() -> None:
    st = new_heartbeat_state(WSHeartbeatConfig(pong_timeout_sec=0.05))
    st.last_pong_at = time.monotonic() - 1.0
    assert is_stale(st) is True


def test_build_ping_payload() -> None:
    p = build_ping_payload()
    assert p["type"] == "ping"
    assert "ts" in p


def test_is_pong_message() -> None:
    assert is_pong_message({"type": "pong"}) is True
    assert is_pong_message({"type": "ping"}) is False
    assert is_pong_message("x") is False


def test_config_defaults() -> None:
    cfg = WSHeartbeatConfig()
    assert cfg.ping_interval_sec > 0
    assert cfg.max_missed >= 1


def test_receive_timeout_awaiting() -> None:
    st = new_heartbeat_state(WSHeartbeatConfig(ping_interval_sec=20, pong_timeout_sec=7))
    assert receive_timeout_sec(st) == 20
    mark_server_ping_sent(st)
    assert receive_timeout_sec(st) == 7
