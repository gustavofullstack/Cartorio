"""Testes do RFC 7807 Problem Details handler.

Cobertura:
- HTTPException 4xx vira application/problem+json com type/title/status/detail/instance
- HTTPException 5xx vira application/problem+json + log error
- RequestValidationError (422) vira problem+json com errors[] listando campos
- Exception generica vira 500 + log exception (NAO expoe msg original)
- Headers do HTTPException sao preservados
- request_id eh gerado se nao existir em request.state
- type URL segue padrao https://cartorio.com.br/problems/{slug}
- content-type eh application/problem+json (RFC 7807 sec 3)
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.middleware.problem_details import (
    PROBLEM_CONTENT_TYPE,
    _build_problem,
    install_problem_handlers,
)


class Item(BaseModel):
    name: str
    price: float


def _build_app() -> FastAPI:
    app = FastAPI()
    install_problem_handlers(app)

    @app.get("/not-found")
    async def not_found() -> None:
        raise HTTPException(status_code=404, detail="recurso X nao existe")

    @app.get("/forbidden")
    async def forbidden() -> None:
        raise HTTPException(
            status_code=403,
            detail="acesso negado",
            headers={"X-Reason": "lgpd-blocked"},
        )

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("vazou PII: cpf=123.456.789-00")

    @app.post("/items")
    async def create_item(item: Item) -> dict:
        return {"ok": True}

    return app


class TestProblemDetailsHandler:
    """TDD strict."""

    def test_http_exception_404_returns_problem_json(self):
        app = _build_app()
        client = TestClient(app)

        resp = client.get("/not-found")
        assert resp.status_code == 404
        assert resp.headers["content-type"].startswith(PROBLEM_CONTENT_TYPE)

        body = resp.json()
        assert body["type"] == "https://cartorio.com.br/problems/not-found"
        assert body["title"] == "Nao Encontrado"
        assert body["status"] == 404
        assert body["detail"] == "recurso X nao existe"
        assert body["instance"] == "/not-found"
        assert "request_id" in body

    def test_http_exception_403_preserves_headers(self):
        """Headers do HTTPException sao preservados."""
        app = _build_app()
        client = TestClient(app)

        resp = client.get("/forbidden")
        assert resp.status_code == 403
        assert resp.headers.get("x-reason") == "lgpd-blocked"
        assert resp.headers["content-type"].startswith(PROBLEM_CONTENT_TYPE)

        body = resp.json()
        assert body["status"] == 403
        assert body["title"] == "Acesso Negado"

    def test_validation_error_422_returns_problem_json_with_errors(self):
        """RequestValidationError (422) vira problem+json com errors[]."""
        app = _build_app()
        client = TestClient(app)

        resp = client.post("/items", json={"name": "", "price": "nao-e-numero"})
        assert resp.status_code == 422
        assert resp.headers["content-type"].startswith(PROBLEM_CONTENT_TYPE)

        body = resp.json()
        assert body["type"] == "https://cartorio.com.br/problems/validation-error"
        assert body["title"] == "Erro de Validacao"
        assert body["status"] == 422
        assert "errors" in body
        assert isinstance(body["errors"], list)
        assert len(body["errors"]) >= 1
        # Cada error tem field/message/type
        for err in body["errors"]:
            assert "field" in err
            assert "message" in err
            assert "type" in err

    def test_generic_exception_returns_500_without_leak(self, caplog):
        """Exception generica vira 500 + NAO expoe mensagem original (PII/leak)."""
        app = _build_app()
        # raise_server_exceptions=False impede Starlette de re-raisear e dump do stack
        client = TestClient(app, raise_server_exceptions=False)

        with caplog.at_level(logging.ERROR, logger="cartorio.problem"):
            resp = client.get("/boom")

        assert resp.status_code == 500
        assert resp.headers["content-type"].startswith(PROBLEM_CONTENT_TYPE)

        body = resp.json()
        assert body["status"] == 500
        assert body["title"] == "Erro Interno"
        # NAO pode vazar PII/stack original
        assert "123.456.789" not in resp.text
        assert "cpf" not in resp.text.lower()
        assert "RuntimeError" not in resp.text

        # Log deve capturar exception
        assert any("Unhandled" in r.message for r in caplog.records)

    def test_request_id_present(self):
        """request_id sempre presente no problem."""
        app = _build_app()
        client = TestClient(app)

        resp = client.get("/not-found")
        body = resp.json()
        assert body["request_id"].startswith("req_")
        assert len(body["request_id"]) > 4

    def test_type_url_pattern(self):
        """type URL segue padrao https://cartorio.com.br/problems/{slug}."""
        app = _build_app()
        client = TestClient(app)

        for path, expected_slug in [
            ("/not-found", "not-found"),
            ("/forbidden", "forbidden"),
        ]:
            resp = client.get(path)
            body = resp.json()
            assert body["type"] == f"https://cartorio.com.br/problems/{expected_slug}"

    def test_content_type_is_problem_json(self):
        """content-type = application/problem+json (RFC 7807 sec 3)."""
        app = _build_app()
        client = TestClient(app)

        resp = client.get("/not-found")
        assert resp.headers["content-type"] == "application/problem+json"

    def test_build_problem_helper(self):
        """_build_problem() funciona standalone (sem request)."""
        problem = _build_problem(status_code=404, detail="recurso X nao existe")
        assert problem["type"] == "https://cartorio.com.br/problems/not-found"
        assert problem["title"] == "Nao Encontrado"
        assert problem["status"] == 404
        assert problem["detail"] == "recurso X nao existe"
        assert "instance" not in problem
        assert "request_id" not in problem

    def test_build_problem_extras(self):
        """_build_problem aceita extras (ex: errors[])."""
        problem = _build_problem(
            status_code=422,
            detail="validacao falhou",
            extras={"errors": [{"field": "cpf", "message": "invalido"}]},
        )
        assert "errors" in problem
        assert problem["errors"][0]["field"] == "cpf"

    def test_build_problem_unknown_status_uses_default(self):
        """Status code fora do mapa usa slug/title default."""
        problem = _build_problem(status_code=418, detail="eu sou um bule de cha")
        assert problem["type"] == "https://cartorio.com.br/problems/error"
        assert problem["title"] == "Erro"
        assert problem["status"] == 418
