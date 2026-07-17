"""G8.03.T2 — Mute do bot quando escrevente assume (HITL).

Quando o Chatwoot notifica que um humano assumiu a conversa
(`conversation_status_changed` para open/pending com assignee, ou
`message_created` outgoing do agent), gravamos uma chave Redis
`bot:mute:{channel}:{conversation_key}` com TTL.

O pipeline do bot (Telegram/WhatsApp) consulta `is_bot_muted` **antes**
de chamar LLM — se muted, não responde automaticamente.

LGPD: chaves usam IDs opacos (chat_id / conversation_id), sem PII.
Default fail-open se Redis indisponível (não travar atendimento).

Modified by Gustavo Almeida — G8.03.T2 Wave 36.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# Prefixo canônico (DRY com redis_ttl_inventory se inventariado depois)
MUTE_KEY_PREFIX = 'bot:mute'
DEFAULT_TTL_SEC = 8 * 3600  # 8h jornada do escrevente


class RedisLike(Protocol):
    """Subset síncrono/assíncrono mínimo usado aqui (duck typing)."""

    def get(self, name: str) -> Any: ...
    def set(self, name: str, value: Any, ex: int | None = None) -> Any: ...
    def delete(self, *names: str) -> Any: ...


@dataclass(frozen=True, slots=True)
class BotMuteConfig:
    ttl_sec: int = DEFAULT_TTL_SEC
    key_prefix: str = MUTE_KEY_PREFIX


def mute_key(channel: str, conversation_key: str, *, prefix: str = MUTE_KEY_PREFIX) -> str:
    """Monta chave Redis normalizada (sem PII)."""
    ch = (channel or 'unknown').strip().lower()
    ck = str(conversation_key or '').strip()
    if not ck:
        raise ValueError('conversation_key required')
    return f'{prefix}:{ch}:{ck}'


def mute_bot(
    redis: Any,
    channel: str,
    conversation_key: str,
    *,
    reason: str = 'hitl',
    ttl_sec: int = DEFAULT_TTL_SEC,
    config: BotMuteConfig | None = None,
) -> str:
    """Ativa mute. Retorna a chave escrita.

    `redis` pode ser client sync (redis.Redis) com .set(name, value, ex=...).
    """
    cfg = config or BotMuteConfig(ttl_sec=ttl_sec)
    key = mute_key(channel, conversation_key, prefix=cfg.key_prefix)
    value = f'1|{reason}'
    try:
        redis.set(key, value, ex=int(cfg.ttl_sec))
        logger.info('bot_mute.on key=%s reason=%s ttl=%s', key, reason, cfg.ttl_sec)
    except Exception as exc:  # noqa: BLE001
        logger.warning('bot_mute.on.fail key=%s err=%s', key, type(exc).__name__)
    return key


def unmute_bot(
    redis: Any,
    channel: str,
    conversation_key: str,
    *,
    config: BotMuteConfig | None = None,
) -> bool:
    """Remove mute. True se delete executou sem erro."""
    cfg = config or BotMuteConfig()
    key = mute_key(channel, conversation_key, prefix=cfg.key_prefix)
    try:
        redis.delete(key)
        logger.info('bot_mute.off key=%s', key)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning('bot_mute.off.fail key=%s err=%s', key, type(exc).__name__)
        return False


def is_bot_muted(
    redis: Any,
    channel: str,
    conversation_key: str,
    *,
    config: BotMuteConfig | None = None,
) -> bool:
    """True se mute ativo. Fail-open (False) se Redis cair."""
    cfg = config or BotMuteConfig()
    try:
        key = mute_key(channel, conversation_key, prefix=cfg.key_prefix)
    except ValueError:
        return False
    try:
        raw = redis.get(key)
        if raw is None:
            return False
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8', errors='replace')
        return bool(str(raw).startswith('1'))
    except Exception as exc:  # noqa: BLE001
        logger.warning('bot_mute.check.fail err=%s', type(exc).__name__)
        return False


def parse_mute_value(raw: str | bytes | None) -> tuple[bool, str]:
    """Parse valor `1|reason` → (active, reason)."""
    if raw is None:
        return False, ''
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', errors='replace')
    text = str(raw)
    if not text.startswith('1'):
        return False, ''
    parts = text.split('|', 1)
    reason = parts[1] if len(parts) > 1 else 'hitl'
    return True, reason


__all__ = [
    'BotMuteConfig',
    'DEFAULT_TTL_SEC',
    'MUTE_KEY_PREFIX',
    'is_bot_muted',
    'mute_bot',
    'mute_key',
    'parse_mute_value',
    'unmute_bot',
]
