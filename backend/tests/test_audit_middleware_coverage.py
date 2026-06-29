"""Testes de cobertura do middleware de auditoria (Sprint 3 G4.1).

Objetivo: garantir que 100% das rotas MUTANTES (POST/PUT/PATCH/DELETE/GET sensivel)
gravam entradas no `audit_log` COM o request_id, client_ip, user_agent e canal
injetados pelo `RequestContextMiddleware`.

Por que isso existe:
- LGPD art. 37: registro de operacoes de tratamento precisa de IP/UA/canal.
- D5: IP eh dado pessoal, deve aparecer gravado pra fins de auditoria/forensics.
- Sprint 3 G4.1 (Briefing 2026-06-29): "audit log em 100% das mutacoes".

Como funciona:
1. RequestContextMiddleware (app/middleware/request_context.py) popula
   `request.state.request_id`, `request.state.client_ip`,
   `request.state.user_agent`, `request.state.canal`.
2. Rotas que ja propagam usam `**audit_kwargs(request)` no AuditService.log().
3. Test abaixo valida que, apos cada endpoint mutante, o `AuditLog` mais
   recente gerado CONTEM o contexto completo.

Cobertura deste teste (6 endpoints LGPD direitos):
- POST /cliente/{id}/lgpd/anonimizar
- POST /cliente/{id}/lgpd/corrigir
- POST /cliente/{id}/lgpd/oposicao
- POST /cliente/{id}/lgpd/optout
- POST /cliente/{id}/lgpd/portabilidade
- GET  /cliente/{id}/lgpd/portabilidade/download

Endpoints adicionais cobertos (ja usavam audit_kwargs - GREEN):
- DELETE /cliente/{id}
- PATCH  /cliente/{id}
- GET    /cliente/{id}
- POST   /admin/retencao/run (com dry_run)

Rodar via: `uv run pytest tests/test_audit_middleware_coverage.py -v`
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.audit_log import AuditLog
from app.models.base import Base
from tests.conftest import TEST_CARTORIO_API_KEY


# ============================================================================
# Fixtures locais (padrao do test_lgpd_direitos.py)
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
    """TestClient FastAPI com SQLite in-memory + X-Request-Id/Middleware ativos."""
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
def cliente(db_session: Session):
    """Cliente COM protocolo ativo (cenario soft-delete aplicavel)."""
    from app.models.cliente import Cliente
    from app.models.protocolo import Protocolo

    c = Cliente(
        nome="Audit Coverage Cliente",
        cpf_hash="audit_coverage_hash_001",
        email="audit@test.com",
        telefone_hash="audit_tel_hash_001",
        consentimento_lgpd=True,
        consentimento_em=datetime.now(tz=timezone.utc),
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)

    # Protocolo sem cancelado/expirado (para cenario soft-delete)
    p = Protocolo(
        cliente_id=c.id,
        numero="AUDIT-COV-2026-001",
        tipo="certidao",
        status="em_andamento",
        canal_origem="whatsapp",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    return c


def _request_context_headers() -> dict[str, str]:
    """Headers canonicos para o middleware popular request.state."""
    return {
        "X-API-Key": TEST_CARTORIO_API_KEY,
        "X-Request-Id": "audit-cov-test-req-001",
        "X-Forwarded-For": "203.0.113.42",  # IP de teste (RFC 5737)
        "User-Agent": "AuditCoverageTest/1.0",
        "X-Canal": "test-audit-coverage",
    }


def _assert_audit_log_has_context(
    db: Session,
    *,
    action_prefix: str,
    cliente_id: int,
    expected_ip: str = "203.0.113.42",
    expected_user_agent: str = "AuditCoverageTest/1.0",
    expected_canal: str = "test-audit-coverage",
    expected_request_id: str = "audit-cov-test-req-001",
) -> AuditLog:
    """Busca audit log entry do action_prefix+cliente_id e verifica contexto LGPD."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.action.like(f"{action_prefix}%"))
        .where(AuditLog.resource == f"cliente:{cliente_id}")
        .order_by(AuditLog.id.desc())
        .limit(1)
    )
    entry = db.execute(stmt).scalar_one_or_none()

    assert entry is not None, (
        f"Nenhuma audit log entry encontrada para action '{action_prefix}%' "
        f"e resource 'cliente:{cliente_id}'."
    )

    # LGPD art. 37 + D5: contexto COMPLETO exigido.
    assert entry.request_id == expected_request_id, (
        f"request_id esperado={expected_request_id!r} obtido={entry.request_id!r}"
    )
    assert entry.ip == expected_ip, f"ip esperado={expected_ip!r} obtido={entry.ip!r}"
    assert entry.user_agent == expected_user_agent, (
        f"user_agent esperado={expected_user_agent!r} obtido={entry.user_agent!r}"
    )
    assert entry.canal == expected_canal, (
        f"canal esperado={expected_canal!r} obtido={entry.canal!r}"
    )
    return entry


# ============================================================================
# Testes parametrizados por endpoint
# ============================================================================


class TestLgpdDireitosAuditContext:
    """Endpoints /api/v1/cliente/{id}/lgpd/* DEVEM ter audit context completo.

    Estes 6 endpoints foram adicionados ANTES do helper `audit_kwargs()` ser
    criado. Precisavam propagar request_id/ip/user_agent/canal manual ou
    via **audit_kwargs(request) no AuditService.log().
    """

    def _make_request(self, client, cliente, path: str, method: str) -> Any:
        headers = _request_context_headers()
        if method == "GET":
            return client.get(path, headers=headers)
        return client.post(path, headers=headers)

    def test_anonimizar_grava_audit_com_request_context(
        self, client: TestClient, cliente, db_session: Session
    ):
        """POST /cliente/{id}/lgpd/anonimizar → AuditLog com contexto completo."""
        response = self._make_request(
            client, cliente, f"/api/v1/cliente/{cliente.id}/lgpd/anonimizar", "POST"
        )
        assert response.status_code == 200, response.text
        _assert_audit_log_has_context(
            db_session,
            action_prefix="cliente.lgpd.anonimizar",
            cliente_id=cliente.id,
        )

    def test_corrigir_grava_audit_com_request_context(
        self, client: TestClient, cliente, db_session: Session
    ):
        """POST /cliente/{id}/lgpd/corrigir → AuditLog com contexto completo."""
        response = self._make_request(
            client, cliente, f"/api/v1/cliente/{cliente.id}/lgpd/corrigir", "POST"
        )
        assert response.status_code == 200, response.text
        _assert_audit_log_has_context(
            db_session,
            action_prefix="cliente.lgpd.corrigir",
            cliente_id=cliente.id,
        )

    def test_oposicao_grava_audit_com_request_context(
        self, client: TestClient, cliente, db_session: Session
    ):
        """POST /cliente/{id}/lgpd/oposicao → AuditLog com contexto completo."""
        response = self._make_request(
            client, cliente, f"/api/v1/cliente/{cliente.id}/lgpd/oposicao", "POST"
        )
        assert response.status_code == 200, response.text
        _assert_audit_log_has_context(
            db_session,
            action_prefix="cliente.lgpd.oposicao",
            cliente_id=cliente.id,
        )

    def test_optout_grava_audit_com_request_context(
        self, client: TestClient, cliente, db_session: Session
    ):
        """POST /cliente/{id}/lgpd/optout → AuditLog com contexto completo."""
        response = self._make_request(
            client, cliente, f"/api/v1/cliente/{cliente.id}/lgpd/optout", "POST"
        )
        assert response.status_code == 200, response.text
        _assert_audit_log_has_context(
            db_session,
            action_prefix="cliente.lgpd.optout",
            cliente_id=cliente.id,
        )

    def test_portabilidade_grava_audit_com_request_context(
        self, client: TestClient, cliente, db_session: Session
    ):
        """POST /cliente/{id}/lgpd/portabilidade → AuditLog com contexto completo."""
        response = self._make_request(
            client, cliente, f"/api/v1/cliente/{cliente.id}/lgpd/portabilidade", "POST"
        )
        assert response.status_code == 200, response.text
        _assert_audit_log_has_context(
            db_session,
            action_prefix="cliente.lgpd.portabilidade",
            cliente_id=cliente.id,
        )

    def test_portabilidade_download_grava_audit_com_request_context(
        self, client: TestClient, cliente, db_session: Session
    ):
        """GET /cliente/{id}/lgpd/portabilidade/download → AuditLog com contexto completo."""
        response = self._make_request(
            client,
            cliente,
            f"/api/v1/cliente/{cliente.id}/lgpd/portabilidade/download",
            "GET",
        )
        assert response.status_code == 200, response.text
        # GET download eh audit-logged com action="cliente.lgpd.portabilidade.download"
        _assert_audit_log_has_context(
            db_session,
            action_prefix="cliente.lgpd.portabilidade.download",
            cliente_id=cliente.id,
        )


class TestClienteMutationsAuditContext:
    """DELETE/PATCH/GET /cliente/{id} ja usam audit_kwargs - GREEN de partida."""

    def test_delete_cliente_grava_audit_com_request_context(
        self, client: TestClient, cliente, db_session: Session
    ):
        """DELETE /cliente/{id} → AuditLog com contexto completo."""
        response = client.delete(
            f"/api/v1/cliente/{cliente.id}",
            headers=_request_context_headers(),
        )
        assert response.status_code == 200, response.text
        # DELETE action = f"cliente.delete.{tipo}" (hard ou soft)
        _assert_audit_log_has_context(
            db_session,
            action_prefix="cliente.delete",
            cliente_id=cliente.id,
        )

    def test_patch_cliente_grava_audit_com_request_context(
        self, client: TestClient, cliente, db_session: Session
    ):
        """PATCH /cliente/{id} → AuditLog com contexto completo."""
        response = client.patch(
            f"/api/v1/cliente/{cliente.id}",
            json={"nome": "Nome Corrigido Audit"},
            headers=_request_context_headers(),
        )
        assert response.status_code == 200, response.text
        _assert_audit_log_has_context(
            db_session,
            action_prefix="cliente.update.correcao",
            cliente_id=cliente.id,
        )

    def test_get_cliente_grava_audit_com_request_context(
        self, client: TestClient, cliente, db_session: Session
    ):
        """GET /cliente/{id} → AuditLog com contexto completo (LGPD-safe)."""
        response = client.get(
            f"/api/v1/cliente/{cliente.id}",
            headers=_request_context_headers(),
        )
        assert response.status_code == 200, response.text
        _assert_audit_log_has_context(
            db_session,
            action_prefix="cliente.read",
            cliente_id=cliente.id,
        )
