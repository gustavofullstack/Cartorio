"""G8.01.T1 — Stress harness de concorrência WebSocket (mocks).

Não abre rede real: usa MockWS + ConnectionManager.

Modified by Gustavo Almeida — Wave 35.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConcurrentWSReport:
    target: int
    registered: int
    broadcast_delivered: int
    errors: int
    duration_ms: float
    failed_indices: list[int] = field(default_factory=list)


class MockWS:
    """WebSocket mínimo compatível com ConnectionManager.send_json."""

    def __init__(self, *, fail: bool = False, idx: int = 0) -> None:
        self.fail = fail
        self.idx = idx
        self.messages: list[dict[str, Any]] = []
        self.closed = False

    async def send_json(self, payload: dict[str, Any]) -> None:
        if self.fail or self.closed:
            raise RuntimeError(f'mock_ws_dead:{self.idx}')
        self.messages.append(payload)


async def stress_register_broadcast(
    manager: Any,
    room: str,
    n_clients: int,
    payload: dict[str, Any],
    *,
    fail_every: int | None = None,
) -> ConcurrentWSReport:
    """Registra n_clients mocks, broadcast, retorna métricas.

    fail_every: se setado, cada N-ésimo client falha no send.
    """
    start = time.perf_counter()
    clients: list[MockWS] = []
    failed_idx: list[int] = []
    for i in range(n_clients):
        fail = fail_every is not None and fail_every > 0 and (i + 1) % fail_every == 0
        ws = MockWS(fail=fail, idx=i)
        clients.append(ws)
        manager.register(ws, room)
        if fail:
            failed_idx.append(i)

    delivered = await manager.broadcast(room, payload)
    # count errors as those that failed send (manager unregisters them)
    errors = len(failed_idx)
    elapsed = (time.perf_counter() - start) * 1000.0
    return ConcurrentWSReport(
        target=n_clients,
        registered=n_clients,
        broadcast_delivered=int(delivered),
        errors=errors,
        duration_ms=elapsed,
        failed_indices=failed_idx,
    )


__all__ = ['ConcurrentWSReport', 'MockWS', 'stress_register_broadcast']
