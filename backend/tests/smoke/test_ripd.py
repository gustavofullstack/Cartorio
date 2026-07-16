"""Smoke test de conformidade do Relatório de Impacto à Proteção de Dados (RIPD) - Wave 2 S2.T3.

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Exigência do Pydantic: chave precisa ter no mínimo 64 caracteres
API_KEY = "a" * 64


@pytest.fixture(autouse=True)
def override_settings():
    from app.api.deps import get_settings
    from app.config import Settings

    # Sobrescreve a dependência de settings injetada pelo FastAPI
    app.dependency_overrides[get_settings] = lambda: Settings(
        cartorio_api_key=API_KEY,
        app_env="development",  # Pydantic valida Literals: development, staging, production
    )
    yield
    app.dependency_overrides.clear()


def test_smoke_ripd_compliance_payload() -> None:
    """Valida se o endpoint RIPD responde adequadamente e retorna todos os campos da ANPD."""
    headers = {"X-API-Key": API_KEY}

    # 1. Requisição nominal
    resp = client.get("/api/v1/lgpd/ripd", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    # 2. Validar chaves obrigatórias
    assert "metadata" in body
    assert "categorias_dados_pessoais" in body
    assert "finalidades" in body
    assert "bases_legais" in body
    assert "riscos_identificados" in body
    assert "medidas_mitigacao" in body
    assert "politica_retencao" in body
    assert "direitos_titular_art_18" in body

    # 3. Validar integridade do DPO
    dpo = body["metadata"]["agente_tratamento"]["encarregado_dpo"]
    assert "Gustavo Almeida" in dpo["nome"]
    assert dpo["email"] == "dpo@2notasudi.com.br"


def test_smoke_ripd_format_markdown() -> None:
    """Valida se a exportação em formato Markdown do RIPD está estruturada."""
    headers = {"X-API-Key": API_KEY}

    resp = client.get("/api/v1/lgpd/ripd?format=markdown", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "ripd_markdown" in body
    md = body["ripd_markdown"]
    assert md.startswith("# ")
    assert "Relatorio de Impacto a Protecao de Dados" in md
    assert "art. 18" in md.lower()
