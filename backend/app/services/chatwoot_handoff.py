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
        _handle_message_created(db, payload)
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


def _handle_message_created(db: Session, payload: dict[str, Any]) -> None:
    """Processa message_created do Chatwoot.

    Se message_type == 'outgoing' (escrevente respondeu),
    reenvia a mensagem ao Telegram do cliente correspondente.
    Mensagens 'incoming' (do cliente) são apenas logadas (já vieram do Telegram).
    """
    message_type = payload.get("message_type")
    content = payload.get("content", "")
    conv = payload.get("conversation", {})
    conv_id = conv.get("id")
    sender = payload.get("sender", {})
    sender_name = sender.get("name", "Escrevente")

    log.info(
        "chatwoot_handoff: message_created conv=%s type=%s sender=%s",
        conv_id,
        message_type,
        sender_name,
    )

    # Só faz sync bidirecional para mensagens outgoing (escrevente → cliente)
    if message_type != "outgoing" or not content or not conv_id:
        return

    # Busca o atendimento para encontrar o chat_id do Telegram
    atendimento = db.execute(
        select(Atendimento).where(Atendimento.chatwoot_conversation_id == conv_id)
    ).scalar_one_or_none()

    if not atendimento:
        log.warning("chatwoot sync: atendimento nao encontrado para conv %s", conv_id)
        return

    telegram_chat_id = atendimento.canal  # canal armazena telegram_chat_id quando aplicavel
    if not telegram_chat_id:
        log.warning("chatwoot sync: chat_id Telegram nao encontrado para atendimento %s", atendimento.id)
        return

    # Envia a mensagem de volta ao Telegram via bot API (async fire-and-forget)
    import asyncio

    asyncio.create_task(_send_to_telegram(telegram_chat_id, content, sender_name, conv_id))

    # Audit log da mensagem bidirecional
    AuditService.log(
        db,
        actor_id=f"chatwoot:{sender.get('id', 'unknown')}",
        action="chatwoot.sync.outgoing_to_telegram",
        resource=f"atendimento:{atendimento.id}",
        actor_type="agent",
        payload={
            "chatwoot_conversation_id": conv_id,
            "telegram_chat_id": str(telegram_chat_id),
            "sender_name": sender_name,
            "content_length": len(content),
        },
    )


async def _send_to_telegram(chat_id: str | int, content: str, sender_name: str, conv_id: Any) -> None:
    """Envia mensagem do escrevente (Chatwoot) de volta ao Telegram."""
    token = settings.telegram_bot_token
    if not token:
        log.warning("chatwoot sync: TELEGRAM_BOT_TOKEN nao configurado, mensagem nao enviada")
        return

    text = f"👤 *{sender_name}* (Atendente):\n{content}"
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        try:
            r = await client.post(
                url,
                json={"chat_id": str(chat_id), "text": text, "parse_mode": "Markdown"},
            )
            if r.status_code == 200:
                log.info("chatwoot sync: mensagem enviada ao Telegram chat=%s conv=%s", chat_id, conv_id)
            else:
                log.warning(
                    "chatwoot sync: Telegram API retornou %d para chat=%s conv=%s",
                    r.status_code,
                    chat_id,
                    conv_id,
                )
        except Exception as exc:
            log.warning("chatwoot sync: falha ao enviar ao Telegram chat=%s: %s", chat_id, exc)


def _save_event(db: Session, source: str, event_id: str, payload: dict[str, Any]) -> None:
    """Grava WebhookEvent pra idempotencia."""
    payload_hash = hashlib.sha256(str(payload).encode("utf-8")).hexdigest()
    db.add(WebhookEvent(source=source, event_id=event_id, payload_hash=payload_hash))
    db.flush()


# ============================================================
# FIX 2026-07-12: handoff Agent -> Chatwoot (HITL outbound)
# ============================================================
import os  # noqa: E402

import httpx  # noqa: E402

CHATWOOT_PUBLIC_URL = os.environ.get(
    "CHATWOOT_PUBLIC_URL", "https://chatwoot.2notasudi.com.br"
).rstrip("/")
CHATWOOT_API_BASE_URL = os.environ.get("CHATWOOT_BASE_URL", "http://cartorio_chatwoot:3000").rstrip(
    "/"
)
CHATWOOT_API_KEY = os.environ.get("CHATWOOT_API_KEY", "")
CHATWOOT_ACCOUNT_ID = os.environ.get("CHATWOOT_ACCOUNT_ID", "")
CHATWOOT_INBOX_ID = os.environ.get("CHATWOOT_INBOX_ID", "")


async def handoff_to_chatwoot(
    *,
    chat_id: int | str,
    text: str,
    attachments: list[dict[str, Any]] | None = None,
    history: list[str] | None = None,
) -> tuple[bool, dict[str, Any]]:
    """FIX 2026-07-12: cria conversa Chatwoot e envia contexto do cliente Telegram.

    Retorna (ok, info). Falha silenciosa se Chatwoot offline.
    """
    if not CHATWOOT_API_KEY or not CHATWOOT_ACCOUNT_ID or not CHATWOOT_INBOX_ID:
        return False, {
            "error": "chatwoot_not_configured",
            "api_key_present": bool(CHATWOOT_API_KEY),
        }

    contact_id = await _ensure_contact(chat_id)
    if not contact_id:
        return False, {"error": "contact_create_failed"}

    conv_id = await _create_conversation(contact_id)
    if not conv_id:
        return False, {"error": "conversation_create_failed", "contact_id": contact_id}

    body = _format_body(text, attachments, history)
    sent_ok = await _send_message_to_conversation(conv_id, body)

    public_url = f"{CHATWOOT_PUBLIC_URL}/app/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conv_id}"
    return sent_ok, {
        "conversation_id": conv_id,
        "contact_id": contact_id,
        "public_url": public_url,
    }


async def _ensure_contact(chat_id: int | str) -> str | None:
    headers = {"api_access_token": CHATWOOT_API_KEY, "Content-Type": "application/json"}
    source_id = f"telegram:{chat_id}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        try:
            r = await client.get(
                f"{CHATWOOT_API_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/contacts/search",
                headers=headers,
                params={"q": source_id},
            )
            if r.status_code == 200:
                data = r.json()
                found = data.get("payload") if isinstance(data, dict) else data
                if isinstance(found, list):
                    for c in found:
                        if c.get("source_id") == source_id:
                            return str(c.get("id"))
        except Exception as exc:
            log.warning("chatwoot search contact fail: %s", exc)
        try:
            r = await client.post(
                f"{CHATWOOT_API_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/contacts",
                headers=headers,
                json={
                    "name": f"Telegram {chat_id}",
                    "source_id": source_id,
                    "custom_attributes": {"telegram_chat_id": str(chat_id), "canal": "telegram"},
                },
            )
            if r.status_code in (200, 201):
                data = r.json()
                contact = data.get("payload", data) if isinstance(data, dict) else data
                return str(contact.get("id"))
        except Exception as exc:
            log.warning("chatwoot create contact fail: %s", exc)
        return None


async def _create_conversation(contact_id: str) -> str | None:
    headers = {"api_access_token": CHATWOOT_API_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        try:
            r = await client.post(
                f"{CHATWOOT_API_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations",
                headers=headers,
                json={"contact_id": contact_id, "inbox_id": CHATWOOT_INBOX_ID, "status": "open"},
            )
            if r.status_code in (200, 201):
                data = r.json()
                conv = data.get("payload", data) if isinstance(data, dict) else data
                return str(conv.get("id"))
        except Exception as exc:
            log.warning("chatwoot create conversation fail: %s", exc)
        return None


def _format_body(
    text: str, attachments: list[dict[str, Any]] | None, history: list[str] | None
) -> str:
    lines = ["[HITL Telegram - Agent AI Cartorio]", ""]
    lines.append("Mensagem atual:")
    lines.append(text or "(vazio)")
    if attachments:
        lines.append("")
        lines.append(f"Anexos recebidos: {len(attachments)}")
        for a in attachments[:10]:
            t = a.get("type", "?")
            n = a.get("file_name") or a.get("file_unique_id", "?")
            sz = a.get("file_size", "?")
            cap = a.get("caption", "")
            local = a.get("local_path", "")
            lines.append(f"- [{t}] {n} ({sz} bytes)")
            if cap:
                lines.append(f"    caption: {cap}")
            if local:
                lines.append(f"    path servidor: {local}")
    if history:
        lines.append("")
        lines.append(f"Historico recente (ultimos {min(len(history), 6)}):")
        for h in history[-6:]:
            lines.append(f"  {h[:200]}")
    return "\n".join(lines)


async def _send_message_to_conversation(conv_id: str, body: str) -> bool:
    headers = {"api_access_token": CHATWOOT_API_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
        try:
            r = await client.post(
                f"{CHATWOOT_API_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conv_id}/messages",
                headers=headers,
                json={"content": body, "message_type": "incoming"},
            )
            return r.status_code in (200, 201)
        except Exception as exc:
            log.warning("chatwoot send message fail: %s", exc)
            return False


__all__ = ["process_chatwoot_event", "handoff_to_chatwoot"]
