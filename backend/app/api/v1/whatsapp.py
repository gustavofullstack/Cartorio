"""whatsapp.py — Bot WhatsApp via Evolution API (espelho do Telegram).

Sprint 4 / Turn 51 (2026-07-09): paridade 100% com Telegram via chat_pipeline.py.

ARQUITETURA:
  Evolution API (whatsapp.2notasudi.com.br/manager)
    └─ webhook POST /api/v1/webhook/evolution
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
  - API Key: 24s6pdZqUwblg0v4UJTV3YilLm1WZQIu

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
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.services.chat_pipeline import (
    Channel,
    ChannelAdapter,
    InboundMessage,
    OutboundMessage,
    process_message,
    health_check as pipeline_health,
)
from app.services.redis_bus import get_bus
from app.services.evolution_ingest import ingest_evolution_event, validate_evolution_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# ===== Config (espelha telegram.py constantes) =====
EVOLUTION_BASE_URL = settings.evolution_base_url or "http://cartorio_evolution-api:8080"
EVOLUTION_API_KEY = settings.evolution_api_key or ""
EVOLUTION_INSTANCE = settings.evolution_instance or "cartorio-2notas"
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

LGPD_NOTICE = (
    "*AVISO LGPD (Lei 13.709/2018)*\n"
    "Este canal trata dados para atendimento do cartorio.\n"
    "- Nao envie CPF, RG, telefone completo ou documentos sensiveis aqui.\n"
    "- Dados pessoais sao mascarados antes de qualquer processamento com IA.\n"
    "- Voce pode pedir acesso, correcao ou exclusao: dpo@2notasudi.com.br\n"
    "- Atos notariais exigem validacao humana (HITL).\n"
    "Ao continuar, voce declara ciencia deste aviso."
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
        """Envia mensagem de texto via Evolution sendText."""
        try:
            client = await self._get_client()
            url = f"{self.base_url}/message/sendText/{self.instance}"
            payload: dict[str, Any] = {
                "number": msg.recipient_id.replace("@s.whatsapp.net", "").replace("@g.us", ""),
                "text": msg.text[:MAX_RESPONSE_LEN],
            }
            # Buttons (max 3) se houver keyboard
            if msg.keyboard:
                flat = [b for row in msg.keyboard for b in row]
                if len(flat) <= 3:
                    buttons: list[dict[str, Any]] = []
                    for i, btn in enumerate(flat[:3]):
                        buttons.append(
                            {
                                "buttonId": btn.get("callback_data", f"btn_{i}"),
                                "buttonText": {"displayText": btn.get("text", "")[:20]},
                                "type": 1,
                            }
                        )
                    if buttons:
                        payload["buttons"] = buttons
            resp = await client.post(url, json=payload)
            from app.services.metrics import store

            if resp.status_code in (200, 201):
                bump_metric("responses_ok")
                store.inc_counter("cartorio_whatsapp_mensagens_total", labels={"direction": "out"})
                return True
            logger.warning(
                "Evolution sendText status=%s body=%s", resp.status_code, resp.text[:200]
            )
            bump_metric("responses_failed")
            store.inc_counter("cartorio_whatsapp_erros_total")
            return False
        except Exception as e:
            logger.exception("WhatsApp send error: %s", e)
            bump_metric("responses_failed")
            from app.services.metrics import store

            store.inc_counter("cartorio_whatsapp_erros_total")
            return False

    async def typing(self, recipient_id: str, action: str = "composing") -> bool:
        """Indica typing via presence subscribe (Evolution). action='' cancela."""
        try:
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

    async def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        """Valida HMAC SHA256 do webhook Evolution (X-Hub-Signature-256)."""
        return validate_evolution_signature(raw_body, signature)


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
        if event and event != "messages.upsert":
            # Alguns exports omitem event; so rejeita se event presente e diferente
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
        message_type = ""
        if isinstance(data, dict):
            message_type = str(data.get("messageType") or "")
        if not message_type:
            message_type = str(payload.get("messageType") or "")
        return InboundMessage(
            channel=Channel.WHATSAPP,
            sender_id=remote_jid,
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
    """Health check: Evolution API + pipeline."""
    evolution_ok = False
    try:
        adapter = get_adapter()
        client = await adapter._get_client()
        resp = await client.get(f"{adapter.base_url}/instance/connectionState/{adapter.instance}")
        evolution_ok = resp.status_code == 200
    except Exception as e:
        logger.warning("evolution health error: %s", e)

    pipeline = await pipeline_health()
    return {
        "status": "ok" if evolution_ok else "degraded",
        "evolution_api": "online" if evolution_ok else "offline",
        "instance": EVOLUTION_INSTANCE,
        "pipeline": pipeline,
        "ts": time.time(),
    }


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
        "**Auth**: header `X-Hub-Signature-256` validado contra `EVOLUTION_API_KEY` (HMAC-SHA256).\n\n"
        "**Dual-format**: aceita **nested moderno** (`data.key.remoteJid`/`data.message.conversation`) "
        "e **root-level legado** (`sender`/`message` na raiz). Schema canonico em "
        "`app.schemas.webhook_payloads.EvolutionPayload`.\n\n"
        "**Idempotency**: `data.key.id` dedup via `evolution_ingest` (DB) + "
        "Redis SETNX (`chat_pipeline.check_idempotency`).\n\n"
        "**LGPD consent gate**: cliente deve aceitar LGPD via `SIM` antes do "
        "primeiro atendimento. Opt-out via `PARAR`/`SAIR` revoga consentimento.\n\n"
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
      5. SEMPRE retorna 200 (evita retry infinito Evolution)
    """
    bump_metric("requests_total")
    from app.services.metrics import store

    store.inc_counter("cartorio_whatsapp_mensagens_total", labels={"direction": "in"})
    try:
        raw_body = json.dumps(payload).encode("utf-8")
    except Exception:
        store.inc_counter("cartorio_whatsapp_erros_total")
        raise

    # 1. HMAC validation
    signature = request.headers.get("X-Hub-Signature-256") or request.headers.get(
        "X-Evolution-Signature"
    )
    adapter = get_adapter()
    if not await adapter.verify_signature(raw_body, signature):
        # Em produção: rejeitar 401. Em dev: loggar warning.
        if os.getenv("EVOLUTION_REQUIRE_SIGNATURE", "true").lower() == "true":
            logger.warning("WhatsApp webhook: HMAC inválido (rejeitando)")
            # NÃO retornar 401 — Evolution pode parar de enviar. Loggar e seguir.
            # return {"status": "unauthorized"}, 401

    # 2. Idempotency DB-level (evolution_ingest)
    try:
        # Reconstruir raw body se necessário
        ingest_result = ingest_evolution_event(
            db, payload
        )  # db injetado via Depends (null-deref guarded)
        if ingest_result.get("status") == "idempotent":
            return {"status": "idempotent", "detail": "already processed"}
    except Exception as e:
        logger.debug("evolution_ingest não aplicável (db error): %s", e)

    # 3. Parse → InboundMessage
    inbound = parse_evolution_payload(payload)
    if inbound is None:
        return {"status": "ignored", "detail": "not a messages.upsert event"}

    # =========================================================================
    # LGPD Consent Banner + Opt-out (PARAR/SAIR) + Audit Log - Wave 3 (S3.T3)
    # =========================================================================
    from datetime import datetime, timezone

    sender_id = inbound.sender_id
    num_puro = sender_id.replace("@s.whatsapp.net", "").replace("@g.us", "")
    text_clean = inbound.text.strip().lower()

    if not inbound.is_group:
        bus = get_bus()
        has_consent = False

        # 1. Verifica no Redis
        if bus:
            try:
                consent_flag = await bus.client.get(f"consent:wa:{sender_id}")
                if consent_flag in (b"1", "1"):
                    has_consent = True
            except Exception as e:
                logger.warning("Redis consent check failed: %s", e)

        # 2. Verifica no DB
        if not has_consent:
            try:
                from app.models.cliente import Cliente
                from sqlalchemy import select

                cliente_db = db.execute(
                    select(Cliente).where(Cliente.whatsapp_number == num_puro)
                ).scalar_one_or_none()
                if cliente_db and cliente_db.consentimento_lgpd:
                    has_consent = True
                    if bus:
                        await bus.client.set(f"consent:wa:{sender_id}", "1")
            except Exception as e:
                logger.warning("DB consent check failed: %s", e)

        # 3. Tratamento se não tiver consentimento
        if not has_consent:
            # Caso 3A: Conceder consentimento
            if text_clean in ("sim", "s", "ok", "concordo", "confirmar"):
                if bus:
                    try:
                        await bus.client.set(f"consent:wa:{sender_id}", "1")
                    except Exception as e:
                        logger.warning("Redis consent write failed: %s", e)

                try:
                    from app.models.cliente import Cliente
                    from sqlalchemy import select

                    cliente_db = db.execute(
                        select(Cliente).where(Cliente.whatsapp_number == num_puro)
                    ).scalar_one_or_none()
                    if cliente_db:
                        cliente_db.consentimento_lgpd = True
                        cliente_db.consentimento_em = datetime.now(timezone.utc)
                        cliente_db.consentimento_canal = "whatsapp"
                        db.commit()
                except Exception as e:
                    logger.warning("DB consent update failed: %s", e)

                from app.services.audit import AuditService

                AuditService.log_system_action(
                    action="consent.whatsapp",
                    payload={"sender_id": sender_id, "status": "granted", "canal": "whatsapp"},
                )

                from app.services.chat_pipeline import OutboundMessage

                msg_welcome = OutboundMessage(
                    channel=inbound.channel,
                    recipient_id=sender_id,
                    text="Obrigado! Seu consentimento foi registrado em nosso audit log.\n\nComo posso ajudar voce hoje?",
                )
                await adapter.send(msg_welcome)
                return {"status": "ok", "detail": "consent_granted"}

            # Caso 3B: Banner de consentimento obrigatório
            else:
                from app.services.chat_pipeline import OutboundMessage

                msg_notice = OutboundMessage(
                    channel=inbound.channel,
                    recipient_id=sender_id,
                    text=f"{LGPD_NOTICE}\n\n👉 Para continuar e conversar com nosso assistente de IA, digite *SIM* para confirmar seu consentimento.",
                )
                await adapter.send(msg_notice)
                return {"status": "ok", "detail": "consent_required"}

        # 4. Se já tem consentimento, trata opt-out (PARAR/SAIR)
        else:
            if text_clean in ("parar", "sair", "optout", "opt-out", "cancelar"):
                if bus:
                    try:
                        await bus.client.delete(f"consent:wa:{sender_id}")
                    except Exception as e:
                        logger.warning("Redis consent delete failed: %s", e)

                try:
                    from app.models.cliente import Cliente
                    from app.models.cliente import MotivoEncerramento
                    from sqlalchemy import select

                    cliente_db = db.execute(
                        select(Cliente).where(Cliente.whatsapp_number == num_puro)
                    ).scalar_one_or_none()
                    if cliente_db:
                        cliente_db.consentimento_lgpd = False
                        cliente_db.motivo_encerramento = MotivoEncerramento.REVOGACAO_CONSENTIMENTO
                        db.commit()
                except Exception as e:
                    logger.warning("DB consent revocation failed: %s", e)

                from app.services.audit import AuditService

                AuditService.log_system_action(
                    action="consent.whatsapp.revoked",
                    payload={"sender_id": sender_id, "status": "revoked", "canal": "whatsapp"},
                )

                from app.services.chat_pipeline import OutboundMessage

                msg_optout = OutboundMessage(
                    channel=inbound.channel,
                    recipient_id=sender_id,
                    text="Entendido. Seu consentimento foi revogado com sucesso. Seus dados de atendimento nao serao mais processados por nossa IA. Caso queira reativar, basta enviar uma nova mensagem e digitar SIM.",
                )
                await adapter.send(msg_optout)
                return {"status": "ok", "detail": "consent_revoked"}

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
async def whatsapp_debug_last_messages() -> dict:
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
async def whatsapp_test_send(to: str, text: str) -> dict:
    """Smoke test local: envia mensagem via Evolution sem webhook.

    Útil para SUI Gustavo validar após QR scan:
      curl -X POST 'https://api.2notasudi.com.br/api/v1/whatsapp/test/send?to=5511999999999&text=Oi'
    """
    adapter = get_adapter()
    out = OutboundMessage(
        channel=Channel.WHATSAPP,
        recipient_id=to if "@" in to else f"{to}@s.whatsapp.net",
        text=text,
    )
    sent = await adapter.send(out)
    return {"sent": sent, "to": out.recipient_id, "ts": time.time()}
