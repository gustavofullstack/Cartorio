"""Allowlist HMAC para remetentes da Pietra no WhatsApp.

Telefones e hashes de contatos sao configuracao secreta e nunca ficam no Git.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass


_NON_DIGITS = re.compile(r"\D+")


@dataclass(frozen=True)
class WhatsAppAccessDecision:
    allowed: bool
    reason: str


def normalize_whatsapp_number(value: str | None) -> str | None:
    """Normaliza telefone brasileiro/JID em E.164, ou retorna ``None``."""
    raw = (value or "").strip()
    if not raw or "@g.us" in raw or "@broadcast" in raw or raw.endswith("@lid"):
        return None
    digits = _NON_DIGITS.sub("", raw.split("@", maxsplit=1)[0]).lstrip("0")
    national = digits[2:] if digits.startswith("55") else digits
    if len(national) == 10 and national[2] in "6789":
        national = national[:2] + "9" + national[2:]
    if len(national) != 11:
        return None
    return f"+55{national}"


def hmac_sender(number: str, *, hmac_key: str) -> str:
    if len(hmac_key) < 32:
        raise ValueError("allowlist HMAC key must have at least 32 characters")
    return hmac.new(hmac_key.encode(), number.encode(), hashlib.sha256).hexdigest()


def pseudonymous_sender_id(value: str, *, hmac_key: str) -> str:
    """Pseudonimo estavel para chaves/cache sem reter JID ou telefone."""
    if len(hmac_key) < 32:
        raise ValueError("allowlist HMAC key must have at least 32 characters")
    return hmac.new(hmac_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def parse_allowed_sender_hashes(value: str) -> frozenset[str]:
    return frozenset(
        item.strip().lower()
        for item in value.split(",")
        if re.fullmatch(r"[0-9a-fA-F]{64}", item.strip())
    )


def decide_whatsapp_access(
    sender_id: str,
    *,
    sender_id_alt: str | None,
    allowed_sender_hashes: str,
    hmac_key: str,
    restrict_inbound: bool,
) -> WhatsAppAccessDecision:
    """Decide acesso sem persistir telefone; modo restrito falha fechado."""
    if not restrict_inbound:
        return WhatsAppAccessDecision(True, "allowlist_disabled")
    if len(hmac_key) < 32:
        return WhatsAppAccessDecision(False, "allowlist_key_not_configured")
    allowed = parse_allowed_sender_hashes(allowed_sender_hashes)
    if not allowed:
        return WhatsAppAccessDecision(False, "allowlist_not_configured")
    candidates = {
        hmac_sender(normalized, hmac_key=hmac_key)
        for normalized in (
            normalize_whatsapp_number(sender_id),
            normalize_whatsapp_number(sender_id_alt),
        )
        if normalized
    }
    if not candidates:
        return WhatsAppAccessDecision(False, "sender_not_normalizable")
    if candidates.isdisjoint(allowed):
        return WhatsAppAccessDecision(False, "sender_not_allowed")
    return WhatsAppAccessDecision(True, "sender_allowed")
