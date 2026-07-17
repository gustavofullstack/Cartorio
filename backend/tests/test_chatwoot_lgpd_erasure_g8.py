"""G8.03.T4 — LGPD Art. 18 erasure/anonymization path (Chatwoot-linked).

Unit tests for local plan + contact scrubbing (no Chatwoot API).
"""

from __future__ import annotations

import json

import pytest

from app.services.chatwoot_lgpd_erasure import (
    ERASURE_ACTIONS,
    ChatwootErasurePlan,
    apply_local_anonymization,
    plan_erasure,
    plan_with_anonymization,
    validate_no_raw_cpf,
)


def test_plan_erasure_has_canonical_actions() -> None:
    plan = plan_erasure("conv-42")
    assert isinstance(plan, ChatwootErasurePlan)
    assert plan.conversation_id == "conv-42"
    assert plan.actions == list(ERASURE_ACTIONS)
    assert plan.actions == [
        "mute_clear",
        "soft_delete_local",
        "anonymize_contact_attrs",
        "audit_log",
    ]
    assert plan.pii_fields_scrubbed == []


def test_plan_erasure_strips_conversation_id() -> None:
    plan = plan_erasure("  99  ")
    assert plan.conversation_id == "99"


def test_plan_erasure_requires_conversation_id() -> None:
    with pytest.raises(ValueError, match="conversation_id"):
        plan_erasure("")
    with pytest.raises(ValueError, match="conversation_id"):
        plan_erasure("   ")


def test_apply_local_anonymization_scrubs_phone_email_name() -> None:
    profile = {
        "name": "Maria Souza",
        "email": "maria@example.com",
        "phone": "+55 34 99876-5432",
        "conversation_id": "cw-1",
        "inbox_id": 7,
    }
    out = apply_local_anonymization(profile)

    assert out["name"] == "[ANONIMIZADO art.18 V]"
    assert out["email"].startswith("[EMAIL_HASH:")
    assert out["phone"].startswith("[PHONE_HASH:")
    assert out["conversation_id"] == "cw-1"
    assert out["inbox_id"] == 7
    assert set(out["_pii_fields_scrubbed"]) == {"name", "email", "phone"}

    # raw values must not remain
    blob = json.dumps(out, ensure_ascii=False)
    assert "Maria Souza" not in blob
    assert "maria@example.com" not in blob
    assert "99876" not in blob
    assert validate_no_raw_cpf(blob) is True


def test_apply_local_anonymization_hashes_cpf_field() -> None:
    profile = {"cpf": "529.982.247-25", "nome": "João"}
    out = apply_local_anonymization(profile)
    assert out["cpf"].startswith("[CPF_HASH:")
    assert out["nome"] == "[ANONIMIZADO art.18 V]"
    assert "529" not in out["cpf"]
    assert validate_no_raw_cpf(json.dumps(out)) is True


def test_apply_local_anonymization_idempotent_on_placeholders() -> None:
    once = apply_local_anonymization(
        {"name": "A", "email": "a@b.co", "phone": "34999999999"}
    )
    twice = apply_local_anonymization(
        {
            "name": once["name"],
            "email": once["email"],
            "phone": once["phone"],
        }
    )
    # Still placeholders / hashes; never reintroduce raw PII
    assert twice["name"] == "[ANONIMIZADO art.18 V]"
    assert twice["email"].startswith("[EMAIL_HASH:")
    assert twice["phone"].startswith("[PHONE_HASH:")


def test_apply_local_anonymization_rejects_non_dict() -> None:
    with pytest.raises(TypeError):
        apply_local_anonymization("not-a-dict")  # type: ignore[arg-type]


def test_validate_no_raw_cpf_detects_formatted_and_digits() -> None:
    assert validate_no_raw_cpf(None) is True
    assert validate_no_raw_cpf("") is True
    assert validate_no_raw_cpf("protocolo OK sem documento") is True
    assert validate_no_raw_cpf("contato: ***.***.***-**") is True

    assert validate_no_raw_cpf("CPF 529.982.247-25 inválido") is False
    assert validate_no_raw_cpf("cpf=52998224725") is False
    assert validate_no_raw_cpf("52998224725") is False


def test_plan_with_anonymization_fills_pii_fields() -> None:
    plan, anon = plan_with_anonymization(
        "cw-77",
        {"name": "X", "email": "x@y.z", "phone": "11999990000", "role": "contact"},
    )
    assert plan.conversation_id == "cw-77"
    assert "anonymize_contact_attrs" in plan.actions
    assert set(plan.pii_fields_scrubbed) == {"name", "email", "phone"}
    assert anon["role"] == "contact"
    assert validate_no_raw_cpf(json.dumps(anon, ensure_ascii=False)) is True


def test_erasure_plan_actions_order_stable() -> None:
    """Ordem Art. 18: mute → soft-delete → anonymize → audit."""
    a = plan_erasure("1").actions
    b = plan_erasure("2").actions
    assert a == b
    assert a.index("mute_clear") < a.index("soft_delete_local")
    assert a.index("soft_delete_local") < a.index("anonymize_contact_attrs")
    assert a.index("anonymize_contact_attrs") < a.index("audit_log")
