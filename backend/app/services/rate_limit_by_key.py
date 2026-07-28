"""Rate limiting por API key (substitui o atual por session_id quando X-API-Key presente).

Decisao: 3 tiers de API key com limites diferentes.
- N8N (alta freq, polling/cron): 600 req/min
- DPO/escrevente (humano via dashboard): 60 req/min
- Padrao / sem key: 30 req/min (fail-secure)

Algoritmo: Redis INCR com TTL sliding window de 60s.
- Chave: ratelimit:apikey:<hash>:<minute_bucket>
- Valor: contador
- TTL: 60s

Anti-spoofing (E2.03 H4): tier elevado SOMENTE via match exato
(constant-time) com a key registrada em ``settings.cartorio_api_key``.
Prefixos ('n8n-', 'dpo-', ...) ou tamanho NUNCA elevam tier — sao
trivialmente forjaveis. Key desconhecida/malformada cai em 'padrao'
(fail-secure).

LGPD: o hash da API key NAO pode ser reversivel. SHA-256 da key ja eh
suficiente (key tem 64 chars hex = 256 bits de entropia).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
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

# A7: sliding window rate limit (60 req/min/IP) - camada adicional
from app.services.sliding_window import (  # noqa: E402
    RedisSlidingWindowStore,
    sliding_window_check,
)


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

# Telegram autentica cada entrega no próprio endpoint com
# ``X-Telegram-Bot-Api-Secret-Token``. O webhook chega através de proxy e as
# réplicas podem receber o mesmo IP encaminhado; aplicar o DDoS por IP e o
# tier sem API key aqui transforma retries legítimos do Telegram em 429. A
# proteção deste caminho é a validação do secret no router Telegram.
SIGNED_WEBHOOK_PATHS = frozenset(
    {
        "/api/v1/telegram/webhook",
        "/api/v1/pietra/v1/chat/completions",
        "/api/v1/pietra/chat/completions",
    }
)


# ============================================================================
# Identificacao de tier
# ============================================================================


def _hash_api_key(api_key: str) -> str:
    """Hash SHA-256 da API key (LGPD-safe, nao reversivel)."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:32]


def identify_tier(api_key: str | None) -> ApiKeyTier:
    """Identifica o tier da API key.

    E2.03 H4 (anti-spoofing): tier elevado exige match EXATO com a key
    registrada em ``settings.cartorio_api_key`` (mesma validacao strict
    64-hex de ``app.api.deps.require_cartorio_api_key``), comparada em
    constant-time via ``hmac.compare_digest``.

    - Key registrada (inter-service N8N/Admin): tier='n8n' (600 req/min)
    - Qualquer outra key (desconhecida, malformada, com prefixo 'n8n-'/
      'dpo-'/'admin-' forjado, ou string longa): tier='padrao' (fail-secure)

    Prefixo/tamanho NUNCA elevam tier: sao controlados pelo caller e
    trivialmente spoofable. Tier 'dpo' fica reservado ate existir
    registro de keys por tier.

    Em Sprint 4+: substituir por tabela `api_keys` no DB com campo `tier`.
    """
    if not api_key:
        return "padrao"
    expected = settings.cartorio_api_key
    if expected and hmac.compare_digest(api_key.encode("utf-8"), expected.encode("utf-8")):
        return "n8n"
    dpo_expected = settings.cartorio_dpo_api_key
    if dpo_expected and hmac.compare_digest(api_key.encode("utf-8"), dpo_expected.encode("utf-8")):
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
        ddos_per_minute: int = 100,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._url = redis_url or settings.redis_url
        self._api_key_header = api_key_header
        self._paths = paths_prefixes
        self._ddos_per_minute = ddos_per_minute
        self._client: redis_async.Redis | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None
        # A7: sliding window store compartilhado
        self._sliding_store: RedisSlidingWindowStore = RedisSlidingWindowStore(self._url)

    async def _get_client(self) -> redis_async.Redis | None:
        current_loop = asyncio.get_running_loop()
        if (
            self._client is not None
            and self._client_loop is not None
            and self._client_loop is not current_loop
        ):
            old_client = self._client
            self._client = None
            self._client_loop = None
            try:
                await old_client.aclose()
            except (redis_async.RedisError, OSError, RuntimeError):
                logger.debug("rate_limit: discarded Redis client bound to closed loop")
        if self._client is None:
            try:
                self._client = redis_async.from_url(
                    self._url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                )
                self._client_loop = current_loop
                await self._client.ping()
            except (redis_async.RedisError, OSError) as e:
                logger.warning("rate_limit: Redis offline, fail-open: %s", e)
                self._client = None
                self._client_loop = None
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

    async def _check_ip_ddos(self, client_ip: str) -> RateLimitResult:
        """Defesa DDoS: limite ABSOLUTO por IP (independente de API key).

        Limite: 100 req/min por IP. Se um atacante rotacionar API keys
        ou nao usar key nenhuma, este limite o segura antes do limite
        por tier.
        """
        client = await self._get_client()
        if client is None:
            return RateLimitResult(allowed=True, current=0, limit=0, retry_after=0)

        ip_hash = _hash_api_key(f"ip:{client_ip}")
        now_minute = int(time.time() // 60)
        redis_key = f"ratelimit:ip:{ip_hash}:{now_minute}"
        limit = self._ddos_per_minute

        try:
            pipe = client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, 60)
            current, _ = await pipe.execute()
        except redis_async.RedisError as e:
            logger.warning("rate_limit: Redis error em IP DDoS check, fail-open: %s", e)
            return RateLimitResult(allowed=True, current=0, limit=0, retry_after=0)

        current = int(current)
        allowed = current <= limit
        retry_after = 60 - (int(time.time()) % 60) if not allowed else 0
        return RateLimitResult(
            allowed=allowed, current=current, limit=limit, retry_after=retry_after
        )

    async def _check_sliding_window(self, client_ip: str) -> RateLimitResult:
        """A7: sliding window log algorithm (60 req/min/IP).

        Camada 1.5 — roda DEPOIS do DDoS fixed-window e ANTES do per-tier.
        Usa ZSET no Redis para sliding window real (sem boundary attack).
        Fail-open se Redis offline.
        """
        ip_hash = _hash_api_key(f"sliding:ip:{client_ip}")
        result = await sliding_window_check(
            self._sliding_store,  # type: ignore[arg-type]
            key=f"sliding:ip:{ip_hash}",
            limit=self._ddos_per_minute,
            window_s=60,
        )
        return RateLimitResult(
            allowed=result.allowed,
            current=result.current,
            limit=result.limit,
            retry_after=result.retry_after,
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Webhook assinado: não possui X-API-Key e pode compartilhar o IP do
        # proxy entre retries/updates. A autenticação acontece no endpoint.
        if request.url.path in SIGNED_WEBHOOK_PATHS:
            return await call_next(request)

        # Filtra por path
        if self._paths and not any(request.url.path.startswith(p) for p in self._paths):
            return await call_next(request)

        # O TrustedProxyMiddleware resolve XFF somente para peers confiáveis.
        # Nunca leia o header diretamente aqui: um cliente direto conseguiria
        # escolher buckets de rate limit e contornar o limite por IP.
        client_ip = request.client.host if request.client else "unknown"

        # Camada 1: DDoS protection (limite absoluto por IP, fixed window)
        ip_result = await self._check_ip_ddos(client_ip)
        if not ip_result.allowed:
            logger.warning(
                "rate_limit.ddos: ip=%s current=%d limit=%d path=%s",
                client_ip,
                ip_result.current,
                ip_result.limit,
                request.url.path,
            )
            try:
                from app.services.metrics import store as metrics_store

                metrics_store.inc_rate_limit_total(layer="ddos", tier="none")
            except Exception:  # noqa: BLE001 — metrics never block path
                pass
            return Response(
                content=(
                    f'{{"erro":"RATE_LIMITED_DDOS","mensagem":"Limite absoluto de '
                    f"{ip_result.limit} req/min por IP atingido. Tente em "
                    f'{ip_result.retry_after}s."}}'
                ),
                status_code=429,
                headers={
                    "Retry-After": str(ip_result.retry_after),
                    "X-RateLimit-Limit": str(ip_result.limit),
                    "X-RateLimit-Remaining": "0",
                },
                media_type="application/json",
            )

        # Camada 1.5: A7 sliding window real (sem boundary attack)
        sliding_result = await self._check_sliding_window(client_ip)
        if not sliding_result.allowed:
            logger.warning(
                "rate_limit.sliding: ip=%s current=%d limit=%d path=%s",
                client_ip,
                sliding_result.current,
                sliding_result.limit,
                request.url.path,
            )
            try:
                from app.services.metrics import store as metrics_store

                metrics_store.inc_rate_limit_total(layer="sliding", tier="none")
            except Exception:  # noqa: BLE001
                pass
            return Response(
                content=(
                    f'{{"erro":"RATE_LIMITED_SLIDING","mensagem":"Limite sliding window '
                    f"{sliding_result.limit} req/min por IP. Tente em "
                    f'{sliding_result.retry_after}s."}}'
                ),
                status_code=429,
                headers={
                    "Retry-After": str(sliding_result.retry_after),
                    "X-RateLimit-Limit": str(sliding_result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Algorithm": "sliding-window",
                },
                media_type="application/json",
            )

        # Identifica API key (camada 2: rate limit por tier)
        api_key = request.headers.get(self._api_key_header)
        if api_key:
            tier = identify_tier(api_key)
            key_hash = _hash_api_key(api_key)
        else:
            tier = "padrao"
            # Hash anonimo: IP do cliente (LGPD-safe, nao reversivel)
            key_hash = _hash_api_key(f"ip:{client_ip}")

        result = await self._check(key_hash, tier)

        if not result.allowed:
            policy = TIER_POLICIES[tier]
            logger.warning(
                "rate_limit: tier=%s hash=%s current=%d limit=%d",
                tier,
                key_hash[:8],
                result.current,
                result.limit,
            )
            try:
                from app.services.metrics import store as metrics_store

                metrics_store.inc_rate_limit_total(layer="tier", tier=str(tier))
            except Exception:  # noqa: BLE001
                pass
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
