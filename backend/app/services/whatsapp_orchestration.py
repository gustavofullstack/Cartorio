"""Orquestracao P0 do WhatsApp: stale, lock FIFO, burst numerado, idempotencia de saida.

Auditoria 2026-08-11: respostas atrasadas (52min), fora de ordem, duplicadas
e perguntas perdidas. Este modulo e deterministico e fail-open se Redis cair.

Nao toca QR, tenant, banco real nem secrets.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Final

from app.core.redis_keys import RedisKey
from app.services.redis_bus import get_bus

logger = logging.getLogger(__name__)

STALE_MAX_AGE_SEC: Final[int] = 300  # 5 min — evento antigo nao gera resposta
IDEMPOTENCY_TTL_SEC: Final[int] = 86400  # 24h, alinhado ao contrato do projeto
CONVERSATION_LOCK_TTL_SEC: Final[int] = 90
OUTPUT_IDEMPOTENCY_TTL_SEC: Final[int] = 86400


def is_stale_event(event_ts: float, *, now: float | None = None) -> bool:
    """True se o evento e antigo demais para gerar resposta ao cliente."""
    current = now if now is not None else time.time()
    try:
        age = current - float(event_ts)
    except (TypeError, ValueError):
        return False
    return age > STALE_MAX_AGE_SEC


def number_burst_messages(texts: list[str]) -> str:
    """Consolida rajada preservando TODAS as mensagens, na ordem, numeradas.

    0 msgs -> ""
    1 msg  -> texto puro
    2+     -> bloco numerado (nunca descarta a primeira)
    """
    cleaned = [t.strip() for t in texts if (t or "").strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    lines = [
        (
            f"O cliente enviou {len(cleaned)} mensagens. "
            "Responda CADA uma, numerada, na mesma ordem, sem pular nenhuma:"
        )
    ]
    for i, text in enumerate(cleaned, start=1):
        lines.append(f"{i}) {text}")
    return "\n".join(lines)


def _conv_lock_key(channel: str, sender_id: str) -> str:
    digest = hashlib.sha256(sender_id.encode("utf-8")).hexdigest()[:24]
    return RedisKey.lock(f"chat_{channel}_{digest}")


async def acquire_conversation_lock(channel: str, sender_id: str) -> bool:
    """SETNX por conversa. True = este worker processa; False = outro ja segura."""
    bus = get_bus()
    if not bus:
        return True
    key = _conv_lock_key(channel, sender_id)
    is_new = await bus.client.set(key, "1", ex=CONVERSATION_LOCK_TTL_SEC, nx=True)
    return bool(is_new)


async def release_conversation_lock(channel: str, sender_id: str) -> None:
    bus = get_bus()
    if not bus:
        return
    try:
        await bus.client.delete(_conv_lock_key(channel, sender_id))
    except Exception:
        logger.warning("conversation lock release failed", exc_info=True)


async def check_output_idempotency(channel: str, sender_id: str, content_hash: str) -> bool:
    """True = ja enviou este texto/hash para o mesmo chat (pular send). False = enviar."""
    if not content_hash:
        return False
    bus = get_bus()
    if not bus:
        return False
    digest = hashlib.sha256(sender_id.encode("utf-8")).hexdigest()[:24]
    payload = hashlib.sha256(content_hash.encode("utf-8")).hexdigest()
    key = RedisKey.idempotency("chat_out", f"{channel}_{digest}_{payload}")
    is_new = await bus.client.set(key, "1", ex=OUTPUT_IDEMPOTENCY_TTL_SEC, nx=True)
    return not bool(is_new)
