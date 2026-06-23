"""Redis pub/sub helper service.

Usado para broadcasting de eventos entre instancias da API (multi-replica no
Swarm) e para alimentar o WebSocket /ws/atendimentos com mensagens em tempo real.

Padroes:
- Channel names: namespace prefixado (`cartorio:atendimentos`, `cartorio:protocolos`)
- Mensagens serializadas como JSON
- Subscribe retorna AsyncIterator que faz poll loop no threadpool (redis-py
  eh sync, nao bloqueia event loop via asyncio.to_thread)
- Pattern subscribe: suporta wildcards (`cartorio:*`)
- Health: ping_timeout=2s pra nao travar radar healthcheck

LGPD: Redis nao eh log persistente, so transport. Mensagens devem ser
hashed/scrubbed ANTES de publicar (sugestao: ver `app.services.pii.scrub`).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis_async
import redis.asyncio.client

from app.config import settings

logger = logging.getLogger(__name__)

# Constants para evitar typo em callers
CHANNEL_ATENDIMENTOS = "cartorio:atendimentos"
CHANNEL_PROTOCOLOS = "cartorio:protocolos"
CHANNEL_ALERTAS = "cartorio:alertas"


class RedisBusError(Exception):
    """Erro do RedisBus (config ausente, connect timeout, etc)."""


class RedisBus:
    """Wrapper async do redis-py para pub/sub.

    Usage:
        bus = RedisBus()
        await bus.publish("cartorio:atendimentos", {"evento": "novo", "id": 1})
        async for msg in bus.subscribe("cartorio:atendimentos"):
            handle(msg)
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._url = redis_url or settings.redis_url
        self._client: redis_async.Redis | None = None

    async def _get_client(self) -> redis_async.Redis:
        """Lazy connect. Falha rapida se redis_url nao setado."""
        if self._client is None:
            if not self._url:
                raise RedisBusError("redis_url nao configurado em settings")
            self._client = redis_async.from_url(
                self._url,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        """Fecha client (cleanup em lifespan shutdown)."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def ping(self) -> bool:
        """Health check rapido. Retorna True se redis responde a PING.

        RedisBusError de config (sem URL) NAO retorna False — propaga.
        Erros de rede/connect retornam False (redis offline).
        """
        from redis.exceptions import RedisError

        try:
            client = await self._get_client()
            return bool(await client.ping())
        except RedisError:
            return False
        except Exception:  # noqa: BLE001
            return False

    async def publish(self, channel: str, payload: dict[str, Any]) -> int:
        """Publica payload (JSON-serializado) num channel.

        Returns:
            Numero de subscribers que receberam a mensagem.
        """
        if not channel or not isinstance(channel, str):
            raise RedisBusError("channel deve ser string nao-vazia")
        if not isinstance(payload, dict):
            raise RedisBusError("payload deve ser dict")
        try:
            client = await self._get_client()
            msg = json.dumps(payload, default=str, ensure_ascii=False)
            count = await client.publish(channel, msg)
            logger.debug("redis.publish channel=%s subscribers=%d", channel, count)
            return int(count)
        except RedisBusError:
            raise
        except Exception as e:
            raise RedisBusError(f"publish falhou: {e}") from e

    async def subscribe(self, *channels: str) -> AsyncIterator[dict[str, Any]]:
        """Subscribe a 1+ channels. AsyncIterator que yielda dicts.

        Yields:
            dict com chaves: 'channel' (str) e 'data' (Any).

        Usage:
            async for msg in bus.subscribe("cartorio:atendimentos"):
                if msg["channel"] == CHANNEL_ATENDIMENTOS:
                    handle(msg["data"])
        """
        if not channels:
            raise RedisBusError("pelo menos 1 channel obrigatorio")
        try:
            client = await self._get_client()
            pubsub = client.pubsub()
            await pubsub.subscribe(*channels)
            try:
                while True:
                    msg = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if msg is None:
                        await asyncio.sleep(0.05)  # yield pro event loop
                        continue
                    if msg.get("type") != "message":
                        continue
                    channel = msg.get("channel", "")
                    raw = msg.get("data", "")
                    try:
                        data = json.loads(raw)
                    except (TypeError, ValueError):
                        data = {"raw": raw}
                    yield {"channel": channel, "data": data}
            finally:
                try:
                    await pubsub.unsubscribe()
                except Exception:  # noqa: BLE001
                    pass
                await pubsub.aclose()
        except RedisBusError:
            raise
        except Exception as e:
            raise RedisBusError(f"subscribe falhou: {e}") from e

    async def pattern_subscribe(
        self, pattern: str
    ) -> AsyncIterator[dict[str, Any]]:
        """PSUBSCRIBE com pattern (ex: 'cartorio:*').

        Yields:
            dict com chaves: 'channel' (matched channel), 'pattern' e 'data'.
        """
        if not pattern:
            raise RedisBusError("pattern obrigatorio")
        try:
            client = await self._get_client()
            pubsub = client.pubsub()
            await pubsub.psubscribe(pattern)
            try:
                while True:
                    msg = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if msg is None:
                        await asyncio.sleep(0.05)
                        continue
                    if msg.get("type") != "pmessage":
                        continue
                    channel = msg.get("channel", "")
                    raw = msg.get("data", "")
                    try:
                        data = json.loads(raw)
                    except (TypeError, ValueError):
                        data = {"raw": raw}
                    yield {
                        "channel": channel,
                        "pattern": pattern,
                        "data": data,
                    }
            finally:
                try:
                    await pubsub.punsubscribe()
                except Exception:  # noqa: BLE001
                    pass
                await pubsub.aclose()
        except RedisBusError:
            raise
        except Exception as e:
            raise RedisBusError(f"pattern_subscribe falhou: {e}") from e


# Singleton lazy
_bus: RedisBus | None = None


def get_bus() -> RedisBus:
    """Singleton do RedisBus. Use como Depends em endpoints."""
    global _bus
    if _bus is None:
        _bus = RedisBus()
    return _bus


__all__ = [
    "CHANNEL_ALERTAS",
    "CHANNEL_ATENDIMENTOS",
    "CHANNEL_PROTOCOLOS",
    "RedisBus",
    "RedisBusError",
    "get_bus",
]