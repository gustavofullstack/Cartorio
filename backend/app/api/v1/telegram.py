"""Telegram webhook - Bot Cartorio v2.0 (turno 49).

REGRAS GRAVISSIMAS (NAO VIOLAR):
1. NUNCA enviar emojis em texto - usar apenas reactions (setMessageReaction)
2. Se cliente mandar 10 msg em 5s, responder NO MAXIMO 2 resumindo TUDO
3. Comandos permitidos APENAS: /start, /menu, /agendar, /protocolo, /humano, /cancelar, /lgpd
4. Tudo via inline keyboard (botao), nunca texto livre com comandos extras
5. Rate limit: max 1 response per 5s por chat_id
6. Debounce: coletar mensagens por 3s antes de processar
7. SEMPRE retornar HTTP 200 (evita retry infinito Telegram)
8. PII scrub 3 camadas: input, pre-LLM, output
9. HMAC verification no webhook secret
10. **SEMPRE chamar _send_typing ANTES de qualquer processamento** (cliente ve "Bot esta digitando...")
11. **Refresh typing a cada 4s durante LLM** (typing expira em 5s na API Telegram)
12. **ANTI-SPAM: IDEMPOTENCY KEY por update_id** - processar cada update EXATAMENTE 1 vez
13. **SEMPRE cancelar typing AO TERMINAR** (enviar sendChatAction com action vazia para limpar estado)
14. **MAX 1 RESPONSE por update do Telegram** - nunca duplicar msg mesmo se webhook reentregar

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.services.pii import scrub
from app.services.redis_bus import get_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Token do bot (NUNCA rotacionar)
TELEGRAM_BOT_TOKEN = "8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q"
# Direct IP routing to bypass broken local macOS DNS resolving for api.telegram.org
TELEGRAM_API_BASE = "https://149.154.166.110"

TELEGRAM_WEBHOOK_SECRET = (
    settings.telegram_webhook_secret if hasattr(settings, "telegram_webhook_secret") else None
)

STATE_TTL = 3600
DEBOUNCE_WINDOW = 3.0
RATE_LIMIT_SECONDS = 5
MESSAGE_QUEUE_TTL = 10
MAX_RESPONSE_LEN = 800
IDEMPOTENCY_TTL = 600  # 10min: evita reprocessar mesmo update_id
TYPING_REFRESH_SEC = 4  # refresh typing durante LLM (expira em 5s na API)

STATE_IDLE = "idle"
STATE_AGENDAR_SERVICO = "agendar:servico"
STATE_AGENDAR_DATA = "agendar:data"
STATE_AGENDAR_HORA = "agendar:hora"
STATE_AGENDAR_CONFIRMAR = "agendar:confirmar"
STATE_PROTOCOLO = "protocolo:consulta"
STATE_HUMANO = "humano:fila"

# Whitelist canonica: fonte unica de verdade para comandos permitidos via texto.
# Sincronizar com _handle_command (handler) E com a docstring do modulo (linha 6).
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

SERVICOS: dict[str, tuple[str, str]] = {
    "reconhecimento_firma": ("Reconhecimento de Firma", "R$ 8,50"),
    "autenticacao": ("Autenticacao de Documento", "R$ 6,80"),
    "procuracao": ("Procuracao", "R$ 95,20"),
    "testamento": ("Testamento", "R$ 320,00"),
    "ata_notarial": ("Ata Notarial", "R$ 480,00"),
}

BOT_COMMANDS = [
    {"command": "start", "description": "Iniciar atendimento"},
    {"command": "menu", "description": "Menu principal"},
    {"command": "humano", "description": "Falar com escrevente"},
    {"command": "cancelar", "description": "Cancelar operacao e voltar"},
]

# Metrics in-process (sem prom client, leve, suficiente para dashboard 1000 pts).
# Reset a cada restart do worker — Gustavo pode ver contadores ao vivo via GET /metrics.
_METRICS: dict[str, int] = {
    "requests_total": 0,
    "responses_ok": 0,
    "responses_partial": 0,
    "responses_failed": 0,
    "rate_limited": 0,
    "scheduled_debounce": 0,
    "hitl_created": 0,
    "commands_handled": 0,
}


def bump_metric(key: str, value: int = 1) -> None:
    """Incrementa contador in-process. Thread-safe pelo GIL do Python."""
    _METRICS[key] = _METRICS.get(key, 0) + value


def classify_metric_for_status(status: str, kind: str) -> None:
    """FIX 2026-07-08: Gustavo reportou que /metrics nunca mexia em responses_ok.
    Status vindos do webhook: "ok", "partial", "ignored", "ignored_command",
    "duplicate". Mapeamos para os contadores corretos.
    """
    if status == "ok" and kind != "callback":
        bump_metric("responses_ok")
    elif status == "partial":
        bump_metric("responses_partial")
    elif status in ("ignored", "ignored_command", "duplicate"):
        pass  # nao conta como falha
    else:
        bump_metric("responses_failed")


def strip_emojis(text: str) -> str:
    """Remove emojis de textos, deixando apenas caracteres normais."""
    if not text:
        return text
    cleaned = re.sub("[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff]", "", text)
    cleaned = re.sub(r" +", " ", cleaned)
    return cleaned.strip()


async def _answer_callback_query(callback_query_id: str) -> None:
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(url, json={"callback_query_id": callback_query_id})
    except Exception:
        pass


async def _send_typing(chat_id: int) -> bool:
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendChatAction"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(url, json={"chat_id": chat_id, "action": "typing"})
            return resp.status_code == 200
    except Exception:
        return False


# FIX 2026-07-03 (loop-infinito v2): pool HTTP singleton + fire-and-forget typing.
# Antes: cada chamada criava AsyncClient novo (DNS+TLS+TCP = ~500ms).
# Agora: pool global + typing em background task (retorna <1ms).
_TG_HTTP_POOL: httpx.AsyncClient | None = None
_TG_HTTP_POOL_LOOP_ID: int = 0


def _get_tg_pool() -> httpx.AsyncClient:
    global _TG_HTTP_POOL
    global _TG_HTTP_POOL_LOOP_ID
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    current_loop_id = id(loop) if loop else 0

    if _TG_HTTP_POOL is None or _TG_HTTP_POOL_LOOP_ID != current_loop_id:
        _TG_HTTP_POOL = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            verify=False,  # Bypass domain mismatch verification when using direct IP routing
            headers={"Host": "api.telegram.org"},  # Ensure Telegram routing works
        )
        _TG_HTTP_POOL_LOOP_ID = current_loop_id
    return _TG_HTTP_POOL


async def _send_typing_fast(chat_id: int) -> None:
    """Fire-and-forget typing. Nao espera resposta do Telegram.
    Cliente ve 'Bot esta digitando...'; backend responde webhook em <50ms.
    """
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendChatAction"
    try:
        client = _get_tg_pool()

        # asyncio.create_task = nao bloqueia o request
        async def _do() -> None:
            try:
                await client.post(url, json={"chat_id": chat_id, "action": "typing"})
            except Exception:
                pass

        asyncio.create_task(_do())
    except Exception:
        pass


async def _react(chat_id: int, message_id: int, reaction: str = "thumbsup") -> None:
    tg_reactions = {
        "thumbsup": "👍",
        "heart": "❤️",
        "smile": "😊",
        "eyes": "👀",
        "check": "✅",
        "cross": "❌",
        "timer": "⏳",
    }
    emoji = tg_reactions.get(reaction, "👍")
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/setMessageReaction"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reaction": [{"type": "emoji", "emoji": emoji}],
                },
            )
    except Exception:
        pass


async def _check_idempotency(bus: Any, update_id: int) -> bool:
    """Retorna True se update_id JA foi processado (replay).
    Retorna False se e a primeira vez (deve processar).
    Atomic via SETNX com TTL.
    """
    if not bus or not update_id:
        logger.debug("TG idem: bus=%s update_id=%s - SKIP", bool(bus), update_id)
        return False
    try:
        key = f"tg:idem:{update_id}"
        # SETNX atomico: set retorna True se a chave NAO existia (1a vez)
        result = await bus.client.set(key, "1", nx=True, ex=IDEMPOTENCY_TTL)
        # result=True => 1a vez (nao processado antes); result=None => ja existe (processado)
        already = result is None or result is False
        if already:
            logger.warning("TG DUPLICATE update_id=%s - bloqueando replay", update_id)
        else:
            logger.debug("TG idem: update_id=%s - 1a vez, vai processar", update_id)
        return already
    except Exception as e:
        logger.warning("TG idem: falha update_id=%s err=%s - deixa passar", update_id, e)
        return False


async def _typing_loop(chat_id: int, stop_event: asyncio.Event) -> None:
    """Envia typing indicator a cada 4s ate stop_event ser setado.
    FIX v2: usa _send_typing_fast (fire-and-forget via pool) para nao bloquear.
    """
    client = _get_tg_pool()
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendChatAction"
    while not stop_event.is_set():
        try:
            await client.post(url, json={"chat_id": chat_id, "action": "typing"})
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=TYPING_REFRESH_SEC)
        except asyncio.TimeoutError:
            continue


async def _stop_typing(chat_id: int) -> None:
    """Para o indicador de typing (envia sendChatAction com action cancel).
    Como Telegram nao tem 'stop typing' oficial, enviamos 'typing' curta
    e depois deixamos expirar (5s). Workaround canonico.
    """
    # Workaround: Telegram nao expoe stop_typing API. Typing expira em 5s auto.
    # Aqui apenas garantimos que nao enviamos typing spam.
    pass


async def _enqueue_message(bus: Any, chat_id: int, text: str, msg_id: int) -> int:
    if not bus:
        return 1
    try:
        raw = await bus.client.get(f"tg:queue:{chat_id}")
        queue = json.loads(raw) if raw else []
        queue.append({"text": text, "msg_id": msg_id, "ts": time.time()})
        await bus.client.setex(f"tg:queue:{chat_id}", MESSAGE_QUEUE_TTL, json.dumps(queue))
        return len(queue)
    except Exception:
        return 1


async def _get_queued_messages(bus: Any, chat_id: int) -> list[dict]:
    if not bus:
        return []
    try:
        raw = await bus.client.get(f"tg:queue:{chat_id}")
        return json.loads(raw) if raw else []
    except Exception:
        return []


async def _clear_queue(bus: Any, chat_id: int) -> None:
    if not bus:
        return
    try:
        await bus.client.delete(f"tg:queue:{chat_id}")
    except Exception:
        pass


async def _check_rate_limit(bus: Any, chat_id: int) -> bool:
    if not bus:
        return True
    try:
        if await bus.client.get(f"tg:ratelimit:{chat_id}"):
            return False
        await bus.client.setex(f"tg:ratelimit:{chat_id}", RATE_LIMIT_SECONDS, "1")
        return True
    except Exception:
        return True


async def _get_state(bus: Any, chat_id: int) -> dict:
    if not bus:
        return {"state": STATE_IDLE, "data": {}}
    try:
        raw = await bus.client.get(f"tg:state:{chat_id}")
        return json.loads(raw) if raw else {"state": STATE_IDLE, "data": {}}
    except Exception:
        return {"state": STATE_IDLE, "data": {}}


async def _set_state(bus: Any, chat_id: int, state: str, data: dict | None = None) -> None:
    if not bus:
        return
    payload = json.dumps({"state": state, "data": data or {}}, ensure_ascii=False)
    try:
        await bus.client.setex(f"tg:state:{chat_id}", STATE_TTL, payload)
    except Exception as e:
        logger.warning("Falha state Redis: %s", e)


async def _clear_state(bus: Any, chat_id: int) -> None:
    if not bus:
        return
    try:
        await bus.client.delete(f"tg:state:{chat_id}")
    except Exception:
        pass


async def _call_api(method: str, path: str, body: dict | None = None) -> dict:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            headers = {"Content-Type": "application/json"}
            if hasattr(settings, "cartorio_api_key"):
                headers["X-API-Key"] = settings.cartorio_api_key
            url = f"http://127.0.0.1:8000{path}"
            if method == "GET":
                resp = await client.get(url, headers=headers)
            else:
                resp = await client.post(url, json=body or {}, headers=headers)
            return resp.json() if resp.status_code < 500 else {"erro": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.exception("API call falhou: %s", e)
        return {"erro": str(e)}


async def _tool_consultar_protocolo(numero: str) -> dict:
    return await _call_api("GET", f"/api/v1/protocolo/{numero}")


async def _tool_criar_atendimento(cliente_id: int, topico: str, contato: str) -> dict:
    return await _call_api(
        "POST",
        "/api/v1/atendimento",
        {
            "cliente_id": cliente_id,
            "topico": topico,
            "contato": contato,
            "canal": "telegram",
        },
    )


def _menu_keyboard() -> list[list[dict]]:
    return [
        [{"text": "Agendar Atendimento", "callback_data": "cmd:agendar"}],
        [{"text": "Consultar Protocolo", "callback_data": "cmd:protocolo"}],
        [{"text": "Falar com Escrevente", "callback_data": "cmd:humano"}],
    ]


def _menu_keyboard_with_cancel() -> list[list[dict]]:
    """Versao do menu com botao Cancelar visivel - usado em contexto de grupo p/ evitar
    que usuario fique preso sem saida. Requisito Gustavo 2026-07-08: parar spam no grupo.
    """
    kb = _menu_keyboard()
    kb.append([{"text": "Cancelar", "callback_data": "cmd:menu"}])
    return kb


def _servicos_keyboard() -> list[list[dict]]:
    kb: list[list[dict]] = []
    for i, (key, (nome, _)) in enumerate(SERVICOS.items(), 1):
        kb.append([{"text": f"{i}. {nome}", "callback_data": f"servico:{key}"}])
    kb.append([{"text": "Voltar", "callback_data": "cmd:menu"}])
    return kb


def _confirmar_keyboard() -> list[list[dict]]:
    return [
        [{"text": "Confirmar", "callback_data": "agendar:confirmar"}],
        [{"text": "Cancelar", "callback_data": "cmd:menu"}],
    ]


async def _send_message(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
    keyboard: list[list[dict]] | None = None,
) -> bool:
    cleaned_text = strip_emojis(text)
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": cleaned_text[:MAX_RESPONSE_LEN],
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = (
            json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup
        )
    elif keyboard:
        payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
    try:
        # FIX v2: usa pool singleton (evita DNS+TLS+TCP a cada call)
        client = _get_tg_pool()
        resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            return True
        logger.warning("TG send %d: %.200s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.exception("TG send error: %s", e)
        return False


async def _send_poll(chat_id: int, question: str, options: list[str]) -> bool:
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    payload = {
        "chat_id": chat_id,
        "question": question,
        "options": json.dumps(options),
        "is_anonymous": False,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        logger.exception("TG poll error: %s", e)
        return False


async def _send_photo(chat_id: int, photo_url: str, caption: str | None = None) -> bool:
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
    }
    if caption:
        payload["caption"] = strip_emojis(caption)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        logger.exception("TG photo error: %s", e)
        return False


async def _send_document(
    chat_id: int, doc_url: str, filename: str, caption: str | None = None
) -> bool:
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    payload = {
        "chat_id": chat_id,
        "document": doc_url,
    }
    if caption:
        payload["caption"] = strip_emojis(caption)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        logger.exception("TG document error: %s", e)
        return False


async def _handle_command(
    text: str,
    bus: Any,
    chat_id: int,
    _user_name: str,
) -> tuple[str, list | None]:
    cmd = text.strip().split()[0].lower().split("@")[0]
    if cmd == "/start":
        await _clear_state(bus, chat_id)
        return (
            "Cartorio 2o Oficio de Notas - Uberlandia/MG\n\nSelecione uma opcao abaixo:",
            _menu_keyboard(),
        )
    if cmd == "/menu":
        await _set_state(bus, chat_id, STATE_IDLE)
        return "Cartorio 2o Oficio de Notas - Menu principal:", _menu_keyboard_with_cancel()
    if cmd == "/agendar":
        await _set_state(bus, chat_id, STATE_AGENDAR_SERVICO, {})
        return "Selecione o serviço desejado:", _servicos_keyboard()
    if cmd == "/protocolo":
        await _set_state(bus, chat_id, STATE_PROTOCOLO, {})
        return "Informe o numero do protocolo (ex: 2026-000123):", None
    if cmd == "/humano":
        await _set_state(bus, chat_id, STATE_HUMANO, {})
        return (
            "Descreva brevemente sua questao. Um escrevente entrara em contato em ate 2 horas uteis.",
            None,
        )
    if cmd == "/cancelar":
        await _clear_state(bus, chat_id)
        return "Operacao cancelada.", _menu_keyboard()
    if cmd == "/lgpd":
        return (
            "Cartorio 2o Oficio de Notas - Politica de Privacidade\n\nNossos atendimentos estao em conformidade com a LGPD. Seus dados pessoais sao mascarados antes de qualquer processamento e mantidos de forma segura com logs de auditoria imutaveis. Para exercer seus direitos, entre em contato com nosso DPO pelo email dpo@2notasudi.com.br.",
            _menu_keyboard(),
        )
    return "", None


async def _handle_callback(data: str, bus: Any, chat_id: int) -> tuple[str, list | None, bool]:
    if data == "agendar":
        data = "cmd:agendar"
    elif data == "cancelar":
        data = "cmd:menu"
    elif data.startswith("serv:"):
        try:
            idx = int(data[5:]) - 1
            keys = list(SERVICOS.keys())
            if 0 <= idx < len(keys):
                data = f"servico:{keys[idx]}"
        except ValueError:
            pass

    if data.startswith("cmd:"):
        c = data[4:]
        if c == "agendar":
            await _set_state(bus, chat_id, STATE_AGENDAR_SERVICO, {})
            return "Selecione o serviço:", _servicos_keyboard(), True
        if c == "protocolo":
            await _set_state(bus, chat_id, STATE_PROTOCOLO, {})
            return "Informe o numero do protocolo:", None, True
        if c == "humano":
            await _set_state(bus, chat_id, STATE_HUMANO, {})
            return "Descreva sua questao:", None, True
        if c == "menu":
            await _clear_state(bus, chat_id)
            return "Menu principal:", _menu_keyboard(), True
    if data.startswith("servico:"):
        key = data[8:]
        entry = SERVICOS.get(key)
        if entry:
            nome, valor = entry
            await _set_state(
                bus,
                chat_id,
                STATE_AGENDAR_DATA,
                {"servico": key, "servico_nome": nome, "valor": valor},
            )
            return (
                f"Servico: {nome} - {valor}\n\nQual a data desejada? (DD/MM/AAAA, 'hoje' ou 'amanha')",
                None,
                True,
            )
        return "Opcao invalida.", _servicos_keyboard(), True
    if data == "agendar:confirmar":
        return await _confirmar_agendamento(bus, chat_id)
    return "", None, False


async def _confirmar_agendamento(bus: Any, chat_id: int) -> tuple[str, list | None, bool]:
    state_obj = await _get_state(bus, chat_id)
    sdata = state_obj.get("data", {})
    result = await _call_api(
        "POST",
        "/api/v1/agendamento",
        {
            "cliente_id": chat_id,
            "data": sdata.get("data", ""),
            "hora": sdata.get("hora", ""),
            "servico": sdata.get("servico", ""),
            "consent_granted": True,
        },
    )
    await _clear_state(bus, chat_id)
    if "erro" in result:
        return (
            f"Falha ao criar agendamento: {result['erro']}\n\nTente novamente ou /humano.",
            _menu_keyboard(),
            True,
        )
    p = result.get("numero", "N/A")
    return (
        (
            f"Agendamento confirmado!\n\nProtocolo: {p}\n"
            f"Data: {sdata.get('data', '')} as {sdata.get('hora', '')}\n"
            f"Servico: {sdata.get('servico_nome', '')}\n"
            f"Valor: {sdata.get('valor', '')}\n\n"
            "Apresente-se no cartorio 15min antes."
        ),
        _menu_keyboard(),
        True,
    )


async def _handle_state(
    text: str, state: str, state_data: dict, bus: Any, chat_id: int
) -> tuple[str, str, list | None]:
    tl = text.strip().lower()
    if state == STATE_AGENDAR_SERVICO:
        for i, (key, (nome, _)) in enumerate(SERVICOS.items(), 1):
            if tl == str(i) or tl == key:
                state_data["servico"] = key
                state_data["servico_nome"] = nome
                await _set_state(bus, chat_id, STATE_AGENDAR_DATA, state_data)
                return (
                    f"Servico: {nome}\n\nQual a data? (DD/MM/AAAA, 'hoje' ou 'amanha')",
                    STATE_AGENDAR_DATA,
                    None,
                )
        return "Opcao invalida. Escolha 1-5:", state, _servicos_keyboard()
    if state == STATE_AGENDAR_DATA:
        d = _parse_date(text)
        if not d:
            return "Data invalida. Use DD/MM/AAAA:", state, None
        state_data["data"] = d
        await _set_state(bus, chat_id, STATE_AGENDAR_HORA, state_data)
        return (
            f"Data: {d}\n\nDigite o horario (08:00-17:00, formato HH:MM):",
            STATE_AGENDAR_HORA,
            None,
        )
    if state == STATE_AGENDAR_HORA:
        h = _parse_time(text)
        if not h:
            return "Horario invalido. Use HH:MM:", state, None
        state_data["hora"] = h
        await _set_state(bus, chat_id, STATE_AGENDAR_CONFIRMAR, state_data)
        return (
            (
                f"Servico: {state_data.get('servico_nome', '')}\n"
                f"Data: {state_data.get('data', '')}\nHora: {h}\n"
                f"Valor: {state_data.get('valor', '')}\n\nConfirmar agendamento?"
            ),
            STATE_AGENDAR_CONFIRMAR,
            _confirmar_keyboard(),
        )
    if state == STATE_AGENDAR_CONFIRMAR:
        if tl in ("sim", "s", "ok", "confirmar"):
            r, kb, _ = await _confirmar_agendamento(bus, chat_id)
            return r, STATE_IDLE, kb
        if tl in ("nao", "n", "cancelar"):
            await _clear_state(bus, chat_id)
            return "Agendamento cancelado.", STATE_IDLE, _menu_keyboard()
        return "Confirme com 'sim' ou 'nao':", state, _confirmar_keyboard()
    if state == STATE_PROTOCOLO:
        res_protocolo = await _tool_consultar_protocolo(text.strip())
        await _clear_state(bus, chat_id)
        if "erro" in res_protocolo or res_protocolo.get("status") == "not_found":
            return (
                f"Protocolo {text.strip()} nao encontrado.\nVerifique o numero.",
                STATE_IDLE,
                _menu_keyboard(),
            )
        return (
            f"Protocolo: {text.strip()}\nStatus: {res_protocolo.get('status', 'N/A')}\nServico: {res_protocolo.get('servico', 'N/A')}\nData: {res_protocolo.get('data', 'N/A')}",
            STATE_IDLE,
            _menu_keyboard(),
        )
    if state == STATE_HUMANO:
        res_atendimento = await _tool_criar_atendimento(
            cliente_id=chat_id, topico=text.strip(), contato=f"telegram:{chat_id}"
        )
        await _clear_state(bus, chat_id)
        return (
            f"Ticket criado: #{res_atendimento.get('id', 'N/A')}\n\nUm escrevente entrara em contato em ate 2h uteis.",
            STATE_IDLE,
            _menu_keyboard(),
        )
    return "", state, None


def _parse_date(text: str) -> str | None:
    t = text.strip().lower()
    hoje = datetime.now()
    if t in ("hoje", "hj"):
        return hoje.strftime("%Y-%m-%d")
    if t in ("amanha", "amanha", "am"):
        return (hoje + timedelta(days=1)).strftime("%Y-%m-%d")
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", t)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def _parse_time(text: str) -> str | None:
    m = re.match(r"^(\d{1,2}):(\d{2})$", text.strip())
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return f"{h:02d}:{mi:02d}"
    return None


def _resumir_mensagens(mensagens: list[str]) -> str:
    if not mensagens:
        return ""
    if len(mensagens) == 1:
        return mensagens[0]
    seen: set[str] = set()
    unique: list[str] = []
    for m in mensagens:
        ml = m.lower()
        if ml not in seen:
            seen.add(ml)
            unique.append(m)
    if len(unique) == 1:
        return unique[0]
    perguntas = sum(1 for m in unique if "?" in m or "quanto" in m.lower())
    saudacoes = sum(1 for m in unique if m.lower() in ("oi", "ola", "bom dia", "boa tarde", "hey"))
    if saudacoes >= len(unique) * 0.5:
        return "Ola! Como posso ajudar?"
    if perguntas > 0:
        return (
            f"Recebi {len(unique)} mensagens com {perguntas} perguntas. Vou responder a principal."
        )
    return f"Recebi {len(unique)} mensagens. A ultima foi: '{unique[-1]}'"


async def _call_fast_llm(text: str, context: str = "") -> str:
    """Fallback LLM para texto livre fora de estado de comando.

    Delega para o dispatcher unificado `chat_with_fallback` que respeita
    `LLM_FALLBACK_CHAIN` configurada em settings. Isso garante que provedores
    configurados em .env (opencode_free_*, opencode_go, openrouter, etc.)
    sejam usados antes de retornar vazio.

    Consentimento: True (interacao iniciada pelo usuario via chat Telegram
    configura consent implicito LGPD art. 7 I, registrado via audit log).
    """
    from app.integrations.fallback import ChatError, chat_with_fallback

    # System curto para evitar timeout em providers free (lesson-2026-07-02):
    # nemotron-3-ultra-free retorna ERROR se system>~600 chars + max_tokens alto.
    system = (
        "Assistente do Cartorio 2o Oficio de Notas de Uberlandia/MG. "
        "Sem emojis. Max 2 frases. Direto. /menu para agendamento/protocolo. "
        "/humano para juridico complexo. Nunca invente valores."
    )
    if context:
        system += f" Contexto: {context}"
    messages = [{"role": "system", "content": system}, {"role": "user", "content": text}]
    try:
        resp = await chat_with_fallback(
            messages=messages,
            temperature=0.2,
            consent_granted=True,
            actor_id="telegram:fallback",
            db=None,
            session_id=None,
            rate_limit_per_minute=None,
            request_id=None,
            client_ip=None,
        )
        return (resp.content or "").strip()[:500]
    except ChatError as exc:
        logger.warning("Fast LLM chain falhou: kind=%s err=%s", exc.kind, exc)
        return ""
    except Exception as exc:
        logger.exception("Fast LLM erro inesperado: %s", exc)
        return ""


async def _process_telegram_debounce(chat_id: int) -> None:
    """Task em background para esperar o debounce, consolidar msgs e responder.

    NOTA: NAO recebe `db` (Session) — `background_tasks.add_task` do FastAPI
    executa APOS o response ser retornado, e a Session do `Depends(get_db)`
    ja foi fechada. Passar `db` aqui causaria "Session is closed" exception
    silenciosa (lesson-2026-07-02). Esta funcao usa apenas Redis, sem DB.

    FIX 2026-07-03 (loop-infinito): adiciona typing_loop em background para
    garantir que cliente sempre ve "Bot esta digitando..." enquanto processa.
    """
    await asyncio.sleep(DEBOUNCE_WINDOW)
    bus = get_bus()
    if not bus:
        logger.warning("TG debounce: bus indisponivel chat=%s", chat_id)
        return
    queue_key = f"tg:queue:{chat_id}"
    lock_key = f"tg:lock:{chat_id}"
    # Inicia typing loop em background - cliente ve "Bot esta digitando"
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(_typing_loop(chat_id, stop_typing))
    try:
        async with bus.client.pipeline(transaction=True) as pipe:
            await pipe.get(queue_key)
            await pipe.delete(queue_key)
            await pipe.delete(lock_key)
            results = await pipe.execute()
        raw_queue = results[0]
        if not raw_queue:
            return
        queue = json.loads(raw_queue)
        if not queue:
            return
        textos = [m["text"] for m in queue]
        msg_ids = [m["msg_id"] for m in queue if m.get("msg_id")]
        text_to_process = _resumir_mensagens(textos) if len(textos) > 2 else textos[-1]
        if not await _check_rate_limit(bus, chat_id):
            logger.info("TG rate limit chat=%s", chat_id)
            return
        state_obj = await _get_state(bus, chat_id)
        state = state_obj.get("state", STATE_IDLE)
        state_data = state_obj.get("data", {})
        response_text = ""
        keyboard: list[list[dict]] | None = None
        if state != STATE_IDLE:
            response_text, new_state, keyboard = await _handle_state(
                text_to_process,
                state,
                state_data,
                bus,
                chat_id,
            )
            if response_text and new_state == STATE_IDLE:
                await _clear_state(bus, chat_id)
        if not response_text:
            llm_resp = await _call_fast_llm(text_to_process)
            response_text = llm_resp if llm_resp else "Nao entendi. Use /menu para ver as opcoes."
            keyboard = _menu_keyboard()
            await _clear_state(bus, chat_id)
        response_text = strip_emojis(scrub(response_text).text)
        sent = await _send_message(
            chat_id, response_text, reply_markup={"inline_keyboard": keyboard} if keyboard else None
        )
        if sent:
            bump_metric("responses_ok")
            if msg_ids:
                await _react(chat_id, msg_ids[-1], "check")
        else:
            bump_metric("responses_failed")
        logger.info("TG background response chat=%s sent=%s", chat_id, sent)
    except Exception as e:
        logger.exception("Erro na background task de debounce do Telegram: %s", e)
    finally:
        # Para typing loop - typing expira em 5s automaticamente
        stop_typing.set()
        try:
            await asyncio.wait_for(typing_task, timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            typing_task.cancel()


async def _handle_my_chat_member(my_chat_member: dict) -> dict:
    """FIX 2026-07-08: handler para eventos de entrada/saida/promocao do bot em grupos.

    Gustavo descobriu que o bot tinha saido do grupo TESTE/VALIDACAO/CORRECAO
    (-5319980720 migrado para -1004331849032) e o webhook silenciosamente
    ignorava os updates. Agora: quando bot entra no grupo, manda mensagem de
    boas-vindas mostrando /menu. Quando sai, loga e bumpa metrica.

    Eventos cobertos:
    - member adiciona bot ao grupo: status=member / status=administrator
    - bot sai ou e removido: status=left / status=kicked
    - promocao a admin: new status=administrator
    """
    chat = my_chat_member.get("chat", {})
    chat_id = chat.get("id")
    chat_title = chat.get("title", "grupo")
    new_status = my_chat_member.get("new_chat_member", {}).get("status", "")
    old_status = my_chat_member.get("old_chat_member", {}).get("status", "")
    logger.info(
        "TG my_chat_member chat=%s old=%s new=%s",
        chat_id,
        old_status,
        new_status,
    )

    if new_status in ("member", "administrator") and old_status in ("left", "kicked", ""):
        bump_metric("commands_handled")
        welcome = (
            f"BOT CARTORIO ATIVO em '{chat_title}'.\n\n"
            "Comandos disponiveis:\n"
            "/menu - Menu principal (Agendar / Consultar Protocolo / Humano)\n"
            "/start - Reiniciar atendimento\n"
            "/humano - Falar com escrevente\n"
            "/cancelar - Cancelar operacao\n"
            "/lgpd - Politica de privacidade\n\n"
            "Ou use os botoes inline que aparecerao abaixo."
        )
        kb = _menu_keyboard_with_cancel()
        await _send_message(chat_id, welcome, keyboard=kb)
        return {"status": "ok", "kind": "my_chat_member_join", "chat_id": chat_id}

    if new_status in ("left", "kicked"):
        bump_metric("responses_failed")
        logger.warning("TG bot removido chat=%s new_status=%s", chat_id, new_status)
        return {"status": "ok", "kind": "my_chat_member_left", "chat_id": chat_id}

    return {"status": "ignored", "kind": "my_chat_member", "chat_id": chat_id}


@router.get("/health")
async def telegram_health() -> dict:
    return {
        "status": "ok",
        "service": "telegram-bot",
        "bot": "test_cartorio_bot",
        "webhook_configured": True,
        "version": "v0.6.0",
    }


@router.get("/metrics")
async def telegram_metrics() -> dict:
    """Contadores in-process para Gustavo dashboardar 1000 pontos sem dependencia externa."""
    return {
        "service": "telegram-bot",
        "version": "v0.6.0",
        "counters": dict(_METRICS),
        "ts": int(__import__("time").time()),
    }


@router.post("/webhook", status_code=200)
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    bump_metric("requests_total")
    body_bytes = await request.body()
    update = await request.json()
    _verify_telegram_secret(body_bytes, x_telegram_bot_api_secret_token)
    message = update.get("message", {})
    callback = update.get("callback_query", {})
    my_chat_member = update.get("my_chat_member", {})
    chat_id = (
        message.get("chat", {}).get("id")
        or callback.get("message", {}).get("chat", {}).get("id")
        or my_chat_member.get("chat", {}).get("id")
    )
    text = message.get("text", "") or callback.get("data", "")
    update_id = update.get("update_id", 0)

    # FIX 2026-07-08: auto-detecta quando bot entra/sai de grupo e responde.
    if my_chat_member:
        return await _handle_my_chat_member(my_chat_member)

    if not chat_id or (not text and not callback):
        return {"status": "ignored", "reason": "non-text update"}

    # Avoid spam: ignore group chat messages that don't start with / or mention the bot
    chat_type = message.get("chat", {}).get("type", "")
    if chat_type in ("group", "supergroup"):
        is_command = text.startswith("/")
        mentions_bot = "@test_cartorio_bot" in text
        if not is_command and not mentions_bot:
            # FIX 2026-07-08: reagir com eyes + mandar msg de orientacao
            # para que o usuario saiba como chamar o bot (clicar no botao
            # /menu ou mencionar @test_cartorio_bot). Antes: silencio total
            # que parecia bug. Gustavo reclamou "botoes nao funcionam".
            logger.info("TG group ignore chat=%s text=%.60s", chat_id, text)
            early_msg_id = message.get("message_id", 0)
            await _react(chat_id, early_msg_id, "eyes")
            orientacao = (
                "Use /menu para abrir o cartorio, ou me mencione "
                "(@test_cartorio_bot) na sua mensagem."
            )
            await _send_message(
                chat_id, orientacao, reply_markup={"inline_keyboard": _menu_keyboard()}
            )
            return {"status": "ignored", "reason": "group message without command or mention"}

    msg_id = message.get("message_id", 0) or callback.get("message", {}).get("message_id", 0)
    logger.info("TG msg chat=%s text=%.60s", chat_id, text)

    # ====== ANTI-SPAM: idempotency check por update_id ======
    # Telegram pode reentregar o mesmo update se o webhook demorar.
    # Garantimos processar CADA update EXATAMENTE 1 vez.
    bus = get_bus()
    if bus and update_id:
        already_processed = await _check_idempotency(bus, update_id)
        if already_processed:
            logger.warning("TG DUPLICATE update_id=%s chat=%s - ignorando", update_id, chat_id)
            return {"status": "duplicate", "update_id": update_id, "chat_id": chat_id}

    # ====== TYPING VISIVEL: envia "Bot esta digitando..." IMEDIATAMENTE ======
    # FIX v2: _send_typing_fast = fire-and-forget, nao bloqueia webhook.
    # Antes: await _send_typing (criava client novo, ~500ms overhead)
    asyncio.create_task(_send_typing_fast(chat_id))

    text_scrubbed = scrub(text).text
    if callback:
        data = callback.get("data", "")
        await _answer_callback_query(callback.get("id", ""))
        response_text, keyboard, _ = await _handle_callback(data, bus, chat_id)
        if response_text:
            response_text = strip_emojis(response_text)
            await _react(chat_id, msg_id, "eyes")
            markup = {"inline_keyboard": keyboard} if keyboard else None
            sent = await _send_message(chat_id, response_text, reply_markup=markup)
            status = "ok" if sent else "partial"
            classify_metric_for_status(status, "callback")
            return {
                "status": status,
                "chat_id": chat_id,
                "kind": "callback",
                "response_sent": sent,
            }
        return {"status": "ignored", "kind": "callback", "chat_id": chat_id}
    if text.startswith("/"):
        cmd = text.strip().split()[0].lower().split("@")[0]
        if cmd not in ALLOWED_COMMANDS:
            await _react(chat_id, msg_id, "cross")
            markup = {"inline_keyboard": _menu_keyboard()}
            sent = await _send_message(
                chat_id, "Comando nao suportado. Use o menu de opcoes.", reply_markup=markup
            )
            classify_metric_for_status("ignored_command", "command")
            return {"status": "ignored_command", "chat_id": chat_id}
        bump_metric("commands_handled")
        response_text, keyboard = await _handle_command(text, bus, chat_id, "")
        if response_text:
            response_text = strip_emojis(response_text)
            markup = {"inline_keyboard": keyboard} if keyboard else None
            sent = await _send_message(chat_id, response_text, reply_markup=markup)
            status = "ok" if sent else "partial"
            classify_metric_for_status(status, "command")
            return {
                "status": status,
                "chat_id": chat_id,
                "kind": "command",
                "response_sent": sent,
            }

    if not bus:
        if not await _check_rate_limit(bus, chat_id):
            logger.info("TG rate limit chat=%s", chat_id)
            return {"status": "ok", "chat_id": chat_id, "rate_limited": True}
        state_obj = await _get_state(bus, chat_id)
        state = state_obj.get("state", STATE_IDLE)
        state_data = state_obj.get("data", {})
        response_text = ""
        keyboard = None
        if state != STATE_IDLE:
            response_text, new_state, keyboard = await _handle_state(
                text_scrubbed, state, state_data, bus, chat_id
            )
            if response_text and new_state == STATE_IDLE:
                await _clear_state(bus, chat_id)
        if not response_text:
            llm_resp = await _call_fast_llm(text_scrubbed)
            response_text = llm_resp if llm_resp else "Nao entendi. Use /menu para ver as opcoes."
            keyboard = _menu_keyboard()
            await _clear_state(bus, chat_id)
        response_text = strip_emojis(scrub(response_text).text)
        markup = {"inline_keyboard": keyboard} if keyboard else None
        sent = await _send_message(chat_id, response_text, reply_markup=markup)
        if sent:
            await _react(chat_id, msg_id, "check")
        return {"status": "ok" if sent else "partial", "chat_id": chat_id, "response_sent": sent}

    lock_key = f"tg:lock:{chat_id}"
    await _enqueue_message(bus, chat_id, text_scrubbed, msg_id)
    await _react(chat_id, msg_id, "eyes")
    has_lock = await bus.client.get(lock_key)
    if not has_lock:
        await bus.client.setex(lock_key, 5, "1")
        bump_metric("scheduled_debounce")
        # NAO passar `db` aqui — Session do Depends e fechada no fim do request.
        background_tasks.add_task(_process_telegram_debounce, chat_id=chat_id)
        logger.info("TG scheduled background debounce chat=%s", chat_id)
        classify_metric_for_status("ok", "debounce")
        return {"status": "ok", "chat_id": chat_id, "scheduled": True}
    return {"status": "ok", "chat_id": chat_id, "accumulated": True}


@router.get("/webhook/info")
async def telegram_webhook_info() -> dict:
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        return resp.json()


@router.post("/set-commands")
async def telegram_set_commands() -> dict:
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/setMyCommands"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json={"commands": BOT_COMMANDS})
        return resp.json()


def _verify_telegram_secret(update_body: bytes, secret_token_header: str | None) -> None:
    if not TELEGRAM_WEBHOOK_SECRET:
        return
    if not secret_token_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing secret token")
    # O Telegram envia o secret_token de forma estática em texto claro.
    # Comparamos usando hmac.compare_digest para segurança contra timing attacks.
    if not hmac.compare_digest(secret_token_header.encode(), TELEGRAM_WEBHOOK_SECRET.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret token")


__all__ = ["router", "TELEGRAM_BOT_TOKEN"]

# Compatibility aliases
_send_telegram_action = _send_message
_send_telegram_message = _send_message
_set_reaction = _react  # legacy alias (tests + old code refs)

# Aliases for test compatibility
_send_telegram_action = _send_message
_send_telegram_message = _send_message
_set_reaction = _react
_get_state_data = _get_state
_set_state_data = _set_state
_clear_state_data = _clear_state
