"""Testes unitários e de integração do consentimento LGPD no canal WhatsApp (Wave 3 S3.T3).

Modified by Gustavo Almeida.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_background_process():
    """Mocka a execução do pipeline de processamento em background."""
    with patch("app.api.v1.whatsapp.process_message") as mock_proc:
        yield mock_proc


@pytest.fixture
def mock_adapter():
    """Mocks o WhatsAppAdapter.send para não fazer chamadas HTTP reais upstream."""
    with patch("app.api.v1.whatsapp.get_adapter") as mock_get:
        adapter = AsyncMock()
        adapter.send = AsyncMock(return_value=True)
        adapter.verify_signature = AsyncMock(return_value=True)
        mock_get.return_value = adapter
        yield adapter


def _make_evolution_payload(text: str, sender: str = "5534988888888") -> dict:
    """Helper para mockar payload da Evolution API."""
    return {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {
                "remoteJid": f"{sender}@s.whatsapp.net",
                "fromMe": False,
                "id": "MSG_ID_TEST_CONSENT",
            },
            "message": {
                "conversation": text,
            },
            "pushName": "Test Consent User",
        }
    }


@pytest.mark.asyncio
async def test_whatsapp_first_message_requires_consent(mock_adapter, db_session) -> None:
    """Se o usuário mandar mensagem pela primeira vez, deve receber o banner e retornar consent_required."""
    payload = _make_evolution_payload("Olá assistente")
    
    resp = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "ok"
    assert res["detail"] == "consent_required"
    
    mock_adapter.send.assert_called_once()
    sent_text = mock_adapter.send.call_args[0][0].text
    assert "AVISO LGPD" in sent_text
    assert "digite *SIM*" in sent_text


@pytest.mark.asyncio
async def test_whatsapp_opt_in_grant_consent(mock_adapter, db_session) -> None:
    """Se o usuário mandar 'SIM', deve registrar o consentimento no Redis/DB e retornar consent_granted."""
    payload = _make_evolution_payload("SIM")
    
    resp = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "ok"
    assert res["detail"] == "consent_granted"

    from app.models.audit_log import AuditLog
    entry = db_session.query(AuditLog).filter(AuditLog.action == "consent.whatsapp").first()
    assert entry is not None
    assert entry.payload["status"] == "granted"


@pytest.mark.asyncio
async def test_whatsapp_subsequent_message_bypasses_banner(mock_adapter, db_session) -> None:
    """Se o consentimento estiver ativo no Redis/DB, as mensagens seguintes devem prosseguir sem exibir o banner."""
    sender = "5534977777777"
    from app.models.cliente import Cliente
    from app.services.pii import hash_pii
    from app.config import settings
    
    # Cria cliente simulado com consentimento ativo no banco
    c = Cliente(
        cpf_hash=hash_pii("123.456.789-99", salt=settings.audit_hmac_key[:32]),
        nome="Cliente Consentido",
        whatsapp_number=sender,
        consentimento_lgpd=True
    )
    db_session.add(c)
    db_session.commit()

    payload = _make_evolution_payload("Quero agendar", sender=sender)
    
    resp = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    
    assert res["status"] == "ok"
    assert "detail" not in res  # Sem consent_required ou consent_granted


@pytest.mark.asyncio
async def test_whatsapp_opt_out_revokes_consent(mock_adapter, db_session) -> None:
    """Se o usuário mandar 'PARAR', deve revogar o consentimento e retornar consent_revoked."""
    sender = "5534966666666"
    from app.models.cliente import Cliente
    from app.services.pii import hash_pii
    from app.config import settings
    
    c = Cliente(
        cpf_hash=hash_pii("123.456.789-88", salt=settings.audit_hmac_key[:32]),
        nome="Cliente Revogador",
        whatsapp_number=sender,
        consentimento_lgpd=True
    )
    db_session.add(c)
    db_session.commit()

    # Mocka a função get_bus do whatsapp.py para retornar um RedisBus mockado
    with patch("app.api.v1.whatsapp.get_bus") as mock_get_bus:
        mock_bus = AsyncMock()
        mock_bus.client.get = AsyncMock(return_value=b"1")
        mock_bus.client.delete = AsyncMock(return_value=True)
        mock_get_bus.return_value = mock_bus

        payload = _make_evolution_payload("PARAR", sender=sender)
        
        resp = client.post("/api/v1/whatsapp/webhook", json=payload)
        assert resp.status_code == 200
        res = resp.json()
        assert res["status"] == "ok"
        assert res["detail"] == "consent_revoked"

        from app.models.audit_log import AuditLog
        entry = db_session.query(AuditLog).filter(AuditLog.action == "consent.whatsapp.revoked").first()
        assert entry is not None
        assert entry.payload["status"] == "revoked"
        
        db_session.refresh(c)
        assert c.consentimento_lgpd is False
        assert c.motivo_encerramento.value == "revogacao_consentimento"
