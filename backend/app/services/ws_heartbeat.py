"""G8.01.T3 — Heartbeat WebSocket ping/pong robusto.

Usado por /ws/atendimentos:
- client {"type":"ping"} -> server pong
- server {"type":"ping","ts":iso} apos idle; espera pong
- apos max_missed timeouts: should_disconnect()

Estado e timers usam time.monotonic() quando `now` e float; datetime ok em unit tests.

Modified by Gustavo Almeida — Wave 35.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _now_mono() -> float:
    return time.monotonic()


@dataclass(frozen=True, slots=True)
class WSHeartbeatConfig:
    ping_interval_sec: float = 20.0
    pong_timeout_sec: float = 10.0
    max_missed: int = 2


@dataclass(slots=True)
class WSHeartbeatState:
    last_pong_at: float = field(default_factory=_now_mono)
    last_ping_at: float | None = None
    missed_count: int = 0
    awaiting_pong: bool = False
    config: WSHeartbeatConfig = field(default_factory=WSHeartbeatConfig)

    def should_disconnect(self, config: WSHeartbeatConfig | None = None) -> bool:
        cfg = config or self.config
        return self.missed_count >= cfg.max_missed


def new_heartbeat_state(config: WSHeartbeatConfig | None = None) -> WSHeartbeatState:
    cfg = config or WSHeartbeatConfig()
    return WSHeartbeatState(config=cfg, last_pong_at=_now_mono())


def mark_pong(state: WSHeartbeatState, now: float | datetime | None = None) -> WSHeartbeatState:
    """Registra pong/atividade do cliente."""
    ts = _coerce_now(now)
    state.last_pong_at = ts
    state.missed_count = 0
    state.awaiting_pong = False
    return state


def mark_ping(state: WSHeartbeatState, now: float | datetime | None = None) -> WSHeartbeatState:
    state.last_ping_at = _coerce_now(now)
    return state


def mark_server_ping_sent(
    state: WSHeartbeatState, now: float | datetime | None = None
) -> WSHeartbeatState:
    state.last_ping_at = _coerce_now(now)
    state.awaiting_pong = True
    return state


def mark_missed(state: WSHeartbeatState) -> WSHeartbeatState:
    state.missed_count += 1
    state.awaiting_pong = False
    return state


def is_stale(
    state: WSHeartbeatState,
    now: float | datetime | None = None,
    config: WSHeartbeatConfig | None = None,
) -> bool:
    cfg = config or state.config
    ts = _coerce_now(now)
    # se last_pong_at for datetime legado de testes
    last = state.last_pong_at
    if isinstance(last, datetime):
        ref = now if isinstance(now, datetime) else _utcnow()
        assert isinstance(ref, datetime)
        return (ref - last).total_seconds() > cfg.pong_timeout_sec
    return (ts - float(last)) > cfg.pong_timeout_sec


def receive_timeout_sec(
    state: WSHeartbeatState, config: WSHeartbeatConfig | None = None
) -> float:
    """Timeout para asyncio.wait_for(receive): pong_timeout se awaiting, senao ping_interval."""
    cfg = config or state.config
    if state.awaiting_pong:
        return max(0.1, cfg.pong_timeout_sec)
    return max(0.1, cfg.ping_interval_sec)


def build_server_ping(ts: datetime | None = None) -> dict[str, str]:
    when = ts or _utcnow()
    return {'type': 'ping', 'ts': when.isoformat()}


def build_ping_payload(ts: datetime | None = None) -> dict[str, str]:
    return build_server_ping(ts)


def is_pong_message(data: object) -> bool:
    return isinstance(data, dict) and data.get('type') == 'pong'


def is_ping_message(data: object) -> bool:
    return isinstance(data, dict) and data.get('type') == 'ping'


def _coerce_now(now: float | datetime | None) -> float:
    if now is None:
        return _now_mono()
    if isinstance(now, datetime):
        # testes que passam datetime: usar epoch-ish via timestamp
        return now.timestamp()
    return float(now)


__all__ = [
    'WSHeartbeatConfig',
    'WSHeartbeatState',
    'build_ping_payload',
    'build_server_ping',
    'is_ping_message',
    'is_pong_message',
    'is_stale',
    'mark_missed',
    'mark_ping',
    'mark_pong',
    'mark_server_ping_sent',
    'new_heartbeat_state',
    'receive_timeout_sec',
]
