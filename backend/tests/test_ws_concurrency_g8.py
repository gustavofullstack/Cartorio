"""G8.01.T1 — stress 100+ WS mocks.

Modified by Gustavo Almeida — Wave 35.
"""

from __future__ import annotations

import pytest

from app.services.websocket_manager import ConnectionManager
from app.services.ws_concurrency import stress_register_broadcast


@pytest.mark.asyncio
async def test_100_register_broadcast_all_delivered() -> None:
    mgr = ConnectionManager()
    report = await stress_register_broadcast(
        mgr, 'room:stress', 100, {'type': 'event', 'n': 1}
    )
    assert report.target == 100
    assert report.registered == 100
    assert report.broadcast_delivered == 100
    assert report.errors == 0
    assert report.duration_ms >= 0


@pytest.mark.asyncio
async def test_150_with_partial_failures_unregisters_dead() -> None:
    mgr = ConnectionManager()
    report = await stress_register_broadcast(
        mgr,
        'room:partial',
        150,
        {'type': 'tick'},
        fail_every=10,  # 15 failures
    )
    assert report.target == 150
    assert report.errors == 15
    assert report.broadcast_delivered == 135
    # dead unregistered → remaining connections == delivered survivors
    assert mgr.total_connections() == 135


@pytest.mark.asyncio
async def test_report_duration_positive() -> None:
    mgr = ConnectionManager()
    report = await stress_register_broadcast(mgr, 'r', 10, {'ok': True})
    assert report.duration_ms >= 0


@pytest.mark.asyncio
async def test_zero_clients_ok() -> None:
    mgr = ConnectionManager()
    report = await stress_register_broadcast(mgr, 'empty', 0, {'x': 1})
    assert report.broadcast_delivered == 0
    assert report.registered == 0
