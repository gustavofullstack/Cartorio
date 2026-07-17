"""Testes do endpoint /api/v1/lgpd/privacy-policy/{cliente_id} (D22).

Cobre:
- Auth X-API-Key obrigatorio
- Format markdown e json
- 404 para cliente inexistente
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.cliente import Cliente

client = TestClient(app)

AUTH_HEADERS = {"X-API-Key": "a" * 64}


@pytest.fixture
def test_engine():
    """Engine SQLite in-memory — usa app.db.engine (patchado pelo autouse)."""
    import app.db as appdb

    return appdb.engine


@pytest.fixture
def test_session_factory(test_engine):
    import app.db as appdb

    return appdb.SessionLocal


@pytest.fixture
def http_client(test_engine, test_session_factory):
    """TestClient que usa o engine SQLite ja configurado pelo conftest autouse."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def cliente_ativo(test_session_factory):
    """Insere cliente de teste."""
    session = test_session_factory()
    c = Cliente(
        nome="Teste Endpoint Policy",
        cpf_hash="hash_endpoint_policy",
        email="policy@example.com",
        telefone_hash="hash_tel_endpoint_policy",
        consentimento_lgpd=True,
        consentimento_em=datetime.now(tz=timezone.utc),
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    cid = c.id
    session.close()
    return cid


class TestLGPDPrivacyPolicyEndpoint:
    """D22 — Endpoint Privacy Policy."""

    def test_endpoint_401_sem_api_key(self, http_client, cliente_ativo) -> None:
        """Sem X-API-Key -> 401."""
        resp = http_client.get(f"/api/v1/lgpd/privacy-policy/{cliente_ativo}")
        assert resp.status_code == 401

    def test_endpoint_404_cliente_inexistente(self, http_client) -> None:
        """Cliente inexistente -> 404."""
        resp = http_client.get("/api/v1/lgpd/privacy-policy/99999", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_endpoint_markdown_default(self, http_client, cliente_ativo) -> None:
        """GET sem query format -> markdown default."""
        resp = http_client.get(f"/api/v1/lgpd/privacy-policy/{cliente_ativo}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "markdown"
        assert "policy_markdown" in body
        assert body["policy_markdown"].startswith("# ")

    def test_endpoint_explicit_markdown(self, http_client, cliente_ativo) -> None:
        """?format=markdown -> 200 com policy_markdown."""
        resp = http_client.get(
            f"/api/v1/lgpd/privacy-policy/{cliente_ativo}?format=markdown",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "markdown"
        assert "policy_markdown" in body

    def test_endpoint_json(self, http_client, cliente_ativo) -> None:
        """?format=json -> 200 com dict estruturado."""
        resp = http_client.get(
            f"/api/v1/lgpd/privacy-policy/{cliente_ativo}?format=json",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "cliente" in body
        assert "contact_dpo" in body
        assert "direitos_art_18" in body

    def test_endpoint_format_invalido_retorna_422(self, http_client, cliente_ativo) -> None:
        """?format=html (invalido) -> 422."""
        resp = http_client.get(
            f"/api/v1/lgpd/privacy-policy/{cliente_ativo}?format=html",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_endpoint_marca_nome_cliente_no_md(self, http_client, cliente_ativo) -> None:
        """policy_markdown NAO contem nome completo do cliente."""
        resp = http_client.get(f"/api/v1/lgpd/privacy-policy/{cliente_ativo}", headers=AUTH_HEADERS)
        md = resp.json()["policy_markdown"]
        titular_section = md.split("---")[0]
        assert "Teste Endpoint Policy" not in titular_section
        assert "T*** E*** P***" in md

    def test_endpoint_marca_email_no_md(self, http_client, cliente_ativo) -> None:
        """policy_markdown contem email mascarado."""
        resp = http_client.get(f"/api/v1/lgpd/privacy-policy/{cliente_ativo}", headers=AUTH_HEADERS)
        md = resp.json()["policy_markdown"]
        assert "policy@example.com" not in md
        assert "p***@" in md

    def test_endpoint_contem_contact_dpo(self, http_client, cliente_ativo) -> None:
        """Endpoint inclui contact do DPO (Gustavo Almeida)."""
        resp = http_client.get(f"/api/v1/lgpd/privacy-policy/{cliente_ativo}", headers=AUTH_HEADERS)
        md = resp.json()["policy_markdown"]
        assert "Gustavo Almeida" in md
        assert "6682284055" in md

    def test_endpoint_json_inclui_telegram_dpo(self, http_client, cliente_ativo) -> None:
        """JSON estruturado tem telegram 6682284055."""
        resp = http_client.get(
            f"/api/v1/lgpd/privacy-policy/{cliente_ativo}?format=json",
            headers=AUTH_HEADERS,
        )
        body = resp.json()
        assert body["contact_dpo"]["telegram_chat_id"] == "6682284055"
