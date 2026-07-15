"""Testes do LGPD DPO Dashboard endpoints (D25).

Cobre os 3 endpoints administrativos:
- /api/v1/lgpd/dpo/metrics — KPIs agregados
- /api/v1/lgpd/dpo/audit-trail/{cliente_id} — historico
- /api/v1/lgpd/dpo/retention-queue — itens elegiveis

Auth dupla: X-API-Key + JWT Bearer com claim dpo=True.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.audit_log import AuditLog
from app.models.cliente import Cliente

client = TestClient(app)

AUTH_HEADERS_BASE = {"X-API-Key": "a" * 64}


def _dpo_jwt() -> str:
    """Emite JWT access token com claim dpo=True."""
    from app.services.auth_jwt import issue_access_token

    return issue_access_token(str(uuid.uuid4()), dpo=True)


def _non_dpo_jwt() -> str:
    """Emite JWT sem claim dpo (deve falhar com 403)."""
    from app.services.auth_jwt import issue_access_token

    return issue_access_token(str(uuid.uuid4()), dpo=False)


def _auth_headers_dpo() -> dict[str, str]:
    return {**AUTH_HEADERS_BASE, "Authorization": f"Bearer {_dpo_jwt()}"}


@pytest.fixture
def db_setup():
    """Cria alguns clientes + audit entries."""
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        # Cliente 1: ativo
        c1 = Cliente(
            nome="Cliente Ativo",
            cpf_hash="hash_c1",
            email="c1@x.com",
            consentimento_lgpd=True,
        )
        # Cliente 2: ativo (com old created_at para teste de retencao)
        c2 = Cliente(
            nome="Cliente Antigo",
            cpf_hash="hash_c2_old",
            email="c2@x.com",
            consentimento_lgpd=True,
        )
        c2.created_at = datetime.now(tz=timezone.utc) - timedelta(days=365 * 7)  # 7y atras
        session.add(c1)
        session.add(c2)
        session.commit()
        session.refresh(c1)
        session.refresh(c2)

        # Audit entry do c1
        AuditService_module = __import__(
            "app.services.audit", fromlist=["AuditService"]
        ).AuditService
        AuditService_module.log(
            session,
            actor_id=str(c1.id),
            actor_type="cliente",
            action="cliente.created.lgpd_blocked",
            resource=f"cliente:{c1.id}",
            payload={"hello": "world"},
        )

        yield {"cliente_ativo_id": c1.id, "cliente_antigo_id": c2.id}
    finally:
        session.close()


class TestLGPDDpoMetricsEndpoint:
    """D25 — /api/v1/lgpd/dpo/metrics."""

    def test_metrics_401_sem_x_api_key(self) -> None:
        """Sem X-API-Key -> 401."""
        resp = client.get("/api/v1/lgpd/dpo/metrics")
        assert resp.status_code == 401

    def test_metrics_401_sem_jwt(self) -> None:
        """X-API-Key OK mas sem JWT -> 401 (require_dpo_role)."""
        resp = client.get("/api/v1/lgpd/dpo/metrics", headers=AUTH_HEADERS_BASE)
        assert resp.status_code == 401

    def test_metrics_403_sem_claim_dpo(self) -> None:
        """JWT sem claim dpo -> 403 (DP0 nao eh DPO)."""
        headers = {**AUTH_HEADERS_BASE, "Authorization": f"Bearer {_non_dpo_jwt()}"}
        resp = client.get("/api/v1/lgpd/dpo/metrics", headers=headers)
        assert resp.status_code == 403

    def test_metrics_200_com_dpo_jwt(self, db_setup) -> None:
        """Com X-API-Key + JWT DPO -> 200 com KPIs."""
        resp = client.get("/api/v1/lgpd/dpo/metrics", headers=_auth_headers_dpo())
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # Estrutura esperada
        assert "gerado_em" in body
        assert "clientes" in body
        assert "conversas" in body
        assert "audit" in body
        assert "rights_art_18_exercidos_30d" in body
        assert "retention_queue_size" in body
        assert "retention_policy" in body

        # Clientes inclui ativos + anonimizados
        clientes = body["clientes"]
        assert clientes["total"] == 2
        assert clientes["ativos"] == 2
        assert clientes["anonimizados"] == 0

    def test_metrics_inclui_audit_chain_info(self, db_setup) -> None:
        """Metrics inclui audit chain_ok + chain_length."""
        resp = client.get("/api/v1/lgpd/dpo/metrics", headers=_auth_headers_dpo())
        assert resp.status_code == 200
        audit = resp.json()["audit"]
        assert "chain_ok" in audit
        assert "chain_length" in audit
        assert "last_entry" in audit
        assert audit["chain_length"] >= 1

    def test_metrics_inclui_last_entry(self, db_setup) -> None:
        """last_entry tem id, action, actor_id, timestamp."""
        resp = client.get("/api/v1/lgpd/dpo/metrics", headers=_auth_headers_dpo())
        body = resp.json()
        last = body["audit"]["last_entry"]
        assert last is not None
        assert "id" in last
        assert "action" in last
        assert "actor_id" in last


class TestLGPDDpoAuditTrailEndpoint:
    """D25 — /api/v1/lgpd/dpo/audit-trail/{cliente_id}."""

    def test_audit_trail_401_sem_x_api_key(self) -> None:
        """Sem X-API-Key -> 401."""
        resp = client.get("/api/v1/lgpd/dpo/audit-trail/1")
        assert resp.status_code == 401

    def test_audit_trail_403_sem_dpo(self) -> None:
        """JWT sem dpo=True -> 403."""
        headers = {**AUTH_HEADERS_BASE, "Authorization": f"Bearer {_non_dpo_jwt()}"}
        resp = client.get("/api/v1/lgpd/dpo/audit-trail/1", headers=headers)
        assert resp.status_code == 403

    def test_audit_trail_404_cliente_inexistente(self) -> None:
        """Cliente 99999 nao existe -> 404."""
        resp = client.get(
            "/api/v1/lgpd/dpo/audit-trail/99999",
            headers=_auth_headers_dpo(),
        )
        assert resp.status_code == 404

    def test_audit_trail_retorna_entries(self, db_setup) -> None:
        """Audit trail retorna entries do cliente ativo."""
        cid = db_setup["cliente_ativo_id"]
        resp = client.get(
            f"/api/v1/lgpd/dpo/audit-trail/{cid}",
            headers=_auth_headers_dpo(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["cliente_id"] == cid
        assert body["total_entries"] >= 1
        assert body["returned"] >= 1
        assert "audit_trail" in body
        first_entry = body["audit_trail"][0]
        assert "id" in first_entry
        assert "action" in first_entry
        assert "timestamp" in first_entry
        assert "ip_truncated" in first_entry
        assert "hash" in first_entry
        assert "lgpd_relevant" in first_entry

    def test_audit_trail_lgpd_relevante_marcado(self, db_setup) -> None:
        """Entries com action=lgpd.* sao marcadas como lgpd_relevant=True."""
        from app.db import SessionLocal
        from app.services.audit import AuditService

        session = SessionLocal()
        cid = db_setup["cliente_ativo_id"]
        # Cria entry LGPD
        AuditService.log(
            session,
            actor_id=str(cid),
            actor_type="cliente",
            action="lgpd.consent.granted",
            resource=f"cliente/{cid}",
            payload={"finalidades": ["marketing"]},
        )
        session.commit()
        session.close()

        resp = client.get(
            f"/api/v1/lgpd/dpo/audit-trail/{cid}",
            headers=_auth_headers_dpo(),
        )
        body = resp.json()
        # Procura entry com lgpd_relevant=True
        lgpd_entries = [e for e in body["audit_trail"] if e.get("lgpd_relevant")]
        assert len(lgpd_entries) >= 1
        assert any(e["action"] == "lgpd.consent.granted" for e in lgpd_entries)

    def test_audit_trail_paginacao(self, db_setup) -> None:
        """Query params limit + offset funcionam."""
        cid = db_setup["cliente_ativo_id"]
        resp = client.get(
            f"/api/v1/lgpd/dpo/audit-trail/{cid}?limit=5&offset=0",
            headers=_auth_headers_dpo(),
        )
        body = resp.json()
        assert body["limit"] == 5
        assert body["offset"] == 0

    def test_audit_trail_nao_expoe_pii_raw(self, db_setup) -> None:
        """Audit trail NAO expoe IP completo (apenas truncated)."""
        cid = db_setup["cliente_ativo_id"]
        resp = client.get(
            f"/api/v1/lgpd/dpo/audit-trail/{cid}",
            headers=_auth_headers_dpo(),
        )
        body = resp.json()
        for entry in body["audit_trail"]:
            # LGPD-by-design: ip_truncated only
            assert "ip" not in entry
            # Apenas ip_truncated
            assert (
                entry.get("ip_truncated") is None
                or "/" in entry.get("ip_truncated", "")
                or entry.get("ip_truncated") == "[anonimizado]"
            )


class TestLGPDDpoRetentionQueueEndpoint:
    """D25 — /api/v1/lgpd/dpo/retention-queue."""

    def test_retention_queue_401(self) -> None:
        """Sem X-API-Key -> 401."""
        resp = client.get("/api/v1/lgpd/dpo/retention-queue")
        assert resp.status_code == 401

    def test_retention_queue_403_sem_dpo(self) -> None:
        """JWT sem dpo -> 403."""
        headers = {**AUTH_HEADERS_BASE, "Authorization": f"Bearer {_non_dpo_jwt()}"}
        resp = client.get("/api/v1/lgpd/dpo/retention-queue", headers=headers)
        assert resp.status_code == 403

    def test_retention_queue_200(self, db_setup) -> None:
        """Retorna lista de clientes elegiveis."""
        resp = client.get(
            "/api/v1/lgpd/dpo/retention-queue",
            headers=_auth_headers_dpo(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "gerado_em" in body
        assert "policy" in body
        assert "items" in body
        assert "total_items" in body
        # base_legal deve referenciar CNJ 74/2018
        assert "CNJ 74/2018" in body["policy"]["base_legal"]

    def test_retention_queue_item_mascarado(self, db_setup) -> None:
        """Items tem IDs mascarados (LGPD-by-design)."""
        resp = client.get(
            "/api/v1/lgpd/dpo/retention-queue",
            headers=_auth_headers_dpo(),
        )
        body = resp.json()
        if body["items"]:
            first = body["items"][0]
            # cliente_id_mascarado formato C0001
            assert first["cliente_id_mascarado"].startswith("C")
            assert first["cliente_id_mascarado"][1:].isdigit()
            # cpf_hash truncado
            cpf_hash_masked = first.get("cpf_hash_mascarado")
            assert cpf_hash_masked is None or "..." in cpf_hash_masked
            # dias_inativo >= 1825 (>5y)
            assert first.get("dias_inativo") is None or first["dias_inativo"] >= 1825

    def test_retention_queue_nao_expoe_nome_completo(self, db_setup) -> None:
        """Items NAO expoe nome completo do cliente."""
        resp = client.get(
            "/api/v1/lgpd/dpo/retention-queue",
            headers=_auth_headers_dpo(),
        )
        body = resp.json()
        for item in body["items"]:
            assert "nome" not in item
            assert "email" not in item
            assert "cpf" not in item  # so cpf_hash_mascarado

    def test_retention_queue_limit_query_param(self, db_setup) -> None:
        """Query param limit customizado."""
        resp = client.get(
            "/api/v1/lgpd/dpo/retention-queue?limit=5",
            headers=_auth_headers_dpo(),
        )
        body = resp.json()
        assert body["limit"] == 5


# ============================================================================
# Sanidade LGPD-by-design
# ============================================================================


class TestLGPDDpoDashboardLGPD:
    """LGPD-by-design: mascaramento + audit chain preservado."""

    def test_dashboard_gera_audit_log(self, db_setup) -> None:
        """Cada acesso ao dashboard gera audit entry (LGPD art. 37)."""
        from app.db import SessionLocal

        session = SessionLocal()
        try:
            count_before = (
                session.query(AuditLog).filter(AuditLog.action.like("lgpd.dpo.%")).count()
            )

            client.get("/api/v1/lgpd/dpo/metrics", headers=_auth_headers_dpo())
            client.get(
                "/api/v1/lgpd/dpo/retention-queue",
                headers=_auth_headers_dpo(),
            )

            count_after = session.query(AuditLog).filter(AuditLog.action.like("lgpd.dpo.%")).count()
            # Pelo menos 2 novas audit entries (metrics + retention)
            assert count_after >= count_before + 2
        finally:
            session.close()

    def test_double_auth_exigido(self) -> None:
        """Endpoints DPO exigem JWT com claim dpo=True + X-API-Key."""
        # Sem X-API-Key -> 401
        assert client.get("/api/v1/lgpd/dpo/metrics").status_code == 401
        # Sem JWT -> 401
        assert client.get("/api/v1/lgpd/dpo/metrics", headers=AUTH_HEADERS_BASE).status_code == 401
        # JWT sem DPO -> 403
        bad_headers = {
            **AUTH_HEADERS_BASE,
            "Authorization": f"Bearer {_non_dpo_jwt()}",
        }
        assert client.get("/api/v1/lgpd/dpo/metrics", headers=bad_headers).status_code == 403
