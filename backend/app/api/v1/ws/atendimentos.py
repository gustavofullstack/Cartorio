"""Endpoint WebSocket /ws/atendimentos (T2.API.T19 + G8.01.T3 heartbeat).

Broadcast real-time para dashboard de atendimentos. Cada cliente conectado
escuta o channel 'cartorio:atendimentos' e recebe mensagens publicadas por
qualquer instancia da API (via Redis pub/sub do RedisBus).

Arquitetura multi-replica:
- Cliente conecta em uma replica da API (qualquer uma no Swarm).
- A replica adiciona o client no ConnectionManager local.
- Worker Redis subscribe local escuta 'cartorio:atendimentos' no Redis.
- Mensagem publicada em QUALQUER replica -> Redis -> todos subscribers ->
  broadcast local para clients conectados naquela replica.
- Resultado: dashboard em tempo real independente de qual API publicou.

Heartbeat (G8.01.T3):
- Cliente -> server {"type":"ping"} -> {"type":"pong"} (contrato G7, compativel).
- Server -> client {"type":"ping","ts":iso} apos idle de ping_interval; espera
  {"type":"pong"}. Apos max_missed timeouts, fecha a conexao e unregister.
- last_seen atualizado no ConnectionManager a cada atividade/pong.

LGPD: NAO persiste mensagens. Apenas forwarding. PII scrubbing deve ser
feito ANTES de chamar publish/broadcast (ver app/services/pii.py).

Audit: mensagens de protocolo/handoff geram audit log via AuditService
no servico que chama publish (NAO no WebSocket endpoint).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.services.redis_bus import RedisBus, get_bus
from app.services.websocket_manager import ConnectionManager, get_manager
from app.services.ws_heartbeat import (
    WSHeartbeatConfig,
    build_server_ping,
    mark_missed,
    mark_pong,
    mark_server_ping_sent,
    new_heartbeat_state,
    receive_timeout_sec,
)

logger = logging.getLogger(__name__)


ws_router = APIRouter()

# Defaults de producao (proxy keep-alive). Testes unitarios usam o modulo puro.
_DEFAULT_HB = WSHeartbeatConfig()


async def _redis_listener_loop(
    manager: ConnectionManager,
    bus: RedisBus,
    channel: str,
) -> None:
    """Task background: escuta RedisBus.subscribe e faz broadcast local.

    Roda indefinidamente ate a conexao WebSocket fechar. Cancelamento
    limpo via asyncio.CancelledError -> silencioso (logger.debug).
    """
    try:
        async for msg in bus.subscribe(channel):
            data = msg.get('data')
            if not isinstance(data, dict):
                continue
            delivered = await manager.broadcast(channel, data)
            logger.debug(
                'ws.redis.broadcast channel=%s delivered=%d total_conns=%d',
                channel,
                delivered,
                manager.total_connections(),
            )
    except asyncio.CancelledError:
        logger.debug('ws.redis.listener.cancelled channel=%s', channel)
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception('ws.redis.listener.crashed channel=%s err=%s', channel, e)


async def _close_ws_clean(websocket: WebSocket, code: int = 1000) -> None:
    """Fecha o WS se ainda estiver aberto (best-effort)."""
    try:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=code)
    except Exception:  # noqa: BLE001
        pass


@ws_router.websocket('/ws/atendimentos')
async def ws_atendimentos(websocket: WebSocket) -> None:
    """WebSocket endpoint para dashboard de atendimentos.

    Protocol:
    1. Cliente conecta.
    2. Server aceita + adiciona no manager (room=cartorio:atendimentos).
    3. Server inicia background task: escuta Redis 'cartorio:atendimentos'.
    4. Cliente recebe broadcasts (atendimentos novos, status updates, etc).
    5. Keep-alive bidirecional:
       - client {"type":"ping"} -> server {"type":"pong"}
       - server {"type":"ping","ts":iso} apos idle -> espera client {"type":"pong"}
       - apos max_missed pong timeouts: close limpo + unregister
    6. Cliente desconecta. Server limpa manager + cancela listener.
    """
    manager: ConnectionManager = get_manager()
    bus: RedisBus = get_bus()
    channel = 'cartorio:atendimentos'
    hb_config = _DEFAULT_HB
    hb_state = new_heartbeat_state(hb_config)

    await websocket.accept()
    manager.register(websocket, channel)

    listener_task: asyncio.Task[None] | None = None
    try:
        listener_task = asyncio.create_task(_redis_listener_loop(manager, bus, channel))
        # Loop principal: receive com timeout para server-side heartbeat.
        while True:
            timeout = receive_timeout_sec(hb_state, hb_config)
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=timeout)
            except asyncio.TimeoutError:
                if hb_state.awaiting_pong:
                    mark_missed(hb_state)
                    logger.debug(
                        'ws.heartbeat.pong_timeout channel=%s missed=%d',
                        channel,
                        hb_state.missed_count,
                    )
                    if hb_state.should_disconnect():
                        logger.info(
                            'ws.heartbeat.disconnect channel=%s reason=max_missed missed=%d',
                            channel,
                            hb_state.missed_count,
                        )
                        await _close_ws_clean(websocket, code=1001)
                        break
                    # Ainda ha tentativas: reenvia ping
                    ok = await manager.send_personal(websocket, build_server_ping())
                    if not ok:
                        break
                    mark_server_ping_sent(hb_state, now=time.monotonic())
                    continue

                # Idle: manda server ping e espera pong no proximo ciclo
                ok = await manager.send_personal(websocket, build_server_ping())
                if not ok:
                    break
                mark_server_ping_sent(hb_state, now=time.monotonic())
                continue

            try:
                data = json.loads(raw)
            except (TypeError, ValueError):
                data = {'raw': raw}

            msg_type = data.get('type') if isinstance(data, dict) else None
            now = time.monotonic()

            if msg_type == 'ping':
                # Client-initiated ping (G7 contract) — responde pong + conta como vivo
                mark_pong(hb_state, now=now)
                manager.touch(websocket, now=now)
                await websocket.send_json({'type': 'pong'})
            elif msg_type == 'pong':
                # Resposta ao server ping
                mark_pong(hb_state, now=now)
                manager.touch(websocket, now=now)
            else:
                # Qualquer outra atividade prova vida; echo pra debug
                mark_pong(hb_state, now=now)
                manager.touch(websocket, now=now)
                await websocket.send_json({'type': 'echo', 'data': data})
    except WebSocketDisconnect:
        logger.debug('ws.disconnect channel=%s', channel)
    except Exception as e:  # noqa: BLE001
        logger.warning('ws.error channel=%s err=%s', channel, type(e).__name__)
    finally:
        manager.unregister(websocket, channel)
        if listener_task is not None:
            listener_task.cancel()
            try:
                await listener_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass


__all__ = ['ws_router', 'ws_atendimentos']
