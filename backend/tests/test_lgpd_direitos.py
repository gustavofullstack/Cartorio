"""Testes dos endpoints LGPD direitos do titular (D08-D12).

Cobre os 5 POST direitos (anonimizar, corrigir, oposicao, optout, portabilidade)
+ o GET download portabilidade (D09).

Padrao TDD: RED antes de GREEN para cada endpoint novo.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from tests.conftest import TEST_CARTORIO_API_KEY


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def db_session(test_session_factory):
    """Sessao para criar dados de setup."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_engine, test_session_factory):
    """TestClient FastAPI com SQLite in-memory."""
    from app.db import get_db

    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        Base.metadata.create_all(test_engine)

        def _override_get_db():
            db = test_session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override_get_db

        try:
            with TestClient(app) as c:
                yield c
        finally:
            app.dependency_overrides.clear()


# ===========================================================================
# GET /cliente/{id}/lgpd/portabilidade/download (D09)
# ===========================================================================


class TestDownloadPortabilidade:
    """Testes do endpoint GET de download de portabilidade (LGPD art. 18 V)."""

    def test_download_portabilidade_200(self, client: TestClient, db_session):
        """Retorna 200 com dados do titular quando cliente existe."""
        from app.models.cliente import Cliente

        c = Cliente(
            nome="Maria Portabilidade",
            cpf_hash="hash_maria_port_001",
            email="maria@test.com",
            telefone_hash="hash_tel_maria_002",
            consentimento_lgpd=True,
            consentimento_em=datetime.now(tz=timezone.utc),
            consentimento_ip="10.0.0.1",
            consentimento_canal="whatsapp",
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        response = client.get(
            f"/api/v1/cliente/{c.id}/lgpd/portabilidade/download",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["direito"] == "portabilidade.download"
        assert data["cliente_id"] == c.id
        assert "export_hash" in data
        assert "dados" in data
        assert data["dados"]["cliente"]["nome"] == "M*** P***"  # D29-G2: mascarado
        assert data["dados"]["cliente"]["cpf_hash"] == "hash_maria_port_001"
        # D29-G2: header Deprecation presente (endpoint v1 deprecated)
        assert response.headers.get("Deprecation") == "true"

    def test_download_portabilidade_404(self, client: TestClient):
        """Retorna 404 quando cliente nao existe."""
        response = client.get(
            "/api/v1/cliente/99999/lgpd/portabilidade/download",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["erro"] == "CLIENTE_NOT_FOUND"

    def test_download_portabilidade_401(self, client: TestClient, db_session):
        """Retorna 401 sem X-API-Key valida."""
        from app.models.cliente import Cliente

        c = Cliente(nome="Sem Key", cpf_hash="hash_sem_key")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        response = client.get(
            f"/api/v1/cliente/{c.id}/lgpd/portabilidade/download",
        )
        assert response.status_code == 401

    def test_download_portabilidade_inclui_protocolos(self, client: TestClient, db_session):
        """Retorna protocolos associados ao titular."""
        from app.models.cliente import Cliente
        from app.models.protocolo import Protocolo

        c = Cliente(nome="Com Protocolo", cpf_hash="hash_prot")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        p = Protocolo(
            cliente_id=c.id,
            numero="CART-2026-9999",
            tipo="certidao_casamento",
            status="em_andamento",
            canal_origem="whatsapp",
        )
        db_session.add(p)
        db_session.commit()

        response = client.get(
            f"/api/v1/cliente/{c.id}/lgpd/portabilidade/download",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["dados"]["protocolos"]) == 1
        assert data["dados"]["protocolos"][0]["numero"] == "CART-2026-9999"

    def test_download_portabilidade_export_hash_muda(self, client: TestClient, db_session):
        """Export hash e diferente para clientes diferentes (integridade)."""
        from app.models.cliente import Cliente

        c1 = Cliente(nome="Cliente A", cpf_hash="hash_a_001")
        c2 = Cliente(nome="Cliente B", cpf_hash="hash_b_002")
        db_session.add_all([c1, c2])
        db_session.commit()
        db_session.refresh(c1)
        db_session.refresh(c2)

        r1 = client.get(
            f"/api/v1/cliente/{c1.id}/lgpd/portabilidade/download",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        r2 = client.get(
            f"/api/v1/cliente/{c2.id}/lgpd/portabilidade/download",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )

        assert r1.json()["export_hash"] != r2.json()["export_hash"]


# ===========================================================================
# POST /cliente/{id}/lgpd/anonimizar (D08)
# ===========================================================================


class TestAnonimizar:
    """Testes do endpoint de anonimizacao (LGPD art. 18 IV)."""

    def test_anonimizar_200(self, client: TestClient, db_session):
        """Retorna 200 quando cliente existe."""
        from app.models.cliente import Cliente

        c = Cliente(nome="Ana Anonimizar", cpf_hash="hash_ana")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        response = client.post(
            f"/api/v1/cliente/{c.id}/lgpd/anonimizar",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["direito"] == "anonimizar"
        assert data["cliente_id"] == c.id

    def test_anonimizar_404(self, client: TestClient):
        """Retorna 404 quando cliente nao existe."""
        response = client.post(
            "/api/v1/cliente/99999/lgpd/anonimizar",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 404

    def test_anonimizar_401(self, client: TestClient):
        """Retorna 401 sem X-API-Key."""
        response = client.post("/api/v1/cliente/1/lgpd/anonimizar")
        assert response.status_code == 401


# ===========================================================================
# POST /cliente/{id}/lgpd/corrigir (LGPD art. 18 III)
# ===========================================================================


class TestCorrigir:
    """Testes do endpoint de correcao (LGPD art. 18 III)."""

    def test_corrigir_200(self, client: TestClient, db_session):
        """Retorna 200 quando cliente existe."""
        from app.models.cliente import Cliente

        c = Cliente(nome="Carlos Corrigir", cpf_hash="hash_carlos")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        response = client.post(
            f"/api/v1/cliente/{c.id}/lgpd/corrigir",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 200

    def test_corrigir_404(self, client: TestClient):
        """Retorna 404 quando cliente nao existe."""
        response = client.post(
            "/api/v1/cliente/99999/lgpd/corrigir",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 404


# ===========================================================================
# POST /cliente/{id}/lgpd/oposicao (D11 - LGPD art. 18 IX)
# ===========================================================================


class TestOposicao:
    """Testes do endpoint de oposicao (LGPD art. 18 IX)."""

    def test_oposicao_200(self, client: TestClient, db_session):
        """Retorna 200 quando cliente existe."""
        from app.models.cliente import Cliente

        c = Cliente(nome="Oscar Oposicao", cpf_hash="hash_oscar")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        response = client.post(
            f"/api/v1/cliente/{c.id}/lgpd/oposicao",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 200

    def test_oposicao_404(self, client: TestClient):
        """Retorna 404 quando cliente nao existe."""
        response = client.post(
            "/api/v1/cliente/99999/lgpd/oposicao",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 404


# ===========================================================================
# POST /cliente/{id}/lgpd/optout (D12 - LGPD art. 18 IX parcial)
# ===========================================================================


class TestOptout:
    """Testes do endpoint de opt-out de comunicacoes."""

    def test_optout_200(self, client: TestClient, db_session):
        """Retorna 200 quando cliente existe."""
        from app.models.cliente import Cliente

        c = Cliente(nome="Otavio Optout", cpf_hash="hash_otavio")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        response = client.post(
            f"/api/v1/cliente/{c.id}/lgpd/optout",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 200

    def test_optout_404(self, client: TestClient):
        """Retorna 404 quando cliente nao existe."""
        response = client.post(
            "/api/v1/cliente/99999/lgpd/optout",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 404


# ===========================================================================
# POST /cliente/{id}/lgpd/portabilidade (LGPD art. 18 V)
# ===========================================================================


class TestPortabilidade:
    """Testes do endpoint de portabilidade (LGPD art. 18 V)."""

    def test_portabilidade_200(self, client: TestClient, db_session):
        """Retorna 200 com export_url quando cliente existe."""
        from app.models.cliente import Cliente

        c = Cliente(nome="Paula Portabilidade", cpf_hash="hash_paula")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        response = client.post(
            f"/api/v1/cliente/{c.id}/lgpd/portabilidade",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["direito"] == "portabilidade"
        assert "export_url" in data
        assert f"/api/v1/cliente/{c.id}/lgpd/portabilidade/download" in data["export_url"]

    def test_portabilidade_404(self, client: TestClient):
        """Retorna 404 quando cliente nao existe."""
        response = client.post(
            "/api/v1/cliente/99999/lgpd/portabilidade",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert response.status_code == 404

    def test_portabilidade_e2e(self, client: TestClient, db_session):
        """Fluxo completo: POST portabilidade + GET download."""
        from app.models.cliente import Cliente

        c = Cliente(
            nome="E2E Portabilidade",
            cpf_hash="hash_e2e",
            email="e2e@test.com",
            consentimento_lgpd=True,
            consentimento_em=datetime.now(tz=timezone.utc),
            consentimento_ip="10.0.0.1",
            consentimento_canal="web",
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        # POST
        post_resp = client.post(
            f"/api/v1/cliente/{c.id}/lgpd/portabilidade",
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert post_resp.status_code == 200
        export_url = post_resp.json()["export_url"]

        # GET download
        get_resp = client.get(
            export_url,
            headers={"X-API-Key": TEST_CARTORIO_API_KEY},
        )
        assert get_resp.status_code == 200
        dados = get_resp.json()
        assert dados["dados"]["cliente"]["nome"] == "E*** P***"  # D29-G2: mascarado
        assert dados["dados"]["cliente"]["email"] == "e***@com"  # D29-G2: service-level mask
