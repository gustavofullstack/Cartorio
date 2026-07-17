"""Novos testes unitários para preencher lacunas de cobertura da Wave 1 (Squad S1).
Cobre:
- app/services/cursor.py (encode, decode, decode_safe com erros)
- app/middleware/deprecation.py (DeprecationHeadersMiddleware com rotas v1 e v2)

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

# =============================================================================
# Testes do cursor.py
# =============================================================================


def test_cursor_helpers_nominal() -> None:
    from app.services.cursor import encode_cursor, decode_cursor, decode_cursor_safe

    payload = {"id_after": 42, "tipo": "escritura"}
    cursor_str = encode_cursor(payload)
    assert isinstance(cursor_str, str)
    assert len(cursor_str) > 0

    # Decodificação correta
    decoded = decode_cursor(cursor_str)
    assert decoded == payload

    # Decodificação segura
    val = decode_cursor_safe(cursor_str, "id_after")
    assert val == 42

    # Chave inexistente retorna None
    val_missing = decode_cursor_safe(cursor_str, "non_existent")
    assert val_missing is None


def test_cursor_helpers_erros() -> None:
    from app.services.cursor import decode_cursor, decode_cursor_safe

    # Cursores inválidos (malformados)
    with pytest.raises(ValueError):
        decode_cursor("cursor-invalido-malformado!")

    # JSON malformado codificado em base64
    import base64

    invalid_json_b64 = base64.urlsafe_b64encode(b"{malformed_json").decode("utf-8")
    with pytest.raises(ValueError):
        decode_cursor(invalid_json_b64)

    # decode_cursor_safe deve capturar erros silenciosamente e retornar None
    assert decode_cursor_safe("cursor-invalido-malformado!", "id_after") is None
    assert decode_cursor_safe(invalid_json_b64, "id_after") is None
    assert decode_cursor_safe(None, "id_after") is None  # type: ignore


# =============================================================================
# Testes do deprecation.py
# =============================================================================


def test_deprecation_middleware_headers() -> None:
    from app.middleware.deprecation import DeprecationHeadersMiddleware, _build_v2_link

    # Testa função auxiliar
    assert _build_v2_link("/api/v1/clientes") == "/api/v2/clientes"
    assert _build_v2_link("/api/v1/subpath/123") == "/api/v2/subpath/123"
    assert _build_v2_link("/other/route") == "/api/v2/"

    # App FastAPI de teste
    app = FastAPI()
    app.add_middleware(DeprecationHeadersMiddleware)

    @app.get("/api/v1/teste")
    async def v1_route(request: Request):
        return {"version": "v1"}

    @app.get("/api/v2/teste")
    async def v2_route(request: Request):
        return {"version": "v2"}

    @app.get("/health")
    async def health_route(request: Request):
        return {"status": "ok"}

    client = TestClient(app)

    # 1. Rota v1 deve conter os headers de depreciação
    resp_v1 = client.get("/api/v1/teste")
    assert resp_v1.status_code == 200
    assert resp_v1.headers.get("Deprecation") == "true"
    assert "2027" in resp_v1.headers.get("Sunset", "")
    assert resp_v1.headers.get("Link") == '</api/v2/teste>; rel="successor-version"'

    # 2. Rota v2 NÃO deve conter os headers
    resp_v2 = client.get("/api/v2/teste")
    assert resp_v2.status_code == 200
    assert "Deprecation" not in resp_v2.headers
    assert "Sunset" not in resp_v2.headers
    assert "Link" not in resp_v2.headers

    # 3. Rota comum (/health) NÃO deve conter os headers
    resp_health = client.get("/health")
    assert resp_health.status_code == 200
    assert "Deprecation" not in resp_health.headers
