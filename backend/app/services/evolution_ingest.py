"""Service evolution_ingest - normaliza eventos do Evolution API.

Quando o Evolution API envia um webhook, extraimos:
- event_type (messages.upsert e o unico que processamos)
- message_id (id do WhatsApp, pra idempotencia)
- sender (remoteJid)
- text (conversation ou extendedTextMessage.text)
- instance

Idempotencia: gravamos (source='evolution', event_id=message_id) na tabela
webhook_events. Se ja existe, retornamos 'idempotent' sem reprocessar.

LGPD: o payload bruto NAO e persistido. Apenas o hash SHA256 dele vai pra
webhook_events.payload_hash (auditoria, sem dado pessoal).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.webhook_event import WebhookEvent

log = logging.getLogger(__name__)


def _webhook_secrets() -> tuple[str, str]:
    """Retorna (current, prev) secrets de webhook Evolution (env dinâmico)."""
    return (
        os.getenv("EVOLUTION_WEBHOOK_SECRET") or "",
        os.getenv("EVOLUTION_WEBHOOK_SECRET_PREV") or "",
    )


def _secret_header_match(provided: str | None, secrets: tuple[str, str]) -> bool:
    """Compara header compartilhado (timing-safe) com secrets ativos."""
    if not provided:
        return False
    candidate = provided.strip()
    # Aceita "Bearer <secret>" além do valor puro.
    if candidate.lower().startswith("bearer "):
        candidate = candidate[7:].strip()
    for key in secrets:
        if key and hmac.compare_digest(candidate, key):
            return True
    return False


def validate_evolution_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    """Valida HMAC-SHA256 do body do webhook Evolution.

    Retorna True se:
    - Signature corresponde ao HMAC-SHA256(raw_body, EVOLUTION_WEBHOOK_SECRET), ou
    - Signature corresponde ao secret anterior (EVOLUTION_WEBHOOK_SECRET_PREV)
      durante janela de rotacao 90d (G7.10.T3), ou
    - Secret NAO esta configurado (dev mode - loga warning).

    Retorna False se:
    - Secret configurado mas signature ausente, ou
    - Signature fornecida mas nao corresponde a nenhum secret ativo.

    Suporta formato `sha256=<hex>` (estilo GitHub/Stripe) alem do hex puro.
    Comparacao sempre timing-safe via hmac.compare_digest.
    """
    # Le env var dinamicamente (NAO usa settings cache) - permite teste monkeypatch
    secret, secret_prev = _webhook_secrets()
    if not secret and not secret_prev:
        log.warning("evolution webhook: EVOLUTION_WEBHOOK_SECRET nao configurado, dev mode")
        return True
    if not signature:
        return False
    # Strip prefix "sha256=" se presente
    sig_hex = signature
    if sig_hex.startswith("sha256="):
        sig_hex = sig_hex[len("sha256=") :]

    def _match(key: str) -> bool:
        if not key:
            return False
        expected = hmac.new(key.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig_hex)

    # Aceita current OU previous (rotacao zero-downtime).
    if _match(secret) or _match(secret_prev):
        return True
    return False


def validate_evolution_webhook_auth(
    raw_body: bytes,
    signature: Optional[str] = None,
    shared_secret_header: Optional[str] = None,
) -> bool:
    """Auth do webhook Evolution: HMAC **ou** header secreto compartilhado.

    Evolution API (Baileys) frequentemente **não** assina o body com
    X-Hub-Signature-256. Em produção aceitamos, de forma fail-closed:

    1. HMAC válido (X-Hub-Signature-256 / X-Evolution-Signature), **ou**
    2. Header estático igual ao secret:
       ``X-Evolution-Webhook-Secret`` / ``X-Webhook-Secret`` / ``Authorization: Bearer …``

    Sem secret configurado → dev mode (True + warning), igual ao HMAC-only.
    Comparações sempre timing-safe. Nunca loga o valor do secret.
    """
    secret, secret_prev = _webhook_secrets()
    if not secret and not secret_prev:
        log.warning("evolution webhook: EVOLUTION_WEBHOOK_SECRET nao configurado, dev mode")
        return True
    if validate_evolution_signature(raw_body, signature):
        return True
    if _secret_header_match(shared_secret_header, (secret, secret_prev)):
        return True
    return False


def ingest_evolution_event(
    db: Session,
    payload: dict[str, Any],
    raw_body: Optional[bytes] = None,
    signature: Optional[str] = None,
) -> dict[str, Any]:
    """Normaliza e processa um evento do Evolution API.

    Returns:
        dict com:
        - status: 'accepted' | 'idempotent' | 'ignored' | 'rejected'
        - reason: string descritiva se nao accepted
        - event_type, message_id, sender, text, instance (se accepted)
    """
    # A8: validar HMAC signature se raw_body fornecido
    if raw_body is not None and not validate_evolution_signature(raw_body, signature):
        log.warning("evolution_ingest: signature invalida (len=%d)", len(signature or ""))
        return {"status": "rejected", "reason": "invalid_signature"}

    event = payload.get("event", "")
    instance = payload.get("instance", "")

    # Filtro: so processamos MESSAGES_UPSERT (com varias variacoes de casing)
    if not event.lower().endswith("messages.upsert"):
        return {"status": "ignored", "reason": "event_not_messages_upsert", "event": event}

    data = payload.get("data")
    if not isinstance(data, dict):
        return {"status": "rejected", "reason": "missing_data"}

    key = data.get("key") or {}
    message = data.get("message") or {}

    message_id = key.get("id")
    sender = key.get("remoteJid")

    # Texto pode estar em varios campos dependendo do tipo de msg
    text = (
        message.get("conversation")
        or message.get("extendedTextMessage", {}).get("text")
        or message.get("imageMessage", {}).get("caption")
        or ""
    )

    if not message_id or not sender:
        return {
            "status": "rejected",
            "reason": "missing_message_id_or_sender",
            "message_id": message_id,
            "sender": sender,
        }

    # Idempotencia: checa se ja processamos esse message_id
    existing = db.execute(
        select(WebhookEvent).where(
            WebhookEvent.source == "evolution",
            WebhookEvent.event_id == message_id,
        )
    ).scalar_one_or_none()

    if existing is not None:
        log.info("evolution_ingest idempotent: message_id=%s ja processado", message_id)
        return {"status": "idempotent", "message_id": message_id}

    # Grava evento pra idempotencia
    payload_str = str(payload).encode("utf-8")
    payload_hash = hashlib.sha256(payload_str).hexdigest()
    db.add(
        WebhookEvent(
            source="evolution",
            event_id=message_id,
            payload_hash=payload_hash,
        )
    )
    db.flush()

    log.info(
        "evolution_ingest accepted: message_id=%s sender=%s instance=%s",
        message_id,
        sender,
        instance,
    )
    return {
        "status": "accepted",
        "event_type": event,
        "message_id": message_id,
        "sender": sender,
        "text": text,
        "instance": instance,
    }
