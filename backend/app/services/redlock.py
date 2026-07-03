"""Redlock distributed lock — coordena migrations/seed entre replicas API (A20).

Implementacao: Redis SET NX EX (atomic lock distribuido).
LGPD: nome do lock NAO expoe dados pessoais, apenas identificador tecnico.

API publica:
    - acquire_lock(name, ttl_seconds)        -> str | None
    - release_lock(name, token)               -> bool
    - is_locked(name)                         -> bool
    - redlock(name, ttl_seconds, blocking,    -> context manager
             timeout)
    - LockBusyError                           -> exception quando lock nao
                                                  pode ser adquirido
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger(__name__)

# TTL padrao para migrations/seed (segundos). Configuravel via env.
DEFAULT_LOCK_TTL_SECONDS = int(os.getenv("REDIS_LOCK_TTL_SECONDS", "300"))
DEFAULT_LOCK_PREFIX = os.getenv("REDIS_LOCK_PREFIX", "redlock:")

# Exit code para falhas de lock em migrations/seed (EX_TEMPFAIL do sysv init).
EXIT_LOCK_BUSY = 75


class LockBusyError(RuntimeError):
    """Levantada quando o lock nao pode ser adquirido (outro replica OU Redis offline).

    Caller deve decidir se retry (timeout > 0) ou fail-fast (exit 75).
    """


def _get_redis_client() -> Any:
    """Lazy import redis (nao quebra se nao instalado)."""
    try:
        import redis  # type: ignore[import-untyped]

        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return redis.Redis.from_url(url, socket_connect_timeout=2)
    except ImportError:
        return None


def _key(name: str) -> str:
    """Constroi a chave Redis para o lock.

    Formato canonico: '<prefix><name>' onde prefix e configuravel
    (default 'redlock:'). NUNCA inclui dados pessoais (LGPD-safe).
    """
    return f"{DEFAULT_LOCK_PREFIX}{name}"


def acquire_lock(name: str, ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS) -> str | None:
    """Tenta adquirir lock distribuido. Retorna token se sucesso, None se ocupado.

    Args:
        name: nome do lock (ex: 'alembic:migration', 'seed:vault_secrets')
        ttl_seconds: tempo maximo de retencao (auto-release se processo morrer)

    Returns:
        token UUID4 se lock adquirido, None se ja estava locked.
        Em caso de Redis indisponivel, retorna None (fail-open).
    """
    r = _get_redis_client()
    if r is None:
        logger.warning("Redlock: Redis indisponivel, lock nao aplicado (fail-open)")
        return None
    token = uuid.uuid4().hex
    key = _key(name)
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
    key = _key(name)
    # Lua script atomico: so deleta se token confere (evita race com TTL)
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
    """Verifica se lock esta ativo (sem tentar adquirir).

    Util para diferenciar 'outro replica locked' de 'Redis indisponivel':
        if not acquire_lock(...):
            if is_locked(...):
                # outra replica
            else:
                # redis offline
    """
    r = _get_redis_client()
    if r is None:
        return False
    try:
        return bool(r.exists(_key(name)))
    except Exception:
        return False


@contextmanager
def redlock(
    name: str,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
    blocking: bool = True,
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> Iterator[str]:
    """Context manager para redlock distribuido (A20).

    Uso:
        from app.services.redlock import redlock, LockBusyError

        try:
            with redlock("alembic:migration", ttl_seconds=300) as token:
                run_migrations_online()
        except LockBusyError as e:
            print(f"Outra replica migrando: {e}", file=sys.stderr)
            sys.exit(75)

    Args:
        name: identificador tecnico do lock (sem prefixo).
        ttl_seconds: TTL do lock no Redis (auto-release se processo morrer).
        blocking: se True, espera ate timeout antes de levantar LockBusyError.
                  Se False, falha imediato (timeout ignorado).
        timeout: tempo maximo de espera em segundos (apenas se blocking=True).
                 Use timeout=0 para fail-fast sem espera.
        poll_interval: intervalo entre tentativas de acquire (segundos).

    Raises:
        LockBusyError: lock nao pode ser adquirido dentro do timeout.

    Yields:
        token do lock (string UUID4 hex).
    """
    token: str | None = None
    if blocking and timeout > 0:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            token = acquire_lock(name, ttl_seconds=ttl_seconds)
            if token is not None:
                break
            time.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))
    else:
        token = acquire_lock(name, ttl_seconds=ttl_seconds)

    if token is None:
        # Diagnostico: lock ocupado por outra replica OU Redis offline
        if is_locked(name):
            msg = f"redlock '{name}' ocupado por outro processo"
        else:
            msg = f"redlock '{name}' indisponivel (Redis offline ou erro)"
        logger.warning("Redlock: %s (timeout=%.1fs)", msg, timeout)
        raise LockBusyError(msg)

    try:
        yield token
    finally:
        # Release em qualquer saida (normal, exception, KeyboardInterrupt)
        released = release_lock(name, token)
        if not released:
            logger.warning(
                "Redlock: %s NAO foi liberado pelo token (TTL vai expirar em ate %ds)",
                name,
                ttl_seconds,
            )
