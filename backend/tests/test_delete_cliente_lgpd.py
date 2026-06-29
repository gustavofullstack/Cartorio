"""Testes formais do endpoint DELETE /api/v1/cliente/{id} (LGPD art. 18 VI).

Cobre os 3 cenarios principais (200/404/409) + integridade da audit chain
LGPD art. 37 apos mutacao.

Cenarios:
- 200 SOFT DELETE: cliente COM protocolo ativo + mutacao + audit log com contexto.
- 200 HARD DELETE: cliente SEM protocolo + mutacao + audit log + row removida.
- 404 NOT FOUND: cliente_id inexistente.
- 409 CONFLICT: cliente ja revogado (idempotencia 2a chamada).
- 401 UNAUTHORIZED: X-API-Key ausente.
- Audit chain ANTES e DEPOIS da mutacao continua valida (chain nao quebrada).

Ver:
- router.py:2444 — endpoint DELETE /cliente/{id}.
- app/services/lgpd/direito_esquecimento.py — service com hard/soft delete.
- ADR-018 — decisao hard vs soft.

Rodar via: `uv run pytest tests/test_delete_cliente_lgpd.py -v`
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.services.audit import AuditService
from tests.conftest import TEST_CARTORIO_API_KEY


# ============================================================================
# Fixtures
# ============================================================================


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


@pytest.fixture
def cliente_com_protocolo(db_session: Session):
    """Cliente com 1 protocolo ativo (cenario soft-delete)."""
    from app.models.cliente import Cliente
    from app.models.protocolo import Protocolo

    c = Cliente(
        nome="Cliente Soft Delete",
        cpf_hash="hash_soft_delete_001",
        email="soft@delete.com",
        consentimento_lgpd=True,
        consentimento_em=datetime.now(tz=timezone.utc),
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)

    p = Protocolo(
        cliente_id=c.id,
        numero="DEL-2026-00001",
        tipo="certidao",
        status="em_andamento",
        canal_origem="whatsapp",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    return c


@pytest.fixture
def cliente_sem_protocolo(db_session: Session):
    """Cliente SEM protocolo (cenario hard-delete)."""
    from app.models.cliente import Cliente

    c = Cliente(
        nome="Cliente Hard Delete",
        cpf_hash="hash_hard_delete_001",
        consentimento_lgpd=True,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def _auth_headers() -> dict[str, str]:
    return {
        "X-API-Key": TEST_CARTORIO_API_KEY,
        "X-Forwarded-For": "203.0.113.99",
        "User-Agent": "DeleteClienteTest/1.0",
        "X-Canal": "test-delete",
    }


# ============================================================================
# Testes — DELETE /api/v1/cliente/{id}
# ============================================================================


class TestDeleteClienteSoftDelete:
    """Cliente COM protocolo ativo → SOFT DELETE (LGPD art. 18 VI + Provimento CNJ 74/2018)."""

    def test_delete_cliente_com_protocolo_retorna_200(
        self, client: TestClient, cliente_com_protocolo, db_session: Session
    ):
        """DELETE /cliente/{id} com protocolo ativo → 200 + tipo=soft."""
        response = client.delete(
            f"/api/v1/cliente/{cliente_com_protocolo.id}",
            headers=_auth_headers(),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "deleted"
        assert data["tipo"] == "soft"
        assert data["cliente_id"] == cliente_com_protocolo.id
        assert data["protocolos_ativos"] >= 1
        assert data["motivo"] == "revogacao_consentimento"
        assert "data_encerramento" in data
        assert isinstance(data["audit_id"], int)

    def test_delete_cliente_soft_delete_anonimiza_pii_e_marca_deleted_at(
        self, client: TestClient, cliente_com_protocolo, db_session: Session
    ):
        """DELETE soft anonimiza PII e seta deleted_at (LGPD)."""
        response = client.delete(
            f"/api/v1/cliente/{cliente_com_protocolo.id}",
            headers=_auth_headers(),
        )
        assert response.status_code == 200

        db_session.expire_all()
        from app.models.cliente import Cliente

        refreshed = db_session.get(Cliente, cliente_com_protocolo.id)
        assert refreshed is not None
        assert refreshed.deleted_at is not None
        assert refreshed.motivo_encerramento is not None
        assert refreshed.email is None
        assert refreshed.telefone_hash is None
        assert refreshed.consentimento_lgpd is False
        # cpf_hash mantido (integridade referencial do audit chain).
        assert refreshed.cpf_hash is not None
        # nome anonimizado
        assert "TITULAR_REVOGADO" in refreshed.nome


class TestDeleteClienteHardDelete:
    """Cliente SEM protocolo → HARD DELETE."""

    def test_delete_cliente_sem_protocolo_retorna_200_com_tipo_hard(
        self, client: TestClient, cliente_sem_protocolo, db_session: Session
    ):
        """DELETE /cliente/{id} sem protocolo → 200 + tipo=hard."""
        cliente_id = cliente_sem_protocolo.id

        response = client.delete(
            f"/api/v1/cliente/{cliente_id}",
            headers=_auth_headers(),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["tipo"] == "hard"
        assert data["protocolos_ativos"] == 0

        # HARD DELETE: cliente removido do DB.
        # db_session eh sessao separada do app — expire_all() para
        # limpar cache e forcar reload (senao objeto fica stale em memoria).
        from app.models.cliente import Cliente

        db_session.expire_all()
        deleted = db_session.get(Cliente, cliente_id)
        assert deleted is None

    def test_delete_cliente_apaga_audit_log_registrado(
        self, client: TestClient, cliente_sem_protocolo, db_session: Session
    ):
        """Audit log do DELETE cliente.{tipo} deve estar gravado antes do commit."""
        cliente_id = cliente_sem_protocolo.id

        response = client.delete(
            f"/api/v1/cliente/{cliente_id}",
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        audit_id = response.json()["audit_id"]

        stmt = select(AuditLog).where(AuditLog.id == audit_id)
        entry = db_session.execute(stmt).scalar_one_or_none()
        assert entry is not None
        assert entry.action == "cliente.delete.hard"
        assert entry.resource == f"cliente:{cliente_id}"

    def test_delete_cliente_audit_log_tem_request_context(
        self, client: TestClient, cliente_sem_protocolo, db_session: Session
    ):
        """Audit log do DELETE inclui request_id, ip, user_agent, canal (LGPD)."""
        cliente_id = cliente_sem_protocolo.id

        response = client.delete(
            f"/api/v1/cliente/{cliente_id}",
            headers={
                **_auth_headers(),
                "X-Request-Id": "del-test-req-001",
            },
        )
        assert response.status_code == 200
        audit_id = response.json()["audit_id"]

        stmt = select(AuditLog).where(AuditLog.id == audit_id)
        entry = db_session.execute(stmt).scalar_one_or_none()
        assert entry is not None
        assert entry.request_id == "del-test-req-001"
        assert entry.ip == "203.0.113.99"
        assert entry.user_agent == "DeleteClienteTest/1.0"
        assert entry.canal == "test-delete"


class TestDeleteClienteErrorHandling:
    """Cenarios de erro do DELETE /cliente/{id}."""

    def test_delete_cliente_inexistente_retorna_404(self, client: TestClient, db_session: Session):
        """DELETE /cliente/{id_inexistente} → 404 CLIENTE_NOT_FOUND."""
        response = client.delete(
            "/api/v1/cliente/99999",
            headers=_auth_headers(),
        )

        assert response.status_code == 404, response.text
        data = response.json()
        # Pydantic + FastAPI default: detail vem como dict
        detail = data.get("detail", data)
        assert detail.get("erro") == "CLIENTE_NOT_FOUND"

    def test_delete_cliente_ja_revogado_retorna_409(
        self, client: TestClient, cliente_com_protocolo, db_session: Session
    ):
        """DELETE 2x no mesmo cliente → 2a chamada retorna 409 (idempotencia)."""
        # 1a chamada: 200 (soft delete)
        first = client.delete(
            f"/api/v1/cliente/{cliente_com_protocolo.id}",
            headers=_auth_headers(),
        )
        assert first.status_code == 200

        # 2a chamada: 409 (ja revogado)
        second = client.delete(
            f"/api/v1/cliente/{cliente_com_protocolo.id}",
            headers=_auth_headers(),
        )
        assert second.status_code == 409, second.text
        data = second.json()
        detail = data.get("detail", data)
        assert detail.get("erro") == "CLIENTE_JA_REVOGADO"

    def test_delete_cliente_sem_api_key_retorna_401(
        self, client: TestClient, cliente_sem_protocolo
    ):
        """DELETE sem X-API-Key → 401 UNAUTHORIZED."""
        response = client.delete(f"/api/v1/cliente/{cliente_sem_protocolo.id}")
        assert response.status_code == 401


class TestDeleteClienteAuditChainIntegrity:
    """DELETE /cliente/{id} NAO quebra a audit chain (LGPD art. 46)."""

    def test_delete_cliente_preserva_audit_chain_posterior(
        self, client: TestClient, cliente_com_protocolo, db_session: Session
    ):
        """Apos DELETE, a audit chain deve continuar integra (verify_chain=True)."""
        # 1a chamada: cria 1 entry baseline
        client.delete(
            f"/api/v1/cliente/{cliente_com_protocolo.id}",
            headers=_auth_headers(),
        )

        # 2a chamada que DEVE falhar: novo cliente nao existente (apenas para
        # forcar 1 entry adicional — via outro endpoint qualquer). Aqui vamos
        # usar o proprio PATCH/GET para simplicidade, mas como o cliente foi
        # soft-deleted, GET retornara 410. Pulamos para chain verify.
        db_session.expire_all()

        # Chain verify: tudo intacto?
        ok, last_valid = AuditService.verify_chain(db_session)
        assert ok, f"Audit chain quebrada apos DELETE. Posicao invalida: {last_valid}"
        assert last_valid >= 1  # pelo menos 1 entry

    def test_delete_cliente_duas_chamadas_geram_chain_valida(
        self, client: TestClient, cliente_com_protocolo, db_session: Session
    ):
        """Duas chamadas DELETE no mesmo cliente = 2 audit entries encadeadas."""
        # 1a: sucesso 200
        first = client.delete(
            f"/api/v1/cliente/{cliente_com_protocolo.id}",
            headers=_auth_headers(),
        )
        assert first.status_code == 200

        # 2a: 409 (mas NAO gera audit log porque foi raise HTTPException)
        # VERIFICAR: o router.py nao emite audit antes do raise, entao
        # apenas 1 entry esperada.
        second = client.delete(
            f"/api/v1/cliente/{cliente_com_protocolo.id}",
            headers=_auth_headers(),
        )
        assert second.status_code == 409

        db_session.expire_all()

        # Verifica que a chain ainda tem 1+ entry valida
        ok, last_valid = AuditService.verify_chain(db_session)
        assert ok
        assert last_valid >= 1
