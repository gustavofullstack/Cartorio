"""Rate limiting por API key (substitui o atual por session_id quando X-API-Key presente).

Decisao: 3 tiers de API key com limites diferentes.
- N8N (alta freq, polling/cron): 600 req/min
- DPO/escrevente (humano via dashboard): 60 req/min
- Padrao / sem key: 30 req/min (fail-secure)

Algoritmo: Redis INCR com TTL sliding window de 60s.
- Chave: ratelimit:apikey:<hash>:<minute_bucket>
- Valor: contador
- TTL: 60s

LGPD: o hash da API key NAO pode ser reversivel. SHA-256 da key ja eh
suficiente (key tem 64 chars hex = 256 bits de entropia).
"""
from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

import redis.asyncio as redis_async
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Tipos
# ============================================================================

ApiKeyTier = Literal["n8n", "dpo", "padrao"]


@dataclass(frozen=True)
class RateLimitPolicy:
    """Politica de rate limit por tier de API key."""

    per_minute: int
    description: str


# Tier defaults - ajustaveis via env se necessario
TIER_POLICIES: dict[ApiKeyTier, RateLimitPolicy] = {
    "n8n": RateLimitPolicy(per_minute=600, description="N8N workflows (cron, polling)"),
    "dpo": RateLimitPolicy(per_minute=60, description="DPO/escrevente (humano)"),
    "padrao": RateLimitPolicy(per_minute=30, description="Sem X-API-Key (fail-secure)"),
}


# ============================================================================
# Identificacao de tier
# ============================================================================


def _hash_api_key(api_key: str) -> str:
    """Hash SHA-256 da API key (LGPD-safe, nao reversivel)."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:32]


def identify_tier(api_key: str | None) -> ApiKeyTier:
    """Identifica o tier da API key baseado no prefixo/heuristica.

    Heuristica simples (sem banco de keys dedicado):
    - Se key comeca com 'n8n-' ou tamanho > 64: tier='n8n'
    - Se key comeca com 'dpo-' ou 'escrevente-': tier='dpo'
    - Caso contrario: 'padrao'

    Em Sprint 4+: substituir por tabela `api_keys` no DB com campo `tier`.
    """
    if not api_key:
        return "padrao"
    if api_key.startswith(("n8n-", "sk-n8n-")) or len(api_key) > 64:
        return "n8n"
    if api_key.startswith(("dpo-", "escrevente-", "admin-")):
        return "dpo"
    return "padrao"


# ============================================================================
# Storage Redis
# ============================================================================


class RateLimitResult:
    """Resultado da checagem de rate limit."""

    def __init__(self, allowed: bool, current: int, limit: int, retry_after: int) -> None:
        self.allowed = allowed
        self.current = current
        self.limit = limit
        self.retry_after = retry_after


class RateLimitByKeyMiddleware(BaseHTTPMiddleware):
    """Rate limit por API key com tiers.

    Args:
        app: FastAPI app.
        redis_url: URL Redis. Default = settings.redis_url.
        api_key_header: Header que carrega a key (default X-API-Key).
        paths_prefixes: Quais paths sao rate-limited. Default: /api/v1/
                         (tudo da API). Vazio = todos.
    """

    DEFAULT_PATHS = ("/api/v1/",)

    def __init__(
        self,
        app: object,  # noqa: ANN401
        redis_url: str | None = None,
        api_key_header: str = "x-api-key",
        paths_prefixes: tuple[str, ...] = DEFAULT_PATHS,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._url = redis_url or settings.redis_url
        self._api_key_header = api_key_header
        self._paths = paths_prefixes
        self._client: redis_async.Redis | None = None

    async def _get_client(self) -> redis_async.Redis | None:
        if self._client is None:
            try:
                self._client = redis_async.from_url(
                    self._url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                )
                await self._client.ping()
            except (redis_async.RedisError, OSError) as e:
                logger.warning("rate_limit: Redis offline, fail-open: %s", e)
                self._client = None
        return self._client

    async def _check(self, key_hash: str, tier: ApiKeyTier) -> RateLimitResult:
        client = await self._get_client()
        if client is None:
            # Fail-open: se Redis offline, NAO bloqueia (mas log)
            return RateLimitResult(allowed=True, current=0, limit=0, retry_after=0)

        policy = TIER_POLICIES[tier]
        now_minute = int(time.time() // 60)
        redis_key = f"ratelimit:apikey:{key_hash}:{now_minute}"

        try:
            # Atomic: INCR + EXPIRE
            pipe = client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, 60)
            current, _ = await pipe.execute()
        except redis_async.RedisError as e:
            logger.warning("rate_limit: Redis error, fail-open: %s", e)
            return RateLimitResult(allowed=True, current=0, limit=0, retry_after=0)

        current = int(current)
        allowed = current <= policy.per_minute
        retry_after = 60 - (int(time.time()) % 60) if not allowed else 0

        return RateLimitResult(
            allowed=allowed,
            current=current,
            limit=policy.per_minute,
            retry_after=retry_after,
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Filtra por path
        if self._paths and not any(request.url.path.startswith(p) for p in self._paths):
            return await call_next(request)

        # Identifica API key
        api_key = request.headers.get(self._api_key_header)
        if api_key:
            tier = identify_tier(api_key)
            key_hash = _hash_api_key(api_key)
        else:
            tier = "padrao"
            # Hash anonimo: IP do cliente (LGPD-safe, nao reversivel)
            client_ip = request.headers.get("x-forwarded-for", "unknown").split(",")[0].strip()
            key_hash = _hash_api_key(f"ip:{client_ip}")

        result = await self._check(key_hash, tier)

        if not result.allowed:
            policy = TIER_POLICIES[tier]
            logger.warning(
                "rate_limit: tier=%s hash=%s current=%d limit=%d",
                tier, key_hash[:8], result.current, result.limit,
            )
            return Response(
                content=(
                    f'{{"erro":"RATE_LIMITED","mensagem":"Limite de {result.limit} req/min '
                    f'atigido para tier {tier}. Tente em {result.retry_after}s."}}'
                ),
                status_code=429,
                headers={
                    "Retry-After": str(result.retry_after),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                },
                media_type="application/json",
            )

        # Allowed: adiciona headers informativos e segue
        response = await call_next(request)
        policy = TIER_POLICIES[tier]
        response.headers["X-RateLimit-Limit"] = str(policy.per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, policy.per_minute - result.current))
        return response


__all__ = [
    "ApiKeyTier",
    "RateLimitByKeyMiddleware",
    "RateLimitPolicy",
    "TIER_POLICIES",
    "identify_tier",
]
