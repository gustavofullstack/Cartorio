"""RequestContextMiddleware - popula request.state com metadados de auditoria.

O que ele faz:
- Gera/propaga um request_id (UUIDv4) por request:
  * Se o cliente mandou X-Request-Id, respeita (tracing distribuido).
  * Caso contrario, gera UUIDv4 novo.
  * Ecoa o request_id no response header X-Request-Id (proxys/load balancers).
- Extrai client_ip respeitando X-Forwarded-For:
  * Primeiro hop do XFF = cliente real atras do proxy reverso.
  * Fallback: request.client.host (util em testes/dev).
- Captura User-Agent e X-Canal (whatsapp/telegram/web/balcao/email).
- Anexa timestamp_iso UTC no momento da entrada (ISO 8601).

Por que isso importa:
- LGPD art. 37: registro de operacoes de tratamento precisa de IP/UA/canal.
- D5 (decisao arquitetural 2026-06-23): IP eh dado pessoal, armazenar
  truncado /24 em output mas completo 2y para fins de auditoria/forensics.
- Permite que AuditService.log() receba ip/user_agent/request_id sem que
  cada rota precise extrair manualmente.

NAO faz:
- Rate limiting (isso eh RateLimitMiddleware).
- Validacao de auth (webhooks usam HMAC + X-API-Key direto na rota).
- Sanitizacao de IP (output deve ser tratado na camada de presenter).

Implementacao:
- Usa BaseHTTPMiddleware (mesmo padrao do RateLimitMiddleware ja em uso)
  para consistencia arquitetural com o resto da API.
- Exposto como classe para `app.add_middleware(RequestContextMiddleware)`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


def _extract_client_ip(request: Request) -> str | None:
    """Extrai IP do cliente respeitando X-Forwarded-For.

    XFF pode ter varios hops separados por virgula. O PRIMEIRO eh o
    cliente real; os demais sao proxies intermedios. Em producao o
    Traefik ja confia no XFF, entao pegamos o primeiro.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return None


def _generate_or_propagate_request_id(incoming: str | None) -> str:
    """Se cliente mandou X-Request-Id ou X-Correlation-Id valido, usa. Senao, gera UUIDv4."""
    if incoming and 8 <= len(incoming) <= 128:
        return incoming
    return str(uuid.uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Popula request.state com request_id, client_ip, user_agent, canal, timestamp.

    Uso em main.py:
        from app.middleware.request_context import RequestContextMiddleware
        app.add_middleware(RequestContextMiddleware)

    Uso nas rotas:
        from fastapi import Request

        @router.post("/foo")
        def foo(request: Request) -> dict:
            AuditService.log(
                db,
                actor_id=...,
                action=...,
                resource=...,
                payload=...,
                ip=request.state.client_ip,
                user_agent=request.state.user_agent,
                request_id=request.state.request_id,
            )
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Correlation ID: aceita X-Request-Id, X-Correlation-Id OU gera novo
        # X-Correlation-Id e' o padrao W3C (https://www.w3.org/TR/correlation-id/)
        incoming = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
        request_id = _generate_or_propagate_request_id(incoming)
        client_ip = _extract_client_ip(request)
        user_agent = request.headers.get("user-agent")
        canal = request.headers.get("x-canal")
        timestamp_iso = datetime.now(UTC).isoformat(timespec="microseconds")

        # Popula request.state (acessivel via Request injetado nas rotas)
        request.state.request_id = request_id
        request.state.client_ip = client_ip
        request.state.user_agent = user_agent
        request.state.canal = canal
        request.state.timestamp_iso = timestamp_iso
        # Tambem disponivel como atributo do request.state.correlation_id
        request.state.correlation_id = request_id

        # Log estruturado do request (inclui correlation_id)
        # T9-MED-10: loga IP TRUNCADO (/24 ou /32), nao IP full (LGPD-by-design D5).
        import logging

        from app.utils.ip import truncate_ip

        logger = logging.getLogger("cartorio.request")
        logger.info(
            "request.start method=%s path=%s correlation_id=%s client_ip=%s canal=%s",
            request.method,
            request.url.path,
            request_id,
            truncate_ip(client_ip) or "unknown",
            canal,
        )

        response = await call_next(request)

        # Ecoa no response pra tracing distribuido (curl -i mostra)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Correlation-Id"] = request_id  # W3C standard

        # Log do fim do request
        logger.info(
            "request.end method=%s path=%s status=%d correlation_id=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
            (datetime.now(UTC) - datetime.fromisoformat(timestamp_iso)).total_seconds() * 1000,
        )
        return response


__all__ = ["RequestContextMiddleware"]
