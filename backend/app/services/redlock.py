"""Redlock distributed lock — coordena migrations/seed entre replicas API (A20).

Implementacao: Redis SET NX EX (atomic lock distribuido).
LGPD: nome do lock NAO expoe dados pessoais, apenas identificador tecnico.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def _get_redis_client() -> Any:
    """Lazy import redis (nao quebra se nao instalado)."""
    try:
        import redis  # type: ignore[import-untyped]
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return redis.Redis.from_url(url, socket_connect_timeout=2)
    except ImportError:
        return None


def acquire_lock(name: str, ttl_seconds: int = 60) -> str | None:
    """Tenta adquirir lock distribuido. Retorna token se sucesso, None se ocupado.

    Args:
        name: nome do lock (ex: 'migrations:run', 'seed:emolumento')
        ttl_seconds: tempo maximo de retencao (auto-release se processo morrer)

    Returns:
        token UUID4 se lock adquirido, None se ja estava locked.
    """
    r = _get_redis_client()
    if r is None:
        logger.warning("Redlock: Redis indisponivel, lock nao aplicado (fail-open)")
        return None
    token = uuid.uuid4().hex
    key = f"redlock:{name}"
    try:
        ok = r.set(key, token, nx=True, ex=ttl_seconds)
        if ok:
            logger.info("Redlock: acquired %s token=%s ttl=%ds", name, token[:8], ttl_seconds)
            return token
        logger.debug("Redlock: %s ja locked por outro processo", name)
        return None
    except Exception as e:
        logger.warning("Redlock: falha ao adquirir %s: %s", name, e)
        return None


def release_lock(name: str, token: str) -> bool:
    """Libera lock se ainda pertence ao token (evita race condition).

    Args:
        name: nome do lock
        token: token retornado por acquire_lock

    Returns:
        True se liberado, False se token nao confere ou lock ja expirou.
    """
    r = _get_redis_client()
    if r is None:
        return False
    key = f"redlock:{name}"
    # Lua script atomico: so deleta se token confere
    script = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    else
        return 0
    end
    """
    try:
        result = r.eval(script, 1, key, token)
        return bool(result)
    except Exception as e:
        logger.warning("Redlock: falha ao liberar %s: %s", name, e)
        return False


def is_locked(name: str) -> bool:
    """Verifica se lock esta ativo (sem tentar adquirir)."""
    r = _get_redis_client()
    if r is None:
        return False
    try:
        return bool(r.exists(f"redlock:{name}"))
    except Exception:
        return False
