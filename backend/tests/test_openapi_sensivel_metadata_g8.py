"""Testes de enriquecimento de metadados sensíveis no OpenAPI (G8.17.T3)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_openapi_contains_x_sensivel_metadata(client):
    """G8.17.T3: O JSON do OpenAPI deve marcar campos de dados sensíveis com x-sensivel: True."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    assert isinstance(schemas, dict)

    # 1. Validar no ProtocoloCreateRequest (cliente_cpf e cliente_nome se sensível, cpf deve ser)
    proto_create = schemas.get("ProtocoloCreateRequest")
    assert proto_create is not None
    proto_properties = proto_create.get("properties", {})
    assert proto_properties.get("cliente_cpf", {}).get("x-sensivel") is True

    # 2. Validar no ClienteCorrecaoRequest (email)
    correcao_req = schemas.get("ClienteCorrecaoRequest")
    assert correcao_req is not None
    correcao_properties = correcao_req.get("properties", {})
    assert correcao_properties.get("email", {}).get("x-sensivel") is True

    # 3. Validar no AuditLogCreate (ip)
    audit_create = schemas.get("AuditLogCreate")
    assert audit_create is not None
    audit_properties = audit_create.get("properties", {})
    assert audit_properties.get("ip", {}).get("x-sensivel") is True
