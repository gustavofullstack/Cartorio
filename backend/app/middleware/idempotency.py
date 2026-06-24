"""IdempotencyMiddleware - intercepta POST com header `Idempotency-Key`.

A6: cliente envia `Idempotency-Key: <uuid>` em POST. Backend faz SETNX
no store (Redis) com TTL 24h. Se ja existe, retorna resposta cacheada
sem duplicar a mutacao. Se body eh diferente, retorna 422.

LGPD: cache armazena APENAS o response (sem PII).
Chave = sha256(Idempotency-Key + endpoint + method).

Comportamento:
- Sem Idempotency-Key: passa direto.
- Idempotency-Key vazia: 400.
- Idempotency-Key + primeira chamada: cacheia response e retorna.
- Idempotency-Key + replay (mesmo body): retorna response cacheada.
- Idempotency-Key + body diferente: 422 (conflito).
- Response 5xx: NAO cacheia (cliente pode tentar de novo).
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.idempotency_store import (
    IdempotencyStore,
    RedisIdempotencyStore,
)

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 86400  # 24h
DEFAULT_PATHS = ("/api/v1/",)


def _hash_idempotency_key(key: str, endpoint: str, method: str) -> str:
    """Gera chave de cache deterministica a partir do header + endpoint + method.

    LGPD: hash garante que o Idempotency-Key original nao vaza no Redis.
    """
    payload = f"{method}:{endpoint}:{key}"
    return f"idempotency:{hashlib.sha256(payload.encode()).hexdigest()}"


def _body_hash(body_bytes: bytes) -> str:
    """Hash SHA-256 do body para deteccao de conflito."""
    return hashlib.sha256(body_bytes).hexdigest()


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware de idempotency para POST em paths protegidos.

    Args:
        app: FastAPI app.
        store: IdempotencyStore (Redis ou fake). Default = Redis.
        paths_prefixes: Prefixos de path interceptados. Default = /api/v1/.
        ttl_seconds: TTL da chave no store. Default = 24h.
    """

    def __init__(
        self,
        app: Any,  # noqa: ANN401
        store: IdempotencyStore | None = None,
        paths_prefixes: tuple[str, ...] = DEFAULT_PATHS,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        super().__init__(app)
        self._store = store or RedisIdempotencyStore()
        self._paths = paths_prefixes
        self._ttl = ttl_seconds

    def _should_intercept(self, method: str, path: str) -> bool:
        if method != "POST":
            return False
        return any(path.startswith(p) for p in self._paths)

    @staticmethod
    def _response_from_cache(cached: dict[str, Any]) -> Response:
        """Reconstrói Response a partir do dict cacheado."""
        return Response(
            content=cached.get("body", b""),
            status_code=cached.get("status_code", 200),
            headers=cached.get("headers", {}),
            media_type=cached.get("media_type", "application/json"),
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self._should_intercept(request.method, request.url.path):
            return await call_next(request)

        # Le header (case-insensitive: aceita Idempotency-Key, idempotency-key, etc)
        idem_key = request.headers.get("idempotency-key") or request.headers.get(
            "Idempotency-Key"
        ) or request.headers.get("IDEMPOTENCY-KEY")
        if idem_key is None:
            # Tenta tambem chaves Title-case (Starlette Headers normaliza lowercase)
            for k, v in request.headers.items():
                if k.lower() == "idempotency-key":
                    idem_key = v
                    break

        # Sem header: passa direto
        if idem_key is None:
            return await call_next(request)

        # Header presente mas vazio: erro
        if not idem_key.strip():
            return Response(
                content=json.dumps(
                    {
                        "erro": "IDEMPOTENCY_KEY_EMPTY",
                        "mensagem": "Header Idempotency-Key presente mas vazio.",
                    }
                ),
                status_code=400,
                media_type="application/json",
            )

        # Le body (precisa pra detectar conflito de body diferente)
        body_bytes = await request.body()
        body_h = _body_hash(body_bytes)

        # Chave do store: hash(header + endpoint + method)
        cache_key = _hash_idempotency_key(idem_key, request.url.path, request.method)

        # Tenta buscar replay
        try:
            cached = await self._store.get(cache_key)
        except Exception as e:  # noqa: BLE001
            # Fail-open: se Redis offline, passa direto (nao bloqueia o usuario)
            logger.warning("idempotency: store offline, fail-open: %s", e)
            return await call_next(request)

        if cached is not None:
            cached_body_h = cached.get("body_hash")
            if cached_body_h == body_h:
                # Replay valido: retorna response cacheada
                logger.info("idempotency: replay cache_key=%s", cache_key[:32])
                return self._response_from_cache(cached)
            # Conflito: mesma key com body diferente
            logger.warning(
                "idempotency: conflito de body, cache_key=%s", cache_key[:32]
            )
            return Response(
                content=json.dumps(
                    {
                        "erro": "IDEMPOTENCY_KEY_CONFLICT",
                        "mensagem": (
                            "Idempotency-Key ja utilizada com outro body. "
                            "Use uma key nova ou envie o mesmo body."
                        ),
                    }
                ),
                status_code=422,
                media_type="application/json",
            )

        # Primeira chamada: executa handler
        response = await call_next(request)

        # Cacheia apenas responses 2xx/3xx/4xx (NAO 5xx - cliente pode tentar de novo)
        if response.status_code < 500:
            try:
                # Captura body do response
                resp_body = b""
                async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                    if isinstance(chunk, str):
                        resp_body += chunk.encode()
                    else:
                        resp_body += chunk

                cached_value: dict[str, Any] = {
                    "body_hash": body_h,
                    "status_code": response.status_code,
                    "body": resp_body.decode("utf-8", errors="replace"),
                    "headers": dict(response.headers),
                    "media_type": response.media_type or "application/json",
                }
                await self._store.setnx(cache_key, cached_value, self._ttl)
            except Exception as e:  # noqa: BLE001
                # Falha ao cachear NAO deve quebrar o request
                logger.warning("idempotency: falha ao cachear, fail-open: %s", e)

        # Reconstroi response (body_iterator foi consumido)
        return Response(
            content=resp_body if "resp_body" in locals() else b"",
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type or "application/json",
        )


__all__ = ["IdempotencyMiddleware"]
