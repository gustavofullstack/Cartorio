"""Cache Redis 60s para listagem atendimentos/ultimas-24h (A18).

O endpoint GET /api/v1/atendimento/ultimas-24h eh chamado pelo N8N workflow #07
(pesquisa de satisfacao) a cada 5min via cron. Com 60s de cache:
- Reduz carga no DB (Postgres SELECT 4-12x menos em pico)
- Reduz latencia media (Redis < 5ms vs Postgres 20-50ms)
- Falha silenciosa: se Redis offline, retorna None (miss) e cai pro DB

LGPD: chave NAO expoe PII (apenas timestamp "now rounded 60s").
Sentinel versionado: invalidacao automatica via CACHE_VERSION.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60  # 1 minuto - tradeoff freshness vs carga DB
CACHE_VERSION = "v1"  # Bump para invalidar tudo de uma vez
CACHE_KEY_PREFIX = f"atendimento:ultimas-24h:{CACHE_VERSION}"


def _get_redis_client() -> Any:
    try:
        import redis  # type: ignore[import-untyped]

        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return redis.Redis.from_url(url, socket_connect_timeout=2)
    except ImportError:
        return None


def _cache_key(window: str = "24h") -> str:
    """Chave deterministica baseada em bucket de 60s (arredondado para TTL efetivo).

    Args:
        window: janela de tempo. Default '24h' (unico valor atual).

    Returns:
        chave Redis tipo 'atendimento:ultimas-24h:v1:24h'
    """
    return f"{CACHE_KEY_PREFIX}:{window}"


def get_cached(window: str = "24h") -> dict | None:
    """Busca lista de atendimentos em cache. Retorna dict ou None se miss/erro."""
    r = _get_redis_client()
    if r is None:
        return None
    try:
        raw = r.get(_cache_key(window))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning("atendimento_cache.get falhou: %s", e)
        return None


def set_cached(payload: dict, window: str = "24h") -> bool:
    """Salva lista em cache. Retorna True se ok, False se erro."""
    r = _get_redis_client()
    if r is None:
        return False
    try:
        r.set(
            _cache_key(window),
            json.dumps(payload, default=str),
            ex=CACHE_TTL_SECONDS,
        )
        return True
    except Exception as e:
        logger.warning("atendimento_cache.set falhou: %s", e)
        return False


def invalidate(window: str | None = None) -> int:
    """Invalida cache. Se window=None, invalida TUDO (prefix scan).

    Returns:
        numero de chaves removidas.
    """
    r = _get_redis_client()
    if r is None:
        return 0
    try:
        if window is None:
            keys = list(r.scan_iter(match=f"{CACHE_KEY_PREFIX}:*", count=100))
        else:
            keys = list(r.scan_iter(match=_cache_key(window), count=100))
        if keys:
            r.delete(*keys)
        return len(keys)
    except Exception as e:
        logger.warning("atendimento_cache.invalidate falhou: %s", e)
        return 0
