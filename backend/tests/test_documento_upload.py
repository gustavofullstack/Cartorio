"""Testes do endpoint POST /api/v1/documento/upload."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ.setdefault("CARTORIO_API_KEY", "test-key-12345")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import hashlib  # noqa: E402

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


AUTH = {"X-API-Key": "test-key-12345"}


def _make_protocolo(db, numero="2026-00001"):
    from app.models.protocolo import Protocolo
    p = Protocolo(
        cliente_id=1,  # dummy FK
        numero=numero,
        tipo="escritura_compra_venda",
        status="em_andamento",
        canal_origem="web",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.id


def test_upload_pdf_valido(client):
    """Upload de PDF com hash valido -> 200 + metadata."""
    from app.db import session_scope
    with session_scope() as db:
        pid = _make_protocolo(db)

    # Hash SHA256 ficticio (64 chars hex)
    fake_hash = hashlib.sha256(b"PDF content").hexdigest()

    form_data = {
        "protocolo_id": pid,
        "tipo": "escritura_assinada",
        "storage_path": "protocolos/2026-00001/escritura.pdf",
        "mime_type": "application/pdf",
        "hash_sha256": fake_hash,
        "tamanho_bytes": 102400,
        "uploaded_by": "escrevente-1",
        "uploaded_by_tipo": "escrevente",
    }

    resp = client.post("/api/v1/documento/upload", data=form_data, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["hash_sha256"] == fake_hash
    assert body["mime_type"] == "application/pdf"
    assert body["storage_path"] == "protocolos/2026-00001/escritura.pdf"


def test_upload_sem_auth_retorna_401(client):
    # Sem form data E sem auth: FastAPI retorna 422 (validation form) antes de 401.
    # Mas COM form data E sem auth: deve ser 401.
    fake_hash = hashlib.sha256(b"x").hexdigest()
    form_data = {
        "protocolo_id": 1,
        "tipo": "rg",
        "storage_path": "x",
        "mime_type": "application/pdf",
        "hash_sha256": fake_hash,
    }
    resp = client.post("/api/v1/documento/upload", data=form_data)  # sem AUTH header
    assert resp.status_code == 401


def test_upload_hash_invalido_retorna_400(client):
    """Hash que nao eh SHA256 hex de 64 chars -> 400."""
    from app.db import session_scope
    with session_scope() as db:
        pid = _make_protocolo(db)

    form_data = {
        "protocolo_id": pid,
        "tipo": "rg",
        "storage_path": "x",
        "mime_type": "application/pdf",
        "hash_sha256": "abc",  # muito curto
    }
    resp = client.post("/api/v1/documento/upload", data=form_data, headers=AUTH)
    assert resp.status_code == 400
    assert resp.json()["erro"] == "INVALID_HASH"


def test_upload_mime_invalido_retorna_400(client):
    from app.db import session_scope
    with session_scope() as db:
        pid = _make_protocolo(db)

    fake_hash = hashlib.sha256(b"x").hexdigest()
    form_data = {
        "protocolo_id": pid,
        "tipo": "rg",
        "storage_path": "x",
        "mime_type": "application/x-msdownload",  # exe
        "hash_sha256": fake_hash,
    }
    resp = client.post("/api/v1/documento/upload", data=form_data, headers=AUTH)
    assert resp.status_code == 400
    assert resp.json()["erro"] == "INVALID_MIME"


def test_upload_protocolo_inexistente_404(client):
    fake_hash = hashlib.sha256(b"x").hexdigest()
    form_data = {
        "protocolo_id": 99999,
        "tipo": "rg",
        "storage_path": "x",
        "mime_type": "application/pdf",
        "hash_sha256": fake_hash,
    }
    resp = client.post("/api/v1/documento/upload", data=form_data, headers=AUTH)
    assert resp.status_code == 404


def test_upload_response_shape(client):
    from app.db import session_scope
    with session_scope() as db:
        pid = _make_protocolo(db)

    fake_hash = hashlib.sha256(b"x").hexdigest()
    form_data = {
        "protocolo_id": pid,
        "tipo": "rg",
        "storage_path": "x",
        "mime_type": "application/pdf",
        "hash_sha256": fake_hash,
        "uploaded_by": "test",
    }
    resp = client.post("/api/v1/documento/upload", data=form_data, headers=AUTH)
    body = resp.json()
    expected_keys = {
        "id", "protocolo_id", "tipo", "storage_path", "storage_provider",
        "mime_type", "tamanho_bytes", "hash_sha256", "uploaded_by", "uploaded_at",
    }
    assert set(body.keys()) == expected_keys
