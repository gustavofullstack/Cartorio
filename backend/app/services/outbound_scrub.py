"""Scrub de SAIDA com allowlist de contatos institucionais publicos.

Extraido do path Telegram para o WhatsApp nao redatar dpo@2notasudi.com.br.
"""

from __future__ import annotations

import re

from app.services.pii import scrub

_OFFICIAL_OUTBOUND_PROTECT: tuple[tuple[str, str], ...] = (
    ("dpo@2notasudi.com.br", "\x00DPO_EMAIL\x00"),
    ("DPO@2notasudi.com.br", "\x00DPO_EMAIL\x00"),
    ("contato@2notasudi.com.br", "\x00CONTATO_EMAIL\x00"),
    ("https://api.2notasudi.com.br", "\x00API_URL\x00"),
    ("https://2notasudi.com.br", "\x00SITE_URL\x00"),
)
_OFFICIAL_OUTBOUND_RESTORE: tuple[tuple[str, str], ...] = (
    ("\x00DPO_EMAIL\x00", "dpo@2notasudi.com.br"),
    ("\x00CONTATO_EMAIL\x00", "contato@2notasudi.com.br"),
    ("\x00API_URL\x00", "https://api.2notasudi.com.br"),
    ("\x00SITE_URL\x00", "https://2notasudi.com.br"),
)


def protect_official_outbound(text: str) -> str:
    protected = text
    for real, token in _OFFICIAL_OUTBOUND_PROTECT:
        protected = re.sub(
            rf"(?<![\w.+-]){re.escape(real)}(?=$|[\s,;:!?\)\]\}}]|\.(?=\s|$))",
            token,
            protected,
        )
    return protected


def restore_official_outbound(text: str) -> str:
    restored = text
    for token, real in _OFFICIAL_OUTBOUND_RESTORE:
        restored = restored.replace(token, real)
    return restored


def scrub_bot_outbound(text: str) -> str:
    if not text:
        return text
    scrubbed = scrub(protect_official_outbound(text)).text
    scrubbed = restore_official_outbound(scrubbed)
    scrubbed = scrubbed.replace(
        "Direitos LGPD: [EMAIL_REDACTED]",
        "Direitos LGPD: dpo@2notasudi.com.br",
    )
    return scrubbed
