"""P0 #194 — WhatsApp poll LGPD nativa + roteamento apos consentimento.

Bateria curta e focada. Nao substitui a suite completa.

Cobre o canal vivo de clientes (Evolution/WhatsApp):
1. primeira mensagem envia aviso + poll nativa Sim/Nao
2. POLL YES persiste consentimento e fecha o gate
3. POLL NO nao concede consentimento
4. retry do YES e idempotente
5. fallback textual "sim"
6. usuario ja consentido nao recebe LGPD/poll de novo
7. poll ativa nao duplica
8. LID sem remoteJidAlt apos SIM no telefone continua no router
9. aviso inicial nao impede a primeira pergunta
10. segunda pergunta tambem agenda o pipeline
11. webhook duplicado nao bloqueia a proxima mensagem
12. voto de poll nao e tratado como midia
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.channel_failsafe import unsupported_whatsapp_media

client = TestClient(app)

LID = "123456789012345@lid"
PHONE = "5534988123456"


class _FakePipeline:
    def __init__(self, bus: _FakeBus) -> None:
        self._bus = bus
        self._ops: list[tuple[str, str]] = []

    async def __aenter__(self) -> _FakePipeline:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def get(self, key: str) -> None:
        self._ops.append(("get", key))

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._ops.append(("del", key))

    async def execute(self) -> list:
        out: list = []
        for op, key in self._ops:
            if op == "get":
                out.append(self._bus.store.get(key))
            else:
                out.append(1 if self._bus.store.pop(key, None) is not None else 0)
        return out


class _FakeBus:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.client = self

    async def set(
        self, key: str, value: str, *, ex: int | None = None, nx: bool = False
    ) -> str | None:
        if nx and key in self.store:
            return None
        self.store[key] = value
        return "OK"

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if self.store.pop(key, None) is not None:
                removed += 1
        return removed

    def pipeline(self, transaction: bool = True) -> _FakePipeline:
        return _FakePipeline(self)


@pytest.fixture(autouse=True)
def mock_background_process():
    with patch("app.api.v1.whatsapp.process_message") as mock_proc:
        yield mock_proc


@pytest.fixture
def bus() -> _FakeBus:
    return _FakeBus()


@pytest.fixture(autouse=True)
def patch_bus(bus: _FakeBus):
    with patch("app.api.v1.whatsapp.get_bus", return_value=bus):
        yield bus


@pytest.fixture
def mock_adapter():
    with patch("app.api.v1.whatsapp.get_adapter") as mock_get:
        adapter = MagicMock()
        adapter.send = AsyncMock(return_value=True)
        adapter.send_poll = AsyncMock(return_value="POLL_LGPD_001")
        adapter.verify_signature = AsyncMock(return_value=True)
        mock_get.return_value = adapter
        yield adapter


def _text_payload(
    text: str,
    *,
    sender: str = PHONE,
    message_id: str = "WA-MSG-1",
    remote_jid_alt: str | None = None,
    lid: str | None = None,
) -> dict:
    remote_jid = lid or f"{sender}@s.whatsapp.net"
    key: dict[str, object] = {
        "remoteJid": remote_jid,
        "fromMe": False,
        "id": message_id,
    }
    if remote_jid_alt:
        key["remoteJidAlt"] = remote_jid_alt
    return {
        "event": "messages.upsert",
        "instance": "cartorio-agent",
        "data": {
            "key": key,
            "message": {"conversation": text},
            "messageType": "conversation",
            "pushName": "Cliente Poll",
        },
    }


def _poll_vote_payload(
    *,
    option_name: str,
    poll_id: str = "POLL_LGPD_001",
    message_id: str = "WA-VOTE-1",
    sender: str = PHONE,
    lid: str | None = None,
    remote_jid_alt: str | None = None,
) -> dict:
    remote_jid = lid or f"{sender}@s.whatsapp.net"
    key: dict[str, object] = {
        "remoteJid": remote_jid,
        "fromMe": False,
        "id": message_id,
    }
    if remote_jid_alt:
        key["remoteJidAlt"] = remote_jid_alt
    return {
        "event": "messages.upsert",
        "instance": "cartorio-agent",
        "data": {
            "key": key,
            "messageType": "pollUpdateMessage",
            "message": {
                "pollUpdateMessage": {
                    "pollCreationMessageKey": {
                        "id": poll_id,
                        "fromMe": True,
                    },
                    "vote": {"selectedOptions": [{"optionName": option_name}]},
                }
            },
        },
    }


def _sent_texts(mock_adapter: MagicMock) -> list[str]:
    return [str(call.args[0].text) for call in mock_adapter.send.await_args_list if call.args]


@pytest.mark.asyncio
async def test_first_message_sends_lgpd_notice_and_native_poll(
    mock_adapter: MagicMock, db_session
) -> None:
    resp = client.post("/api/v1/whatsapp/webhook", json=_text_payload("Oi"))
    assert resp.status_code == 200
    assert resp.json()["detail"] == "consent_required"
    assert mock_adapter.send.await_count == 1
    notice = _sent_texts(mock_adapter)[0]
    assert "AVISO LGPD" in notice
    assert "SIM" in notice
    mock_adapter.send_poll.assert_awaited_once()
    question = mock_adapter.send_poll.await_args.args[1]
    options = mock_adapter.send_poll.await_args.args[2]
    assert "concorda com o tratamento" in question.lower()
    assert options == ["Sim", "Nao"]


@pytest.mark.asyncio
async def test_poll_yes_persists_consent_and_closes_gate(
    mock_adapter: MagicMock, db_session, mock_background_process
) -> None:
    client.post("/api/v1/whatsapp/webhook", json=_text_payload("Oi", message_id="WA-OPEN"))
    mock_adapter.send.reset_mock()
    mock_adapter.send_poll.reset_mock()

    granted = client.post(
        "/api/v1/whatsapp/webhook",
        json=_poll_vote_payload(option_name="Sim", message_id="WA-YES"),
    )
    assert granted.status_code == 200
    assert granted.json()["detail"] == "consent_granted"
    assert any("confirmado" in text.lower() for text in _sent_texts(mock_adapter))
    mock_adapter.send_poll.assert_not_awaited()

    mock_adapter.send.reset_mock()
    follow = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload(
            "Quanto custa reconhecer firma?",
            message_id="WA-Q1",
        ),
    )
    assert follow.status_code == 200
    assert "detail" not in follow.json()
    mock_adapter.send.assert_not_awaited()
    mock_adapter.send_poll.assert_not_awaited()
    mock_background_process.assert_called_once()


@pytest.mark.asyncio
async def test_poll_no_does_not_grant_consent(
    mock_adapter: MagicMock, db_session, mock_background_process
) -> None:
    client.post("/api/v1/whatsapp/webhook", json=_text_payload("Oi", message_id="WA-OPEN-NO"))
    mock_adapter.send.reset_mock()
    declined = client.post(
        "/api/v1/whatsapp/webhook",
        json=_poll_vote_payload(option_name="Nao", message_id="WA-NO", poll_id="POLL_LGPD_001"),
    )
    assert declined.status_code == 200
    assert declined.json()["detail"] == "consent_declined"
    assert mock_background_process.call_count == 0
    follow = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload("Quanto custa reconhecer firma?", message_id="WA-AFTER-NO"),
    )
    assert follow.json()["detail"] == "consent_required"


@pytest.mark.asyncio
async def test_poll_yes_retry_is_idempotent(mock_adapter: MagicMock, db_session) -> None:
    client.post("/api/v1/whatsapp/webhook", json=_text_payload("Oi", message_id="WA-OPEN-R"))
    first = client.post(
        "/api/v1/whatsapp/webhook",
        json=_poll_vote_payload(option_name="Sim", message_id="WA-YES-1"),
    )
    assert first.json()["detail"] == "consent_granted"
    mock_adapter.send.reset_mock()
    mock_adapter.send_poll.reset_mock()
    retry = client.post(
        "/api/v1/whatsapp/webhook",
        json=_poll_vote_payload(option_name="Sim", message_id="WA-YES-RETRY"),
    )
    assert retry.json()["detail"] in {"consent_granted", "consent_already_granted"}
    assert retry.json().get("idempotent") is True
    mock_adapter.send.assert_not_awaited()
    mock_adapter.send_poll.assert_not_awaited()


@pytest.mark.asyncio
async def test_fallback_sim_grants_consent(
    mock_adapter: MagicMock, db_session, mock_background_process
) -> None:
    granted = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload(" sim ", message_id="WA-SIM"),
    )
    assert granted.status_code == 200
    assert granted.json()["detail"] == "consent_granted"
    assert any("confirmado" in text.lower() for text in _sent_texts(mock_adapter))
    mock_adapter.send_poll.assert_not_awaited()
    mock_background_process.assert_not_called()


@pytest.mark.asyncio
async def test_already_consented_does_not_receive_lgpd_or_poll(
    mock_adapter: MagicMock, db_session, mock_background_process
) -> None:
    from app.models.cliente import Cliente
    from app.services.pietra_coleta import hash_phone

    db_session.add(
        Cliente(
            cpf_hash="d" * 64,
            nome="Cliente Consentido",
            telefone_hash=hash_phone(PHONE),
            consentimento_lgpd=True,
        )
    )
    db_session.commit()
    resp = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload("Oi", message_id="WA-ALREADY"),
    )
    assert resp.status_code == 200
    assert "detail" not in resp.json()
    mock_adapter.send.assert_not_awaited()
    mock_adapter.send_poll.assert_not_awaited()
    mock_background_process.assert_called_once()


@pytest.mark.asyncio
async def test_active_poll_does_not_duplicate(mock_adapter: MagicMock, db_session) -> None:
    first = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload("Oi", message_id="WA-POLL-1"),
    )
    assert first.json()["detail"] == "consent_required"
    assert mock_adapter.send_poll.await_count == 1
    mock_adapter.send.reset_mock()
    mock_adapter.send_poll.reset_mock()
    second = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload("Quanto custa reconhecer firma?", message_id="WA-POLL-2"),
    )
    assert second.json()["detail"] == "consent_required"
    mock_adapter.send.assert_not_awaited()
    mock_adapter.send_poll.assert_not_awaited()


@pytest.mark.asyncio
async def test_lid_after_phone_consent_reaches_router(
    mock_adapter: MagicMock, db_session, mock_background_process
) -> None:
    """Regressao do silencio: SIM no JID de telefone, pergunta seguinte so em @lid."""
    granted = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload(
            "SIM",
            message_id="WA-SIM-LID",
            lid=LID,
            remote_jid_alt=f"{PHONE}@s.whatsapp.net",
        ),
    )
    assert granted.json()["detail"] == "consent_granted"
    mock_adapter.send.reset_mock()
    mock_adapter.send_poll.reset_mock()
    follow = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload(
            "Quanto custa reconhecer firma?",
            message_id="WA-LID-Q1",
            lid=LID,
        ),
    )
    assert follow.status_code == 200
    assert follow.json().get("detail") != "consent_required"
    mock_adapter.send.assert_not_awaited()
    mock_adapter.send_poll.assert_not_awaited()
    mock_background_process.assert_called_once()

    second = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload(
            "E autenticacao?",
            message_id="WA-LID-Q2",
            lid=LID,
        ),
    )
    assert second.status_code == 200
    assert second.json().get("detail") != "consent_required"
    assert mock_background_process.call_count == 2


@pytest.mark.asyncio
async def test_duplicate_webhook_does_not_block_next_message(
    mock_adapter: MagicMock, db_session, mock_background_process
) -> None:
    from app.models.cliente import Cliente
    from app.services.pietra_coleta import hash_phone

    db_session.add(
        Cliente(
            cpf_hash="e" * 64,
            nome="Cliente Dup",
            telefone_hash=hash_phone(PHONE),
            consentimento_lgpd=True,
        )
    )
    db_session.commit()
    first = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload("Quanto custa reconhecer firma?", message_id="WA-DUP"),
    )
    assert first.status_code == 200
    dup = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload("Quanto custa reconhecer firma?", message_id="WA-DUP"),
    )
    assert dup.json()["status"] == "idempotent"
    nxt = client.post(
        "/api/v1/whatsapp/webhook",
        json=_text_payload("E autenticacao?", message_id="WA-NEXT"),
    )
    assert nxt.status_code == 200
    assert "detail" not in nxt.json()
    assert mock_background_process.call_count == 2


@pytest.mark.asyncio
async def test_poll_vote_is_not_unsupported_media() -> None:
    assert unsupported_whatsapp_media("pollUpdateMessage") is None
    assert unsupported_whatsapp_media("pollCreationMessageV3") is None
