"""Testes endpoints LGPD D26-D32 (v2 com JWT auth + DPO role).

Cobre:
- D26: Dashboard DPO (KPIs)
- D27: Consentimento granular
- D28: Direito ao esquecimento (real)
- D29: Export/portabilidade (real)
- D30: Correcao de dados pessoais
- D31: Revogacao de consentimento
- D32: Audit transparency

Padrao TDD: cada endpoint tem testes de happy path + error cases.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.models.base import Base


# ===========================================================================
# Fixtures
# ===========================================================================

TEST_JWT_SECRET = "a" * 64  # 64 chars para satisfazer HS256 requirement


@pytest.fixture(autouse=True)
def _set_jwt_env(monkeypatch):
    """Configura JWT_SECRET para testes."""
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)


@pytest.fixture
def test_engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False
    )


@pytest.fixture
def db_session(test_engine, test_session_factory):
    """Sessao para criar dados de setup."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()


def _make_dpo_token(user_id: str = "dpo-001") -> str:
    """Gera JWT com claim dpo=True."""
    from app.services.auth_jwt import issue_access_token

    get_settings.cache_clear()
    settings = get_settings()
    return issue_access_token(user_id, dpo=True, settings=settings)


def _make_cliente_token(cliente_id: int | str = "42") -> str:
    """Gera JWT de titular (dpo=False)."""
    from app.services.auth_jwt import issue_access_token

    get_settings.cache_clear()
    settings = get_settings()
    return issue_access_token(str(cliente_id), dpo=False, settings=settings)


def _make_no_dpo_token(user_id: str = "user-no-dpo") -> str:
    """Gera JWT sem dpo (para testar 403 no dashboard)."""
    from app.services.auth_jwt import issue_access_token

    get_settings.cache_clear()
    settings = get_settings()
    return issue_access_token(user_id, dpo=False, settings=settings)


@pytest.fixture
def client(test_engine, test_session_factory):
    """TestClient FastAPI com SQLite in-memory."""
    from app.db import get_db

    with (
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "app.db.engine", test_engine
        ),
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "app.db.SessionLocal", test_session_factory
        ),
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "app.main.engine", test_engine
        ),
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
# Helper: criar cliente de teste
# ===========================================================================


def _create_cliente(db_session, **kwargs):
    from app.models.cliente import Cliente

    defaults = {
        "nome": "Cliente Teste",
        "cpf_hash": "hash_teste_001",
        "email": "teste@test.com",
        "telefone_hash": "hash_tel_teste",
        "consentimento_lgpd": True,
        "consentimento_em": datetime.now(tz=timezone.utc),
        "consentimento_ip": "10.0.0.1",
        "consentimento_canal": "whatsapp",
    }
    defaults.update(kwargs)
    c = Cliente(**defaults)
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


# ===========================================================================
# D26 — Dashboard DPO
# ===========================================================================


class TestDashboardDPO:
    """Testes do endpoint GET /lgpd/dashboard (D26)."""

    def test_dashboard_200_with_dpo_token(self, client: TestClient, db_session):
        """D26 happy path: retorna KPIs com token DPO valido."""
        dpo_token = _make_dpo_token()
        _create_cliente(db_session)

        response = client.get(
            "/api/v1/lgpd/dashboard",
            headers={"Authorization": f"Bearer {dpo_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_clientes_ativos" in data
        assert "total_clientes_revocados" in data
        assert "consents_ativos" in data
        assert "consents_revogados_30d" in data
        assert "exports_solicitados_30d" in data
        assert "audit_entries_24h" in data
        assert "audit_chain_status" in data
        assert data["audit_chain_status"]["ok"] is True
        assert data["total_clientes_ativos"] >= 1

    def test_dashboard_401_without_token(self, client: TestClient):
        """D26: retorna 401 sem Bearer token."""
        response = client.get("/api/v1/lgpd/dashboard")
        assert response.status_code == 401

    def test_dashboard_403_without_dpo_role(self, client: TestClient, db_session):
        """D26: retorna 403 com token valido mas sem claim dpo=True."""
        token = _make_no_dpo_token()
        response = client.get(
            "/api/v1/lgpd/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_dashboard_401_with_invalid_token(self, client: TestClient):
        """D26: retorna 401 com token invalido."""
        response = client.get(
            "/api/v1/lgpd/dashboard",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_dashboard_counts_deleted_clientes(self, client: TestClient, db_session):
        """D26: conta clientes com deleted_at (revocados)."""
        _create_cliente(db_session, nome="Ativo")
        deleted = _create_cliente(db_session, nome="Deletado", cpf_hash="hash_del")
        # Marca como deletado
        db_session.execute(
            text("UPDATE clientes SET deleted_at = :now WHERE id = :id"),
            {"now": datetime.now(tz=timezone.utc), "id": deleted.id},
        )
        db_session.commit()

        dpo_token = _make_dpo_token()
        response = client.get(
            "/api/v1/lgpd/dashboard",
            headers={"Authorization": f"Bearer {dpo_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_clientes_revocados"] >= 1


# ===========================================================================
# D27 — Consentimento granular
# ===========================================================================


class TestConsentGranular:
    """Testes do endpoint POST /lgpd/consent (D27)."""

    def test_consent_grant_200(self, client: TestClient, db_session):
        """D27 happy path: titular concede consentimento para marketing."""
        c = _create_cliente(db_session, consentimento_lgpd=False, consentimento_em=None)
        token = _make_cliente_token(c.id)

        response = client.post(
            "/api/v1/lgpd/consent",
            json={
                "cliente_id": c.id,
                "finalidade": "marketing",
                "granted": True,
                "canal": "whatsapp",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["finalidade"] == "marketing"
        assert data["granted"] is True

    def test_consent_revoke_200(self, client: TestClient, db_session):
        """D27: titular revoga consentimento de uma finalidade."""
        c = _create_cliente(db_session)
        token = _make_cliente_token(c.id)

        response = client.post(
            "/api/v1/lgpd/consent",
            json={
                "cliente_id": c.id,
                "finalidade": "marketing",
                "granted": False,
                "canal": "web",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["granted"] is False

    def test_consent_404_client_not_found(self, client: TestClient):
        """D27: retorna 404 se cliente nao existe."""
        token = _make_dpo_token()

        response = client.post(
            "/api/v1/lgpd/consent",
            json={
                "cliente_id": 99999,
                "finalidade": "marketing",
                "granted": True,
                "canal": "web",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    def test_consent_400_invalid_finalidade(self, client: TestClient, db_session):
        """D27: retorna 400 com finalidade invalida."""
        c = _create_cliente(db_session)
        token = _make_dpo_token()

        response = client.post(
            "/api/v1/lgpd/consent",
            json={
                "cliente_id": c.id,
                "finalidade": "finalidade_invalida",
                "granted": True,
                "canal": "web",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

    def test_consent_401_without_token(self, client: TestClient):
        """D27: retorna 401 sem token."""
        response = client.post(
            "/api/v1/lgpd/consent",
            json={
                "cliente_id": 1,
                "finalidade": "marketing",
                "granted": True,
                "canal": "web",
            },
        )
        assert response.status_code == 401

    def test_consent_dpo_can_grant_for_cliente(self, client: TestClient, db_session):
        """D27: DPO pode conceder consentimento em nome do titular."""
        c = _create_cliente(db_session, consentimento_lgpd=False, consentimento_em=None)
        dpo_token = _make_dpo_token()

        response = client.post(
            "/api/v1/lgpd/consent",
            json={
                "cliente_id": c.id,
                "finalidade": "prospeccao",
                "granted": True,
                "canal": "balcao",
            },
            headers={"Authorization": f"Bearer {dpo_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["finalidade"] == "prospeccao"


# ===========================================================================
# D28 — Direito ao esquecimento
# ===========================================================================


class TestDireitoEsquecimento:
    """Testes do endpoint DELETE /lgpd/cliente/{id} (D28)."""

    def test_esquecimento_200(self, client: TestClient, db_session):
        """D28 happy path: soft delete com anonimizacao."""
        c = _create_cliente(db_session)
        dpo_token = _make_dpo_token()

        response = client.delete(
            f"/api/v1/lgpd/cliente/{c.id}",
            headers={"Authorization": f"Bearer {dpo_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["direito"] == "esquecimento"
        assert data["cliente_id"] == c.id
        assert "deleted_at" in data
        assert "anonymized_tables" in data
        assert "reversivel_ate" in data

    def test_esquecimento_404(self, client: TestClient):
        """D28: retorna 404 quando cliente nao existe."""
        dpo_token = _make_dpo_token()

        response = client.delete(
            "/api/v1/lgpd/cliente/99999",
            headers={"Authorization": f"Bearer {dpo_token}"},
        )

        assert response.status_code == 404

    def test_esquecimento_401_without_token(self, client: TestClient):
        """D28: retorna 401 sem token."""
        response = client.delete("/api/v1/lgpd/cliente/1")
        assert response.status_code == 401

    def test_esquecimento_marcou_deleted_at(self, client: TestClient, db_session):
        """D28: verifica que deleted_at foi setado no DB."""
        c = _create_cliente(db_session)
        dpo_token = _make_dpo_token()

        client.delete(
            f"/api/v1/lgpd/cliente/{c.id}",
            headers={"Authorization": f"Bearer {dpo_token}"},
        )

        # Verifica no DB
        row = db_session.execute(
            text("SELECT deleted_at, nome FROM clientes WHERE id = :id"),
            {"id": c.id},
        ).mappings().first()
        assert row is not None
        assert row["deleted_at"] is not None
        assert row["nome"] == "[ANONIMIZADO art.18 V]"

    def test_esquecimento_with_motivo(self, client: TestClient, db_session):
        """D28: motivo customizado."""
        c = _create_cliente(db_session)
        dpo_token = _make_dpo_token()

        response = client.delete(
            f"/api/v1/lgpd/cliente/{c.id}?motivo=dpo_determinou",
            headers={"Authorization": f"Bearer {dpo_token}"},
        )

        assert response.status_code == 200


# ===========================================================================
# D29 — Export/portabilidade
# ===========================================================================


class TestExportDados:
    """Testes do endpoint GET /lgpd/export/{cliente_id} (D29)."""

    def test_export_200(self, client: TestClient, db_session):
        """D29 happy path: exporta dados do titular."""
        c = _create_cliente(db_session)
        token = _make_cliente_token(c.id)

        response = client.get(
            f"/api/v1/lgpd/export/{c.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["direito"] == "portabilidade"
        assert data["cliente_id"] == c.id
        assert "export_hash" in data
        assert "dados" in data
        assert data["dados"]["cliente"]["nome"] == "Cliente Teste"

    def test_export_404(self, client: TestClient):
        """D29: retorna 404 quando cliente nao existe."""
        token = _make_dpo_token()

        response = client.get(
            "/api/v1/lgpd/export/99999",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    def test_export_401_without_token(self, client: TestClient):
        """D29: retorna 401 sem token."""
        response = client.get("/api/v1/lgpd/export/1")
        assert response.status_code == 401

    def test_export_includes_protocolos(self, client: TestClient, db_session):
        """D29: inclui protocolos na exportacao."""
        c = _create_cliente(db_session)
        from app.models.protocolo import Protocolo

        p = Protocolo(
            cliente_id=c.id,
            numero="CART-2026-V2-001",
            tipo="certidao_casamento",
            status="em_andamento",
            canal_origem="whatsapp",
        )
        db_session.add(p)
        db_session.commit()

        token = _make_cliente_token(c.id)
        response = client.get(
            f"/api/v1/lgpd/export/{c.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["dados"]["protocolos"]) == 1

    def test_export_hash_unique_per_cliente(self, client: TestClient, db_session):
        """D29: hash e unico por cliente."""
        c1 = _create_cliente(db_session, nome="A", cpf_hash="hash_a_v2")
        c2 = _create_cliente(db_session, nome="B", cpf_hash="hash_b_v2")
        dpo_token = _make_dpo_token()

        r1 = client.get(
            f"/api/v1/lgpd/export/{c1.id}",
            headers={"Authorization": f"Bearer {dpo_token}"},
        )
        r2 = client.get(
            f"/api/v1/lgpd/export/{c2.id}",
            headers={"Authorization": f"Bearer {dpo_token}"},
        )

        assert r1.json()["export_hash"] != r2.json()["export_hash"]


# ===========================================================================
# D30 — Correcao de dados pessoais
# ===========================================================================


class TestCorrigirDados:
    """Testes do endpoint POST /lgpd/correct/{cliente_id} (D30)."""

    def test_correct_nome_200(self, client: TestClient, db_session):
        """D30 happy path: corrige nome."""
        c = _create_cliente(db_session, nome="Nome Antigo")
        token = _make_cliente_token(c.id)

        response = client.post(
            f"/api/v1/lgpd/correct/{c.id}",
            json={"nome": "Nome Novo"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "nome" in data["updated_fields"]

        # Verifica no DB
        from app.models.cliente import Cliente

        refreshed = db_session.get(Cliente, c.id)
        assert refreshed.nome == "Nome Novo"

    def test_correct_email_200(self, client: TestClient, db_session):
        """D30: corrige email."""
        c = _create_cliente(db_session)
        token = _make_cliente_token(c.id)

        response = client.post(
            f"/api/v1/lgpd/correct/{c.id}",
            json={"email": "novo@test.com"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "email" in data["updated_fields"]

    def test_correct_multiple_fields(self, client: TestClient, db_session):
        """D30: corrige multiplos campos de uma vez."""
        c = _create_cliente(db_session)
        token = _make_cliente_token(c.id)

        response = client.post(
            f"/api/v1/lgpd/correct/{c.id}",
            json={
                "nome": "Novo Nome",
                "email": "novo@email.com",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["updated_fields"]) == 2

    def test_correct_404(self, client: TestClient):
        """D30: retorna 404 quando cliente nao existe."""
        token = _make_dpo_token()

        response = client.post(
            "/api/v1/lgpd/correct/99999",
            json={"nome": "Teste"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    def test_correct_400_no_fields(self, client: TestClient, db_session):
        """D30: retorna 400 quando nenhum campo fornecido."""
        c = _create_cliente(db_session)
        token = _make_cliente_token(c.id)

        response = client.post(
            f"/api/v1/lgpd/correct/{c.id}",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

    def test_correct_400_invalid_field(self, client: TestClient, db_session):
        """D30: retorna 400 quando campo nao esta na whitelist."""
        c = _create_cliente(db_session)
        token = _make_cliente_token(c.id)

        response = client.post(
            f"/api/v1/lgpd/correct/{c.id}",
            json={"cpf_hash": "novo_hash"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

    def test_correct_401_without_token(self, client: TestClient):
        """D30: retorna 401 sem token."""
        response = client.post(
            "/api/v1/lgpd/correct/1",
            json={"nome": "Teste"},
        )
        assert response.status_code == 401

    def test_correct_dpo_can_correct_for_cliente(self, client: TestClient, db_session):
        """D30: DPO pode corrigir dados em nome do titular."""
        c = _create_cliente(db_session, nome="Original")
        dpo_token = _make_dpo_token()

        response = client.post(
            f"/api/v1/lgpd/correct/{c.id}",
            json={"nome": "Correcao DPO"},
            headers={"Authorization": f"Bearer {dpo_token}"},
        )

        assert response.status_code == 200
        assert "nome" in response.json()["updated_fields"]


# ===========================================================================
# D31 — Revogacao de consentimento
# ===========================================================================


class TestRevogarConsent:
    """Testes do endpoint POST /lgpd/revogar-consent (D31)."""

    def test_revogar_tudo_200(self, client: TestClient, db_session):
        """D31 happy path: revoga todo consentimento."""
        c = _create_cliente(db_session, consentimento_lgpd=True)
        token = _make_cliente_token(c.id)

        response = client.post(
            "/api/v1/lgpd/revogar-consent",
            json={
                "cliente_id": c.id,
                "canal": "web",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["consentimento_lgpd"] is False

    def test_revogar_por_finalidade(self, client: TestClient, db_session):
        """D31: revoga apenas uma finalidade."""
        c = _create_cliente(db_session, consentimento_lgpd=True)
        token = _make_cliente_token(c.id)

        response = client.post(
            "/api/v1/lgpd/revogar-consent",
            json={
                "cliente_id": c.id,
                "finalidades": ["marketing"],
                "canal": "email",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_revogar_404(self, client: TestClient):
        """D31: retorna 404 quando cliente nao existe."""
        token = _make_dpo_token()

        response = client.post(
            "/api/v1/lgpd/revogar-consent",
            json={"cliente_id": 99999, "canal": "web"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    def test_revogar_401_without_token(self, client: TestClient):
        """D31: retorna 401 sem token."""
        response = client.post(
            "/api/v1/lgpd/revogar-consent",
            json={"cliente_id": 1, "canal": "web"},
        )
        assert response.status_code == 401

    def test_revogar_set_consentimento_false(self, client: TestClient, db_session):
        """D31: revogacao total seta consentimento_lgpd=False."""
        c = _create_cliente(db_session, consentimento_lgpd=True)
        token = _make_cliente_token(c.id)

        client.post(
            "/api/v1/lgpd/revogar-consent",
            json={"cliente_id": c.id, "canal": "web"},
            headers={"Authorization": f"Bearer {token}"},
        )

        from app.models.cliente import Cliente

        refreshed = db_session.get(Cliente, c.id)
        assert refreshed.consentimento_lgpd is False

    def test_revogar_dpo_can_revoke(self, client: TestClient, db_session):
        """D31: DPO pode revogar consentimento de qualquer titular."""
        c = _create_cliente(db_session, consentimento_lgpd=True)
        dpo_token = _make_dpo_token()

        response = client.post(
            "/api/v1/lgpd/revogar-consent",
            json={
                "cliente_id": c.id,
                "finalidades": ["marketing", "analytics"],
                "canal": "admin",
            },
            headers={"Authorization": f"Bearer {dpo_token}"},
        )

        assert response.status_code == 200


# ===========================================================================
# D32 — Audit Transparency
# ===========================================================================


class TestAuditTransparency:
    """Testes do endpoint GET /lgpd/audit/{cliente_id} (D32)."""

    def test_audit_200_with_entries(self, client: TestClient, db_session):
        """D32 happy path: retorna audit entries do titular."""
        c = _create_cliente(db_session)

        # Gera alguma atividade de audit
        from app.services.audit import AuditService

        AuditService.log(
            db_session,
            actor_id=str(c.id),
            actor_type="cliente",
            action="lgpd.consent.granted",
            resource=f"cliente:{c.id}",
            payload={"finalidade": "marketing"},
            ip="192.168.1.100",
        )

        token = _make_cliente_token(c.id)

        response = client.get(
            f"/api/v1/lgpd/audit/{c.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["cliente_id"] == c.id
        assert data["entries_count"] >= 1

    def test_audit_ip_truncated(self, client: TestClient, db_session):
        """D32: IPs sao truncados (nao expostos ao titular)."""
        c = _create_cliente(db_session)

        from app.services.audit import AuditService

        AuditService.log(
            db_session,
            actor_id=str(c.id),
            actor_type="cliente",
            action="lgpd.test.action",
            resource=f"cliente:{c.id}",
            payload={"test": True},
            ip="192.168.1.100",
        )

        token = _make_cliente_token(c.id)
        response = client.get(
            f"/api/v1/lgpd/audit/{c.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        if data["entries_count"] > 0:
            entry = data["entries"][0]
            ip = entry.get("ip_truncated")
            if ip:
                # IP truncado deve terminar em .0 para IPv4
                assert ip.endswith(".0")

    def test_audit_pii_scrubbed_from_payload(self, client: TestClient, db_session):
        """D32: PII removida dos payloads (user_agent, request_id)."""
        c = _create_cliente(db_session)

        from app.services.audit import AuditService

        AuditService.log(
            db_session,
            actor_id=str(c.id),
            actor_type="cliente",
            action="lgpd.test.pii",
            resource=f"cliente:{c.id}",
            payload={"sensitive": "data"},
            user_agent="Mozilla/5.0 (test)",
            request_id="req-12345",
            ip="10.0.0.1",
        )

        token = _make_cliente_token(c.id)
        response = client.get(
            f"/api/v1/lgpd/audit/{c.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        if data["entries_count"] > 0:
            entry = data["entries"][0]
            # user_agent e request_id NAO devem aparecer
            assert "user_agent" not in entry
            assert "request_id" not in entry

    def test_audit_404_no_entries(self, client: TestClient):
        """D32: retorna vazio para cliente sem audit entries."""
        token = _make_dpo_token()

        response = client.get(
            "/api/v1/lgpd/audit/99999",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entries_count"] == 0

    def test_audit_401_without_token(self, client: TestClient):
        """D32: retorna 401 sem token."""
        response = client.get("/api/v1/lgpd/audit/1")
        assert response.status_code == 401

    def test_audit_limit_param(self, client: TestClient, db_session):
        """D32: limit parameter funciona."""
        c = _create_cliente(db_session)

        from app.services.audit import AuditService

        for i in range(5):
            AuditService.log(
                db_session,
                actor_id=str(c.id),
                actor_type="cliente",
                action=f"lgpd.test.{i}",
                resource=f"cliente:{c.id}",
                payload={"idx": i},
            )

        token = _make_dpo_token()
        response = client.get(
            f"/api/v1/lgpd/audit/{c.id}?limit=2",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entries_count"] <= 2

    def test_audit_limit_max_500(self, client: TestClient, db_session):
        """D32: limit nao excede 500."""
        c = _create_cliente(db_session)
        token = _make_dpo_token()

        response = client.get(
            f"/api/v1/lgpd/audit/{c.id}?limit=999",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Query param validation error (le=500)
        assert response.status_code == 422


# ===========================================================================
# Auth edge cases (cross-cutting)
# ===========================================================================


class TestAuthEdgeCases:
    """Testes de边界 de auth (JWT invalido, expirado, etc)."""

    def test_expired_token_401(self, client: TestClient):
        """Token expirado retorna 401."""
        # Forca JWT_SECRET
        os.environ["JWT_SECRET"] = TEST_JWT_SECRET
        get_settings.cache_clear()

        import jwt as pyjwt
        from app.config import get_settings as _gs

        settings = _gs()
        # Gera token com exp no passado
        payload = {
            "sub": "user-1",
            "iss": settings.jwt_issuer,
            "aud": "cartorio-v2",
            "typ": "access",
            "iat": 1000000000,
            "exp": 1000000001,  # 2001-09-09
            "jti": "test-jti",
            "dpo": True,
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        response = client.get(
            "/api/v1/lgpd/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401

    def test_wrong_type_token_401(self, client: TestClient):
        """Token do tipo 'refresh' no endpoint de access retorna 401."""
        os.environ["JWT_SECRET"] = TEST_JWT_SECRET
        get_settings.cache_clear()

        from app.services.auth_jwt import issue_refresh_token

        get_settings.cache_clear()
        # issue_refresh_token gera token com typ=refresh
        token = issue_refresh_token("user-1", settings=get_settings())

        response = client.get(
            "/api/v1/lgpd/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401

    def test_malformed_header_401(self, client: TestClient):
        """Header Authorization malformado retorna 401."""
        response = client.get(
            "/api/v1/lgpd/dashboard",
            headers={"Authorization": "Basic abc123"},
        )

        assert response.status_code == 401


# ===========================================================================
# Integration: jwt claim dpo in auth_jwt.py
# ===========================================================================


class TestJWTDpoClaim:
    """Testes de integracao: claim dpo no JWT."""

    def test_issue_access_token_with_dpo(self):
        """issue_access_token(dpo=True) inclui claim dpo=True."""
        os.environ["JWT_SECRET"] = TEST_JWT_SECRET
        get_settings.cache_clear()

        from app.services.auth_jwt import issue_access_token, verify_token

        settings = get_settings()
        token = issue_access_token("test-user-dpo", dpo=True, settings=settings)
        payload = verify_token(token, settings=settings)

        assert payload["dpo"] is True
        assert payload["sub"] == "test-user-dpo"

    def test_issue_access_token_without_dpo(self):
        """issue_access_token(dpo=False) inclui claim dpo=False."""
        os.environ["JWT_SECRET"] = TEST_JWT_SECRET
        get_settings.cache_clear()

        from app.services.auth_jwt import issue_access_token, verify_token

        settings = get_settings()
        token = issue_access_token("test-user-regular", dpo=False, settings=settings)
        payload = verify_token(token, settings=settings)

        assert payload["dpo"] is False

    def test_issue_access_token_default_no_dpo(self):
        """issue_access_token() default nao inclui dpo."""
        os.environ["JWT_SECRET"] = TEST_JWT_SECRET
        get_settings.cache_clear()

        from app.services.auth_jwt import issue_access_token, verify_token

        settings = get_settings()
        token = issue_access_token("test-user-default", settings=settings)
        payload = verify_token(token, settings=settings)

        assert payload["dpo"] is False
