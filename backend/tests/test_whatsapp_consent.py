"""Testes unitários e de integração do consentimento LGPD no canal WhatsApp (Wave 3 S3.T3).

Modified by Gustavo Almeida.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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
        adapter = MagicMock()
        adapter.send = AsyncMock(return_value=True)
        adapter.verify_signature = AsyncMock(return_value=True)
        mock_get.return_value = adapter
        yield adapter


def _make_evolution_payload(
    text: str,
    sender: str = "5534988888888",
    message_id: str = "MSG_ID_TEST_CONSENT",
) -> dict:
    """Helper para mockar payload da Evolution API."""
    return {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {
                "remoteJid": f"{sender}@s.whatsapp.net",
                "fromMe": False,
                "id": message_id,
            },
            "message": {
                "conversation": text,
            },
            "pushName": "Test Consent User",
        },
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
async def test_whatsapp_consent_notice_is_not_duplicated_within_ten_minutes(
    mock_adapter,
    db_session,
) -> None:
    """Duas mensagens antes do SIM geram um unico aviso, como exigido pelos prints."""

    with patch("app.api.v1.whatsapp.get_bus") as mock_get_bus:
        mock_bus = MagicMock()
        mock_bus.client.get = AsyncMock(return_value=None)
        mock_bus.client.set = AsyncMock(side_effect=[True, False])
        mock_get_bus.return_value = mock_bus

        first = client.post(
            "/api/v1/whatsapp/webhook",
            json=_make_evolution_payload("Olá", message_id="CONSENT-DEBOUNCE-1"),
        )
        second = client.post(
            "/api/v1/whatsapp/webhook",
            json=_make_evolution_payload("Você está aí?", message_id="CONSENT-DEBOUNCE-2"),
        )

    assert first.json()["detail"] == "consent_required"
    assert second.json()["detail"] == "consent_required"
    mock_adapter.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_whatsapp_opt_in_grant_consent(mock_adapter, db_session) -> None:
    """Se o usuário mandar 'SIM', deve registrar o consentimento no Redis/DB e retornar consent_granted."""
    sender = "5534988888888"
    from app.models.cliente import Cliente
    from app.services.pietra_coleta import hash_phone
    from app.services.pii import hash_pii
    from app.config import settings

    cliente = Cliente(
        cpf_hash=hash_pii("123.456.789-09", salt=settings.audit_hmac_key[:32]),
        nome="Cliente Opt-in",
        telefone_hash=hash_phone(sender),
        whatsapp_number=None,
        consentimento_lgpd=False,
    )
    db_session.add(cliente)
    db_session.commit()

    payload = _make_evolution_payload("SIM", sender=sender)

    resp = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "ok"
    assert res["detail"] == "consent_granted"

    from app.models.audit_log import AuditLog

    entry = db_session.query(AuditLog).filter(AuditLog.action == "consent.whatsapp").first()
    assert entry is not None
    assert entry.payload["status"] == "granted"
    db_session.refresh(cliente)
    assert cliente.consentimento_lgpd is True
    mock_adapter.send.assert_awaited_once()
    assert "consentimento confirmado" in mock_adapter.send.call_args[0][0].text.lower()


@pytest.mark.asyncio
async def test_allowlisted_opt_in_provisions_minimal_cliente_and_leaves_notice(
    mock_adapter,
    db_session,
    mock_background_process,
    monkeypatch,
) -> None:
    """Remetente autorizado sem cliente deve sair do aviso apos SIM."""
    from app.config import settings
    from app.models.cliente import Cliente
    from app.services.pietra_coleta import hash_phone
    from app.services.whatsapp_access import hmac_sender, normalize_whatsapp_number

    sender = "5534933333333"
    hmac_key = "synthetic-whatsapp-allowlist-key-32-bytes"
    normalized = normalize_whatsapp_number(sender)
    assert normalized is not None
    monkeypatch.setattr(settings, "pietra_whatsapp_restrict_inbound", True)
    monkeypatch.setattr(settings, "pietra_whatsapp_allowlist_hmac_key", hmac_key)
    monkeypatch.setattr(
        settings,
        "pietra_whatsapp_allowed_sender_hashes",
        hmac_sender(normalized, hmac_key=hmac_key),
    )

    granted = client.post(
        "/api/v1/whatsapp/webhook",
        json=_make_evolution_payload(
            "SIM",
            sender=sender,
            message_id="CONSENT-ALLOWLISTED-NO-CLIENT",
        ),
    )

    assert granted.status_code == 200
    assert granted.json()["detail"] == "consent_granted"
    assert granted.json()["ack_sent"] is True
    cliente = db_session.query(Cliente).filter_by(telefone_hash=hash_phone(sender)).one()
    assert cliente.consentimento_lgpd is True
    assert cliente.consentimento_canal == "whatsapp"
    assert cliente.whatsapp_number is None
    mock_adapter.send.assert_awaited_once()
    assert "consentimento confirmado" in mock_adapter.send.call_args[0][0].text.lower()

    mock_adapter.send.reset_mock()
    next_message = client.post(
        "/api/v1/whatsapp/webhook",
        json=_make_evolution_payload(
            "Quero falar sobre outro assunto",
            sender=sender,
            message_id="CONSENT-ALLOWLISTED-AFTER-SIM",
        ),
    )

    assert next_message.status_code == 200
    assert "detail" not in next_message.json()
    mock_adapter.send.assert_not_awaited()
    mock_background_process.assert_called_once()


@pytest.mark.asyncio
async def test_whatsapp_subsequent_message_bypasses_banner(mock_adapter, db_session) -> None:
    """Se o consentimento estiver ativo no Redis/DB, as mensagens seguintes devem prosseguir sem exibir o banner."""
    sender = "5534977777777"
    from app.models.cliente import Cliente
    from app.services.pietra_coleta import hash_phone
    from app.services.pii import hash_pii
    from app.config import settings

    # Cria cliente simulado com consentimento ativo no banco
    c = Cliente(
        cpf_hash=hash_pii("123.456.789-99", salt=settings.audit_hmac_key[:32]),
        nome="Cliente Consentido",
        telefone_hash=hash_phone(sender),
        whatsapp_number=None,
        consentimento_lgpd=True,
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
    from app.services.pietra_coleta import hash_phone
    from app.services.pii import hash_pii
    from app.config import settings

    c = Cliente(
        cpf_hash=hash_pii("123.456.789-88", salt=settings.audit_hmac_key[:32]),
        nome="Cliente Revogador",
        telefone_hash=hash_phone(sender),
        whatsapp_number=None,
        consentimento_lgpd=True,
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

        entry = (
            db_session.query(AuditLog).filter(AuditLog.action == "consent.whatsapp.revoked").first()
        )
        assert entry is not None
        assert entry.payload["status"] == "revoked"

        db_session.refresh(c)
        assert c.consentimento_lgpd is False
        assert c.motivo_encerramento.value == "revogacao_consentimento"


@pytest.mark.asyncio
async def test_stale_redis_consent_never_overrides_revoked_database(
    mock_adapter, db_session, mock_background_process
) -> None:
    sender = "5534955555555"
    from app.models.cliente import Cliente
    from app.services.pietra_coleta import hash_phone

    cliente = Cliente(
        cpf_hash="a" * 64,
        nome="Cliente Revogado",
        telefone_hash=hash_phone(sender),
        consentimento_lgpd=False,
    )
    db_session.add(cliente)
    db_session.commit()

    with patch("app.api.v1.whatsapp.get_bus") as get_bus:
        bus = MagicMock()
        bus.client.get = AsyncMock(return_value=b"1")
        bus.client.set = AsyncMock(return_value=True)
        get_bus.return_value = bus
        response = client.post(
            "/api/v1/whatsapp/webhook",
            json=_make_evolution_payload(
                "Quero atendimento",
                sender=sender,
                message_id="CONSENT-STALE-REDIS",
            ),
        )

    assert response.status_code == 200
    assert response.json()["detail"] == "consent_required"
    mock_background_process.assert_not_called()


@pytest.mark.asyncio
async def test_redis_down_does_not_block_durable_database_consent(mock_adapter, db_session) -> None:
    sender = "5534944444444"
    from app.models.cliente import Cliente
    from app.services.pietra_coleta import hash_phone

    cliente = Cliente(
        cpf_hash="b" * 64,
        nome="Cliente Consentido",
        telefone_hash=hash_phone(sender),
        consentimento_lgpd=True,
    )
    db_session.add(cliente)
    db_session.commit()

    with patch("app.api.v1.whatsapp.get_bus") as get_bus:
        bus = MagicMock()
        bus.client.set = AsyncMock(side_effect=ConnectionError("synthetic redis down"))
        get_bus.return_value = bus
        response = client.post(
            "/api/v1/whatsapp/webhook",
            json=_make_evolution_payload(
                "Quero atendimento",
                sender=sender,
                message_id="CONSENT-DB-AUTHORITATIVE",
            ),
        )

    assert response.status_code == 200
    assert "detail" not in response.json()


@pytest.mark.asyncio
async def test_opt_in_without_persisted_cliente_never_claims_granted(
    mock_adapter, db_session
) -> None:
    response = client.post(
        "/api/v1/whatsapp/webhook",
        json=_make_evolution_payload(
            "SIM",
            sender="5534933333333",
            message_id="CONSENT-NO-CLIENT",
        ),
    )

    assert response.status_code == 503
    assert "consent_granted" not in response.text


@pytest.mark.asyncio
async def test_opt_in_audit_failure_rolls_back_and_never_claims_granted(
    mock_adapter, db_session
) -> None:
    sender = "5534922222222"
    from app.models.cliente import Cliente
    from app.models.cliente_channel_identity import ClienteChannelIdentity
    from app.services.pietra_coleta import hash_phone

    cliente = Cliente(
        cpf_hash="c" * 64,
        nome="Cliente Audit Failure",
        telefone_hash=hash_phone(sender),
        consentimento_lgpd=False,
    )
    db_session.add(cliente)
    db_session.commit()

    with patch(
        "app.services.audit.AuditService.log",
        side_effect=RuntimeError("synthetic audit failure"),
    ):
        response = client.post(
            "/api/v1/whatsapp/webhook",
            json=_make_evolution_payload(
                "SIM",
                sender=sender,
                message_id="CONSENT-AUDIT-FAIL",
            ),
        )

    assert response.status_code == 503
    assert "consent_granted" not in response.text
    db_session.expire_all()
    assert db_session.get(Cliente, cliente.id).consentimento_lgpd is False
    assert db_session.query(ClienteChannelIdentity).filter_by(cliente_id=cliente.id).count() == 0


@pytest.mark.asyncio
async def test_opt_out_audit_failure_rolls_back_and_never_claims_revoked(
    mock_adapter, db_session
) -> None:
    sender = "5534911111111"
    from app.models.cliente import Cliente
    from app.services.pietra_coleta import hash_phone

    cliente = Cliente(
        cpf_hash="d" * 64,
        nome="Cliente Revocation Audit Failure",
        telefone_hash=hash_phone(sender),
        consentimento_lgpd=True,
    )
    db_session.add(cliente)
    db_session.commit()

    with patch(
        "app.services.audit.AuditService.log",
        side_effect=RuntimeError("synthetic audit failure"),
    ):
        response = client.post(
            "/api/v1/whatsapp/webhook",
            json=_make_evolution_payload(
                "PARAR",
                sender=sender,
                message_id="REVOCATION-AUDIT-FAIL",
            ),
        )

    assert response.status_code == 503
    assert "consent_revoked" not in response.text
    db_session.expire_all()
    assert db_session.get(Cliente, cliente.id).consentimento_lgpd is True


@pytest.mark.asyncio
async def test_opt_in_cache_failure_is_honest_after_durable_commit(
    mock_adapter, db_session
) -> None:
    sender = "5534900000000"
    from app.models.cliente import Cliente
    from app.services.pietra_coleta import hash_phone

    cliente = Cliente(
        cpf_hash="e" * 64,
        nome="Cliente Cache Failure",
        telefone_hash=hash_phone(sender),
        consentimento_lgpd=False,
    )
    db_session.add(cliente)
    db_session.commit()

    with patch("app.api.v1.whatsapp.get_bus") as get_bus:
        bus = MagicMock()
        bus.client.set = AsyncMock(side_effect=ConnectionError("synthetic redis down"))
        get_bus.return_value = bus
        response = client.post(
            "/api/v1/whatsapp/webhook",
            json=_make_evolution_payload(
                "SIM",
                sender=sender,
                message_id="CONSENT-CACHE-FAIL",
            ),
        )

    assert response.status_code == 200
    assert response.json()["detail"] == "consent_granted"
    assert response.json()["cache_synced"] is False
    db_session.expire_all()
    assert db_session.get(Cliente, cliente.id).consentimento_lgpd is True
