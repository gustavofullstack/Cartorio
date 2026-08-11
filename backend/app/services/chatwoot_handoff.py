"""Service chatwoot_handoff - processa webhooks do Chatwoot.

Quando o Chatwoot notifica que uma conversa foi resolvida (humano finalizou),
atualizamos o atendimento correspondente no DB. Tambem aceitamos message_created
como evento neutro (logar + idempotencia).

Seguranca:
- CHATWOOT_WEBHOOK_ENABLED=false por padrao enquanto o servico esta ausente.
- Quando habilitado, CHATWOOT_WEBHOOK_SECRET + HMAC-SHA256 sao obrigatorios.
- Respostas humanas nunca sao despachadas direto: exigem outbox transacional.

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
from app.services.pii import scrub

log = logging.getLogger(__name__)


def _pseudonymize_chatwoot_id(kind: str, value: object) -> str:
    """Pseudonimiza IDs externos antes de logs, audit ou resposta."""

    key = settings.pietra_conversation_hmac_key
    if len(key) < 32:
        raise RuntimeError("conversation HMAC key is not configured")
    message = f"chatwoot:v1:{kind}:{value}".encode()
    return hmac.new(key.encode(), message, hashlib.sha256).hexdigest()


def _mute_conversation_id(atendimento: Atendimento) -> tuple[str, str] | None:
    """Deriva a chave pseudonima usada pelo consumidor do mute no pipeline."""

    from app.services.chat_pipeline import Channel, pseudonymize_conversation_id

    external_id = str(atendimento.external_id or "")
    if not external_id:
        return None
    try:
        channel = Channel(atendimento.canal)
    except ValueError:
        return None
    if external_id.startswith("hmac:v1:"):
        conversation_pseudonym = external_id.removeprefix("hmac:v1:")
        if len(conversation_pseudonym) != 64:
            return None
        return channel.value, conversation_pseudonym
    return channel.value, pseudonymize_conversation_id(channel, external_id)


def _validate_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    """Valida HMAC-SHA256; secret ausente sempre falha fechado."""
    secret = settings.chatwoot_webhook_secret
    if not secret:
        return False
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

    # 1b. Schema soft-validation (G8.03.T1): known events must match shape;
    # empty/missing event → invalid_payload (fail soft, no exception).
    if not isinstance(payload, dict) or not payload:
        return {"status": "rejected", "reason": "invalid_payload"}

    event = payload.get("event") or "unknown"
    if event in {"conversation_status_changed", "message_created"}:
        from app.schemas.chatwoot_webhook import parse_chatwoot_payload

        if parse_chatwoot_payload(payload) is None:
            log.warning("chatwoot_handoff: invalid_payload event=%s", event)
            return {"status": "rejected", "reason": "invalid_payload", "event": event}
    elif event == "unknown" or payload.get("event") in (None, ""):
        return {"status": "rejected", "reason": "invalid_payload"}

    raw_event_id = str(payload.get("id") or payload.get("message_id") or "")
    event_id = _pseudonymize_chatwoot_id("event", raw_event_id) if raw_event_id else ""

    # 2. Idempotencia
    if event_id:
        existing = db.execute(
            select(WebhookEvent).where(
                WebhookEvent.source == "chatwoot",
                WebhookEvent.event_id == event_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            log.info("chatwoot_handoff idempotent event_hash=%s", event_id[:16])
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
    """Se status=resolved, marca atendimento como concluido.

    G8.03.T2: status open/pending com assignee humano → mute bot (HITL).
    status resolved → unmute bot para novas interações.
    """
    status = payload.get("status") or payload.get("conversation", {}).get("status")
    conv = payload.get("conversation") or {}
    conv_id = conv.get("id") or payload.get("id")
    assignee = (
        payload.get("assignee") or conv.get("meta", {}).get("assignee") or conv.get("assignee")
    )

    if not conv_id:
        return
    conv_hash = _pseudonymize_chatwoot_id("conversation", conv_id)

    # HITL mute/unmute (best-effort Redis)
    try:
        from app.services.bot_mute import mute_bot, unmute_bot
        from app.services.redis_bus import get_bus

        bus = get_bus()
        client = getattr(bus, "client", None) if bus else None
        if client is not None:
            if status in {"open", "pending"} and assignee:
                mute_bot(client, "chatwoot", conv_hash, reason="hitl_assignee")
                # também mute por canal telegram se houver mapping no atendimento
                at = db.execute(
                    select(Atendimento).where(Atendimento.chatwoot_conversation_id == conv_id)
                ).scalar_one_or_none()
                if at is not None and (mute_target := _mute_conversation_id(at)) is not None:
                    mute_bot(client, mute_target[0], mute_target[1], reason="hitl_assignee")
            elif status == "resolved":
                unmute_bot(client, "chatwoot", conv_hash)
                at = db.execute(
                    select(Atendimento).where(Atendimento.chatwoot_conversation_id == conv_id)
                ).scalar_one_or_none()
                if at is not None and (mute_target := _mute_conversation_id(at)) is not None:
                    unmute_bot(client, mute_target[0], mute_target[1])
    except Exception as exc:  # noqa: BLE001
        log.warning("chatwoot_handoff mute hook fail: %s", type(exc).__name__)

    if status != "resolved":
        return

    atendimento = db.execute(
        select(Atendimento).where(Atendimento.chatwoot_conversation_id == conv_id)
    ).scalar_one_or_none()

    if atendimento and not atendimento.concluido_em:
        atendimento.concluido_em = datetime.now(timezone.utc)
        atendimento.status = "concluido"

        AuditService.log(
            db,
            actor_id=f"chatwoot:{conv_hash}",
            action="atendimento.concluido",
            resource=f"atendimento:{atendimento.id}",
            actor_type="agent",
            payload={"chatwoot_conversation_id_pseudonymized": conv_hash},
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

    conv_hash = _pseudonymize_chatwoot_id("conversation", conv_id) if conv_id else ""
    log.info(
        "chatwoot_handoff: message_created conv_hash=%s type=%s",
        conv_hash[:16],
        message_type,
    )

    # Só faz sync bidirecional para mensagens outgoing (escrevente → cliente)
    if message_type != "outgoing" or not content or not conv_id:
        return

    # G8.03.T2: primeira resposta humana → mute bot no canal do cliente
    try:
        from app.services.bot_mute import mute_bot
        from app.services.redis_bus import get_bus

        bus = get_bus()
        client = getattr(bus, "client", None) if bus else None
        if client is not None:
            mute_bot(client, "chatwoot", conv_hash, reason="hitl_outgoing")
    except Exception as exc:  # noqa: BLE001
        log.warning("chatwoot_handoff mute on outgoing fail: %s", type(exc).__name__)

    # Busca o atendimento para encontrar o chat_id do Telegram
    atendimento = db.execute(
        select(Atendimento).where(Atendimento.chatwoot_conversation_id == conv_id)
    ).scalar_one_or_none()

    if not atendimento:
        log.warning("chatwoot sync: atendimento nao encontrado conv_hash=%s", conv_hash[:16])
        return

    # O consumidor no chat_pipeline usa o pseudonimo de conversa, nao o
    # external_id bruto. Registrar ambos os mutes evita corrida entre a primeira
    # resposta do escrevente e uma nova resposta automatica.
    try:
        from app.services.bot_mute import mute_bot
        from app.services.redis_bus import get_bus

        bus = get_bus()
        client = getattr(bus, "client", None) if bus else None
        mute_target = _mute_conversation_id(atendimento)
        if client is not None and mute_target is not None:
            mute_bot(client, mute_target[0], mute_target[1], reason="hitl_outgoing")
    except Exception as exc:  # noqa: BLE001
        log.warning("chatwoot_handoff channel mute on outgoing fail: %s", type(exc).__name__)

    if not atendimento.external_id:
        log.warning("chatwoot sync: channel identity not found atendimento=%s", atendimento.id)
        return

    # Contencao P0: nunca enviar direto ao Telegram. A reativacao exige outbox
    # transacional com identidade recuperavel e worker auditado.
    mute_target = _mute_conversation_id(atendimento)
    sender_id = sender.get("id", "unknown")
    AuditService.log(
        db,
        actor_id=f"chatwoot:{_pseudonymize_chatwoot_id('sender', sender_id)}",
        action="chatwoot.sync.outgoing_dispatch_blocked",
        resource=f"atendimento:{atendimento.id}",
        actor_type="agent",
        payload={
            "chatwoot_conversation_id_pseudonymized": conv_hash,
            "channel_conversation_id_pseudonymized": mute_target[1] if mute_target else None,
            "sender_id_pseudonymized": _pseudonymize_chatwoot_id("sender", sender_id),
            "content_length": len(content),
            "dispatch": "disabled_requires_transactional_outbox",
        },
    )


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
    if not settings.chatwoot_outbound_enabled:
        return False, {"error": "chatwoot_disabled_requires_transactional_outbox"}
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
    # Chatwoot e uma fronteira externa: use identificador pseudonimizado.
    # O vinculo reverso fica no Atendimento local pelo conversation_id.
    source_id = f"telegram:{_pseudonymize_chatwoot_id('contact-source', chat_id)}"
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
            log.warning("chatwoot search contact fail: %s", type(exc).__name__)
        try:
            r = await client.post(
                f"{CHATWOOT_API_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/contacts",
                headers=headers,
                json={
                    "name": "Atendimento Telegram",
                    "source_id": source_id,
                    "custom_attributes": {"canal": "telegram", "pseudonymous": True},
                },
            )
            if r.status_code in (200, 201):
                data = r.json()
                contact = data.get("payload", data) if isinstance(data, dict) else data
                return str(contact.get("id"))
        except Exception as exc:
            log.warning("chatwoot create contact fail: %s", type(exc).__name__)
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
            log.warning("chatwoot create conversation fail: %s", type(exc).__name__)
        return None


def _format_body(
    text: str, attachments: list[dict[str, Any]] | None, history: list[str] | None
) -> str:
    lines = ["[HITL Telegram - Agent AI Cartorio]", ""]
    lines.append("Mensagem atual:")
    lines.append(scrub(text or "(vazio)").text)
    if attachments:
        lines.append("")
        lines.append(f"Anexos recebidos: {len(attachments)}")
        for a in attachments[:10]:
            t = a.get("type", "?")
            n = scrub(str(a.get("file_name") or a.get("file_unique_id", "?"))).text
            sz = a.get("file_size", "?")
            cap = scrub(str(a.get("caption", ""))).text
            lines.append(f"- [{t}] {n} ({sz} bytes)")
            if cap:
                lines.append(f"    caption: {cap}")
    if history:
        lines.append("")
        lines.append(f"Historico recente (ultimos {min(len(history), 6)}):")
        for h in history[-6:]:
            lines.append(f"  {scrub(str(h)).text[:200]}")
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
            log.warning("chatwoot send message fail: %s", type(exc).__name__)
            return False


__all__ = ["process_chatwoot_event", "handoff_to_chatwoot"]
