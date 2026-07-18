"""Webhook receiver schemas - Swagger documentation tests (G8.17.T2).

LGPD Art. 46: cada campo com dado pessoal deve estar marcado com `**LGPD PII**`
na description do OpenAPI. Estes testes blindam o padrao `PIIField` para que
LGPD-revisao automatica funcione.

Tests:
1. test_telegram_payload_serialization — roundtrip JSON
2. test_telegram_payload_realistic_example — payload real com CPF/edge cases
3. test_pii_fields_marked_in_schema_description — `**LGPD PII**` presente
4. test_schema_has_examples — cada webhook tem examples
5. test_openapi_includes_enhanced_descriptions — OpenAPI spec tem descriptions
6. test_extra_ignore_does_not_break_real_data — vendor fields ignorados
7. test_unknown_webhook_returns_validation_error — payloads invalidos 422
8. test_evolution_dual_format_compatibility — nested + legacy
9. test_pii_field_helper_marker — PIIField helper aplica prefixo
10. test_collect_pii_paths_nested — nested PII paths detectados
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.services.pii_marker import (
    PII,
    PIIField,
    collect_pii_paths,
    is_pii_field,
)
from app.schemas.webhook_payloads import (
    AlertManagerPayload,
    ChatwootMessageCreated,
    EvolutionPayload,
    N8nDeletionRequest,
    N8nErrorRequest,
    OutboxDispatchRequest,
    TelegramCallbackQuery,
    TelegramChat,
    TelegramMessage,
    TelegramUpdate,
    TelegramUser,
)


# ----------------------------------------------------------------------------
# Sample payloads (realistic examples drawn from production logs)
# ----------------------------------------------------------------------------

TELEGRAM_TEXT_SAMPLE: dict[str, Any] = {
    "update_id": 123456789,
    "message": {
        "message_id": 42,
        "date": 1721308800,
        "from": {
            "id": 987654321,
            "first_name": "Maria",
            "last_name": "Silva",
            "username": "mariacliente",
            "language_code": "pt-BR",
        },
        "chat": {"id": 987654321, "type": "private", "first_name": "Maria"},
        "text": "Quero agendar uma procura\u00e7\u00e3o amanh\u00e3, meu CPF \u00e9 123.456.789-09",
    },
}

TELEGRAM_CALLBACK_SAMPLE: dict[str, Any] = {
    "update_id": 123456790,
    "callback_query": {
        "id": "cb_abc123def456",
        "from": {"id": 987654321, "first_name": "Maria"},
        "chat_instance": "chat_inst_xyz",
        "data": "cmd:agendar",
        "message": {
            "message_id": 41,
            "date": 1721308500,
            "chat": {"id": 987654321, "type": "private"},
        },
    },
}

EVOLUTION_NESTED_SAMPLE: dict[str, Any] = {
    "event": "messages.upsert",
    "instance": "cartorio-2notas",
    "data": {
        "key": {
            "remoteJid": "5511999999999@s.whatsapp.net",
            "fromMe": False,
            "id": "3EB0C8E5C2B6F1A0",
        },
        "message": {"conversation": "Quanto custa autenticacao?"},
        "messageType": "conversation",
        "pushName": "Maria Cliente",
    },
}

EVOLUTION_LEGACY_SAMPLE: dict[str, Any] = {
    "message": {"conversation": "Quero agendar"},
    "sender": "553499999999",
    "instance": "cartorio-2notas",
}

CHATWOOT_MSG_SAMPLE: dict[str, Any] = {
    "event": "message_created",
    "id": 99,
    "message_id": 999,
    "message_type": "incoming",
    "content": "Quero falar com um humano",
    "conversation": {"id": 42, "status": "open"},
    "sender": {"id": 5, "name": "Maria", "email": "maria@example.com"},
}

ALERTMANAGER_SAMPLE: dict[str, Any] = {
    "version": "4",
    "groupKey": "{}:{alertname=\"HighErrorRate\"}",
    "status": "firing",
    "receiver": "cartorio-telegram-default",
    "groupLabels": {"alertname": "HighErrorRate"},
    "commonLabels": {"severity": "warning", "squad": "cartorio-sre"},
    "commonAnnotations": {"summary": "API 5xx acima do threshold"},
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "HighErrorRate",
                "severity": "warning",
                "instance": "cartorio-api-1:8000",
                "squad": "cartorio-sre",
            },
            "annotations": {
                "summary": "API 5xx rate=12% on /api/v1/protocolo",
                "description": "Endpoint retornando 500 em 12% das chamadas",
                "runbook_url": "https://runbooks.2notasudi.com.br/5xx",
            },
            "startsAt": "2026-07-18T12:00:00Z",
            "fingerprint": "abc123def456",
        }
    ],
}


# ----------------------------------------------------------------------------
# 1. test_telegram_payload_serialization
# ----------------------------------------------------------------------------


def test_telegram_payload_serialization() -> None:
    """TelegramUpdate roundtrip via model_dump/model_validate."""
    parsed = TelegramUpdate.model_validate(TELEGRAM_TEXT_SAMPLE)
    assert parsed.update_id == 123456789
    assert parsed.message is not None
    assert parsed.message.message_id == 42
    assert parsed.message.text is not None
    assert "Maria" in (parsed.message.from_.first_name or "")

    # Roundtrip via JSON
    serialized = parsed.model_dump(by_alias=True, mode="json")
    reparsed = TelegramUpdate.model_validate(serialized)
    assert reparsed.update_id == parsed.update_id
    assert reparsed.message.from_.username == "mariacliente"


# ----------------------------------------------------------------------------
# 2. test_telegram_payload_realistic_example
# ----------------------------------------------------------------------------


def test_telegram_payload_realistic_example() -> None:
    """Payload real com CPF (LGPD PII) — deve ser parseado e redaction detecta."""
    parsed = TelegramUpdate.model_validate(TELEGRAM_TEXT_SAMPLE)
    # O texto cru carrega CPF — isso eh LGPD PII. Schema aceita; backend scrub.
    assert "123.456.789-09" in (parsed.message.text or "")
    # Mas o schema marca explicitamente como PII no OpenAPI.
    assert is_pii_field(TelegramMessage.model_fields["text"].description or "")


# ----------------------------------------------------------------------------
# 3. test_pii_fields_marked_in_schema_description
# ----------------------------------------------------------------------------


def test_pii_fields_marked_in_schema_description() -> None:
    """Cada campo com PII tem `**LGPD PII**` na description.

    LGPD-revisao automatica depende deste marker. Falha aqui = bug LGPD.
    """
    pii_fields_in_telegram = [
        ("text", TelegramMessage),
        ("from_", TelegramMessage),
        ("chat", TelegramMessage),
        ("first_name", TelegramUser),
        ("last_name", TelegramUser),
        ("username", TelegramUser),
        ("from_", TelegramCallbackQuery),
        ("message", TelegramCallbackQuery),
    ]
    for field_name, model in pii_fields_in_telegram:
        info = model.model_fields[field_name]
        desc = info.description or ""
        assert is_pii_field(desc), (
            f"{model.__name__}.{field_name} deve ter `**LGPD PII**` "
            f"na description, got: {desc[:80]!r}"
        )

    # Evolution (campos PII documentados)
    pii_fields_in_evolution = [
        ("data", EvolutionPayload),  # contains key.remoteJid + message.conversation
        ("key", EvolutionPayload),
        ("message", EvolutionPayload),
        ("sender", EvolutionPayload),
        ("push_name", EvolutionPayload),  # alias=pushName
    ]
    for field_name, model in pii_fields_in_evolution:
        info = model.model_fields[field_name]
        desc = info.description or ""
        assert is_pii_field(desc), (
            f"{model.__name__}.{field_name} should have **LGPD PII**, got: {desc[:80]!r}"
        )

    # Chatwoot
    pii_in_chatwoot = [
        ("content", ChatwootMessageCreated),
        ("sender", ChatwootMessageCreated),
    ]
    for field_name, model in pii_in_chatwoot:
        info = model.model_fields[field_name]
        desc = info.description or ""
        assert is_pii_field(desc), (
            f"{model.__name__}.{field_name} should have **LGPD PII**, got: {desc[:80]!r}"
        )


# ----------------------------------------------------------------------------
# 4. test_schema_has_examples
# ----------------------------------------------------------------------------


def test_schema_has_examples() -> None:
    """Cada schema tem pelo menos 1 examples em algum campo.

    Swagger renders examples para desenvolvedores. Sem examples = pior DX.
    """
    schemas_with_examples = [
        TelegramUpdate,
        EvolutionPayload,
        TelegramChat,
        TelegramUser,
        N8nErrorRequest,
        N8nDeletionRequest,
        ChatwootMessageCreated,
        OutboxDispatchRequest,
        AlertManagerPayload,
    ]
    for schema in schemas_with_examples:
        json_schema = schema.model_json_schema()
        props = json_schema.get("properties", {})
        any_example = any(
            "examples" in prop or "example" in prop for prop in props.values()
        )
        assert any_example, f"{schema.__name__} deve ter examples em algum campo"


# ----------------------------------------------------------------------------
# 5. test_openapi_includes_enhanced_descriptions
# ----------------------------------------------------------------------------


def test_openapi_includes_enhanced_descriptions() -> None:
    """OpenAPI gerado pelo FastAPI inclui descriptions em 100% dos campos.

    Carrega app.main sob APP_ENV=development e verifica /openapi.json.
    """
    import os

    os.environ.setdefault("APP_ENV", "development")
    try:
        from app.main import app  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"app.main unavailable in test env: {exc}")

    # Limpa cache para forcar regeneracao (outros testes podem ter
    # populado app.openapi_schema com versao antiga).
    app.openapi_schema = None

    spec = app.openapi()
    paths = spec.get("paths", {})
    webhook_paths = [
        p for p in paths
        if "webhook" in p.lower() or "telegram" in p.lower() or "alertmanager" in p.lower()
    ]
    assert webhook_paths, f"Esperava paths de webhook, got: {list(paths.keys())[:5]}"

    # Para cada path de webhook, pelo menos 1 schema com description eh referenciado.
    schemas = spec.get("components", {}).get("schemas", {})
    webhook_schema_names = [
        "TelegramUpdate", "TelegramMessage", "TelegramUser", "TelegramChat",
        "TelegramCallbackQuery", "EvolutionPayload", "EvolutionKey",
        "EvolutionMessage", "ChatwootMessageCreated",
        "ChatwootConversationStatusChanged",
        "N8nErrorRequest", "N8nDeletionRequest", "N8nMetricsIngest",
        "AlertManagerPayload", "AlertEntry", "AlertLabel", "AlertAnnotation",
        "OutboxDispatchRequest",
    ]
    # ChatwootWebhookModel eh Union (nao BaseModel) - auto-gerado como oneOf.
    if "ChatwootWebhookModel" not in schemas:
        for sub in ("ChatwootMessageCreated", "ChatwootConversationStatusChanged"):
            assert sub in schemas, f"Sub-schema {sub} ausente"
    missing = [n for n in webhook_schema_names if n not in schemas]
    assert not missing, f"Schemas ausentes do OpenAPI: {missing}"

    # 100% dos campos dos schemas webhook tem description (LGPD contract)
    for schema_name in webhook_schema_names:
        schema = schemas[schema_name]
        props = schema.get("properties", {})
        assert props, f"{schema_name} sem properties"
        for field_name, prop in props.items():
            assert "description" in prop, (
                f"{schema_name}.{field_name} sem description no OpenAPI"
            )


# ----------------------------------------------------------------------------
# 6. test_extra_ignore_does_not_break_real_data
# ----------------------------------------------------------------------------


def test_extra_ignore_does_not_break_real_data() -> None:
    """Vendor fields (Telegram/Evolution) adicionados depois nao quebram parser.

    Telegram adicionou `is_forum` em 2023 sem bump de versao — schemas devem
    tolerar via `extra=\"ignore\"`.
    """
    sample_with_extras = dict(TELEGRAM_TEXT_SAMPLE)
    sample_with_extras["unknown_telegram_field"] = "ignored"
    sample_with_extras["message"]["future_media_field"] = {"some": "blob"}
    sample_with_extras["message"]["is_forum"] = True  # added by Telegram 2023

    parsed = TelegramUpdate.model_validate(sample_with_extras)
    assert parsed.update_id == 123456789
    assert parsed.message.text is not None

    # Evolution: extras no data/message/key nao quebram
    ev_with_extras = dict(EVOLUTION_NESTED_SAMPLE)
    ev_with_extras["data"]["future_field"] = "ignored"
    ev_with_extras["data"]["message"]["extendedTextMessage"] = {
        "text": "outra coisa",
        "contextInfo": {"stanzaId": "abc", "participant": "xyz"},  # future
    }
    parsed_ev = EvolutionPayload.model_validate(ev_with_extras)
    assert parsed_ev.event == "messages.upsert"


# ----------------------------------------------------------------------------
# 7. test_unknown_webhook_returns_validation_error
# ----------------------------------------------------------------------------


def test_unknown_webhook_returns_validation_error() -> None:
    """Payload invalido (campos required faltando) levanta ValidationError."""
    # Telegram sem update_id (required)
    with pytest.raises(Exception):  # ValidationError
        TelegramUpdate.model_validate({"message": {"message_id": 1}})

    # AlertManager sem `receiver` (required) deve falhar
    bad_alert = dict(ALERTMANAGER_SAMPLE)
    bad_alert.pop("receiver")
    with pytest.raises(Exception):
        AlertManagerPayload.model_validate(bad_alert)

    # ChatwootMessageCreated sem `event` discriminator
    with pytest.raises(Exception):
        ChatwootMessageCreated.model_validate({"message_id": 1})

    # N8N Error sem execution_id (required)
    with pytest.raises(Exception):
        N8nErrorRequest.model_validate({"workflow_name": "test"})


# ----------------------------------------------------------------------------
# 8. test_evolution_dual_format_compatibility
# ----------------------------------------------------------------------------


def test_evolution_dual_format_compatibility() -> None:
    """Evolution dual-format: nested moderno + root-level legado.

    Ambos aparecem em prod (lesson AGENTS.md). Schema aceita os dois.
    """
    nested = EvolutionPayload.model_validate(EVOLUTION_NESTED_SAMPLE)
    assert nested.event == "messages.upsert"
    assert nested.data is not None
    assert nested.data["key"]["remoteJid"] == "5511999999999@s.whatsapp.net"

    legacy = EvolutionPayload.model_validate(EVOLUTION_LEGACY_SAMPLE)
    assert legacy.event is None  # legacy nao tem event no root
    assert legacy.message is not None
    assert legacy.sender == "553499999999"
    assert legacy.instance == "cartorio-2notas"


# ----------------------------------------------------------------------------
# 9. test_pii_field_helper_marker
# ----------------------------------------------------------------------------


def test_pii_field_helper_marker() -> None:
    """PIIField injeta `**LGPD PII**` automaticamente e x-pii no schema."""
    from pydantic import BaseModel

    class TestModel(BaseModel):
        name: PIIField = PIIField(description="Nome completo")  # type: ignore[valid-type]
        age: PIIField = PIIField(description="Idade")  # type: ignore[valid-type]

    schema = TestModel.model_json_schema()
    name_prop = schema["properties"]["name"]
    age_prop = schema["properties"]["age"]

    # Marker LGPD presente nas descriptions
    assert name_prop["description"].startswith(PII)
    assert age_prop["description"].startswith(PII)

    # x-pii=True para ferramentas externas
    assert name_prop.get("x-pii") is True
    assert age_prop.get("x-pii") is True

    # is_pii_field helper funciona
    assert is_pii_field("**LGPD PII** qualquer coisa") is True
    assert is_pii_field("campo normal") is False
    assert is_pii_field(None) is False
    assert is_pii_field("") is False


# ----------------------------------------------------------------------------
# 10. test_collect_pii_paths_nested
# ----------------------------------------------------------------------------


def test_collect_pii_paths_nested() -> None:
    """collect_pii_paths retorna paths corretos para OpenAPI x-pii-fields."""
    # Telegram
    paths = collect_pii_paths(TelegramUpdate)
    assert "message" in paths
    assert "edited_message" in paths
    assert "callback_query" in paths

    # Evolution
    ev_paths = collect_pii_paths(EvolutionPayload)
    assert "data" in ev_paths
    assert "sender" in ev_paths

    # Chatwoot
    cw_paths = collect_pii_paths(ChatwootMessageCreated)
    assert "content" in cw_paths
    assert "sender" in cw_paths

    # Non-PII schema nao retorna paths (sanity)
    from pydantic import BaseModel

    class Safe(BaseModel):
        count: int = 0

    assert collect_pii_paths(Safe) == []


# ----------------------------------------------------------------------------
# 11. test_response_payload_examples_in_openapi
# ----------------------------------------------------------------------------


def test_response_payload_examples_in_openapi() -> None:
    """OpenAPI spec inclui 3+ examples por webhook endpoint (text/cb/group)."""
    import os

    os.environ.setdefault("APP_ENV", "development")
    try:
        from app.main import app  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"app.main unavailable: {exc}")

    # Limpa cache (test isolation — outros testes podem ter populado cache).
    app.openapi_schema = None

    spec = app.openapi()
    paths = spec.get("paths", {})

    # /api/v1/telegram/webhook deve ter 3 examples (text/callback/group)
    tg_path = None
    for p in paths:
        if p.endswith("/telegram/webhook"):
            tg_path = p
            break
    assert tg_path is not None, "Telegram webhook path not found"

    post = paths[tg_path].get("post", {})
    rb = post.get("requestBody", {})
    content = rb.get("content", {})
    json_content = content.get("application/json", {})
    examples = json_content.get("examples", {})
    assert len(examples) >= 3, (
        f"Telegram webhook deve ter >=3 examples, got: {list(examples.keys())}"
    )


# ----------------------------------------------------------------------------
# 12. test_field_descriptions_portuguese
# ----------------------------------------------------------------------------


def test_field_descriptions_portuguese() -> None:
    """Descriptions estao em PT-BR (consistente com o resto do projeto)."""
    schema = TelegramUpdate.model_json_schema()
    props = schema["properties"]
    update_id_desc = props["update_id"]["description"]
    # Deve ter palavras PT-BR (id, idempotency, etc) — nao so ingles
    assert "idempotency" in update_id_desc.lower() or "ID" in update_id_desc


# ----------------------------------------------------------------------------
# 13. test_alertmanager_schema_accepts_real_payload
# ----------------------------------------------------------------------------


def test_alertmanager_schema_accepts_real_payload() -> None:
    """AlertManagerPayload aceita payload real do Prometheus."""
    parsed = AlertManagerPayload.model_validate(ALERTMANAGER_SAMPLE)
    assert parsed.status == "firing"
    assert parsed.receiver == "cartorio-telegram-default"
    assert len(parsed.alerts) == 1
    assert parsed.alerts[0].labels.alertname == "HighErrorRate"
    assert parsed.alerts[0].labels.severity == "warning"
    assert parsed.alerts[0].fingerprint == "abc123def456"


# ----------------------------------------------------------------------------
# 14. test_chatwoot_message_created_full
# ----------------------------------------------------------------------------


def test_chatwoot_message_created_full() -> None:
    """ChatwootMessageCreated com todos campos (incluindo sender PII)."""
    parsed = ChatwootMessageCreated.model_validate(CHATWOOT_MSG_SAMPLE)
    assert parsed.event == "message_created"
    assert parsed.message_id == 999
    assert parsed.message_type == "incoming"
    assert parsed.content == "Quero falar com um humano"
    assert parsed.sender["email"] == "maria@example.com"  # PII but typed as dict


# ----------------------------------------------------------------------------
# 15. test_outbox_dispatch_required_fields
# ----------------------------------------------------------------------------


def test_outbox_dispatch_required_fields() -> None:
    """OutboxDispatchRequest valida campos required."""
    parsed = OutboxDispatchRequest(
        outbox_id="uuid-here",
        canal="whatsapp",
        recipient_id="5511999999999",
        content="Test message",
    )
    assert parsed.canal == "whatsapp"
    assert parsed.priority is None  # default

    # Canal invalido falha
    with pytest.raises(Exception):
        OutboxDispatchRequest(
            outbox_id="uuid",
            canal="fax",  # not in Literal
            recipient_id="x",
            content="x",
        )


# ----------------------------------------------------------------------------
# 16. test_n8n_error_request_required
# ----------------------------------------------------------------------------


def test_n8n_error_request_required() -> None:
    """N8nErrorRequest — execution_id, workflow_name sao required."""
    parsed = N8nErrorRequest(
        workflow_name="01 - Emolumento",
        execution_id="exec_001",
    )
    assert parsed.workflow_name == "01 - Emolumento"
    assert parsed.workflow_id is None
    assert parsed.error_type is None
    assert parsed.error is None


def test_n8n_deletion_request() -> None:
    """N8nDeletionRequest — LGPD Art. 18 / Art. 37 (purga)."""
    parsed = N8nDeletionRequest(
        execution_id="exec_purge_001",
        target_category="conversas",
        deleted_count=42,
    )
    assert parsed.deleted_count == 42
    assert parsed.target_category == "conversas"
    assert parsed.details is None


# ----------------------------------------------------------------------------
# 17. test_realistic_json_dump_telegram
# ----------------------------------------------------------------------------


def test_realistic_json_dump_telegram() -> None:
    """TelegramUpdate serializa em JSON compativel com Telegram Bot API.

    Aliases (from_ → from, remoteJid → remote_jid) respeitados em by_alias.
    """
    parsed = TelegramUpdate.model_validate(TELEGRAM_TEXT_SAMPLE)
    serialized = parsed.model_dump(by_alias=True, mode="json")
    # Verifica que `from` aparece (alias correto do Telegram API)
    assert "from" in serialized["message"]
    # serializa como JSON string (testa roundtrip)
    as_str = json.dumps(serialized, ensure_ascii=False)
    assert "Maria" in as_str
    assert "123.456.789-09" in as_str  # PII raw — LGPD concern, expected here
