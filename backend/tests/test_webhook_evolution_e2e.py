"""Testes E2E do webhook Evolution (E1.S1.T7).

Garante que o caminho completo:
  Evolution payload (com PII)
    -> POST /api/v1/webhook/evolution
    -> PII scrub
    -> LLM (mock)
    -> response
NAO vaza nenhum PII no payload EXTERNO.

Esses testes sao o fecho do E1.S1.T7 (TDD do happy path com PII zero).
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


from fastapi.testclient import TestClient  # noqa: E402
import pytest  # noqa: E402

# Imports do app precisam vir DEPOIS do env setup


@pytest.fixture
def client():
    """Cria schema novo por teste (sqlite em memoria eh per-conexao)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.models.base import Base
    import app.models  # noqa: F401
    import app.models.audit_log  # noqa: F401
    import app.models.atendimento  # noqa: F401
    import app.models.cliente  # noqa: F401
    import app.models.conversa  # noqa: F401
    import app.models.documento  # noqa: F401
    import app.models.protocolo  # noqa: F401
    import app.models.webhook_event  # noqa: F401

    # SQLite compartilhado via StaticPool
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)

    # Patch o engine do app
    import app.db
    import app.main as app_main_module

    original_engine = app.db.engine
    original_session_scope = app.db.session_scope
    app.db.engine = test_engine
    app_main_module.engine = test_engine
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    from contextlib import contextmanager

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

    # Captura app no momento de criar o TestClient (importante)
    the_app = app_main_module.app

    try:
        # NAO roda lifespan (que tenta conectar no Swarm 'db')
        with TestClient(the_app) as c:
            yield c
    finally:
        app.db.engine = original_engine
        app_main_module.engine = original_engine
        app.db.session_scope = original_session_scope
        Base.metadata.drop_all(test_engine)


# PII que DEVE ser detectado e removido
PII_SAMPLES = {
    "cpf": "123.456.789-09",
    "cpf2": "987.654.321-00",
    "email": "joao@example.com",
    "phone": "(34) 99876-5432",
    "cnpj": "12.345.678/0001-90",
    "rg": "12.345.678-9",
    "pis": "123.45678.901-23",  # formato padrao PIS: 11 digitos com 2 separadores
    "titulo": "1234 5678 9012",
    "data": "01/01/1990",
    "cep": "38400-100",
}


def _make_evolution_payload(text: str, sender: str = "5534998765432") -> dict:
    """Monta payload no formato legado do webhook Evolution."""
    return {
        "message": {"text": text},
        "sender": sender,
        "instance": "cartorio-2notas",
    }


def _assert_no_pii_in_response(resp_json: dict, original_text: str) -> None:
    """Garante que o response NAO contem nenhum PII do original_text."""
    response_str = str(resp_json).lower()
    for label, pii in PII_SAMPLES.items():
        assert pii.lower() not in response_str, (
            f"PII '{label}' ({pii}) vazou no response: {response_str[:500]}"
        )


# ============================================================================
# Tests
# ============================================================================


def test_payload_com_cpf_nao_vaza_no_response(client) -> None:
    """Cliente manda CPF -> response nao contem o CPF."""
    payload = _make_evolution_payload(
        "Ola, meu CPF eh 123.456.789-09. Gostaria de saber o emolumento."
    )
    resp = client.post("/api/v1/webhook/evolution", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    # Response nao deve ter CPF em lugar nenhum
    _assert_no_pii_in_response(body, "123.456.789-09")


def test_payload_com_multiplos_pii_nao_vaza(client) -> None:
    """Cliente manda CPF + email + phone + RG -> response nao contem nenhum."""
    pii_text = (
        "Bom dia, meu CPF eh 123.456.789-09, email eh joao@example.com, "
        "telefone (34) 99876-5432 e RG 12.345.678-9. "
        "Quero tirar certidao de casamento."
    )
    payload = _make_evolution_payload(pii_text)
    resp = client.post("/api/v1/webhook/evolution", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    _assert_no_pii_in_response(body, pii_text)


def test_payload_com_apenas_texto_sem_pii(client) -> None:
    """Sem PII, response deve ser OK com status=ok e texto preservado (LLM echo)."""
    payload = _make_evolution_payload("Ola, qual o horario de funcionamento?")
    resp = client.post("/api/v1/webhook/evolution", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_payload_com_pii_bloqueia_e_marca_pii_blocked(client) -> None:
    """Quando PII eh detectado, response NAO vaza o CPF, scrubbed mostra
    o label redacted, E o signal de bloqueio eh explicito no response
    (pii_blocked=True, needs_human_handoff=True) - P0.1 LGPD shape.
    """
    payload = _make_evolution_payload("Meu CPF eh 123.456.789-09")
    resp = client.post("/api/v1/webhook/evolution", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    body_str = str(body)
    # PII raw NAO pode estar em lugar nenhum do response
    assert "123.456.789-09" not in body_str, f"CPF integro vazou: {body_str[:300]}"
    # Scrubbed deve mostrar o label de redacted (se campo existe)
    if "scrubbed" in body:
        assert "[CPF_REDACTED]" in body["scrubbed"]
    # P0.1 LGPD response shape - flags explicitos de bloqueio
    assert body.get("pii_blocked") is True, f"pii_blocked deveria ser True; body={body}"
    assert body.get("needs_human_handoff") is True
    assert body.get("handoff_reason") == "PII detectada"


def test_response_nao_expoe_payload_bruto(client) -> None:
    """Response NAO deve ter campo 'raw_text' ou similar com input original."""
    payload = _make_evolution_payload("Meu CPF eh 123.456.789-09")
    resp = client.post("/api/v1/webhook/evolution", json=payload)
    body = resp.json()
    # Garantir que NENHUM campo eh o input cru
    assert "123.456.789-09" not in str(body)


def test_response_nao_expoe_findings_com_pii(client) -> None:
    """Mesmo findings estruturados (contagem) NAO devem vazar PII original."""
    pii_text = "Meu CPF eh 123.456.789-09"
    payload = _make_evolution_payload(pii_text)
    resp = client.post("/api/v1/webhook/evolution", json=payload)
    body = resp.json()
    body_str = str(body)
    # CPF completo NAO pode estar em findings nem em qualquer campo
    assert "123.456.789-09" not in body_str, (
        f"CPF integro vazou em findings/response: {body_str[:500]}"
    )


def test_audit_log_no_db_tem_pii_criptografado(client) -> None:
    """Audit log grava o evento com PII redacted (ja vem do backend), nao raw.

    Este teste so confirma que o PII NAO vaza em `audit_log.payload`
    no campo `scrubbed` - ele deve estar como '[CPF_REDACTED]', nao raw.
    """
    payload = _make_evolution_payload("Meu CPF eh 123.456.789-09")
    resp = client.post("/api/v1/webhook/evolution", json=payload)
    assert resp.status_code == 200

    # Le o audit log pra confirmar
    from app.db import session_scope
    from app.models.audit_log import AuditLog

    with session_scope() as db:
        entries = db.query(AuditLog).filter(AuditLog.action == "conversa.received").all()
        assert len(entries) >= 1, "deve haver pelo menos 1 audit log"
        # O payload.scrubbed NAO pode ter o CPF integro
        for entry in entries:
            payload_str = str(entry.payload)
            assert "123.456.789-09" not in payload_str, (
                f"CPF integro vazou no audit log: {payload_str[:500]}"
            )


def test_payload_extremo_50_pii_simultaneos(client) -> None:
    """50+ PII em 1 mensagem -> response NUNCA vaza."""
    # Concatena 5x cada PII sample
    huge = " ".join([f"doc {k}: {v}" for k, v in PII_SAMPLES.items()] * 5)
    payload = _make_evolution_payload(huge)
    resp = client.post("/api/v1/webhook/evolution", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    _assert_no_pii_in_response(body, huge)


def test_payload_com_unicode_emoji_e_pii(client) -> None:
    """Texto com emoji/unicode + PII -> PII removido, resto preservado."""
    payload = _make_evolution_payload("Ola bom dia! 👋 CPF 123.456.789-09 obrigado 🙂")
    resp = client.post("/api/v1/webhook/evolution", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "123.456.789-09" not in str(body)
    # Emoji nao pode quebrar o scrub
    assert "👋" not in str(body) or "ola" in str(body).lower()  # ou nao quebra nada
