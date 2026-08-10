"""Lark Bot webhook - canal Hermes Cartorio AI.

Endpoints (rotas já registradas em ``app.main``):
- POST /api/v1/lark/webhook/lark : recebe eventos do Lark (url_verification + mensagens)
- GET  /api/v1/lark/qr        : gera QR Code PNG para adicionar o bot
- GET  /api/v1/lark/qr-url    : retorna a URL configurada para adicionar o bot

PII e seguranca:
- X-Lark-Signature validado via HMAC-SHA256 com LARK_ENCRYPT_KEY obrigatoria.
- Token de verificacao Lark obrigatorio para todo callback, inclusive challenge.
- Conteudo scrubbado antes de ir ao LLM.
- Idempotencia por event_id no Redis (SETNX, 24h).
- Rate limit por tenant (100 req/min) no Redis, fail-open.

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import logging
import os
import time
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.services.lark import send_text_message
from app.services.pii import scrub
from app.services.redis_bus import get_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lark", tags=["lark"])

LARK_ENCRYPT_KEY: str | None = (
    getattr(settings, "lark_encrypt_key", None) or os.environ.get("LARK_ENCRYPT_KEY") or None
)
LARK_VERIFICATION_TOKEN: str | None = os.environ.get("LARK_VERIFICATION_TOKEN") or None
LARK_ADD_BOT_URL: str | None = (
    getattr(settings, "lark_add_bot_url", None) or os.environ.get("LARK_ADD_BOT_URL") or None
)
LARK_WEBHOOK_RATE_LIMIT_PER_MIN = int(os.environ.get("LARK_WEBHOOK_RATE_LIMIT_PER_MIN", "100"))
LARK_IDEMPOTENCY_TTL_SECONDS = int(os.environ.get("LARK_IDEMPOTENCY_TTL_SECONDS", "86400"))
LARK_WEBHOOK_MAX_AGE_SECONDS = min(
    max(int(os.environ.get("LARK_WEBHOOK_MAX_AGE_SECONDS", "300")), 30), 900
)
LARK_WEBHOOK_MAX_FUTURE_SKEW_SECONDS = min(
    max(int(os.environ.get("LARK_WEBHOOK_MAX_FUTURE_SKEW_SECONDS", "30")), 0), 300
)


def _get_lark_credentials() -> tuple[str, str]:
    """Retorna (app_id, app_secret) sem expor segredo em logs."""
    app_id = getattr(settings, "lark_app_id", None) or os.environ.get("LARK_APP_ID", "")
    app_secret = getattr(settings, "lark_app_secret", None) or os.environ.get("LARK_APP_SECRET", "")
    return app_id, app_secret


def _verify_lark_signature(
    body_raw: bytes,
    signature: str | None,
    timestamp: str | None,
    nonce: str | None,
) -> bool:
    """Valida X-Lark-Signature usando LARK_ENCRYPT_KEY.

    Algoritmo Lark: HMAC-SHA256(timestamp + nonce + body, key).
    Ausencia de chave, assinatura, timestamp ou nonce e sempre uma rejeicao.
    """
    if not LARK_ENCRYPT_KEY or not signature or not timestamp or not nonce:
        return False
    if not timestamp.isdigit() or not nonce.isascii() or not 16 <= len(nonce) <= 256:
        return False
    request_timestamp = int(timestamp)
    now = int(time.time())
    if (
        not now - LARK_WEBHOOK_MAX_AGE_SECONDS
        <= request_timestamp
        <= now + LARK_WEBHOOK_MAX_FUTURE_SKEW_SECONDS
    ):
        return False
    key = LARK_ENCRYPT_KEY.encode("utf-8")
    try:
        body = body_raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    message = f"{timestamp}{nonce}{body}"
    expected = hmac.new(key, message.encode("utf-8"), "sha256").hexdigest()
    return hmac.compare_digest(expected, signature)


def _lark_webhook_configuration_ready() -> bool:
    """Require both independent inbound authentication factors before accepting a callback."""
    return bool(LARK_ENCRYPT_KEY and LARK_VERIFICATION_TOKEN)


def _verify_lark_event_token(payload: dict[str, Any]) -> bool:
    """Validate Lark's event verification token without ever logging either value."""
    verification_token = LARK_VERIFICATION_TOKEN
    if not verification_token:
        return False
    header_candidate = payload.get("header")
    header: dict[str, Any] = header_candidate if isinstance(header_candidate, dict) else {}
    provided = payload.get("token") or header.get("token")
    if not isinstance(provided, str) or not provided:
        return False
    return hmac.compare_digest(provided, verification_token)


async def _claim_lark_nonce(nonce: str) -> bool:
    """Consume one signed nonce in Redis; unavailable replay protection blocks the callback."""
    if not nonce.isascii() or not 16 <= len(nonce) <= 256:
        return False
    try:
        bus = get_bus()
        nonce_digest = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        result = await bus.client.set(
            f"lark:nonce:{nonce_digest}",
            "1",
            nx=True,
            ex=LARK_WEBHOOK_MAX_AGE_SECONDS + LARK_WEBHOOK_MAX_FUTURE_SKEW_SECONDS,
        )
        return result is not None and result is not False
    except Exception as exc:
        logger.warning("Lark nonce store unavailable: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "erro": "LARK_REPLAY_PROTECTION_UNAVAILABLE",
                "mensagem": "Canal Lark indisponivel",
            },
        ) from exc


def _decrypt_lark_payload(encrypt_b64: str) -> dict[str, Any]:
    """Descriptografa payload criptografado do Lark.

    Lark usa AES-256-CBC com chave derivada de LARK_ENCRYPT_KEY.
    Se a biblioteca cryptography nao estiver disponivel, levanta RuntimeError.
    """
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding
    except ImportError as exc:
        raise RuntimeError(
            "cryptography nao instalado - nao e possivel descriptografar Lark"
        ) from exc

    if not LARK_ENCRYPT_KEY:
        raise RuntimeError("LARK_ENCRYPT_KEY nao configurado")

    # A chave de criptografia do Lark e a string em si (32 bytes se a string tiver 32 chars).
    key = LARK_ENCRYPT_KEY.encode("utf-8")
    if len(key) < 32:
        # Pad com zeros se necessario (fallback defensivo)
        key = key.ljust(32, b"\0")
    elif len(key) > 32:
        key = key[:32]

    encrypted = base64.b64decode(encrypt_b64)
    # Lark AES-256-CBC: IV nos primeiros 16 bytes
    iv = encrypted[:16]
    ciphertext = encrypted[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    plain = unpadder.update(padded) + unpadder.finalize()
    return json.loads(plain.decode("utf-8"))


def _parse_event_payload(body_raw: bytes) -> dict[str, Any]:
    """Parse do body do webhook Lark (plain ou criptografado)."""
    try:
        payload = json.loads(body_raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"erro": "INVALID_JSON", "mensagem": "Body nao e JSON valido"},
        ) from exc

    if "encrypt" in payload:
        if not LARK_ENCRYPT_KEY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "erro": "ENCRYPTION_REQUIRED",
                    "mensagem": "Payload criptografado exige LARK_ENCRYPT_KEY",
                },
            )
        try:
            return _decrypt_lark_payload(payload["encrypt"])
        except Exception as exc:
            logger.warning("Lark decrypt failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"erro": "DECRYPT_FAILED", "mensagem": "Falha ao descriptografar payload"},
            ) from exc
    return payload


def _extract_message_text(event: dict[str, Any]) -> tuple[str, str, str]:
    """Extrai (sender_open_id, chat_id, texto) do evento de mensagem.

    Suporta msg_type 'text' e fallback para content.raw.
    """
    message = event.get("message", {}) or {}
    sender = event.get("sender", {}).get("sender_id", {}).get("open_id", "")
    chat_id = message.get("chat_id", "")
    msg_type = message.get("msg_type", "")
    content_str = message.get("content", "{}")
    try:
        content = json.loads(content_str) if isinstance(content_str, str) else content_str
    except json.JSONDecodeError:
        content = {}

    text = ""
    if msg_type == "text":
        text = content.get("text", "")
    else:
        text = content.get("text", "") or str(content)
    return sender, chat_id, text


async def _check_idempotency(event_id: str) -> bool:
    """Retorna True se event_id ja foi processado (replay)."""
    if not event_id:
        return False
    try:
        bus = get_bus()
        key = f"lark:idem:{event_id}"
        result = await bus.client.set(key, "1", nx=True, ex=LARK_IDEMPOTENCY_TTL_SECONDS)
        already = result is None or result is False
        if already:
            logger.warning("Lark duplicate event_id=%s blocked", event_id)
        return already
    except Exception as exc:
        logger.warning("Lark idempotency store unavailable: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"erro": "LARK_IDEMPOTENCY_UNAVAILABLE", "mensagem": "Canal Lark indisponivel"},
        ) from exc


async def _check_rate_limit(tenant_key: str) -> bool:
    """Rate limit por tenant: 100 req/min (ajustavel via env). Fail-open."""
    if not tenant_key:
        return True
    try:
        bus = get_bus()
        now_minute = int(time.time() // 60)
        key = f"lark:ratelimit:{tenant_key}:{now_minute}"
        pipe = bus.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)
        current, _ = await pipe.execute()
        return int(current) <= LARK_WEBHOOK_RATE_LIMIT_PER_MIN
    except Exception as exc:
        logger.warning("Lark rate limit store unavailable: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"erro": "LARK_RATE_LIMIT_UNAVAILABLE", "mensagem": "Canal Lark indisponivel"},
        ) from exc


async def _persist_conversa_lark(
    external_id: str,
    raw_message_scrubbed: str,
    bot_response: str,
    provider: str,
    handoff_to_human: bool = False,
) -> None:
    """Persiste turno no Postgres via conversa table (best-effort)."""
    try:
        from app.api.v1.telegram import _persist_conversa  # type: ignore[attr-defined]

        _persist_conversa(
            canal="lark",
            external_id=external_id,
            raw_message_scrubbed=raw_message_scrubbed,
            intent_detected=None,
            bot_response=bot_response,
            llm_model=provider,
            handoff_to_human=handoff_to_human,
            handoff_reason="agent_action_humano" if handoff_to_human else None,
        )
    except Exception as exc:
        logger.debug("Lark persist_conversa best-effort failed: %s", type(exc).__name__)


@router.post("/webhook/lark")
async def lark_webhook(
    request: Request,
    x_lark_signature: str | None = Header(None, alias="X-Lark-Signature"),
    x_lark_timestamp: str | None = Header(None, alias="X-Lark-Timestamp"),
    x_lark_nonce: str | None = Header(None, alias="X-Lark-Nonce"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Webhook do Lark Bot.

    - url_verification: retorna challenge imediatamente.
    - Mensagens: valida assinatura, idempotencia, rate limit, scrub PII,
      executa agente e responde pelo Lark.
    """
    body_raw = await request.body()

    # 1. Nunca habilita callback em modo sem credenciais: evita fail-open acidental.
    if not _lark_webhook_configuration_ready():
        logger.warning("Lark webhook rejected: inbound authentication is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"erro": "LARK_NOT_CONFIGURED", "mensagem": "Canal Lark indisponivel"},
        )

    # 2. Valida assinatura HMAC-SHA256.
    if not _verify_lark_signature(body_raw, x_lark_signature, x_lark_timestamp, x_lark_nonce):
        logger.warning("Lark webhook signature verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"erro": "UNAUTHORIZED", "mensagem": "Assinatura Lark invalida"},
        )

    # 3. Consume the signed nonce before parsing or any downstream side effect.
    if not await _claim_lark_nonce(x_lark_nonce or ""):
        logger.warning("Lark webhook rejected: replayed nonce")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"erro": "REPLAYED_CALLBACK", "mensagem": "Callback repetido"},
        )

    # 4. Parse payload (plain ou criptografado)
    payload = _parse_event_payload(body_raw)

    # 5. Valida token de verificacao apos decriptar o envelope, quando aplicavel.
    if not _verify_lark_event_token(payload):
        logger.warning("Lark webhook verification token rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"erro": "UNAUTHORIZED", "mensagem": "Token de verificacao Lark invalido"},
        )

    # 6. url_verification challenge
    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge")
        if not isinstance(challenge, str) or not challenge or len(challenge) > 512:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"erro": "INVALID_CHALLENGE", "mensagem": "Challenge Lark invalido"},
            )
        return {"challenge": challenge}

    # 7. Processa eventos de mensagem
    event = payload.get("event", {}) or {}
    header = payload.get("header", {}) or {}
    event_id = header.get("event_id") or event.get("message", {}).get("message_id")
    tenant_key = header.get("tenant_key") or "default"

    if not isinstance(event_id, str) or not event_id or len(event_id) > 256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"erro": "MISSING_EVENT_ID", "mensagem": "Evento Lark invalido"},
        )

    # Idempotencia
    if await _check_idempotency(event_id):
        return {"status": "ignored", "reason": "duplicate_event_id"}

    # Rate limit por tenant
    if not await _check_rate_limit(str(tenant_key)):
        return {
            "status": "rate_limited",
            "retry_after": 60 - (int(time.time()) % 60),
        }

    sender_open_id, chat_id, text = _extract_message_text(event)
    if not sender_open_id:
        return {"status": "ignored", "reason": "missing_sender"}

    # Scrub PII antes do LLM
    text_scrubbed = scrub(text).text

    # Executa agente
    try:
        from app.services.cartorio_agent import run_cartorio_agent

        reply = await run_cartorio_agent(
            text_scrubbed,
            history=None,
            attachments=None,
            chat_id=sender_open_id,
        )
        answer = reply.text or ""
    except Exception as exc:
        logger.warning("Lark agent error: %s", type(exc).__name__)
        answer = (
            "Tive uma falha momentanea no raciocinio. "
            "Tente novamente em alguns instantes ou fale com um escrevente."
        )

    # Scrub de saida
    answer = scrub(answer).text
    if not answer.strip():
        answer = (
            "Sou a Pietra, assistente virtual do 2o Cartorio de Notas de Uberlandia.\n"
            "Como posso ajudar?"
        )

    # Envia resposta pelo Lark (best-effort)
    try:
        await send_text_message(
            receive_id=sender_open_id,
            text=answer,
            receive_id_type="open_id",
        )
        sent = True
    except Exception as exc:
        logger.warning("Lark send_text_message failed: %s", type(exc).__name__)
        sent = False

    # Persistencia best-effort
    await _persist_conversa_lark(
        external_id=sender_open_id,
        raw_message_scrubbed=text_scrubbed,
        bot_response=answer,
        provider="cartorio-agent",
        handoff_to_human="escrevente" in answer.lower() or "humano" in answer.lower(),
    )

    return {"status": "ok" if sent else "partial"}


@router.get("/qr")
async def lark_qr_code(
    url: str | None = Query(None, description="URL opcional para gerar o QR Code"),
) -> Response:
    """Gera QR Code PNG para adicionar o bot Lark.

    Usa LARK_ADD_BOT_URL do .env se nenhuma URL for passada via query string.
    Se nem configuracao nem parametro existirem, retorna 503 com instrucoes.
    """
    target_url = url or LARK_ADD_BOT_URL
    if not target_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "erro": "LARK_ADD_BOT_URL_NOT_CONFIGURED",
                "mensagem": "Configure LARK_ADD_BOT_URL no .env ou passe ?url=...",
            },
        )

    try:
        import qrcode  # type: ignore[import-untyped]
        import qrcode.image.svg  # type: ignore[import-untyped]
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "erro": "QRCODE_LIBRARY_MISSING",
                "mensagem": "Instale a dependencia qrcode (ex: uv add qrcode[pil])",
            },
        ) from exc

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={"Content-Disposition": "inline; filename=lark_add_bot.png"},
    )


@router.get("/qr-url")
async def lark_qr_url() -> dict[str, Any]:
    """Retorna a URL configurada para adicionar o bot (sem expor segredos)."""
    return {
        "configured": bool(LARK_ADD_BOT_URL),
        "url": LARK_ADD_BOT_URL,
        "qr_endpoint": "/api/v1/lark/qr",
    }
