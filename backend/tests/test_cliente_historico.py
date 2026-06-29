"""Testes do endpoint GET /api/v1/cliente/{id}/historico."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from contextlib import contextmanager
    from app.models.base import Base
    import app.models  # noqa: F401
    import app.models.audit_log  # noqa: F401
    import app.models.atendimento  # noqa: F401
    import app.models.cliente  # noqa: F401
    import app.models.conversa  # noqa: F401
    import app.models.documento  # noqa: F401
    import app.models.protocolo  # noqa: F401
    import app.models.webhook_event  # noqa: F401

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)

    import app.db
    import app.main as app_main_module

    original_engine = app.db.engine
    original_session_scope = app.db.session_scope
    app.db.engine = test_engine
    app_main_module.engine = test_engine
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    @contextmanager
    def test_session_scope():
        s = TestSessionLocal()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app.db.SessionLocal = TestSessionLocal
    app.db.session_scope = test_session_scope

    the_app = app_main_module.app
    try:
        with TestClient(the_app) as c:
            yield c
    finally:
        app.db.engine = original_engine
        app_main_module.engine = original_engine
        app.db.session_scope = original_session_scope
        Base.metadata.drop_all(test_engine)


AUTH = {"X-API-Key": "a" * 64}


def _make_cliente(db, cpf_hash="h1"):
    from app.models.cliente import Cliente

    c = Cliente(cpf_hash=cpf_hash, nome="Joao da Silva", consentimento_lgpd=True)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c.id


def _make_protocolo(db, cliente_id, numero, status="em_andamento"):
    from app.models.protocolo import Protocolo

    p = Protocolo(
        cliente_id=cliente_id,
        numero=numero,
        tipo="escritura_compra_venda",
        status=status,
        canal_origem="whatsapp",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.id


def _make_atendimento(db, cliente_id, canal="whatsapp"):
    from app.models.atendimento import Atendimento
    from datetime import datetime, timezone

    a = Atendimento(
        cliente_id=cliente_id,
        canal=canal,
        external_id="test-external-id-001",  # NOT NULL no model
        tipo="duvida",  # NOT NULL no model
        status="em_atendimento",
        iniciado_em=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a.id


def test_historico_cliente_vazio(client):
    from app.db import session_scope

    with session_scope() as db:
        cid = _make_cliente(db)

    resp = client.get(f"/api/v1/cliente/{cid}/historico", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["cliente_id"] == cid
    assert body["total_eventos"] == 0


def test_historico_cliente_com_3_protocolos(client):
    from app.db import session_scope

    with session_scope() as db:
        cid = _make_cliente(db)
        _make_protocolo(db, cid, "2026-00001", "concluido")
        _make_protocolo(db, cid, "2026-00002", "em_andamento")
        _make_protocolo(db, cid, "2026-00003", "aberto")

    resp = client.get(f"/api/v1/cliente/{cid}/historico", headers=AUTH)
    body = resp.json()
    assert body["total_eventos"] == 3


def test_historico_cliente_com_protocolos_e_atendimentos(client):
    from app.db import session_scope

    with session_scope() as db:
        cid = _make_cliente(db)
        _make_protocolo(db, cid, "2026-00001")
        _make_atendimento(db, cid, "whatsapp")

    resp = client.get(f"/api/v1/cliente/{cid}/historico", headers=AUTH)
    body = resp.json()
    assert body["total_eventos"] == 2


def test_historico_ordenado_por_timestamp_desc(client):
    from app.db import session_scope
    from app.models.protocolo import Protocolo
    from datetime import datetime, timezone, timedelta

    with session_scope() as db:
        cid = _make_cliente(db)
        for i, days_ago in enumerate([10, 0, 5]):
            p = Protocolo(
                cliente_id=cid,
                numero=f"2026-{i:04d}",
                tipo="escritura_compra_venda",
                status="concluido",
                canal_origem="web",
                created_at=datetime.now(timezone.utc).replace(tzinfo=None)
                - timedelta(days=days_ago),
            )
            db.add(p)
        db.commit()

    resp = client.get(f"/api/v1/cliente/{cid}/historico", headers=AUTH)
    body = resp.json()
    numeros = [item["numero"] for item in body["items"]]
    # Mais recente (days_ago=0) primeiro
    assert numeros[0] == "2026-0001"
    assert numeros[-1] == "2026-0000"


def test_historico_sem_auth_retorna_401(client):
    resp = client.get("/api/v1/cliente/1/historico")
    assert resp.status_code == 401


def test_historico_auth_invalida_retorna_401(client):
    resp = client.get("/api/v1/cliente/1/historico", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_historico_cliente_inexistente_404(client):
    resp = client.get("/api/v1/cliente/99999/historico", headers=AUTH)
    assert resp.status_code == 404


def test_historico_pode_deletar_true_para_cliente_ativo(client):
    """WF 23 LGPD Esqueci depende: cliente SEM motivo_encerramento pode ser deletado.

    Cobre o caveat do D0.3: WF 23 IF "Pode Deletar?" le $json.pode_deletar
    e dispara DELETE /cliente/{id} LGPD art. 18 VI. Cliente novo (sem
    motivo_encerramento) = pode_deletar=True.
    """
    from app.db import session_scope

    with session_scope() as db:
        cid = _make_cliente(db)

    resp = client.get(f"/api/v1/cliente/{cid}/historico", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pode_deletar"] is True


def test_historico_pode_deletar_false_para_cliente_encerrado(client):
    """Cliente com motivo_encerramento != NULL NAO pode ser deletado novamente.

    LGPD art. 18 VI: revogacao ja foi processada. Workflow #23 deve parar
    no IF e NAO chamar DELETE (ja encerrado). pode_deletar=False.
    """
    from app.db import session_scope
    from app.models.cliente import Cliente, MotivoEncerramento

    with session_scope() as db:
        cid = _make_cliente(db)
        c = db.get(Cliente, cid)
        c.motivo_encerramento = MotivoEncerramento.REVOGACAO_CONSENTIMENTO
        db.commit()

    resp = client.get(f"/api/v1/cliente/{cid}/historico", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pode_deletar"] is False
