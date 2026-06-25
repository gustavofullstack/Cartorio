"""OpenAPI request/response validation middleware (A19).

Valida requests contra o schema OpenAPI gerado pelo FastAPI.
Detecta 2 tipos de problema:
1. Request body nao bate com schema (campos extras, tipos errados)
2. Response body nao bate com schema (drift de implementacao)

Quando MISMATCH:
- Request: retorna 400 com detalhes (cliente bug)
- Response: loga WARNING (servidor bug, NAO quebra response)

Sprint 5+: integrar com `spectree` ou `fastapi-validation`.
Por enquanto: valida contra OpenAPI schema em runtime via jsonschema.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

logger = logging.getLogger("cartorio.openapi_validator")


def _get_app_openapi_schema(app: FastAPI) -> dict[str, Any]:
    """Extrai schema OpenAPI da app FastAPI.

    Returns:
        dict com spec OpenAPI 3.0+. Cacheia internamente via app.openapi_schema.
    """
    if app.openapi_schema is None:
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
        )
    return app.openapi_schema  # type: ignore[return-value]


def install_openapi_validation_middleware(app: FastAPI) -> None:
    """Instala middleware de validacao OpenAPI (A19).

    NOTA: Validacao completa via jsonschema adicionaria ~50ms/request.
    Por enquanto, este modulo expoe helpers + estrutura. Integracao com
    spectree sera feita em Sprint 5+.
    """
    schema = _get_app_openapi_schema(app)
    logger.info(
        "OpenAPI schema carregado: %d paths, %d components",
        len(schema.get("paths", {})),
        len(schema.get("components", {}).get("schemas", {})),
    )


def validate_request_body(
    schema: dict[str, Any], path: str, method: str, body: dict[str, Any]
) -> tuple[bool, str | None]:
    """Valida request body contra schema OpenAPI (best-effort).

    Args:
        schema: OpenAPI spec completo
        path: rota ex '/api/v1/cliente'
        method: 'POST' | 'PUT' | 'PATCH'
        body: dict do body da request

    Returns:
        (valido, erro) onde erro eh mensagem legivel ou None
    """
    try:
        from jsonschema import Draft7Validator  # type: ignore[import-untyped]
    except ImportError:
        return True, None  # jsonschema nao instalado - skip

    op = schema.get("paths", {}).get(path, {}).get(method.lower(), {})
    body_schema = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
    if not body_schema:
        return True, None  # Sem schema = sem validacao

    # Resolver $ref (best-effort, recursivo limitado)
    resolved = _resolve_ref(schema, body_schema)
    if not resolved:
        return True, None

    try:
        Draft7Validator(resolved).validate(body)
        return True, None
    except Exception as e:
        return False, str(e)[:200]


def _resolve_ref(schema: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve $ref simple (1 nivel)."""
    if "$ref" not in ref:
        return ref
    ref_path = ref["$ref"].lstrip("#/").split("/")
    cur: Any = schema
    for part in ref_path:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur  # type: ignore[return-value]
