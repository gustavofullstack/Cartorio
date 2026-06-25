"""RFC 7807 Problem Details for HTTP APIs.

Handler global que converte excecoes em respostas no formato
application/problem+json (RFC 7807). Padrao IETF que substitui
o {"detail": "..."} generico do FastAPI por respostas estruturadas.

Estrutura de response:
{
  "type": "https://cartorio.com.br/problems/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Campo cpf invalido",
  "instance": "/api/v1/cliente",
  "request_id": "req_abc123",
  "errors": [...]  // opcional, para 422 multi-field
}

Vantagens:
- Cliente pode parsear type/title/instance sem ter que olhar string
- Permite internacionalizacao (type eh URL estavel, title eh PT-BR/en)
- Inclui request_id automaticamente (LGPD art. 37 - auditoria)
- Content-type: application/problem+json (RFC 7807 sec 3)
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("cartorio.problem")

PROBLEM_CONTENT_TYPE = "application/problem+json"

PROBLEM_BASE_URL = "https://cartorio.com.br/problems"

# Mapa de excecoes HTTP comuns para type URL + title PT-BR
_HTTP_PROBLEM_MAP: dict[int, tuple[str, str]] = {
    400: ("bad-request", "Requisicao Invalida"),
    401: ("unauthorized", "Nao Autenticado"),
    403: ("forbidden", "Acesso Negado"),
    404: ("not-found", "Nao Encontrado"),
    405: ("method-not-allowed", "Metodo Nao Permitido"),
    409: ("conflict", "Conflito"),
    422: ("validation-error", "Erro de Validacao"),
    429: ("too-many-requests", "Muitas Requisicoes"),
    500: ("internal-error", "Erro Interno"),
    502: ("bad-gateway", "Gateway Ruim"),
    503: ("service-unavailable", "Servico Indisponivel"),
    504: ("gateway-timeout", "Gateway Timeout"),
}


def _problem_url(slug: str) -> str:
    return f"{PROBLEM_BASE_URL}/{slug}"


def _build_problem(
    status_code: int,
    detail: str,
    request: Request | None = None,
    *,
    type_slug: str | None = None,
    title: str | None = None,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Constroi payload RFC 7807."""
    slug, default_title = _HTTP_PROBLEM_MAP.get(
        status_code, ("error", "Erro")
    )
    problem: dict[str, Any] = {
        "type": _problem_url(type_slug or slug),
        "title": title or default_title,
        "status": status_code,
        "detail": detail,
    }
    if request is not None:
        problem["instance"] = str(request.url.path)
        request_id = getattr(request.state, "request_id", None) or f"req_{uuid.uuid4().hex[:12]}"
        problem["request_id"] = request_id
    if extras:
        problem.update(extras)
    return problem


def install_problem_handlers(app: FastAPI) -> None:
    """Instala handlers globais RFC 7807 no FastAPI app.

    Registra 3 handlers:
    1. HTTPException (Starlette) - 4xx/5xx com detail
    2. RequestValidationError - 422 com lista de campos
    3. Exception - 500 generico (catch-all)
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # Se detail ja eh string, usa direto. Se eh dict, preserva info
        # semantica (ex: LGPD_BLOCKED com mensagem + detalhes).
        if isinstance(exc.detail, str):
            detail_str: str = exc.detail
            extras: dict[str, Any] | None = None
        else:
            # detail eh dict com info semantica - extrai mensagem e preserva
            # o resto em extras. Tambem mantem o dict original em "detail"
            # para retrocompat com testes/clientes existentes.
            d = exc.detail if isinstance(exc.detail, dict) else {}
            detail_str = str(d.get("mensagem") or d.get("message") or d.get("detail") or "Erro")
            # Campos LGPD_by_design: erro, detalhes, codigo, etc
            semantic = {k: v for k, v in d.items() if k not in {"mensagem", "message", "detail"}}
            # detail original eh preservado (retrocompat)
            semantic["detail"] = d
            extras = semantic
        problem = _build_problem(
            status_code=exc.status_code,
            detail=detail_str,
            request=request,
            extras=extras,
        )
        # 5xx vai pra Sentry/logger; 4xx eh cliente, nao loga
        if exc.status_code >= 500:
            logger.error(
                "HTTPException 5xx",
                extra={"status": exc.status_code, "path": request.url.path, "detail": detail_str},
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=problem,
            media_type=PROBLEM_CONTENT_TYPE,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # errors() vem do Pydantic v2 com estrutura {loc, msg, type, input, url, ...}
        errors = []
        for err in exc.errors():
            errors.append({
                "field": ".".join(str(p) for p in err.get("loc", [])),
                "message": err.get("msg", ""),
                "type": err.get("type", ""),
            })
        problem = _build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Validacao falhou em {len(errors)} campo(s)",
            request=request,
            extras={"errors": errors},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=problem,
            media_type=PROBLEM_CONTENT_TYPE,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # 500 catch-all. NAO expoe mensagem original (pode vazar PII/stack).
        logger.exception(
            "Unhandled exception",
            extra={"path": request.url.path, "method": request.method},
        )
        problem = _build_problem(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor. Contate o suporte com o request_id.",
            request=request,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=problem,
            media_type=PROBLEM_CONTENT_TYPE,
        )
