"""Service chatwoot_handoff - processa webhooks do Chatwoot.

Quando o Chatwoot notifica que uma conversa foi resolvida (humano finalizou),
atualizamos o atendimento correspondente no DB. Tambem aceitamos message_created
como evento neutro (logar + idempotencia).

Seguranca:
- Se CHATWOOT_WEBHOOK_SECRET estiver setado, validamos HMAC-SHA256 do body.
- Caso contrario, aceitamos sem signature (dev only - NAO recomendado em prod).

Idempotencia: gravamos (source='chatwoot', event_id=payload.id) na tabela
webhook_events. Replay nao duplica.

LGPD: payload bruto NAO e persistido, apenas hash SHA256.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.atendimento import Atendimento
from app.models.webhook_event import WebhookEvent
from app.services.audit import AuditService

log = logging.getLogger(__name__)


def _validate_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    """Valida HMAC-SHA256 do body. Retorna True se OK ou se secret nao configurado."""
    secret = settings.chatwoot_webhook_secret
    if not secret:
        return True  # dev mode: aceita sem signature
    if not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def process_chatwoot_event(
    db: Session,
    payload: dict[str, Any],
    signature: Optional[str] = None,
    raw_body: Optional[bytes] = None,
) -> dict[str, Any]:
    """Processa um evento do Chatwoot.

    Args:
        db: sessao SQLAlchemy
        payload: dict ja parseado do JSON
        signature: header X-Chatwoot-Signature (opcional se secret nao configurado)
        raw_body: bytes brutos do request (necessario pra validar signature)

    Returns:
        dict com status, event_type, reason (se aplicavel)
    """
    # 1. Validar signature se raw_body fornecido
    if raw_body is not None and not _validate_signature(raw_body, signature):
        log.warning("chatwoot_handoff: signature invalida (len=%d)", len(signature or ""))
        return {"status": "rejected", "reason": "invalid_signature"}

    event = payload.get("event", "unknown")
    event_id = str(payload.get("id") or payload.get("message_id") or "")

    # 2. Idempotencia
    if event_id:
        existing = db.execute(
            select(WebhookEvent).where(
                WebhookEvent.source == "chatwoot",
                WebhookEvent.event_id == event_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            log.info("chatwoot_handoff idempotent: event_id=%s", event_id)
            return {"status": "idempotent", "event_id": event_id, "event": event}

    # 3. Processar evento especifico
    if event == "conversation_status_changed":
        _handle_status_changed(db, payload)
    elif event == "message_created":
        log.info(
            "chatwoot_handoff: message_created em conv %s",
            payload.get("conversation", {}).get("id"),
        )
    else:
        if event_id:
            _save_event(db, source="chatwoot", event_id=event_id, payload=payload)
        return {"status": "ignored", "event": event, "reason": "event_not_handled"}

    # 4. Gravar evento pra idempotencia (sucesso)
    if event_id:
        _save_event(db, source="chatwoot", event_id=event_id, payload=payload)

    return {"status": "processed", "event_type": event, "event_id": event_id}


def _handle_status_changed(db: Session, payload: dict[str, Any]) -> None:
    """Se status=resolved, marca atendimento como concluido."""
    status = payload.get("status") or payload.get("conversation", {}).get("status")
    conv_id = payload.get("conversation", {}).get("id")

    if status != "resolved" or not conv_id:
        return

    atendimento = db.execute(
        select(Atendimento).where(Atendimento.chatwoot_conversation_id == conv_id)
    ).scalar_one_or_none()

    if atendimento and not atendimento.concluido_em:
        atendimento.concluido_em = datetime.now(timezone.utc)
        atendimento.status = "concluido"

        AuditService.log(
            db,
            actor_id=f"chatwoot:{conv_id}",
            action="atendimento.concluido",
            resource=f"atendimento:{atendimento.id}",
            actor_type="agent",
            payload={"chatwoot_conversation_id": conv_id},
        )


def _save_event(db: Session, source: str, event_id: str, payload: dict[str, Any]) -> None:
    """Grava WebhookEvent pra idempotencia."""
    payload_hash = hashlib.sha256(str(payload).encode("utf-8")).hexdigest()
    db.add(WebhookEvent(source=source, event_id=event_id, payload_hash=payload_hash))
    db.flush()
