"""whatsapp.py — Bot WhatsApp via Evolution API (espelho do Telegram).

Sprint 4 / Turn 51 (2026-07-09): paridade 100% com Telegram via chat_pipeline.py.

ARQUITETURA:
  Evolution API (whatsapp.2notasudi.com.br/manager)
    └─ webhook POST /api/v1/whatsapp/webhook (legado: /api/v1/webhook/evolution)
         └─ WhatsAppAdapter (este arquivo)
              └─ chat_pipeline.process_message()
                   ├─ check_idempotency (message_id Evolution)
                   ├─ scrub_pii_3_layers (LGPD)
                   ├─ enqueue + debounce 1.2s
                   └─ process_debounced()
                        ├─ rate limit 3s
                        ├─ typing_loop (presence subscribe)
                        ├─ call_llm_with_fallback (LiteLLM→nemotron→opencode→...)
                        ├─ scrub output (camada 3)
                        ├─ adapter.send (POST /message/sendText/cartorio-2notas)
                        └─ adapter.react (POST /message/sendReaction/cartorio-2notas)

ENDPOINTS EVOLUTION API:
  POST {EVOLUTION_BASE_URL}/message/sendText/{instance}  → envia texto
  POST {EVOLUTION_BASE_URL}/message/sendReaction/{instance}  → reação
  POST {EVOLUTION_BASE_URL}/chat/sendPresence/{instance}  → typing indicator
  GET  {EVOLUTION_BASE_URL}/instance/connectionState/{instance}  → status

COMANDOS (mesmos Telegram v2.0):
  /start, /menu, /agendar, /protocolo, /humano, /cancelar, /lgpd

WHATSAPP-SPECIFIC:
  - remoteJid formato: 5511999999999@s.whatsapp.net (privado) ou @g.us (grupo)
  - typing = "composing" (vs Telegram "typing")
  - reactions limitadas vs Telegram (👍 ❤️ 😂 😮 😢 🙏)
  - inline keyboard = buttons (max 3) ou list message (sections)

SUI Gustavo:
  - QR scan em https://whatsapp.2notasudi.com.br/manager
  - Instance: cartorio-2notas
   - API Key: configurada via ambiente (nunca documentar valor literal)

Lesson 141: chat_pipeline extraído
Lesson 143: WhatsApp espelhado 100%
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import require_cartorio_api_key
from app.config import settings
from app.db import get_db
from app.models.cliente import Cliente
from app.services.chat_pipeline import (
    Channel,
    ChannelAdapter,
    InboundMessage,
    OutboundMessage,
    process_message,
    pseudonymize_conversation_id,
    health_check as pipeline_health,
)
from app.services.redis_bus import get_bus
from app.services.whatsapp_access import (
    decide_whatsapp_access,
    normalize_whatsapp_number,
    pseudonymous_sender_id,
)
from app.services.evolution_ingest import (
    ingest_evolution_event,
    is_messages_upsert_event,
    validate_evolution_webhook_auth,
)
from app.services.pietra_coleta import hash_phone, upsert_cliente_por_telefone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _find_cliente_by_whatsapp_hash(
    db: Session,
    normalized_sender: str | None,
) -> Cliente | None:
    """Localiza cliente pelo hash canonico sem consultar telefone em claro."""
    if not normalized_sender:
        return None
    telefone_hash = hash_phone(normalized_sender)
    return db.execute(
        select(Cliente).where(Cliente.telefone_hash == telefone_hash)
    ).scalar_one_or_none()


def _bind_whatsapp_identity(
    db: Session,
    *,
    cliente: Cliente,
    conversation_pseudonym: str,
) -> None:
    """Vincula o pseudonimo somente depois de consentimento valido."""

    if cliente.id is None:
        raise RuntimeError("cliente must be persisted before channel binding")
    from app.services.channel_identity import bind_channel_identity

    bind_channel_identity(
        db,
        cliente_id=cliente.id,
        channel="whatsapp",
        conversation_pseudonym=conversation_pseudonym,
        hmac_kid=settings.pietra_conversation_hmac_kid,
    )


def _provision_allowed_whatsapp_cliente(
    db: Session,
    *,
    normalized_sender: str | None,
    access_reason: str,
) -> Cliente | None:
    """Cria o registro minimo no aceite explicito de remetente autorizado.

    O telefone nunca e persistido em claro. O upsert canonico grava apenas
    ``telefone_hash`` e permanece na mesma transacao do consentimento/audit.
    Sem numero normalizado continua fail-closed.
    """
    if not normalized_sender:
        return None
    logger.debug("provisioning whatsapp cliente reason=%s", access_reason)
    result = upsert_cliente_por_telefone(
        db,
        telefone=normalized_sender,
        consentimento_lgpd=False,
    )
    return db.get(Cliente, result.cliente_id)


def _normalize_lgpd_text_reply(text: str) -> str | None:
    """Classifica aceite/recusa textual explicita. None = nao e resposta de gate."""
    normalized = text.strip().lower()
    normalized = (
        normalized.replace("ã", "a")
        .replace("â", "a")
        .replace("á", "a")
        .replace("à", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("õ", "o")
        .replace("ô", "o")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    if normalized in LGPD_YES_LABELS:
        return "accept"
    if normalized in LGPD_NO_LABELS:
        return "reject"
    return None


def _whatsapp_identity_tokens(sender_id: str, sender_alt: str) -> list[str]:
    tokens: list[str] = []
    for raw in (sender_id, sender_alt):
        token = str(raw or "").strip()
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def _conversation_pseudonyms(sender_id: str, sender_alt: str) -> list[str]:
    seen: list[str] = []
    for token in _whatsapp_identity_tokens(sender_id, sender_alt):
        pseudo = pseudonymize_conversation_id(Channel.WHATSAPP, token)
        if pseudo not in seen:
            seen.append(pseudo)
    return seen


def _consent_cache_keys(pseudonyms: list[str]) -> list[str]:
    return [f"consent:wa:{pseudo}" for pseudo in pseudonyms]


def _notice_cache_keys(pseudonyms: list[str]) -> list[str]:
    return [f"consent:wa:notice:{pseudo}" for pseudo in pseudonyms]


def _active_poll_keys(pseudonyms: list[str]) -> list[str]:
    return [f"wa:lgpd:active_poll:{pseudo}" for pseudo in pseudonyms]


def _poll_map_key(poll_id: str) -> str:
    return f"wa:lgpd:poll:{poll_id}"


def _poll_resolved_key(poll_id: str) -> str:
    return f"wa:lgpd:poll_resolved:{poll_id}"


def _find_cliente_for_inbound(
    db: Session,
    *,
    normalized_sender: str | None,
    conversation_pseudonyms: list[str],
) -> Cliente | None:
    cliente = _find_cliente_by_whatsapp_hash(db, normalized_sender)
    if cliente is not None:
        return cliente
    from app.services.channel_identity import find_cliente_id_by_channel_identity

    for pseudo in conversation_pseudonyms:
        cliente_id = find_cliente_id_by_channel_identity(
            db,
            channel="whatsapp",
            conversation_pseudonym=pseudo,
        )
        if cliente_id is not None:
            found = db.get(Cliente, cliente_id)
            if found is not None:
                return found
    return None


def _bind_all_whatsapp_identities(
    db: Session,
    *,
    cliente: Cliente,
    conversation_pseudonyms: list[str],
) -> None:
    for pseudo in conversation_pseudonyms:
        _bind_whatsapp_identity(
            db,
            cliente=cliente,
            conversation_pseudonym=pseudo,
        )


def extract_whatsapp_lgpd_poll_vote(payload: dict) -> tuple[str | None, int | None]:
    """Extrai (poll_id, option) de voto estruturado da Evolution.

    option=0 -> Sim; option=1 -> Nao. Prefere IDs/labels estaveis a texto livre.
    """
    raw_data = payload.get("data")
    data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
    raw_message = data.get("message")
    message: dict[str, Any] = raw_message if isinstance(raw_message, dict) else {}
    if not message:
        raw_root = payload.get("message")
        message = raw_root if isinstance(raw_root, dict) else {}
    poll_update = message.get("pollUpdateMessage")
    updates = data.get("pollUpdates")
    selected: list[object] = []
    poll_id = ""
    if isinstance(poll_update, dict):
        creation = poll_update.get("pollCreationMessageKey")
        if isinstance(creation, dict):
            poll_id = str(creation.get("id") or "")
        vote = poll_update.get("vote") if isinstance(poll_update.get("vote"), dict) else {}
        raw_selected = vote.get("selectedOptions") if isinstance(vote, dict) else None
        if isinstance(raw_selected, list):
            selected = raw_selected
        elif isinstance(poll_update.get("selectedOptions"), list):
            selected = poll_update["selectedOptions"]
    if not selected and isinstance(updates, list) and updates:
        first = updates[0] if isinstance(updates[0], dict) else {}
        key = first.get("pollUpdateMessageKey") or first.get("key") or {}
        if isinstance(key, dict) and not poll_id:
            poll_id = str(key.get("id") or "")
        vote = first.get("vote") if isinstance(first.get("vote"), dict) else first
        raw_selected = vote.get("selectedOptions") if isinstance(vote, dict) else None
        if isinstance(raw_selected, list):
            selected = raw_selected
    if not selected:
        return (poll_id or None, None)

    labels: list[str] = []
    for item in selected:
        if isinstance(item, dict):
            label = str(item.get("optionName") or item.get("name") or item.get("value") or "")
        else:
            label = str(item)
        label = label.strip()
        if label:
            labels.append(label)
    if not labels:
        return (poll_id or None, None)

    first_label = labels[0]
    if first_label.isdigit():
        option = int(first_label)
        if option in (0, 1):
            return (poll_id or None, option)
        return (poll_id or None, None)
    decision = _normalize_lgpd_text_reply(first_label)
    if decision == "accept":
        return (poll_id or None, 0)
    if decision == "reject":
        return (poll_id or None, 1)
    lowered = first_label.strip().lower()
    if lowered == LGPD_POLL_OPTIONS[0].lower():
        return (poll_id or None, 0)
    if lowered == LGPD_POLL_OPTIONS[1].lower():
        return (poll_id or None, 1)
    return (poll_id or None, None)


def _payload_has_poll_vote(payload: dict) -> bool:
    poll_id, option = extract_whatsapp_lgpd_poll_vote(payload)
    return option in (0, 1) or bool(poll_id)


# ===== Config (espelha telegram.py constantes) =====
EVOLUTION_BASE_URL = settings.evolution_base_url or "http://cartorio_evolution-api:8080"
EVOLUTION_API_KEY = settings.evolution_api_key or ""
EVOLUTION_INSTANCE = settings.evolution_instance or "cartorio-agent"
EVOLUTION_TIMEOUT = 10.0

# ===== Whitelist de comandos (espelha telegram.py) =====
ALLOWED_COMMANDS: frozenset[str] = frozenset(
    {
        "/start",
        "/menu",
        "/agendar",
        "/protocolo",
        "/humano",
        "/cancelar",
        "/lgpd",
    }
)

# ===== Bot state machine (espelha telegram.py) =====
STATE_IDLE = "idle"
STATE_AGENDAR_SERVICO = "agendar:servico"
STATE_AGENDAR_DATA = "agendar:data"
STATE_AGENDAR_HORA = "agendar:hora"
STATE_AGENDAR_CONFIRMAR = "agendar:confirmar"
STATE_PROTOCOLO = "protocolo:consulta"
STATE_HUMANO = "humano:fila"

DEBOUNCE_WINDOW = 1.2
RATE_LIMIT_SECONDS = 3
MAX_RESPONSE_LEN = 800


def split_whatsapp_text(text: str, max_len: int = MAX_RESPONSE_LEN) -> list[str]:
    """Divide texto sem descartar o restante nem cortar palavra quando possivel."""
    if max_len < 1:
        raise ValueError("max_len deve ser positivo")
    remaining = text.strip()
    chunks: list[str] = []
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        window = remaining[: max_len + 1]
        cut = max(window.rfind("\n\n"), window.rfind("\n"))
        if cut < max_len // 2:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = max_len
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return chunks


LGPD_NOTICE = (
    "*AVISO LGPD (Lei 13.709/2018)*\n"
    "Este canal trata dados para atendimento do cartorio.\n"
    "- Nao envie CPF, RG, telefone completo ou documentos sensiveis aqui.\n"
    "- Dados pessoais sao mascarados antes de qualquer processamento com IA.\n"
    "- Voce pode pedir acesso, correcao ou exclusao: dpo@2notasudi.com.br\n"
    "- Atos notariais exigem validacao humana (HITL).\n"
    "Para continuar, responda a enquete *Sim* / *Nao*. Sem essa confirmacao, "
    "nenhuma mensagem sera processada pela IA. Se a enquete nao aparecer, "
    "envie *SIM* ou *NAO*."
)

LGPD_POLL_QUESTION = (
    "Voce concorda com o tratamento dos seus dados para realizacao "
    "do atendimento, conforme informado acima?"
)
LGPD_POLL_OPTIONS = ["Sim", "Nao"]
LGPD_POLL_TTL = 60 * 60
LGPD_YES_LABELS = frozenset({"sim", "s", "aceito", "aceitar", "concordo", "autorizo"})
LGPD_NO_LABELS = frozenset({"nao", "não", "n", "rejeito", "rejeitar", "nego", "nao aceito"})
LGPD_CONSENT_ACK = "Consentimento confirmado. Como posso ajudar?"
LGPD_CONSENT_DENIED = (
    "Consentimento nao registrado. Sem autorizacao LGPD, o atendimento por IA "
    "fica desabilitado para esta conversa. Para tentar novamente, envie SIM."
)

SERVICOS: dict[str, tuple[str, str]] = {
    "reconhecimento_firma": ("Reconhecimento de Firma", "R$ 8,50"),
    "autenticacao": ("Autenticacao de Documento", "R$ 6,80"),
    "procuracao": ("Procuracao", "R$ 95,20"),
    "testamento": ("Testamento", "R$ 320,00"),
    "ata_notarial": ("Ata Notarial", "R$ 480,00"),
}

# ===== In-process metrics =====
_METRICS: dict[str, int] = {
    "requests_total": 0,
    "responses_ok": 0,
    "responses_failed": 0,
    "rate_limited": 0,
    "scheduled_debounce": 0,
    "hitl_created": 0,
}


def bump_metric(key: str, value: int = 1) -> None:
    _METRICS[key] = _METRICS.get(key, 0) + value


# ============================================================
#  WhatsAppAdapter — implementa ChannelAdapter para Evolution API
# ============================================================


class WhatsAppAdapter(ChannelAdapter):
    """Adapter Evolution API para chat_pipeline.

    Evolution API: https://doc.evolution-api.com/v2/api-reference
    Endpoints usados:
      - POST /message/sendText/{instance}
      - POST /message/sendReaction/{instance}
      - POST /chat/sendPresence/{instance}
    """

    def __init__(
        self, base_url: str | None = None, api_key: str | None = None, instance: str | None = None
    ):
        self.base_url = (base_url or EVOLUTION_BASE_URL).rstrip("/")
        self.api_key = api_key or EVOLUTION_API_KEY
        self.instance = instance or EVOLUTION_INSTANCE
        # Timeout granular (lesson 113: httpx.Timeout)
        self.timeout = httpx.Timeout(connect=3.0, read=EVOLUTION_TIMEOUT, write=5.0, pool=3.0)
        # User-Agent fixo (lesson 120: bypass Cloudflare 403)
        self._client: httpx.AsyncClient | None = None
        self._authorized_lid_until: dict[str, float] = {}

    @staticmethod
    def _recipient_hash(recipient_id: str) -> str:
        import hashlib

        return hashlib.sha256(recipient_id.encode()).hexdigest()

    def authorize_recipient(self, recipient_id: str) -> None:
        """Cria binding curto apenas para LID ja aprovado via remoteJidAlt."""
        if recipient_id.endswith("@lid"):
            self._authorized_lid_until[self._recipient_hash(recipient_id)] = time.time() + 120

    def _recipient_is_allowed(self, recipient_id: str) -> bool:
        decision = decide_whatsapp_access(
            recipient_id,
            sender_id_alt=None,
            allowed_sender_hashes=settings.pietra_whatsapp_allowed_sender_hashes,
            hmac_key=settings.pietra_whatsapp_allowlist_hmac_key,
            restrict_inbound=settings.pietra_whatsapp_restrict_inbound,
        )
        if decision.allowed:
            return True
        if not recipient_id.endswith("@lid"):
            return False
        return self._authorized_lid_until.get(self._recipient_hash(recipient_id), 0) >= time.time()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "apikey": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "CartorioBot/2.0 (Evolution-Adapter)",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def send(self, msg: OutboundMessage) -> bool:
        """Envia mensagem de texto via Evolution sendText (sanitizada com 0% emojis)."""
        try:
            if not self._recipient_is_allowed(msg.recipient_id or ""):
                logger.warning("WhatsApp egress blocked: recipient not authorized")
                return False
            from app.services.notificacao import _strip_emojis

            client = await self._get_client()
            url = f"{self.base_url}/message/sendText/{self.instance}"
            clean_text = _strip_emojis(msg.text or "").strip()
            recipient = msg.recipient_id or ""
            if not recipient.endswith("@lid"):
                recipient = recipient.replace("@s.whatsapp.net", "").replace("@g.us", "")
            from app.services.metrics import store

            chunks = split_whatsapp_text(clean_text)
            if not chunks:
                return False
            flat = [button for row in msg.keyboard or [] for button in row]
            buttons = [
                {
                    "buttonId": button.get("callback_data", f"btn_{index}"),
                    "buttonText": {"displayText": button.get("text", "")[:20]},
                    "type": 1,
                }
                for index, button in enumerate(flat[:3])
            ]
            for index, chunk in enumerate(chunks):
                payload: dict[str, Any] = {"number": recipient, "text": chunk}
                if buttons and len(flat) <= 3 and index == len(chunks) - 1:
                    payload["buttons"] = buttons
                resp = await client.post(url, json=payload)
                if resp.status_code not in (200, 201):
                    logger.warning("Evolution sendText failed: status=%s", resp.status_code)
                    bump_metric("responses_failed")
                    store.inc_counter("cartorio_whatsapp_erros_total")
                    return False
                store.inc_counter("cartorio_whatsapp_mensagens_total", labels={"direction": "out"})
            bump_metric("responses_ok")
            return True
        except Exception as e:
            logger.exception("WhatsApp send error: %s", e)
            bump_metric("responses_failed")
            from app.services.metrics import store

            store.inc_counter("cartorio_whatsapp_erros_total")
            return False

    async def send_poll(self, recipient_id: str, question: str, options: list[str]) -> str | None:
        """Envia enquete nativa via Evolution sendPoll. Retorna poll/message id."""
        try:
            if not self._recipient_is_allowed(recipient_id or ""):
                logger.warning("WhatsApp egress blocked: poll recipient not authorized")
                return None
            from app.services.notificacao import _strip_emojis

            client = await self._get_client()
            url = f"{self.base_url}/message/sendPoll/{self.instance}"
            recipient = recipient_id or ""
            if not recipient.endswith("@lid"):
                recipient = recipient.replace("@s.whatsapp.net", "").replace("@g.us", "")
            payload = {
                "number": recipient,
                "pollName": _strip_emojis(question),
                "options": [_strip_emojis(option) for option in options],
                "selectableOptionsCount": 1,
            }
            resp = await client.post(url, json=payload)
            if resp.status_code not in (200, 201):
                logger.warning("Evolution sendPoll failed: status=%s", resp.status_code)
                return None
            body: dict[str, Any] = {}
            try:
                parsed = resp.json()
                if isinstance(parsed, dict):
                    body = parsed
            except Exception:
                body = {}
            raw_key = body.get("key")
            key: dict[str, Any] = raw_key if isinstance(raw_key, dict) else {}
            if not key:
                nested = body.get("message")
                nested_dict = nested if isinstance(nested, dict) else {}
                nested_key = nested_dict.get("key")
                key = nested_key if isinstance(nested_key, dict) else {}
            poll_id = str(key.get("id") or body.get("pollId") or "")
            return poll_id or "poll-sent"
        except Exception as e:
            logger.exception("WhatsApp send_poll error: %s", e)
            return None

    async def typing(self, recipient_id: str, action: str = "composing") -> bool:
        """Indica typing via presence subscribe (Evolution). action='' cancela."""
        try:
            if not self._recipient_is_allowed(recipient_id):
                logger.warning("WhatsApp egress blocked: typing recipient not authorized")
                return False
            if not action:
                action = "paused"
            client = await self._get_client()
            url = f"{self.base_url}/chat/sendPresence/{self.instance}"
            payload = {
                "number": recipient_id.replace("@s.whatsapp.net", "").replace("@g.us", ""),
                "presence": action,  # 'composing' / 'recording' / 'paused'
            }
            resp = await client.post(url, json=payload)
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.warning("WhatsApp typing error (non-blocking): %s", e)
            return False

    async def react(self, recipient_id: str, message_id: str, reaction: str = "thumbsup") -> bool:
        """Adiciona reação via Evolution sendReaction.

        WhatsApp reactions limitadas: 👍 ❤️ 😂 😮 😢 🙏
        Telegram reaction emoji mapeado → WhatsApp.
        """
        try:
            if not self._recipient_is_allowed(recipient_id):
                logger.warning("WhatsApp egress blocked: reaction recipient not authorized")
                return False
            # Map Telegram emoji → WhatsApp emoji
            emoji_map = {
                "thumbsup": "👍",
                "thumbup": "👍",
                "check": "👍",
                "ok": "👍",
                "heart": "❤️",
                "smile": "😂",
                "wow": "😮",
                "cry": "😢",
                "pray": "🙏",
            }
            emoji = emoji_map.get(reaction, "👍")
            client = await self._get_client()
            url = f"{self.base_url}/message/sendReaction/{self.instance}"
            payload = {
                "key": {
                    "remoteJid": recipient_id,
                    "id": message_id,
                    "fromMe": False,
                },
                "reaction": emoji,
            }
            resp = await client.post(url, json=payload)
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.warning("WhatsApp react error (non-blocking): %s", e)
            return False

    async def verify_signature(
        self,
        raw_body: bytes,
        signature: str | None,
        shared_secret_header: str | None = None,
    ) -> bool:
        """Valida HMAC ou header secreto compartilhado do webhook Evolution."""
        return validate_evolution_webhook_auth(
            raw_body,
            signature=signature,
            shared_secret_header=shared_secret_header,
        )


# ============================================================
#  Adapter singleton (compartilhado entre webhook + pipeline)
# ============================================================

_adapter_instance: WhatsAppAdapter | None = None


def get_adapter() -> WhatsAppAdapter:
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = WhatsAppAdapter()
    return _adapter_instance


# ============================================================
#  Normalização: payload Evolution → InboundMessage
# ============================================================


def parse_evolution_payload(payload: dict) -> InboundMessage | None:
    """Extrai mensagem normalizada do payload Evolution API (dual-format).

    Formatos aceitos (ambos aparecem em prod — AGENTS.md):
    1) Nested moderno: payload["data"]["message"] + data["key"]
    2) Root-level legado: payload["message"] + payload["key"]

    Exemplo nested:
    {
      "event": "messages.upsert",
      "instance": "cartorio-2notas",
      "data": {
        "key": {"remoteJid": "...", "fromMe": false, "id": "..."},
        "message": {"conversation": "..."} | {"extendedTextMessage": {"text": "..."}},
        "messageType": "conversation" | "extendedTextMessage",
        "pushName": "Nome do contato"
      }
    }
    """
    try:
        event = payload.get("event", "")
        if event and not is_messages_upsert_event(event) and not _payload_has_poll_vote(payload):
            # Evolution envia messages.upsert E MESSAGES_UPSERT. Sem event, segue.
            return None

        # Dual-format: nested data.* OU root-level (G7.04.T3)
        _data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        _key = _data.get("key") if isinstance(_data.get("key"), dict) else None  # type: ignore[union-attr]
        _message = _data.get("message") if isinstance(_data.get("message"), dict) else None  # type: ignore[union-attr]
        if not _key:
            _key = payload.get("key") if isinstance(payload.get("key"), dict) else {}
        if not _message:
            _message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
        data = _data
        if not isinstance(_key, dict):
            _key = {}
        if not isinstance(_message, dict):
            _message = {}
        key = _key
        message = _message

        remote_jid = key.get("remoteJid", "") or ""
        # WhatsApp LID: o cliente escreve em NNN@lid. sendText ACEITA @lid.
        # Remapear para remoteJidAlt (@s.whatsapp.net) cria um chat paralelo
        # e o cliente nao ve a resposta no thread onde digitou.
        remote_jid_alt = str(key.get("remoteJidAlt") or "").strip()
        reply_jid = remote_jid
        msg_id = key.get("id", "") or ""
        # Texto: conversation OU extendedTextMessage.text
        ext = message.get("extendedTextMessage")
        ext_text = ext.get("text", "") if isinstance(ext, dict) else ""
        text = message.get("conversation") or ext_text or ""
        push_name = (
            (data.get("pushName", "") if isinstance(data, dict) else "")
            or payload.get("pushName", "")
            or ""
        )
        is_group = "@g.us" in remote_jid
        if not remote_jid or not msg_id:
            return None
        # Ignora status/newsletter broadcast e eco fromMe.
        if (
            remote_jid == "status@broadcast"
            or remote_jid.endswith("@broadcast")
            or key.get("fromMe") is True
        ):
            return None
        message_type = ""
        if isinstance(data, dict):
            message_type = str(data.get("messageType") or "")
        if not message_type:
            message_type = str(payload.get("messageType") or "")
        return InboundMessage(
            channel=Channel.WHATSAPP,
            sender_id=reply_jid,
            sender_name=str(push_name),
            text=str(text),
            update_id=msg_id,  # message_id do WhatsApp = idempotency key
            message_ids=[msg_id],
            is_group=is_group,
            extra={
                "instance": payload.get("instance", EVOLUTION_INSTANCE),
                "from_me": key.get("fromMe", False),
                "message_type": message_type,
                "format": "nested" if payload.get("data") else "root",
                "remote_jid_raw": remote_jid,
                "remote_jid_alt": remote_jid_alt or None,
                "addressing_mode": key.get("addressingMode"),
            },
        )
    except Exception as e:
        logger.exception("parse_evolution_payload error: %s", e)
        return None


# ============================================================
#  Endpoints REST (espelho de telegram.py)
# ============================================================


@router.get("/health")
async def whatsapp_health() -> dict:
    """Health check: Evolution API + sessao WhatsApp REAL + pipeline.

    E2.08 / Lesson 260: ``evolution_api=online`` NUNCA implica sessao
    conectada. Parseamos o ``connectionState`` real da instancia
    (open|close|connecting) e so reportamos ``status=ok`` quando a sessao
    esta efetivamente ``open``.
    """
    evolution_ok = False
    session_state = "unknown"
    try:
        adapter = get_adapter()
        client = await adapter._get_client()
        resp = await client.get(f"{adapter.base_url}/instance/connectionState/{adapter.instance}")
        evolution_ok = resp.status_code == 200
        if evolution_ok:
            try:
                data = resp.json()
            except Exception:
                data = {}
            raw_state = (data.get("instance") or {}).get("state") or data.get("state")
            if raw_state:
                session_state = str(raw_state).lower()
    except Exception as e:
        logger.warning("evolution health error: %s", e)

    pipeline = await pipeline_health()
    session_connected = session_state == "open"
    # E3.06: alimenta gauges Prometheus no health check E2.08 (0/1).
    # Metrica nunca derruba o health check.
    try:
        from app.services.metrics import store

        store.set_whatsapp_health(evolution_ok, session_connected)
    except Exception:
        pass
    return {
        "status": "ok" if (evolution_ok and session_connected) else "degraded",
        "evolution_api": "online" if evolution_ok else "offline",
        # Separado por design: NUNCA tratar evolution_api como WhatsApp conectado.
        "whatsapp_session": session_state,
        "session_connected": session_connected,
        "instance": EVOLUTION_INSTANCE,
        "pipeline": pipeline,
        "ts": time.time(),
    }


async def _cache_consent_granted(bus: Any, pseudonyms: list[str]) -> bool:
    if not bus:
        return True
    try:
        for key in _consent_cache_keys(pseudonyms):
            await bus.client.set(key, "1", ex=86400)
        notice_keys = _notice_cache_keys(pseudonyms)
        poll_keys = _active_poll_keys(pseudonyms)
        if notice_keys or poll_keys:
            await bus.client.delete(*notice_keys, *poll_keys)
        return True
    except Exception as exc:
        logger.warning("Redis consent write failed: %s", type(exc).__name__)
        return False


async def _cache_consent_cleared(bus: Any, pseudonyms: list[str]) -> bool:
    if not bus:
        return True
    try:
        keys = (
            _consent_cache_keys(pseudonyms)
            + _notice_cache_keys(pseudonyms)
            + _active_poll_keys(pseudonyms)
        )
        if keys:
            await bus.client.delete(*keys)
        return True
    except Exception as exc:
        logger.warning("Redis consent delete failed: %s", type(exc).__name__)
        return False


async def _has_active_lgpd_poll(bus: Any, pseudonyms: list[str]) -> bool:
    if not bus:
        return False
    try:
        for key in _active_poll_keys(pseudonyms):
            if await bus.client.get(key):
                return True
    except Exception:
        return False
    return False


async def _remember_lgpd_poll(bus: Any, poll_id: str, pseudonyms: list[str]) -> None:
    if not bus or not poll_id:
        return
    try:
        await bus.client.set(_poll_map_key(poll_id), "1", ex=LGPD_POLL_TTL)
        for key in _active_poll_keys(pseudonyms):
            await bus.client.set(key, poll_id, ex=LGPD_POLL_TTL)
    except Exception as exc:
        logger.warning("Redis poll map write failed: %s", type(exc).__name__)


async def _send_whatsapp_lgpd_request(
    adapter: WhatsAppAdapter,
    *,
    sender_id: str,
    bus: Any,
    pseudonyms: list[str],
) -> bool:
    if await _has_active_lgpd_poll(bus, pseudonyms):
        return True
    if bus:
        try:
            for key in _notice_cache_keys(pseudonyms):
                if await bus.client.get(key):
                    return True
        except Exception as exc:
            logger.warning("Redis consent notice read failed: %s", type(exc).__name__)
    notice_ok = await adapter.send(
        OutboundMessage(channel=Channel.WHATSAPP, recipient_id=sender_id, text=LGPD_NOTICE)
    )
    poll_id = None
    send_poll = getattr(adapter, "send_poll", None)
    if callable(send_poll):
        poll_id = await send_poll(sender_id, LGPD_POLL_QUESTION, list(LGPD_POLL_OPTIONS))
    if bus:
        try:
            for key in _notice_cache_keys(pseudonyms):
                await bus.client.set(key, "1", ex=600)
        except Exception as exc:
            logger.warning("Redis consent notice debounce failed: %s", type(exc).__name__)
    if poll_id:
        await _remember_lgpd_poll(bus, str(poll_id), pseudonyms)
    return bool(notice_ok or poll_id)


@router.get("/metrics")
async def whatsapp_metrics() -> dict:
    """Métricas in-process."""
    return {
        "metrics": dict(_METRICS),
        "ts": time.time(),
    }


@router.post(
    "/webhook",
    status_code=200,
    summary="Webhook Evolution API (WhatsApp - HMAC + dual-format + LGPD consent)",
    description=(
        "Recebe mensagens do WhatsApp via Evolution API (https://doc.evolution-api.com/v2/api-reference).\n\n"
        "**Auth**: header `X-Hub-Signature-256` (ou `X-Evolution-Signature`) validado "
        "contra `EVOLUTION_WEBHOOK_SECRET` (HMAC-SHA256). Fail-closed: 401 se inválida; "
        "503 se REQUIRE=true sem secret.\n\n"
        "**Dual-format**: aceita **nested moderno** (`data.key.remoteJid`/`data.message.conversation`) "
        "e **root-level legado** (`sender`/`message` na raiz). Schema canonico em "
        "`app.schemas.webhook_payloads.EvolutionPayload`.\n\n"
        "**Idempotency**: `data.key.id` dedup via `evolution_ingest` (DB) + "
        "Redis SETNX (`chat_pipeline.check_idempotency`).\n\n"
        "**LGPD consent gate**: poll nativa Sim/Nao (Hermes/Evolution sendPoll) "
        "com fallback textual `SIM`/`NAO`. Opt-out via `PARAR`/`SAIR` revoga.\n\n"
        "**Flow**: HMAC -> idempotency -> parse -> consent gate -> pipeline "
        "(debounce 1.2s -> rate limit 3s -> LLM com fallback chain -> scrub output)."
    ),
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/EvolutionPayload"},
                    "examples": {
                        "nested_moderno": {
                            "summary": "Formato nested moderno (recomendado)",
                            "value": {
                                "event": "messages.upsert",
                                "instance": "cartorio-2notas",
                                "data": {
                                    "key": {
                                        "remoteJid": "5511999999999@s.whatsapp.net",
                                        "fromMe": False,
                                        "id": "MSG_ID_EXAMPLE",
                                    },
                                    "message": {"conversation": "Quanto custa autenticacao?"},
                                    "pushName": "Maria Cliente",
                                },
                            },
                        },
                        "root_legado": {
                            "summary": "Formato root-level legado (pre-Sprint 1.2)",
                            "value": {
                                "message": {"conversation": "Quero agendar"},
                                "sender": "553499999999",
                                "instance": "cartorio-2notas",
                            },
                        },
                    },
                }
            }
        }
    },
)
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    """Webhook Evolution → process_message via chat_pipeline.

    Fluxo:
      1. Validar HMAC X-Hub-Signature-256 (validate_evolution_signature)
      2. Idempotency via evolution_ingest (DB) + chat_pipeline.check_idempotency (Redis)
      3. Parse payload → InboundMessage
      4. process_message (pipeline compartilhado)
      5. HMAC inválido → 401 (fail-closed). Demais erros de parse → 200
         para evitar retry storm da Evolution quando autenticado.
    """
    bump_metric("requests_total")
    from app.services.metrics import store

    store.inc_counter("cartorio_whatsapp_mensagens_total", labels={"direction": "in"})
    raw_body = await request.body()

    # 1. Auth: HMAC X-Hub-Signature-256 **ou** header secreto (Evolution não assina body)
    signature = request.headers.get("X-Hub-Signature-256") or request.headers.get(
        "X-Evolution-Signature"
    )
    shared_secret_header = (
        request.headers.get("X-Evolution-Webhook-Secret")
        or request.headers.get("X-Webhook-Secret")
        or request.headers.get("Authorization")
    )
    secret_configured = bool(
        os.getenv("EVOLUTION_WEBHOOK_SECRET") or os.getenv("EVOLUTION_WEBHOOK_SECRET_PREV")
    )
    production_mode = settings.app_env == "production"
    require_env = os.getenv("EVOLUTION_REQUIRE_SIGNATURE")
    if require_env is not None:
        signature_required = production_mode or require_env.lower() == "true"
    else:
        signature_required = production_mode or secret_configured
    auth_supplied = bool(signature or shared_secret_header)
    if (signature_required or auth_supplied) and not secret_configured:
        logger.error("WhatsApp webhook: HMAC obrigatório sem secret configurado")
        raise HTTPException(status_code=503, detail="webhook authentication misconfigured")

    adapter = get_adapter()
    signature_valid = False
    if secret_configured:
        signature_valid = await adapter.verify_signature(
            raw_body, signature, shared_secret_header=shared_secret_header
        )
    if (signature_required or auth_supplied) and not signature_valid:
        logger.warning("WhatsApp webhook: auth inválida (rejeitando)")
        # E3.06: 401 do webhook vira serie observavel (anti brute-force/scan)
        store.inc_webhook_auth_failures("whatsapp")
        raise HTTPException(status_code=401, detail="invalid webhook signature")
    if not signature_required and not auth_supplied:
        logger.warning("WhatsApp webhook sem auth aceito somente fora de produção")

    # 2. Parse + allowlist antes de banco, consentimento, cache, fila ou LLM.
    inbound = parse_evolution_payload(payload)
    if inbound is None:
        return {"status": "ignored", "detail": "not a messages.upsert event"}
    access = decide_whatsapp_access(
        inbound.sender_id,
        sender_id_alt=str(inbound.extra.get("remote_jid_alt") or ""),
        allowed_sender_hashes=settings.pietra_whatsapp_allowed_sender_hashes,
        hmac_key=settings.pietra_whatsapp_allowlist_hmac_key,
        restrict_inbound=settings.pietra_whatsapp_restrict_inbound,
    )
    if not access.allowed:
        logger.info("WhatsApp webhook ignored by sender policy: reason=%s", access.reason)
        return {"status": "ignored", "detail": "sender_not_authorized"}
    adapter.authorize_recipient(inbound.sender_id)

    # 3. Idempotency DB-level somente para remetente autorizado.
    try:
        ingest_result = ingest_evolution_event(db, payload)
        if ingest_result.get("status") == "idempotent":
            return {"status": "idempotent", "detail": "already processed"}
        # Persistir a reserva de idempotência antes de enfileirar o pipeline.
        # `get_db` somente fecha a sessão; sem commit o replay seria aceito.
        db.commit()
    except IntegrityError:
        # Corrida entre duas entregas do mesmo update: a unique constraint é a
        # fonte de verdade. O segundo request não pode chegar ao pipeline.
        db.rollback()
        return {"status": "idempotent", "detail": "already processed"}
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("evolution_ingest indisponível: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="webhook idempotency unavailable") from exc

    # =========================================================================
    # LGPD Consent Banner + Opt-out (PARAR/SAIR) + Audit Log - Wave 3 (S3.T3)
    # =========================================================================
    from datetime import datetime, timezone
    from app.services.audit import AuditService

    sender_id = inbound.sender_id
    sender_alt = str(inbound.extra.get("remote_jid_alt") or "")
    normalized_sender = normalize_whatsapp_number(sender_alt) or normalize_whatsapp_number(
        sender_id
    )
    sender_hash = pseudonymous_sender_id(
        sender_id,
        hmac_key=settings.pietra_whatsapp_allowlist_hmac_key,
    )
    conversation_pseudonyms = _conversation_pseudonyms(sender_id, sender_alt)
    text_decision = _normalize_lgpd_text_reply(inbound.text)
    poll_id, poll_option = extract_whatsapp_lgpd_poll_vote(payload)

    if not inbound.is_group:
        bus = get_bus()
        # DB e a fonte canonica. Redis e somente cache e jamais concede acesso
        # sozinho, evitando que uma chave stale reverta um opt-out duravel.
        try:
            cliente_db = _find_cliente_for_inbound(
                db,
                normalized_sender=normalized_sender,
                conversation_pseudonyms=conversation_pseudonyms,
            )
        except Exception as exc:
            db.rollback()
            logger.error("DB consent lookup failed: %s", type(exc).__name__)
            raise HTTPException(status_code=503, detail="consent persistence unavailable") from exc

        has_consent = bool(cliente_db and cliente_db.consentimento_lgpd)
        if has_consent and cliente_db is not None:
            try:
                _bind_all_whatsapp_identities(
                    db,
                    cliente=cliente_db,
                    conversation_pseudonyms=conversation_pseudonyms,
                )
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.error("Consent identity binding failed: %s", type(exc).__name__)
                raise HTTPException(
                    status_code=503,
                    detail="consent persistence unavailable",
                ) from exc
            await _cache_consent_granted(bus, conversation_pseudonyms)

        if poll_option in (0, 1) and bus and poll_id:
            try:
                already_resolved = bool(await bus.client.get(_poll_resolved_key(poll_id)))
            except Exception:
                already_resolved = False
            if already_resolved:
                return {
                    "status": "ok",
                    "detail": "consent_granted"
                    if has_consent or poll_option == 0
                    else "consent_declined",
                    "idempotent": True,
                    "kind": "poll_answer",
                }

        # 3. Opt-out e opt-in sao sempre explicitos; contato inicial nao e consentimento.
        if inbound.text.strip().lower() in ("parar", "sair", "optout", "opt-out", "cancelar"):
            if has_consent and cliente_db is not None:
                try:
                    from app.models.cliente import MotivoEncerramento

                    cliente_db.consentimento_lgpd = False
                    cliente_db.motivo_encerramento = MotivoEncerramento.REVOGACAO_CONSENTIMENTO
                    AuditService.log(
                        db,
                        actor_id="whatsapp:cliente",
                        actor_type="user",
                        action="consent.whatsapp.revoked",
                        resource=f"cliente:{cliente_db.id}",
                        payload={
                            "sender_hash": sender_hash,
                            "status": "revoked",
                            "canal": "whatsapp",
                        },
                        canal="whatsapp",
                    )
                except Exception as exc:
                    db.rollback()
                    logger.error("Consent revocation transaction failed: %s", type(exc).__name__)
                    raise HTTPException(
                        status_code=503,
                        detail="consent revocation not persisted",
                    ) from exc

                cache_synced = await _cache_consent_cleared(bus, conversation_pseudonyms)
                msg_optout = OutboundMessage(
                    channel=inbound.channel,
                    recipient_id=sender_id,
                    text="Entendido. Seu consentimento foi revogado com sucesso. Seus dados de atendimento nao serao mais processados por nossa IA. Caso queira reativar, basta enviar uma nova mensagem e digitar SIM.",
                )
                await adapter.send(msg_optout)
                return {
                    "status": "ok",
                    "detail": "consent_revoked",
                    "cache_synced": cache_synced,
                }
            return {"status": "ok", "detail": "consent_required"}

        opt_in_requested = text_decision == "accept" or poll_option == 0
        opt_out_requested = text_decision == "reject" or poll_option == 1
        if has_consent and opt_in_requested:
            if poll_option == 0:
                return {
                    "status": "ok",
                    "detail": "consent_already_granted",
                    "idempotent": True,
                    "kind": "poll_answer",
                }
            ack_sent = await adapter.send(
                OutboundMessage(
                    channel=inbound.channel,
                    recipient_id=sender_id,
                    text="Consentimento ja confirmado. Como posso ajudar?",
                )
            )
            return {
                "status": "ok",
                "detail": "consent_already_granted",
                "ack_sent": ack_sent,
            }

        if not has_consent and opt_out_requested:
            if bus:
                await _cache_consent_cleared(bus, conversation_pseudonyms)
            if bus and poll_id:
                try:
                    await bus.client.set(_poll_resolved_key(poll_id), "1", ex=LGPD_POLL_TTL)
                except Exception:
                    pass
            declined = await adapter.send(
                OutboundMessage(
                    channel=inbound.channel,
                    recipient_id=sender_id,
                    text=LGPD_CONSENT_DENIED,
                )
            )
            return {
                "status": "ok",
                "detail": "consent_declined",
                "ack_sent": declined,
                "kind": "poll_answer" if poll_option == 1 else "lgpd_consent",
            }

        if not has_consent and opt_in_requested:
            if cliente_db is None:
                try:
                    cliente_db = _provision_allowed_whatsapp_cliente(
                        db,
                        normalized_sender=normalized_sender,
                        access_reason=access.reason,
                    )
                except Exception as exc:
                    db.rollback()
                    logger.error("Consent cliente provisioning failed: %s", type(exc).__name__)
                    raise HTTPException(
                        status_code=503,
                        detail="consent persistence unavailable",
                    ) from exc
                if cliente_db is None:
                    raise HTTPException(status_code=503, detail="consent persistence unavailable")
            try:
                cliente_db.consentimento_lgpd = True
                cliente_db.consentimento_em = datetime.now(timezone.utc)
                cliente_db.consentimento_canal = "whatsapp"
                _bind_all_whatsapp_identities(
                    db,
                    cliente=cliente_db,
                    conversation_pseudonyms=conversation_pseudonyms,
                )
                AuditService.log(
                    db,
                    actor_id="whatsapp:cliente",
                    actor_type="user",
                    action="consent.whatsapp",
                    resource=f"cliente:{cliente_db.id}",
                    payload={
                        "sender_hash": sender_hash,
                        "status": "granted",
                        "canal": "whatsapp",
                    },
                    canal="whatsapp",
                )
            except Exception as exc:
                db.rollback()
                logger.error("Consent grant transaction failed: %s", type(exc).__name__)
                raise HTTPException(
                    status_code=503,
                    detail="consent grant not persisted",
                ) from exc

            cache_synced = await _cache_consent_granted(bus, conversation_pseudonyms)
            if bus and poll_id:
                try:
                    await bus.client.set(_poll_resolved_key(poll_id), "1", ex=LGPD_POLL_TTL)
                except Exception:
                    pass
            db.commit()
            ack_sent = await adapter.send(
                OutboundMessage(
                    channel=inbound.channel,
                    recipient_id=sender_id,
                    text=LGPD_CONSENT_ACK,
                )
            )
            return {
                "status": "ok",
                "detail": "consent_granted",
                "cache_synced": cache_synced,
                "ack_sent": ack_sent,
                "kind": "poll_answer" if poll_option == 0 else "lgpd_consent",
            }

        if not has_consent:
            await _send_whatsapp_lgpd_request(
                adapter,
                sender_id=sender_id,
                bus=bus,
                pseudonyms=conversation_pseudonyms,
            )
            AuditService.log_system_action(
                action="consent.whatsapp.requested",
                payload={"sender_hash": sender_hash, "status": "pending", "canal": "whatsapp"},
            )
            return {"status": "ok", "detail": "consent_required", "kind": "lgpd_gate"}

    # 4. Pipeline compartilhado
    request_id = request.headers.get("X-Request-ID", f"wa-{int(time.time() * 1000)}")
    background_tasks.add_task(
        process_message,
        inbound,
        adapter,
        request_id=request_id,
    )

    return {"status": "ok", "channel": "whatsapp", "request_id": request_id}


@router.get("/debug/last-messages")
async def whatsapp_debug_last_messages(
    _api_key: str = Depends(require_cartorio_api_key),
) -> dict:
    """Debug: últimas N mensagens processadas (do Redis audit log)."""
    bus = get_bus()
    if not bus:
        return {"messages": [], "detail": "redis indisponível"}
    try:
        raw = await bus.client.lrange("audit:bot:whatsapp", 0, 19)
        messages = [json.loads(r) for r in raw]
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        return {"messages": [], "detail": str(e)}


@router.post("/test/send")
async def whatsapp_test_send(
    to: str,
    text: str,
    _api_key: str = Depends(require_cartorio_api_key),
) -> dict:
    """Smoke test local: envia mensagem via Evolution sem webhook.

    Útil para SUI Gustavo validar após QR scan:
      curl -X POST 'https://api.2notasudi.com.br/api/v1/whatsapp/test/send?to=5511999999999&text=Oi'
    """
    if settings.app_env == "production":
        raise HTTPException(status_code=404, detail="not found")
    adapter = get_adapter()
    out = OutboundMessage(
        channel=Channel.WHATSAPP,
        recipient_id=to if "@" in to else f"{to}@s.whatsapp.net",
        text=text,
    )
    sent = await adapter.send(out)
    return {"sent": sent, "ts": time.time()}
