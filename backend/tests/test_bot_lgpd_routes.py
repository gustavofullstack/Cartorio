"""test_bot_lgpd_routes.py — HTTP route tests for /api/v1/bot/* LGPD endpoints.

Covers:
- POST /api/v1/bot/lgpd/cancelar
- POST /api/v1/bot/lgpd/export
- POST /api/v1/bot/lgpd/access
- POST /api/v1/bot/lgpd/restaurar
- GET  /api/v1/bot/lgpd/revogacoes
- POST /api/v1/bot/lgpd/revogacoes/{id}/delete

Uses shared fixtures from test_lgpd_bot_whatsapp.py:
- client_with_db: TestClient with isolated sqlite in-memory DB
- db_session: standalone sqlite Session for service-level seeding
"""

from __future__ import annotations

from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.services.lgpd.bot_direito_esquecimento import (
    REVOGACAO_TTL_DIAS,
    RevogacaoStatus,
)


# ============================================================================
# Fixtures
#
# Two flavors:
# - client_with_db : standalone TestClient (no shared seed) — used by tests
#   that only exercise validation paths (404, 422, no cliente_id).
# - client_with_db_and_session : shared in-memory DB so seeded rows are
#   visible to both the API endpoint AND the test's helper session.
# ============================================================================


def _make_engine() -> object:
    from app.models.base import Base  # noqa: F401

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def client_with_db() -> Iterator[TestClient]:
    """TestClient com DB sqlite in-memory isolado (sem seed compartilhado)."""
    eng = _make_engine()
    S = sessionmaker(bind=eng, autoflush=False, autocommit=False)

    def _override_db():
        db = S()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client_with_db_and_session() -> Iterator[tuple[TestClient, Session]]:
    """TestClient + Session compartilhando o MESMO engine in-memory.

    Permite que testes seedem dados via db_session e depois batam na rota
    HTTP via TestClient — ambos enxergam os mesmos rows.
    """
    eng = _make_engine()
    S = sessionmaker(bind=eng, autoflush=False, autocommit=False)

    def _override_db():
        db = S()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    seed_db = S()
    try:
        yield TestClient(app), seed_db
    finally:
        seed_db.close()
        app.dependency_overrides.pop(get_db, None)


def _seed_revogacao(
    db: Session,
    *,
    revogacao_id: str,
    cliente_id: int | None,
    channel: str = "whatsapp",
    status: str = RevogacaoStatus.PENDING.value,
) -> None:
    """Helper: insere revogacao pendente via SQL direto (mesma tabela do servico)."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import text

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS lgpd_revogacoes_bot (
                id TEXT PRIMARY KEY,
                cliente_id INTEGER,
                sender_hash TEXT NOT NULL,
                channel TEXT NOT NULL,
                motivo TEXT NOT NULL,
                requested_at TIMESTAMP NOT NULL,
                scheduled_delete_at TIMESTAMP NOT NULL,
                deleted_at TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'pending',
                restored_at TIMESTAMP,
                audit_id TEXT
            )
            """
        )
    )
    now = datetime.now(timezone.utc)
    db.execute(
        text(
            """
            INSERT INTO lgpd_revogacoes_bot
                (id, cliente_id, sender_hash, channel, motivo,
                 requested_at, scheduled_delete_at, status)
            VALUES
                (:id, :cid, :sh, :ch, :m, :req, :sched, :st)
            """
        ),
        {
            "id": revogacao_id,
            "cid": cliente_id,
            "sh": "fakehash" + revogacao_id[:8],
            "ch": channel,
            "m": "revogacao_consentimento",
            "req": now,
            "sched": now + timedelta(days=REVOGACAO_TTL_DIAS),
            "st": status,
        },
    )
    db.commit()


# ============================================================================
# POST /api/v1/bot/lgpd/cancelar
# ============================================================================


class TestBotLgpdCancelar:
    def test_happy_path_registers_revogacao(self, client_with_db: TestClient) -> None:
        """POST /cancelar retorna 200 + revogacao_id + janela_dias=30."""
        resp = client_with_db.post(
            "/api/v1/bot/lgpd/cancelar",
            json={
                "channel": "whatsapp",
                "sender_id": "5511999999999@s.whatsapp.net",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "ok"
        assert body["revogacao_id"]
        assert len(body["revogacao_id"]) >= 8
        assert body["janela_dias"] == 30
        assert body["scheduled_delete_at"]
        assert (
            "LGPD" in body["message"]
            or "DPO" in body["message"]
            or "dpo@" in body["message"].lower()
        )

    def test_422_missing_channel(self, client_with_db: TestClient) -> None:
        """Sem channel → 422 Pydantic ValidationError."""
        resp = client_with_db.post(
            "/api/v1/bot/lgpd/cancelar",
            json={"sender_id": "5511999999999"},
        )
        assert resp.status_code == 422

    def test_invalid_channel_literal_422(self, client_with_db: TestClient) -> None:
        """Channel 'sms' (não-whatsapp/telegram) → 422 Pydantic Literal."""
        resp = client_with_db.post(
            "/api/v1/bot/lgpd/cancelar",
            json={"channel": "sms", "sender_id": "5511999999999"},
        )
        assert resp.status_code == 422

    def test_telegram_channel_accepted(self, client_with_db: TestClient) -> None:
        """Channel 'telegram' também é aceito (não só whatsapp)."""
        resp = client_with_db.post(
            "/api/v1/bot/lgpd/cancelar",
            json={"channel": "telegram", "sender_id": "123456789"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["revogacao_id"]


# ============================================================================
# POST /api/v1/bot/lgpd/export
# ============================================================================


class TestBotLgpdExport:
    def test_422_missing_cliente_id(self, client_with_db: TestClient) -> None:
        """Sem cliente_id → 422 CLIENTE_ID_REQUIRED."""
        resp = client_with_db.post(
            "/api/v1/bot/lgpd/export",
            json={"channel": "whatsapp", "sender_id": "5511999999999"},
        )
        assert resp.status_code == 422
        body = resp.json()
        # FastAPI wraps the HTTPException detail
        assert "CLIENTE_ID_REQUIRED" in str(body)

    def test_404_cliente_inexistente(self, client_with_db: TestClient) -> None:
        """cliente_id que não existe → 404 CLIENTE_NOT_FOUND."""
        resp = client_with_db.post(
            "/api/v1/bot/lgpd/export",
            json={
                "channel": "whatsapp",
                "sender_id": "5511999999999",
                "cliente_id": 99999,
            },
        )
        assert resp.status_code == 404
        body = resp.json()
        assert "CLIENTE_NOT_FOUND" in str(body)

    def test_200_with_seeded_cliente(
        self, client_with_db_and_session: tuple[TestClient, Session]
    ) -> None:
        """Cliente seedado + cliente_id válido → 200 com filename + sha256."""
        from app.models.cliente import Cliente

        client, db = client_with_db_and_session
        c = Cliente(
            nome="Joao da Silva",
            cpf_hash="h" * 64,
            email="joao@example.com",
            consentimento_lgpd=True,
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        resp = client.post(
            "/api/v1/bot/lgpd/export",
            json={
                "channel": "whatsapp",
                "sender_id": "5511999999999",
                "cliente_id": c.id,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["filename"].endswith(".json")
        assert len(body["sha256"]) == 64
        assert body["size_bytes"] > 100
        assert body["data"]["cliente"]["cpf_hash"] == "h" * 64


# ============================================================================
# POST /api/v1/bot/lgpd/access
# ============================================================================


class TestBotLgpdAccess:
    def test_200_no_cliente_id_returns_dpo_message(self, client_with_db: TestClient) -> None:
        """Sem cliente_id → 200 com mensagem DPO orientando contato."""
        resp = client_with_db.post(
            "/api/v1/bot/lgpd/access",
            json={"channel": "whatsapp", "sender_id": "5511999999999"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["cliente_id"] is None
        assert body["cpf_hash"] is None
        assert "dpo@" in body["message"].lower() or "DPO" in body["message"]

    def test_404_cliente_inexistente(self, client_with_db: TestClient) -> None:
        """cliente_id inválido → 404."""
        resp = client_with_db.post(
            "/api/v1/bot/lgpd/access",
            json={
                "channel": "whatsapp",
                "sender_id": "5511999999999",
                "cliente_id": 99999,
            },
        )
        assert resp.status_code == 404

    def test_200_with_seeded_cliente_returns_cpf_hash(
        self, client_with_db_and_session: tuple[TestClient, Session]
    ) -> None:
        """Cliente seedado → 200 com cpf_hash (LGPD-safe, NÃO raw CPF)."""
        from app.models.cliente import Cliente

        client, db = client_with_db_and_session
        c = Cliente(
            nome="Maria Souza",
            cpf_hash="a" * 64,
            email="maria@example.com",
            consentimento_lgpd=True,
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        resp = client.post(
            "/api/v1/bot/lgpd/access",
            json={
                "channel": "whatsapp",
                "sender_id": "5511999999999",
                "cliente_id": c.id,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["cliente_id"] == c.id
        assert body["cpf_hash"] == "a" * 64
        assert body["consentimento_lgpd"] is True


# ============================================================================
# POST /api/v1/bot/lgpd/restaurar
# ============================================================================


class TestBotLgpdRestaurar:
    def test_200_with_active_revogacao(
        self, client_with_db_and_session: tuple[TestClient, Session]
    ) -> None:
        """Revogação pending seedada → 200 com status='ok'."""
        client, db = client_with_db_and_session
        rev_id = "test-rev-00000001"
        _seed_revogacao(db, revogacao_id=rev_id, cliente_id=None)

        resp = client.post(
            "/api/v1/bot/lgpd/restaurar",
            json={"revogacao_id": rev_id},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["revogacao_id"] == rev_id

    def test_not_found_for_unknown_revogacao(self, client_with_db: TestClient) -> None:
        """Revogação inexistente → 200 com status='not_found' (idempotente)."""
        resp = client_with_db.post(
            "/api/v1/bot/lgpd/restaurar",
            json={"revogacao_id": "bogus-rev-id-12345678"},
        )
        # Endpoint retorna 200 + not_found (não 404) — comportamento idempotente
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "not_found"

    def test_422_missing_revogacao_id(self, client_with_db: TestClient) -> None:
        """Sem revogacao_id → 422."""
        resp = client_with_db.post("/api/v1/bot/lgpd/restaurar", json={})
        assert resp.status_code == 422


# ============================================================================
# GET /api/v1/bot/lgpd/revogacoes
# ============================================================================


class TestBotLgpdRevogacoes:
    def test_200_empty_list(self, client_with_db: TestClient) -> None:
        """Sem revogações pendentes → 200 com count=0."""
        resp = client_with_db.get("/api/v1/bot/lgpd/revogacoes", headers={"X-API-Key": "a" * 64})
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["revogacoes"] == []

    def test_200_with_seeded_revogacoes(
        self, client_with_db_and_session: tuple[TestClient, Session]
    ) -> None:
        """Revogações seedadas (scheduled no passado) → listadas como pendentes."""
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import text

        client, db = client_with_db_and_session
        # Cria a tabela (idempotente)
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS lgpd_revogacoes_bot (
                    id TEXT PRIMARY KEY,
                    cliente_id INTEGER,
                    sender_hash TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    motivo TEXT NOT NULL,
                    requested_at TIMESTAMP NOT NULL,
                    scheduled_delete_at TIMESTAMP NOT NULL,
                    deleted_at TIMESTAMP,
                    status TEXT NOT NULL DEFAULT 'pending',
                    restored_at TIMESTAMP,
                    audit_id TEXT
                )
                """
            )
        )
        past = datetime.now(timezone.utc) - timedelta(days=1)
        for i in range(2):
            db.execute(
                text(
                    """
                    INSERT INTO lgpd_revogacoes_bot
                        (id, cliente_id, sender_hash, channel, motivo,
                         requested_at, scheduled_delete_at, status)
                    VALUES
                        (:id, :cid, :sh, :ch, :m, :req, :sched, :st)
                    """
                ),
                {
                    "id": f"past-rev-{i}",
                    "cid": None,
                    "sh": f"hash{i}",
                    "ch": "whatsapp",
                    "m": "revogacao_consentimento",
                    "req": past,
                    "sched": past,
                    "st": "pending",
                },
            )
        db.commit()

        resp = client.get("/api/v1/bot/lgpd/revogacoes", headers={"X-API-Key": "a" * 64})
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] >= 2
        ids = {r["id"] for r in body["revogacoes"]}
        assert "past-rev-0" in ids
        assert "past-rev-1" in ids


# ============================================================================
# POST /api/v1/bot/lgpd/revogacoes/{id}/delete
# ============================================================================


class TestBotLgpdMarcarDeletado:
    def test_200_idempotent_on_already_deleted(
        self, client_with_db_and_session: tuple[TestClient, Session]
    ) -> None:
        """Marcar deletada uma já-deletada é idempotente (not_found na segunda)."""
        client, db = client_with_db_and_session
        rev_id = "del-rev-00000001"
        _seed_revogacao(db, revogacao_id=rev_id, cliente_id=None)

        # Primeira chamada: pending → deleted (sucesso)
        resp1 = client.post(
            f"/api/v1/bot/lgpd/revogacoes/{rev_id}/delete", headers={"X-API-Key": "a" * 64}
        )
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "ok"

        # Segunda chamada: já está deleted → not_found (idempotente)
        resp2 = client.post(
            f"/api/v1/bot/lgpd/revogacoes/{rev_id}/delete", headers={"X-API-Key": "a" * 64}
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "not_found"

    def test_200_bogus_id_returns_not_found(self, client_with_db: TestClient) -> None:
        """ID inexistente → 200 com status='not_found' (não 404 hard)."""
        resp = client_with_db.post(
            "/api/v1/bot/lgpd/revogacoes/bogus-id-zzz/delete", headers={"X-API-Key": "a" * 64}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "not_found"
        assert body["revogacao_id"] == "bogus-id-zzz"
