"""Controle de acesso de remetentes para a Pietra no WhatsApp.

O webhook da Evolution pode identificar uma conversa por JID comum ou por LID.
O controle compara hashes HMAC do E.164, usando ``remoteJidAlt`` quando existir.

Piloto 2026-08-11: com restrict_inbound=True e hashes vazios, somente
Felipe Pizarro (+55 34 99880-7228) e Gustavo Almeida (+55 34 99280-0250).
Nao depende de APP_ENV — producao ja rodou com APP_ENV=test e isso abria o bot.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Final

_NON_DIGITS = re.compile(r"\D+")

# E.164 canonico dos unicos numeros do piloto WhatsApp (Felipe, Gustavo).
PIETRA_WHATSAPP_PILOT_E164: Final[tuple[str, ...]] = (
    "+5534998807228",
    "+5534992800250",
)


@dataclass(frozen=True)
class WhatsAppAccessDecision:
    """Decisao de acesso sem reter o numero do remetente."""

    allowed: bool
    reason: str


def normalize_whatsapp_number(value: str | None) -> str | None:
    """Normaliza um numero brasileiro/JID em E.164, ou retorna ``None``.

    Aceita 13 digitos (55+DDD+9+8), 12 (55+DDD+8, insere o 9 movel),
    11 (DDD+9+8) e 10 (DDD+8). JIDs de grupo, broadcast e LID nao sao
    numeros verificaveis por si so — LID autoriza so via ``remoteJidAlt``.
    """
    raw = (value or "").strip()
    if not raw or "@g.us" in raw or "@broadcast" in raw or raw.endswith("@lid"):
        return None
    local = raw.split("@", maxsplit=1)[0]
    digits = _NON_DIGITS.sub("", local).lstrip("0")
    if not digits:
        return None
    national = digits[2:] if digits.startswith("55") else digits
    if len(national) == 10 and national[2] in "6789":
        national = national[:2] + "9" + national[2:]
    if len(national) != 11:
        return None
    return f"+55{national}"


def hmac_sender(number: str, *, hmac_key: str) -> str:
    """Gera o identificador HMAC do telefone normalizado para a allowlist."""
    if len(hmac_key) < 32:
        raise ValueError("allowlist HMAC key must have at least 32 characters")
    return hmac.new(hmac_key.encode("utf-8"), number.encode("utf-8"), hashlib.sha256).hexdigest()


def parse_allowed_sender_hashes(value: str) -> frozenset[str]:
    """Converte a lista CSV de hashes HMAC em um conjunto validado."""
    return frozenset(
        candidate.strip().lower()
        for candidate in value.split(",")
        if re.fullmatch(r"[0-9a-fA-F]{64}", candidate.strip())
    )


def resolve_allowlist_hmac_key(dedicated_key: str, audit_hmac_key: str) -> str:
    """Prefere chave dedicada; cai na chave de auditoria se ela tiver 32+ chars."""
    dedicated = (dedicated_key or "").strip()
    if len(dedicated) >= 32:
        return dedicated
    fallback = (audit_hmac_key or "").strip()
    return fallback if len(fallback) >= 32 else dedicated


def decide_whatsapp_access(
    sender_id: str,
    *,
    sender_id_alt: str | None,
    allowed_sender_hashes: str,
    hmac_key: str,
    app_env: str,
    restrict_inbound: bool | None = None,
) -> WhatsAppAccessDecision:
    """Aplica allowlist no remetente antes de consentimento ou chamada de IA.

    ``restrict_inbound=True`` (default de producao): hashes vazios caem no
    piloto Felipe+Gustavo. Nao usa APP_ENV para decidir.

    ``restrict_inbound=False``: deixa a suíte local testavel.
    """
    _ = app_env
    if restrict_inbound is False:
        return WhatsAppAccessDecision(True, "allowlist_disabled_nonproduction")
    if len(hmac_key) < 32:
        return WhatsAppAccessDecision(False, "allowlist_key_not_configured")

    allowed = parse_allowed_sender_hashes(allowed_sender_hashes)
    using_pilot = False
    if not allowed:
        allowed = frozenset(
            hmac_sender(number, hmac_key=hmac_key) for number in PIETRA_WHATSAPP_PILOT_E164
        )
        using_pilot = True
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
    reason = "sender_allowed_pilot" if using_pilot else "sender_allowed"
    return WhatsAppAccessDecision(True, reason)
