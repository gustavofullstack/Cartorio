"""WebSocket connection manager.

Gerencia multiplas conexoes WebSocket agrupadas por "room" (channel).
Cada instancia da API mantem seu proprio set local de conexoes.
Para escalar multi-replica no Swarm, integra com RedisBus.subscribe
(ver endpoint /ws/atendimentos em app/api/v1/ws/atendimentos.py).

Padroes:
- Room = channel name (ex: 'cartorio:atendimentos')
- Cada WS pode estar em N rooms (mas MVP usa 1)
- broadcast() envia JSON para todos clients em uma room
- send_personal() envia para um client especifico
- Falha de envio (cliente desconectado) NAO bloqueia outros clientes

Backpressure policy (fail-loud — preferido para cartorio/auditoria):
1. send_json() exception em 1 cliente -> log warning + unregister cliente
   morto. broadcast CONTINUA pros outros clientes (sem silent drop).
2. broadcast parcial: conta delivered= N sucessos, retorna count. Caller
   decide se reenvia pros que falharam (geralmente NAO — cliente vai
   reconectar).
3. Redis listener exception -> log exception + cancela task. Cliente
   recebe WS close (FastAPI/WebSocketDisconnect). Sem retry loop infinito
   silencioso que esconderia bug de infra (Redis down por horas).

LGPD: NAO persiste PII nas mensagens. Apenas forwarding pub/sub.
Ver app/services/pii.py pra scrubbing antes de chamar broadcast.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gerencia conexoes WebSocket agrupadas por room.

    Usage:
        mgr = ConnectionManager()
        await ws.accept()
        mgr.register(ws, "cartorio:atendimentos")
        await mgr.broadcast("cartorio:atendimentos", {"evento": "novo"})
        mgr.unregister(ws, "cartorio:atendimentos")
    """

    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = {}

    def register(self, ws: WebSocket, room: str) -> None:
        """Adiciona WebSocket a uma room. Idempotente."""
        if room not in self.connections:
            self.connections[room] = set()
        self.connections[room].add(ws)
        logger.debug(
            "ws.register room=%s total_in_room=%d grand_total=%d",
            room,
            len(self.connections[room]),
            self.total_connections(),
        )

    def unregister(self, ws: WebSocket, room: str) -> None:
        """Remove WebSocket de uma room. Idempotente (safe se nao existir)."""
        if room in self.connections:
            self.connections[room].discard(ws)
            if not self.connections[room]:
                del self.connections[room]
            logger.debug(
                "ws.unregister room=%s total_in_room=%d grand_total=%d",
                room,
                len(self.connections.get(room, set())),
                self.total_connections(),
            )

    def total_connections(self) -> int:
        """Total de conexoes ativas em todas rooms."""
        return sum(len(s) for s in self.connections.values())

    async def broadcast(self, room: str, payload: dict[str, Any]) -> int:
        """Envia payload JSON para todos clients em uma room.

        Returns:
            Numero de clients que receberam com sucesso. Falhas individuais
            (cliente desconectado, broken pipe) sao ENGOLIDAS (logged warning)
            para nao quebrar broadcast dos outros.

        Estrategia de erro: send-and-collect. Nao aborta no primeiro erro.
        """
        if room not in self.connections:
            return 0
        delivered = 0
        # Snapshot pra evitar mutation during iteration
        clients = list(self.connections[room])
        for ws in clients:
            try:
                await ws.send_json(payload)
                delivered += 1
            except Exception as e:  # noqa: BLE001
                # Cliente provavelmente desconectou. Loga e segue.
                logger.warning(
                    "ws.broadcast.send_failed room=%s err=%s - unregistering",
                    room,
                    type(e).__name__,
                )
                self.unregister(ws, room)
        return delivered

    async def send_personal(self, ws: WebSocket, payload: dict[str, Any]) -> bool:
        """Envia payload JSON para um client especifico.

        Returns:
            True se entregue, False se cliente morto.
        """
        try:
            await ws.send_json(payload)
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "ws.send_personal.send_failed err=%s", type(e).__name__
            )
            return False


# Singleton global (FastAPI lifespan-friendly)
_manager: ConnectionManager | None = None


def get_manager() -> ConnectionManager:
    """Singleton do ConnectionManager. Use como Depends em endpoints."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


__all__ = ["ConnectionManager", "get_manager"]