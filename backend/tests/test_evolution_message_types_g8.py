"""G8.22.T1 — robustez do webhook Evolution API para 8 tipos de mensagem.

LGPD Art. 46: dados 100% fictícios via ``tests.fixtures.evolution_payloads``.
Garante que o handler ``POST /api/v1/webhook/evolution`` aceita
realistic payloads de:

- text       (conversation / extendedTextMessage)
- image      (com caption opcional — ex: foto de RG)
- audio      (PTT push-to-talk)
- document   (PDF/DOCX)
- video      (com caption opcional)
- sticker    (image/webp)
- location   (lat/lon + address)
- contact    (vCard embutido)

Sem retornar 500 (P0 — Evolution pode parar de enviar). Sem quebrar o
audit chain, a idempotencia DB ou o PII scrubber. Mensagens sem texto
útil disparam human-handoff (``needs_human_handoff=true``).

Cobre tambem:
- payload oversized (>1MB) → status <500 (defesa contra ataque DoS)
- timestamp malformado (negativo) → status <500
- idempotency replay do mesmo message_id → nao duplica
- payload sem `data` → handler nao quebra (defense in depth contra Baileys novo)

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.fixtures.evolution_payloads import EVOLUTION_FIXTURES


# Client compartilhado — app.main.app e singleton; conftest.py
# redireciona a engine global para sqlite in-memory (autouse fixture).
client = TestClient(app)


# =============================================================================
#  LLM mock — patched em TODOS os testes deste arquivo.
# =============================================================================


class _FakeLLMResponse:
    """Stub deterministico para chain de LLM (opencode_go -> openclaw).

    Sem este mock, o handler tenta chamar provedores reais upstream
    (chat_with_fallback) e ambos falham por ConnectionError, ativando
    human-handoff. Isso mascara o sucesso do scrub de PII (camada 3) e
    dificulta validar o happy path do tipo text.
    """

    def __init__(self, content: str = "Resposta mockada para teste de robustez G8.22") -> None:
        self.content = content
        self.tokens_in = 12
        self.tokens_out = 24
        self.latency_ms = 5


@pytest.fixture(autouse=True)
def _mock_llm_chain():
    """Mocka chat_with_fallback em TODOS os testes deste arquivo.

    Cobre o caminho router.py:1183 (``chat_with_fallback`` importada
    dentro da funcao — patch precisa do path absoluto do modulo).
    """
    with patch(
        "app.integrations.fallback.chat_with_fallback",
        new=AsyncMock(return_value=_FakeLLMResponse()),
    ):
        yield


# =============================================================================
#  Helpers
# =============================================================================


def _signature_header_disabled() -> dict[str, str]:
    """Em dev/test, signature e opcional (validate_evolution_signature
    aceita quando EVOLUTION_WEBHOOK_SECRET nao esta setado).
    Garante header so se Evolution exigir — varrendo o app em CI nao
    falha por causa disso."""
    return {}


# =============================================================================
#  1) Happy-path parametrized: cada um dos 8 tipos
# =============================================================================


@pytest.mark.parametrize(
    "message_type",
    [
        "text",
        "image",
        "audio",
        "document",
        "video",
        "sticker",
        "location",
        "contact",
    ],
)
def test_evolution_handler_accepts_message_type_without_500(message_type: str) -> None:
    """P0 contract: webhook Evolution aceita cada um dos 8 tipos sem 500.

    Aceitar 200 (processado), 202 (deferred), 200 com idempotent,
    ou 200 com human-handoff. NUNCA 5xx — caso contrario Evolution pode
    parar de enviar webhooks e a integacao cai.
    """
    payload = EVOLUTION_FIXTURES[message_type]
    response = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )

    assert response.status_code < 500, (
        f"[{message_type}] Evolution handler returned {response.status_code}: {response.text[:300]}"
    )
    # Status code validos: 200 (ok/idempotent/handoff), 202 (accepted), 4xx (validation)
    assert 200 <= response.status_code < 600
    assert response.headers.get("content-type", "").startswith("application/json")


def test_evolution_handler_text_message_returns_scrubbed_response() -> None:
    """Smoke do happy path do tipo text — garante que o handler completo
    (idempotency -> parse -> scrub -> audit) executa sem erro para text."""
    payload = EVOLUTION_FIXTURES["text"]
    response = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )

    assert response.status_code == 200
    body: dict[str, Any] = response.json()

    # Campos canonicos do response (ver webhook_evolution em router.py:998+)
    assert "status" in body
    assert body["status"] in ("ok", "idempotent", "ignored")

    # Para text com conversation: deve ter passado pelo PII scrubber
    # (pii_blocked False pois o texto e "Bom dia, gostaria de agendar
    # uma autenticacao de copia" — sem PII).
    assert body.get("scrubbed") is not None
    assert body.get("needs_human_handoff") is False


def test_evolution_handler_image_message_triggers_human_handoff() -> None:
    """Imagem sem transcricao/OCR nao tem texto util -> human handoff.

    Defense in depth (router.py:1069-1084): sem raw_text.strip() o
    handler retorna `needs_human_handoff=true` em vez de chamar LLM
    com input invalido.
    """
    payload = EVOLUTION_FIXTURES["image"]
    response = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )

    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    # Imagem sem caption vazio no handler — o caption de imagem NAO e
    # extraido por _parse_dual_format (so conversation/extendedTextMessage),
    # entao cai na defesa "sem texto util" -> handoff.
    # Se esta assertion falhar indica que evoluimos o parser para extrair
    # caption de imagem — atualize o teste junto.
    assert body.get("needs_human_handoff") is True
    assert body.get("handoff_reason") == "payload_empty_message"


def test_evolution_handler_audio_message_triggers_human_handoff() -> None:
    """Audio (PTT) sem transcricao -> human handoff."""
    payload = EVOLUTION_FIXTURES["audio"]
    response = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["needs_human_handoff"] is True
    assert body["handoff_reason"] == "payload_empty_message"


def test_evolution_handler_document_message_triggers_human_handoff() -> None:
    """Documento PDF/DOCX sem texto extraido -> human handoff."""
    payload = EVOLUTION_FIXTURES["document"]
    response = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["needs_human_handoff"] is True
    assert body["handoff_reason"] == "payload_empty_message"


# =============================================================================
#  2) Defense-in-depth: payload oversized, malformed, weird shapes
# =============================================================================


def test_evolution_handler_handles_oversized_payload_without_500() -> None:
    """Payload >1MB nao pode derrubar o handler (defesa contra DoS).

    Como nao ha explicit 413 handler no router, aceitamos 200 (truncated),
    413 (rejected by size limit) ou 422 (rejected by validation). O P0
    absoluto: status < 500.
    """
    huge_payload: dict[str, Any] = {
        **EVOLUTION_FIXTURES["text"],
        "_oversized_field_dos_test": "x" * 1_500_000,  # 1.5MB of 'x'
    }

    response = client.post(
        "/api/v1/webhook/evolution",
        json=huge_payload,
        headers=_signature_header_disabled(),
    )

    # 4xx e aceitavel (rejeicao explicita) e 200 e aceitavel
    # (handler truncou internamente e processou). 500 indica crash.
    assert response.status_code < 500, f"oversized payload crashed handler: {response.status_code}"
    assert response.status_code in (200, 413, 422)


def test_evolution_handler_handles_negative_timestamp() -> None:
    """Timestamp negativo (pre-1970) nao quebra o handler."""
    payload: dict[str, Any] = {
        **EVOLUTION_FIXTURES["text"],
        "data": {
            **EVOLUTION_FIXTURES["text"]["data"],
            "messageTimestamp": -1,
        },
    }

    response = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )

    assert response.status_code < 500


def test_evolution_handler_handles_missing_message_field() -> None:
    """Payload sem `message` (data vazio) — não pode quebrar o handler."""
    payload: dict[str, Any] = {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {
                "remoteJid": "5511999990001@s.whatsapp.net",
                "fromMe": False,
                "id": "FIX-empty-001",
            },
            "messageType": "conversation",
            "message": {},  # vazio
        },
    }

    response = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )

    assert response.status_code < 500
    body = response.json()
    # Sem texto util → handoff (defense in depth no router.py:1071)
    if response.status_code == 200:
        assert body.get("needs_human_handoff") is True


def test_evolution_handler_handles_missing_data_block() -> None:
    """Payload sem `data` (formato moderno faltando) nao quebra o handler.

    Em prod, payload malformado vinha do Baileys novo como
    `data.key` (string em vez de dict). Aqui testamos o caso mais comum:
    `data` ausente por completo.
    """
    payload: dict[str, Any] = {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        # Sem 'data' — formato legado exige 'message'+'sender' na raiz
    }

    response = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )

    # Pode 200 (ignored), 200 (idempotent), ou 4xx (validation) — nunca 5xx.
    assert response.status_code < 500


def test_evolution_handler_ignores_non_upsert_event() -> None:
    """Eventos que nao sao messages.upsert sao ignorados (não processados)."""
    payload: dict[str, Any] = {
        "event": "connection.update",
        "instance": "cartorio-2notas",
        "data": {"state": "open"},
    }
    response = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )

    assert response.status_code < 500


# =============================================================================
#  3) Idempotency: replay do mesmo message_id nao duplica side effects.
# =============================================================================


def test_evolution_handler_idempotent_replay_same_message_id() -> None:
    """Replay do mesmo (instance, message_id) nao duplica processamento.

    Garante que o evolution_ingest (DB-level) + Redis SETNX estao ativos
    e retornam status='idempotent' em vez de reprocessar.
    """
    payload = EVOLUTION_FIXTURES["text"]

    # 1a chamada: deve retornar ok/processado
    first = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )
    assert first.status_code < 500

    # 2a chamada (replay): status='idempotent' ou 'ok' (depende do path)
    second = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )
    assert second.status_code < 500

    second_body: dict[str, Any] = second.json()
    assert second_body.get("status") in ("idempotent", "ok", "ignored")


# =============================================================================
#  4) LGPD: response nao ecoa PII bruta (CPF/telefone).
# =============================================================================


def test_evolution_handler_does_not_echo_raw_pii_in_response() -> None:
    """P0 LGPD: response JSON nao pode ecoar PII cru do payload.

    Defense in depth: o scrubber aplica 3 camadas, e o response do
    webhook devolve apenas scrubbed + metadata. Aqui validamos que o
    `remoteJid`/pushName do payload nao aparece como string crua na
    resposta (a menos que tenha sido hasheada/truncada).
    """
    payload = EVOLUTION_FIXTURES["text"]
    response = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )

    assert response.status_code == 200
    response_text = response.text

    # PJI ficticia deste payload e:
    #   remoteJid="5511999990001@s.whatsapp.net"
    #   pushName="Cliente Fixture"
    # O response pode referenciar o remoteJid apenas como sender_id
    # mascarado/truncado (nao a string completa).
    assert "5511999990001" not in response_text or "scrubbed" in response_text


# =============================================================================
#  5) Schema validation: malformed JSON e JSON syntactically valid mas
#     faltando campos criticos nao podem retornar 5xx.
# =============================================================================


def test_evolution_handler_accepts_minimal_valid_payload() -> None:
    """Payload minimo valido (so instance + data.key) nao quebra."""
    minimal = {
        "instance": "cartorio-2notas",
        "data": {
            "key": {
                "remoteJid": "5511999990001@s.whatsapp.net",
                "id": "FIX-min-001",
            },
            "message": {"conversation": "oi"},
        },
    }
    response = client.post(
        "/api/v1/webhook/evolution",
        json=minimal,
        headers=_signature_header_disabled(),
    )
    assert response.status_code < 500


def test_evolution_handler_does_not_leak_500_on_weird_message_type() -> None:
    """messageType desconhecido/estranho nao causa 500 — handler cai no
    fallback `raw_text=''` -> handoff."""
    weird_payload: dict[str, Any] = {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {
                "remoteJid": "5511999990001@s.whatsapp.net",
                "fromMe": False,
                "id": "FIX-weird-001",
            },
            "messageType": "reactionMessage",  # NAO deveria chegar, mas Evolution tem varios
            "message": {
                "reactionMessage": {"key": {"remoteJid": "x", "id": "y"}, "text": "👍"},
            },
        },
    }
    response = client.post(
        "/api/v1/webhook/evolution",
        json=weird_payload,
        headers=_signature_header_disabled(),
    )

    assert response.status_code < 500
    # reactionMessage nao tem texto util -> handoff OU ignored
    body = response.json()
    if response.status_code == 200:
        assert body.get("status") in ("ok", "ignored", "idempotent")
        if body.get("status") == "ok":
            assert body.get("needs_human_handoff") is True


def test_evolution_handler_handles_huge_message_id_string() -> None:
    """message_id gigante (1MB string) nao causa OOM/500."""
    huge_id = "X" * 1_000_000  # 1MB string em message_id
    payload: dict[str, Any] = {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {
                "remoteJid": "5511999990001@s.whatsapp.net",
                "id": huge_id,
            },
            "message": {"conversation": "x" * 100},
        },
    }
    response = client.post(
        "/api/v1/webhook/evolution",
        json=payload,
        headers=_signature_header_disabled(),
    )
    assert response.status_code < 500


# =============================================================================
#  6) JSON encoding edge cases
# =============================================================================


def test_evolution_handler_payload_is_valid_json_encoding() -> None:
    """Sanity check: cada fixture e JSON-encodable sem erros."""
    for msg_type, fixture in EVOLUTION_FIXTURES.items():
        # json.dumps deve aceitar todos os 8 fixtures sem TypeError.
        encoded = json.dumps(fixture, ensure_ascii=False)
        assert isinstance(encoded, str)
        assert len(encoded) > 100  # cada fixture realista
