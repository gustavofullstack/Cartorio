"""Telegram webhook endpoint - recebe updates do bot CartorioBot.

Bot: @CartorioBot (a registrar)
Token: 8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q (NAO rotacionar)

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
import re
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.integrations.fallback import chat_with_fallback
from app.services.pii import scrub
from app.services.redis_bus import get_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Token do bot (NUNCA rotacionar - Gustavo + ZCode unicos com acesso)
TELEGRAM_BOT_TOKEN = "8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q"
TELEGRAM_API_BASE = "https://api.telegram.org"

# Regex para remover blocos <think>...</think> que MiniMax-M3 / chain thinking
# retornam antes da resposta final. Telegram parse_mode=HTML nao aceita tag
# "think" -> causa HTTP 400 "Unsupported start tag". Strip ANTES de enviar.
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_think_blocks(text: str) -> str:
    """Remove blocos <think>...</think> e espacos residuais.

    Args:
        text: texto bruto retornado pelo LLM

    Returns:
        texto limpo, sem raciocinio interno
    """
    if not text:
        return text
    cleaned = _THINK_BLOCK_RE.sub("", text)
    # Remove linhas vazias duplicadas que ficam apos strip
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned

# HMAC secret compartilhado com Telegram (configurado via setWebhook)
# Em prod, vir de settings.telegram_webhook_secret
TELEGRAM_WEBHOOK_SECRET = (
    settings.telegram_webhook_secret if hasattr(settings, "telegram_webhook_secret") else None
)


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
    db: Session = Depends(get_db),
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

    # 5. Chamar OpenClaw Agent (LLM) com retry (TURN 47 — absorve flakiness pontual)
    # LLMs pequenos podem ter blip (timeout, 502 gateway, parse). 1 retry com
    # backoff 2s cobre incidentes transitorios sem fazer user esperar muito.
    import asyncio

    last_err: Exception | None = None
    agent_response: str = ""
    for attempt in range(2):
        try:
            agent_response = await _call_openclaw_agent(chat_id, text_scrubbed, db=db)
            last_err = None
            break
        except Exception as e:
            last_err = e
            logger.warning(
                "OpenClaw Agent tentativa %d/2 falhou: %s",
                attempt + 1, e,
            )
            if attempt == 0:
                await asyncio.sleep(2)
    if last_err is not None:
        logger.exception("OpenClaw Agent falhou apos 2 tentativas: %s", last_err)
        agent_response = "Desculpe, tive um problema tecnico. Tente novamente em alguns instantes."

    # 6. Strip blocos <think>...</think> (MiniMax-M3 / thinking models) ANTES do PII scrub.
    # Telegram parse_mode=HTML nao aceita tag "think" -> HTTP 400 sem este strip.
    agent_response = _strip_think_blocks(agent_response)

    # 7. PII scrub resposta (camada 3)
    response_scrubbed = scrub(agent_response).text

    # 8. Enviar resposta via Telegram API (NUNCA levanta - falhas viram log)
    response_sent = await _send_telegram_message(chat_id, response_scrubbed)

    # 9. Audit log (LGPD art. 37) - via db session seria ideal, aqui so log
    logger.info(
        "Telegram response processada chat_id=%s response_len=%d sent=%s",
        chat_id,
        len(response_scrubbed),
        response_sent,
    )

    # FIX 3 (turn 46): sempre retorna 200 mesmo se Telegram falhou.
    # Telegram vai retentar POST webhook se receber !=200 -> loop infinito.
    # response_sent=False indica que o user NAO recebeu a resposta.
    return {
        "status": "ok" if response_sent else "partial",
        "chat_id": chat_id,
        "response_sent": response_sent,
    }


async def _call_openclaw_agent(
    chat_id: int,
    text_scrubbed: str,
    db: Session | None = None,
) -> str:
    """Chama OpenClaw Agent (LLM) com contexto de conversa via Fallback.

    Usa o provider primario (opencode_go / deepseek-v4-flash) configurado
    em settings, com LGPD compliance (PII scrub, audit log, consent gate).

    Args:
        chat_id: ID do chat Telegram
        text_scrubbed: texto do usuario apos PII scrub (camada 1)

    Returns:
        Resposta do agent (string, ja scrubbed camada 3)
    """
    system_prompt = (
        "Voce eh o CartorioBot, assistente virtual oficial do "
        "Cartorio 2 Oficio de Notas de Uberlandia/MG.\n\n"
        "REGRAS:\n"
        "- Responda de forma direta, curta e profissional.\n"
        "- NUNCA invente prazos, valores ou informacoes juridicas.\n"
        "- Para emolumentos, protocolos ou agendamentos, oriente o "
        "cliente a acessar o sistema.\n"
        "- Se nao souber responder, escale para atendente humano.\n"
        "- Nao use emojis.\n"
        "- Seja rapido e objetivo.\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text_scrubbed},
    ]

    try:
        resp = await chat_with_fallback(
            messages=messages,
            consent_granted=True,
            actor_id=f"telegram:{chat_id}",
            session_id=f"tg:{chat_id}",
            db=db,
        )
        return resp.content
    except Exception as e:
        logger.exception("Fallback LLM chat falhou: %s", e)
        return "Desculpe, tive um problema tecnico. Tente novamente em alguns instantes."


async def _send_telegram_message(chat_id: int, text: str) -> bool:
    """Envia mensagem via Telegram Bot API.

    Args:
        chat_id: ID do chat Telegram
        text: texto a enviar (ja passou por PII scrub)

    Returns:
        True se Telegram retornou 200 (em HTML ou plain fallback), False caso contrario.
        NUNCA levanta exception — caller decide o que fazer (turn 46).
    """
    # Sanitiza texto: remove tags nao suportadas pelo Telegram (think, etc)
    safe_text = _sanitize_telegram_html(text)
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": safe_text,
                    "parse_mode": "HTML",
                },
            )
            if resp.status_code == 200:
                return True
            # LGPD/UX: log error mas NAO raise HTTPException.
            # Telegram send failures (chat not found, etc) nao devem
            # causar 502 (Telegram faria retry infinito).
            logger.error(
                "Telegram API error: %d %s",
                resp.status_code,
                resp.text,
            )
            # Fallback: tentar sem parse_mode (texto plain)
            try:
                resp2 = await client.post(
                    url,
                    json={"chat_id": chat_id, "text": safe_text},
                )
                if resp2.status_code == 200:
                    return True
                logger.error("Telegram fallback plain: %d %s", resp2.status_code, resp2.text)
                return False
            except Exception as e2:
                logger.exception("Telegram fallback falhou: %s", e2)
                return False
        except Exception as e:
            logger.exception("Telegram send falhou: %s", e)
            return False


def _sanitize_telegram_html(text: str) -> str:
    """Remove tags/blocos nao suportadas pelo Telegram HTML parser.

    Telegram so aceita: <b>, <i>, <u>, <s>, <strike>, <del>, <a href>, <code>, <pre>.
    Tags como <think>, <reasoning>, <function_calls> quebram parse_mode=HTML com
    'Unsupported start tag'. Aqui stripamos BLOCOS INTEIROS (turn 46 fix).

    Problema turn 45: MiniMax-M3 retorna "<think>...</think>\n\nresposta" — strip
    so das tags deixa " ... \n\nresposta" que parsea OK mas mostra lixo para o user.
    Fix: strip BLOCO INTEIRO (conteudo + tags), nao so tags.
    """
    import re
    # 1) Strip blocos inteiros de thinking/reasoning (turn 46 fix)
    text = re.sub(
        r"<\s*(think|reasoning|analysis|reflection|thought)\b[^>]*>.*?<\s*/\s*\1\s*>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # 2) Strip tags orfas (caso a LLM produza tag aberta sem fechamento)
    text = re.sub(
        r"<\s*/?\s*(think|reasoning|analysis|reflection|thought)\b[^>]*>",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # 3) Limpa whitespace residual
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


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
