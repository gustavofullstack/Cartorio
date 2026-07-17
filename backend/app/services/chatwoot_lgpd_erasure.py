"""G8.03.T4 — LGPD Art. 18 erasure/anonymization path for Chatwoot-linked data.

Validates the local plan + anonymization steps for Chatwoot conversation PII
without calling the external Chatwoot API. Complements
`lgpd_erasure_orchestrator` (titular/cliente) and `bot_mute` (HITL mute).

Steps of a plan (Art. 18 IV/V — eliminação/anonimização):
1. mute_clear — limpa mute Redis da conversa (HITL residual)
2. soft_delete_local — marca metadados locais da conversa como deleted
3. anonymize_contact_attrs — scrub/hash de phone/email/name em profile local
4. audit_log — registra evento append-only (sem raw PII)

LGPD: placeholders/hashes apenas; nunca persistir CPF/email/telefone raw.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

# CPF com ou sem pontuação (mesmo shape de app.services.pii)
_RAW_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")

# Campos de contato comuns em payloads/meta Chatwoot (local mirror)
_NAME_KEYS = frozenset({"name", "nome", "full_name", "display_name"})
_EMAIL_KEYS = frozenset({"email", "e_mail", "mail"})
_PHONE_KEYS = frozenset({"phone", "phone_number", "telefone", "mobile", "whatsapp"})
_CPF_KEYS = frozenset({"cpf", "document", "documento"})

_PLACEHOLDER_NAME = "[ANONIMIZADO art.18 V]"
_PLACEHOLDER_EMAIL = "anon@invalid.local"
_PLACEHOLDER_PHONE = "[PHONE_REDACTED]"
_PLACEHOLDER_CPF = "[CPF_REDACTED]"

ERASURE_ACTIONS: tuple[str, ...] = (
    "mute_clear",
    "soft_delete_local",
    "anonymize_contact_attrs",
    "audit_log",
)


@dataclass(slots=True)
class ChatwootErasurePlan:
    """Plano local de erasure para conversa Chatwoot-linked (LGPD Art. 18)."""

    conversation_id: str
    actions: list[str] = field(default_factory=list)
    pii_fields_scrubbed: list[str] = field(default_factory=list)


def _hash_placeholder(value: str, *, kind: str) -> str:
    """SHA256 prefix placeholder (irreversível, sem raw PII)."""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"[{kind}_HASH:{digest}]"


def plan_erasure(conversation_id: str) -> ChatwootErasurePlan:
    """Monta o plano de exclusão/anonimização para uma conversa Chatwoot.

    Args:
        conversation_id: ID opaco da conversa (sem PII).

    Returns:
        ChatwootErasurePlan com actions canônicas Art. 18.
    """
    cid = str(conversation_id or "").strip()
    if not cid:
        raise ValueError("conversation_id required")

    return ChatwootErasurePlan(
        conversation_id=cid,
        actions=list(ERASURE_ACTIONS),
        pii_fields_scrubbed=[],  # preenchido após apply_local_anonymization
    )


def apply_local_anonymization(profile: dict[str, Any]) -> dict[str, Any]:
    """Anonimiza atributos de contato em um profile local (sem API Chatwoot).

    Scrub/hash de name, email, phone (e cpf se presente). Campos desconhecidos
    são copiados; strings com CPF raw embutido são validadas pelo caller via
    ``validate_no_raw_cpf``.

    Returns:
        Novo dict com placeholders/hashes; lista de campos em
        ``_pii_fields_scrubbed`` (meta interna, não PII).
    """
    if not isinstance(profile, dict):
        raise TypeError("profile must be a dict")

    out: dict[str, Any] = {}
    scrubbed: list[str] = []

    for key, value in profile.items():
        key_l = str(key).lower()
        if not isinstance(value, str) or not value.strip():
            out[key] = value
            continue

        if key_l in _NAME_KEYS:
            out[key] = _PLACEHOLDER_NAME
            scrubbed.append(str(key))
        elif key_l in _EMAIL_KEYS:
            out[key] = _hash_placeholder(value.strip().lower(), kind="EMAIL")
            scrubbed.append(str(key))
        elif key_l in _PHONE_KEYS:
            digits = re.sub(r"\D", "", value)
            seed = digits or value.strip()
            out[key] = _hash_placeholder(seed, kind="PHONE")
            scrubbed.append(str(key))
        elif key_l in _CPF_KEYS:
            digits = re.sub(r"\D", "", value)
            seed = digits or value.strip()
            out[key] = _hash_placeholder(seed, kind="CPF")
            scrubbed.append(str(key))
        else:
            out[key] = value

    out["_pii_fields_scrubbed"] = scrubbed
    return out


def validate_no_raw_cpf(text: str | None) -> bool:
    """True se o texto **não** contém CPF raw (formatado ou só dígitos).

    Usado para validar payloads/logs pós-anonimização (Art. 18 + Art. 46).
    """
    if text is None:
        return True
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return True
    return _RAW_CPF_RE.search(text) is None


def plan_with_anonymization(
    conversation_id: str,
    profile: dict[str, Any],
) -> tuple[ChatwootErasurePlan, dict[str, Any]]:
    """Helper: plan_erasure + apply_local_anonymization e preenche pii_fields_scrubbed."""
    plan = plan_erasure(conversation_id)
    anon = apply_local_anonymization(profile)
    scrubbed = list(anon.get("_pii_fields_scrubbed") or [])
    plan.pii_fields_scrubbed = scrubbed
    return plan, anon


__all__ = [
    "ChatwootErasurePlan",
    "ERASURE_ACTIONS",
    "apply_local_anonymization",
    "plan_erasure",
    "plan_with_anonymization",
    "validate_no_raw_cpf",
]
