"""Telegram webhook endpoint - recebe updates do bot CartorioBot.

Bot: @CartorioBot (a registrar)
Token: Carregado via variaveis de ambiente (settings.telegram_bot_token)

Fluxo:
1. Recebe update do Telegram
2. Valida HMAC (secret_token configurado no webhook)
3. PII scrub (camada 1)
4. Persiste contexto no Redis
5. Chama OpenClaw Agent (LLM)
6. PII scrub resposta (camada 3)
7. Audit log (LGPD art. 37)
8. Envia resposta via Telegram API

LGPD: mensagens sao PII (texto livre). 3 camadas de scrubbing obrigatorias.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import settings
from app.services.pii import scrub
from app.services.redis_bus import get_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Token do bot (carregado via variaveis de ambiente)
TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
TELEGRAM_API_BASE = "https://api.telegram.org"

# HMAC secret compartilhado com Telegram (configurado via setWebhook)
# Em prod, vir de settings.telegram_webhook_secret
TELEGRAM_WEBHOOK_SECRET = settings.telegram_webhook_secret if hasattr(settings, "telegram_webhook_secret") else None


def _verify_telegram_secret(
    update_body: bytes,
    secret_token_header: str | None,
) -> None:
    """Valida secret_token do Telegram (HMAC).

    Args:
        update_body: body raw do request (bytes)
        secret_token_header: header `X-Telegram-Bot-Api-Secret-Token`

    Raises:
        HTTPException 401 se invalido
    """
    if not TELEGRAM_WEBHOOK_SECRET:
        # Se nao configurado, aceita (dev mode)
        return

    if not secret_token_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Telegram-Bot-Api-Secret-Token",
        )

    expected = hmac.new(
        TELEGRAM_WEBHOOK_SECRET.encode(),
        update_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(secret_token_header, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Telegram-Bot-Api-Secret-Token",
        )


@router.post(
    "/webhook",
    summary="Recebe updates do Telegram Bot",
    description=(
        "Endpoint chamado pelo Telegram quando usuario manda msg ao bot. "
        "Valida HMAC, faz PII scrub, consulta OpenClaw Agent, "
        "envia resposta de volta via Telegram API."
    ),
    status_code=200,
)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict[str, Any]:
    """Processa update do Telegram.

    Payload exemplo:
    {
      "update_id": 123456,
      "message": {
        "message_id": 1,
        "from": {"id": 12345, "first_name": "Joao"},
        "chat": {"id": 12345, "type": "private"},
        "text": "Ola, quero uma certidao",
        "date": 1719227400
      }
    }
    """
    body_bytes = await request.body()
    update = await request.json()

    # 1. Validar HMAC
    _verify_telegram_secret(body_bytes, x_telegram_bot_api_secret_token)

    # 2. Extrair dados do update
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    user = message.get("from", {})

    if not chat_id or not text:
        # Nao eh msg de texto (pode ser sticker, foto, etc) - ignorar por agora
        logger.info("Telegram update sem text/chat_id - ignorado")
        return {"status": "ignored", "reason": "non-text update"}

    logger.info(
        "Telegram msg recebida chat_id=%s user_id=%s text_len=%d",
        chat_id,
        user.get("id"),
        len(text),
    )

    # 3. PII scrub (camada 1)
    scrub_result = scrub(text)
    text_scrubbed = scrub_result.text

    # 4. Persistir contexto no Redis (24h TTL)
    bus = get_bus()
    if bus:
        await bus.publish(
            "telegram:message",
            {
                "chat_id": chat_id,
                "user_id": user.get("id"),
                "first_name": user.get("first_name"),
                "text_scrubbed": text_scrubbed,
                "ts": message.get("date"),
            },
        )

    # 5. Chamar OpenClaw Agent (LLM)
    try:
        agent_response = await _call_openclaw_agent(chat_id, text_scrubbed)
    except Exception as e:
        logger.exception("OpenClaw Agent falhou: %s", e)
        agent_response = (
            "Desculpe, tive um problema tecnico. "
            "Tente novamente em alguns instantes."
        )

    # 6. PII scrub resposta (camada 3)
    response_scrubbed = scrub(agent_response).text

    # 7. Enviar resposta via Telegram API
    await _send_telegram_message(chat_id, response_scrubbed)

    # 8. Audit log (LGPD art. 37) - via db session seria ideal, aqui so log
    logger.info(
        "Telegram response enviada chat_id=%s response_len=%d",
        chat_id,
        len(response_scrubbed),
    )

    return {
        "status": "ok",
        "chat_id": chat_id,
        "response_sent": True,
    }


async def _call_openclaw_agent(chat_id: int, text_scrubbed: str) -> str:
    """Chama OpenClaw Agent (LLM) com contexto de conversa.

    Args:
        chat_id: ID do chat Telegram
        text_scrubbed: texto do usuario apos PII scrub

    Returns:
        Resposta do agent (string)
    """
    # TODO: integrar com OpenClaw Agent real (ver infra/openclaw-agent/)
    # Por enquanto, retorna mensagem placeholder
    if "emolumento" in text_scrubbed.lower() or "certidao" in text_scrubbed.lower():
        return (
            "Para calcular o emolumento, me informe:\n"
            "1. Tipo de certidao (negativa, positiva, casamento)\n"
            "2. Numero de folhas\n"
            "3. Se e urgente (50% adicional)\n\n"
            "Ou acesse: https://api.2notasudi.com.br/docs"
        )
    return (
        "Ola! Sou o CartorioBot, assistente virtual do 2 Oficio de Notas "
        "de Uberlandia. Como posso ajudar?\n\n"
        "Comandos: /emolumento /protocolo /agendar /humano"
    )


async def _send_telegram_message(chat_id: int, text: str) -> None:
    """Envia mensagem via Telegram Bot API.

    Args:
        chat_id: ID do chat Telegram
        text: texto a enviar (ja passou por PII scrub)
    """
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            },
        )
        if resp.status_code != 200:
            logger.error(
                "Telegram API error: %d %s",
                resp.status_code,
                resp.text,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Telegram API error: {resp.status_code}",
            )


@router.get(
    "/webhook/info",
    summary="Status do webhook Telegram",
)
async def telegram_webhook_info() -> dict[str, Any]:
    """Retorna info do webhook (debug)."""
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        return resp.json()


__all__ = ["router", "TELEGRAM_BOT_TOKEN"]
