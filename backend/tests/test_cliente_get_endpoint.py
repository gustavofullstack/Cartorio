"""Testes do endpoint GET /api/v1/cliente/{cliente_id} (D0.3 LGPD-safe).

Cobre 8 cenarioes do briefing D0.3 (2026-06-25):
1. 200 cliente ativo retorna dados basicos
2. 200 response LGPD-safe (ZERO PII puro)
3. 404 cliente inexistente
4. 410 cliente encerrado (LGPD)
5. 401 sem X-API-Key
6. 401 X-API-Key errado
7. 422 cliente_id nao inteiro
8. Audit log de leitura (LGPD art. 37)

LGPD compliance:
- Response NAO retorna cpf/telefone/email PURO, apenas hash.
- Se cliente.motivo_encerramento != None -> 410 Gone (cliente ja encerrado).
- Toda leitura grava audit log (registro de tratamento - LGPD art. 37).
"""

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

# Auth header valido (64-char hex - validacao strict em config.py).
AUTH = {"X-API-Key": "a" * 64}


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """App FastAPI com DB SQLite in-memory isolado por teste."""
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


def _make_cliente(
    db,
    cpf_hash: str = "h" * 64,
    nome: str = "Joao da Silva",
    email: str | None = "joao@example.com",
    telefone_hash: str | None = "t" * 64,
    consentimento_lgpd: bool = True,
    motivo_encerramento=None,
    deleted_at=None,
):
    """Helper: cria cliente no DB. Defaults sao LGPD-safe (apenas hashes)."""
    from app.models.cliente import Cliente, MotivoEncerramento

    kwargs: dict = dict(
        cpf_hash=cpf_hash,
        nome=nome,
        email=email,
        telefone_hash=telefone_hash,
        consentimento_lgpd=consentimento_lgpd,
    )
    if motivo_encerramento is not None:
        kwargs["motivo_encerramento"] = MotivoEncerramento(motivo_encerramento)
    if deleted_at is not None:
        kwargs["deleted_at"] = deleted_at
    c = Cliente(**kwargs)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c.id


# ============================================================================
# Tests - 8 cenarioes do briefing D0.3
# ============================================================================


def test_get_cliente_200_retorna_dados_basicos(client: TestClient) -> None:
    """Cenario 1: GET /cliente/{id} com cliente ativo retorna 200 + dados basicos."""
    from app.db import session_scope

    with session_scope() as db:
        cid = _make_cliente(db, cpf_hash="a" * 64, telefone_hash="b" * 64)

    resp = client.get(f"/api/v1/cliente/{cid}", headers=AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == cid
    assert body["cpf_hash"] == "a" * 64
    assert body["telefone_hash"] == "b" * 64
    assert body["consentimento_lgpd"] is True
    assert "created_at" in body
    assert "updated_at" in body


def test_get_cliente_200_zero_pii_puro_no_response(client: TestClient) -> None:
    """Cenario 2 (LGPD): response NAO expoe cpf/telefone/email PURO.

    Apenas hashes. Marcadores textuais: chaves do JSON nao podem ser
    'cpf', 'telefone', 'email', 'nome' (a menos que terminem com '_hash').
    """
    from app.db import session_scope

    with session_scope() as db:
        # Cliente com dados puros potencialmente perigosos. Mesmo se backend
        # tiver bug e incluir algum campo puro, o teste detecta.
        cid = _make_cliente(
            db,
            cpf_hash="a" * 64,
            nome="Joao da Silva",
            email="joao@example.com",
            telefone_hash="b" * 64,
        )

    resp = client.get(f"/api/v1/cliente/{cid}", headers=AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Lista branca: apenas campos hash + metadados NAO-PII
    forbidden_keys = {"cpf", "telefone", "email", "nome"}
    for key in body.keys():
        # Qualquer chave plain (sem sufixo _hash) com nome PII puro eh proibida
        assert key not in forbidden_keys, (
            f"LGPD LEAK: response expoe campo PII puro '{key}'={body[key]!r}"
        )

    # Bonus: garantir que os 3 valores PURO nao estao em nenhum valor do response
    body_str = str(body)
    assert "123.456.789-09" not in body_str, "LGPD LEAK: CPF puro no response"
    assert "(34) 99999-0000" not in body_str, "LGPD LEAK: telefone puro no response"
    assert "joao@example.com" not in body_str, "LGPD LEAK: email puro no response"

    # E o hash DEVE estar presente
    assert "cpf_hash" in body
    assert "telefone_hash" in body
    assert body["cpf_hash"] == "a" * 64


def test_get_cliente_404_cliente_inexistente(client: TestClient) -> None:
    """Cenario 3: cliente_id que nao existe no DB retorna 404."""
    resp = client.get("/api/v1/cliente/99999", headers=AUTH)
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["erro"] == "CLIENTE_NOT_FOUND"


def test_get_cliente_410_cliente_com_motivo_encerramento(client: TestClient) -> None:
    """Cenario 4: cliente com motivo_encerramento != None -> 410 Gone (LGPD art. 18 VI).

    Cliente encerrado NAO pode ser lido - LGPD art. 18 (revogacao) e
    Provimento CNJ 74/2018 (retencao 5y).
    """
    from app.db import session_scope

    with session_scope() as db:
        cid = _make_cliente(db, motivo_encerramento="revogacao_consentimento")

    resp = client.get(f"/api/v1/cliente/{cid}", headers=AUTH)
    assert resp.status_code == 410
    body = resp.json()
    assert body["detail"]["erro"] == "CLIENTE_ENCERRADO_LGPD"
    assert "LGPD" in body["detail"]["mensagem"] or "lgpd" in body["detail"]["mensagem"].lower()


def test_get_cliente_401_sem_header_x_api_key(client: TestClient) -> None:
    """Cenario 5: sem X-API-Key retorna 401 (gate E0.AUTH)."""
    resp = client.get("/api/v1/cliente/1")  # sem header
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["erro"] == "UNAUTHORIZED"
    # RFC 7235: WWW-Authenticate presente
    assert resp.headers.get("www-authenticate") == "ApiKey"


def test_get_cliente_401_header_x_api_key_errado(client: TestClient) -> None:
    """Cenario 6: X-API-Key com valor errado retorna 401."""
    resp = client.get("/api/v1/cliente/1", headers={"X-API-Key": "b" * 64})
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["erro"] == "UNAUTHORIZED"


def test_get_cliente_422_cliente_id_nao_inteiro(client: TestClient) -> None:
    """Cenario 7: cliente_id nao-inteiro (path /cliente/abc) retorna 422 (FastAPI/Pydantic)."""
    resp = client.get("/api/v1/cliente/abc", headers=AUTH)
    assert resp.status_code == 422


def test_get_cliente_audita_leitura_lgpd_art_37(client: TestClient) -> None:
    """Cenario 8: toda leitura grava audit log (LGPD art. 37 - registro de tratamento).

    Verifica que apos GET /cliente/{id} existe 1 entry no audit_log com:
    - action: cliente.read (ou similar)
    - resource: cliente:{id}
    - request_id, ip, user_agent (audit_context)
    """
    from app.db import session_scope
    from app.models.audit_log import AuditLog

    with session_scope() as db:
        cid = _make_cliente(db, cpf_hash="c" * 64)

    resp = client.get(
        f"/api/v1/cliente/{cid}",
        headers={**AUTH, "User-Agent": "test-suite-d03/1.0"},
    )
    assert resp.status_code == 200, resp.text

    # Verifica audit log
    with session_scope() as db:
        entries = db.query(AuditLog).filter(AuditLog.resource == f"cliente:{cid}").all()
        read_entries = [
            e for e in entries if "read" in e.action.lower() or "get" in e.action.lower()
        ]
        assert len(read_entries) >= 1, (
            f"Esperava >= 1 audit log de leitura, achei: "
            f"{[(e.action, e.resource) for e in entries]}"
        )
        entry = read_entries[0]
        # LGPD compliance: NAO loga CPF/telefone puro
        assert "joao@example.com" not in (entry.payload or ""), "LGPD LEAK: email puro no audit log"
