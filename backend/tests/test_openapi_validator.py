"""Testes do openapi_validator (A19)."""
from __future__ import annotations

from fastapi import FastAPI

from app.middleware.openapi_validator import (
    _get_app_openapi_schema,
    _resolve_ref,
    install_openapi_validation_middleware,
)


class TestOpenAPIValidator:
    """TDD strict - A19."""

    def test_get_app_openapi_schema_loads(self):
        """Schema OpenAPI carrega da app."""
        app = FastAPI(title="Test API", version="1.0.0")

        @app.get("/test")
        async def test() -> dict:
            return {"ok": True}

        schema = _get_app_openapi_schema(app)
        assert "paths" in schema
        assert "/test" in schema["paths"]
        assert schema["info"]["title"] == "Test API"

    def test_install_openapi_validation_middleware_runs(self):
        """install_openapi_validation_middleware executa sem erro."""
        app = FastAPI(title="Test API", version="1.0.0")

        @app.get("/test")
        async def test() -> dict:
            return {"ok": True}

        # Nao levanta
        install_openapi_validation_middleware(app)

    def test_resolve_ref_returns_dict(self):
        """_resolve_ref resolve $ref simple."""
        schema = {
            "components": {
                "schemas": {
                    "Item": {"type": "object", "properties": {"id": {"type": "integer"}}}
                }
            }
        }
        ref = {"$ref": "#/components/schemas/Item"}
        resolved = _resolve_ref(schema, ref)
        assert resolved is not None
        assert resolved["type"] == "object"
        assert "id" in resolved["properties"]

    def test_resolve_ref_missing_returns_none(self):
        """_resolve_ref retorna None se $ref invalido."""
        schema: dict = {"components": {"schemas": {}}}
        ref = {"$ref": "#/components/schemas/Missing"}
        assert _resolve_ref(schema, ref) is None

    def test_resolve_ref_passthrough(self):
        """_resolve_ref sem $ref retorna o proprio dict."""
        schema: dict = {}
        ref = {"type": "object"}
        assert _resolve_ref(schema, ref) == ref

    def test_schema_cached(self):
        """Schema eh cacheado em app.openapi_schema."""
        app = FastAPI(title="Test API", version="1.0.0")

        @app.get("/test")
        async def test() -> dict:
            return {"ok": True}

        schema1 = _get_app_openapi_schema(app)
        schema2 = _get_app_openapi_schema(app)
        # Mesma referencia (cache)
        assert schema1 is schema2

    def test_main_app_schema_loads(self):
        """App principal (cartorio-api) tem schema OpenAPI carregavel."""
        from app.main import app

        # Reset cache to force regeneration
        app.openapi_schema = None
        schema = _get_app_openapi_schema(app)
        assert "paths" in schema
        # Tem que ter varios paths
        assert len(schema["paths"]) > 5

    def test_validate_request_body_no_jsonschema(self):
        """validate_request_body retorna True quando jsonschema nao disponivel."""
        import sys

        from app.middleware.openapi_validator import validate_request_body

        schema: dict = {"paths": {"/test": {"post": {"requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}}}}}}

        # Simular jsonschema ausente
        saved = sys.modules.get("jsonschema")
        sys.modules["jsonschema"] = None  # type: ignore[assignment]
        try:
            valid, err = validate_request_body(schema, "/test", "POST", {"key": "val"})
        finally:
            if saved is not None:
                sys.modules["jsonschema"] = saved
            else:
                sys.modules.pop("jsonschema", None)
        assert valid is True
        assert err is None

    def test_validate_request_body_no_request_body(self):
        """validate_request_body retorna True quando nao tem requestBody no schema."""
        from app.middleware.openapi_validator import validate_request_body

        schema = {"paths": {"/test": {"post": {}}}}
        valid, err = validate_request_body(schema, "/test", "POST", {"key": "val"})
        assert valid is True
        assert err is None

    def test_validate_request_body_valid(self):
        """validate_request_body retorna True para body valido."""
        from app.middleware.openapi_validator import validate_request_body

        schema = {
            "paths": {
                "/test": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
                                }
                            }
                        }
                    }
                }
            }
        }
        valid, err = validate_request_body(schema, "/test", "POST", {"name": "Gustavo"})
        assert valid is True
        assert err is None

    def test_validate_request_body_invalid(self):
        """validate_request_body retorna False para body invalido."""
        from app.middleware.openapi_validator import validate_request_body

        schema = {
            "paths": {
                "/test": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
                                }
                            }
                        }
                    }
                }
            }
        }
        valid, err = validate_request_body(schema, "/test", "POST", {})
        assert valid is False
        assert err is not None
        assert "name" in err

    def test_validate_request_body_with_ref(self):
        """validate_request_body resolve $ref antes de validar."""
        from app.middleware.openapi_validator import validate_request_body

        schema = {
            "components": {
                "schemas": {
                    "Item": {"type": "object", "required": ["id"], "properties": {"id": {"type": "integer"}}}
                }
            },
            "paths": {
                "/test": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Item"}
                                }
                            }
                        }
                    }
                }
            }
        }
        valid, err = validate_request_body(schema, "/test", "POST", {"id": 1})
        assert valid is True

    def test_validate_request_body_ref_not_found(self):
        """validate_request_body retorna True quando $ref invalido (fallback)."""
        from app.middleware.openapi_validator import validate_request_body

        schema = {
            "paths": {
                "/test": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Missing"}
                                }
                            }
                        }
                    }
                }
            }
        }
        valid, err = validate_request_body(schema, "/test", "POST", {"anything": True})
        assert valid is True
