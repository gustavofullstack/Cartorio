"""Telegram webhook endpoint - AI Agentica EXECUTORA (turn 47).

Bot: @CartorioAssistantBot (test_cartorio_bot)
Token: 8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q

ARQUITETURA (refatoracao turn 47 - Gustavo pediu):
=================================================
1. COMANDOS NATIVOS (zero LLM, resposta <100ms):
   /start, /menu, /ajuda, /cancelar

2. STATE MACHINE no Redis (contexto stateful entre msgs):
   IDLE -> MENU -> AGENDAR -> COLETANDO_DADOS -> CONFIRMANDO -> DONE

3. TOOLS (MCP-style) que o bot pode chamar:
   - tool_agendar(cliente_id, data, hora, servico)
   - tool_consultar_protocolo(numero)
   - tool_calcular_emolumento(tipo, valor)
   - tool_listar_agendamentos(cliente_id)
   - tool_solicitar_portabilidade(cliente_id)
   - tool_criar_atendimento(cliente_id, topico)

4. LLM RAPIDO (Groq compound / Mistral devstral) - SEM thinking blocks
   Usado APENAS para: interpretacao de intent quando nao bate com comando/state.
   System prompt: contexto do cartorio (docs, emolumentos, LGPD)

5. FALLBACKS / RESPOSTA DIRETA (sem LLM):
   Saudacao, menu, help, confirmacao simples.

LGPD: mensagens sao PII (texto livre). 3 camadas de scrubbing obrigatorias.
Modified by Gustavo Almeida.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.services.pii import scrub
from app.services.redis_bus import get_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Token do bot (NUNCA rotacionar - Gustavo + ZCode unicos com acesso)
TELEGRAM_BOT_TOKEN = "8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q"
TELEGRAM_API_BASE = "https://api.telegram.org"

TELEGRAM_WEBHOOK_SECRET = (
    settings.telegram_webhook_secret if hasattr(settings, "telegram_webhook_secret") else None
)

# === STATE MACHINE ===
# Estados do bot por chat_id (Redis TTL 1h)
STATE_IDLE = "idle"
STATE_MENU = "menu"
STATE_AGENDAR_DATA = "agendar:data"
STATE_AGENDAR_HORA = "agendar:hora"
STATE_AGENDAR_SERVICO = "agendar:servico"
STATE_AGENDAR_CONFIRMAR = "agendar:confirmar"
STATE_PROTOCOLO = "protocolo:consulta"
STATE_EMOLUMENTO_TIPO = "emolumento:tipo"
STATE_EMOLUMENTO_VALOR = "emolumento:valor"
STATE_LGPD = "lgpd:direito"
STATE_HUMANO = "humano:fila"

# TTL do estado (1h)
STATE_TTL = 3600

# === MENUS (sem LLM) ===
MENU_PRINCIPAL = """<b>Cartório 2º Ofício de Notas - Uberlândia/MG</b>

Escolha uma opção:

/agendar - Marcar atendimento
/protocolo - Consultar protocolo
/documento - 2ª via e upload
/emolumento - Consultar valores
/lgpd - Direitos do titular
/humano - Falar com escrevente
/cancelar - Voltar ao início

Ou descreva sua dúvida em texto livre."""

MENU_AGENDAR = """<b>Agendar Atendimento</b>

Para qual serviço?
1. Reconhecimento de firma
2. Autenticação de documento
3. Procuração
4. Testamento
5. Ata notarial

Responda com o número (1-5) ou /cancelar para voltar."""

MENU_EMOLUMENTO = """<b>Consulta de Emolumentos (MG 2026)</b>

Selecione o tipo:
1. Reconhecimento de firma
2. Autenticação
3. Procuração
4. Testamento
5. Ata notarial

Responda com o número (1-5)."""

MENU_LGPD = """<b>Direitos LGPD (Lei 13.709/2018)</b>

1. Acesso aos meus dados
2. Correção de dados
3. Portabilidade (download)
4. Oposição (parar tratamento)
5. Anonimização (esquecimento)
6. Revogar consentimento

Responda com o número (1-6) ou /cancelar."""

# Mapa de servicos (para /agendar e /emolumento)
SERVICOS = {
    "1": ("reconhecimento_firma", "Reconhecimento de Firma", "R$ 8,50"),
    "2": ("autenticacao", "Autenticação de Documento", "R$ 6,80"),
    "3": ("procuracao", "Procuração", "R$ 95,20"),
    "4": ("testamento", "Testamento", "R$ 320,00"),
    "5": ("ata_notarial", "Ata Notarial", "R$ 480,00"),
}

# === DECORATOR DE VERIFICACAO HMAC ===


def _verify_telegram_secret(
    update_body: bytes,
    secret_token_header: str | None,
) -> None:
    if not TELEGRAM_WEBHOOK_SECRET:
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


# === STATE MANAGER (Redis) ===


async def _get_state(bus: Any, chat_id: int) -> dict[str, Any]:
    """Recupera estado do chat no Redis."""
    if not bus:
        return {"state": STATE_IDLE, "data": {}}
    try:
        raw = await bus.client.get(f"tg:state:{chat_id}")
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return {"state": STATE_IDLE, "data": {}}


async def _set_state(bus: Any, chat_id: int, state: str, data: dict | None = None) -> None:
    """Salva estado no Redis com TTL."""
    if not bus:
        return
    payload = json.dumps({"state": state, "data": data or {}}, ensure_ascii=False)
    try:
        await bus.client.setex(f"tg:state:{chat_id}", STATE_TTL, payload)
    except Exception as e:
        logger.warning("Falha ao salvar state no Redis: %s", e)


async def _clear_state(bus: Any, chat_id: int) -> None:
    if not bus:
        return
    try:
        await bus.client.delete(f"tg:state:{chat_id}")
    except Exception:
        pass


# === TOOLS (MCP-STYLE) - Executam acoes reais via API interna ===


async def _tool_agendar(cliente_id: int, data: str, hora: str, servico: str) -> dict:
    """Cria agendamento via API interna."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "http://cartorio_api:8000/api/v1/agendamento",
                json={
                    "cliente_id": cliente_id,
                    "data": data,
                    "hora": hora,
                    "servico": servico,
                    "consent_granted": True,
                },
                headers={"X-API-Key": settings.cartorio_api_key}
                if hasattr(settings, "cartorio_api_key")
                else {},
            )
            return resp.json() if resp.status_code < 500 else {"erro": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.exception("tool_agendar falhou: %s", e)
        return {"erro": str(e)}


async def _tool_consultar_protocolo(numero: str) -> dict:
    """Consulta protocolo via API."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"http://cartorio_api:8000/api/v1/protocolo/{numero}",
                headers={"X-API-Key": settings.cartorio_api_key}
                if hasattr(settings, "cartorio_api_key")
                else {},
            )
            return resp.json() if resp.status_code < 500 else {"erro": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.exception("tool_consultar_protocolo falhou: %s", e)
        return {"erro": str(e)}


async def _tool_calcular_emolumento(tipo: str, valor_base: float | None = None) -> dict:
    """Calcula emolumento via API."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            params = {"tipo": tipo}
            if valor_base:
                params["valor"] = str(valor_base)
            resp = await client.get(
                "http://cartorio_api:8000/api/v1/emolumento/calcular",
                params=params,
            )
            return resp.json() if resp.status_code < 500 else {"erro": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.exception("tool_calcular_emolumento falhou: %s", e)
        return {"erro": str(e)}


async def _tool_criar_atendimento(cliente_id: int, topico: str, contato: str) -> dict:
    """Cria atendimento (handoff humano) via API."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "http://cartorio_api:8000/api/v1/atendimento",
                json={
                    "cliente_id": cliente_id,
                    "topico": topico,
                    "contato": contato,
                    "canal": "telegram",
                },
                headers={"X-API-Key": settings.cartorio_api_key}
                if hasattr(settings, "cartorio_api_key")
                else {},
            )
            return resp.json() if resp.status_code < 500 else {"erro": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.exception("tool_criar_atendimento falhou: %s", e)
        return {"erro": str(e)}


# === INTENT ROUTER - Comandos nativos (sem LLM) ===


async def _handle_command(
    text: str,
    state_data: dict,
    bus: Any,
    chat_id: int,
    user_id: int,
    user_name: str,
) -> tuple[str, bool]:
    """Roteia comandos nativos. Retorna (resposta, is_final).

    Comandos: /start /menu /ajuda /agendar /protocolo /documento
              /emolumento /lgpd /humano /cancelar
    """
    cmd = text.strip().split()[0].lower().split("@")[0]  # /cmd@botname -> /cmd

    if cmd == "/start":
        await _clear_state(bus, chat_id)
        msg = (
            f"<b>Olá, {user_name}!</b> 👋\n\n"
            f"Sou o assistente virtual do Cartório 2º Ofício de Notas de Uberlândia/MG.\n\n"
            f"{MENU_PRINCIPAL}"
        )
        return msg, True

    if cmd in ("/menu", "/ajuda", "/help"):
        await _set_state(bus, chat_id, STATE_MENU)
        return MENU_PRINCIPAL, True

    if cmd == "/cancelar":
        await _clear_state(bus, chat_id)
        return "Operação cancelada. " + MENU_PRINCIPAL, True

    if cmd == "/agendar":
        await _set_state(bus, chat_id, STATE_AGENDAR_SERVICO, {})
        return MENU_AGENDAR, True

    if cmd == "/protocolo":
        await _set_state(bus, chat_id, STATE_PROTOCOLO, {})
        return (
            "<b>Consultar Protocolo</b>\n\nInforme o número do protocolo (ex: 2026-000123):"
        ), True

    if cmd == "/emolumento":
        await _set_state(bus, chat_id, STATE_EMOLUMENTO_TIPO, {})
        return MENU_EMOLUMENTO, True

    if cmd == "/lgpd":
        await _set_state(bus, chat_id, STATE_LGPD, {})
        return MENU_LGPD, True

    if cmd == "/humano":
        await _set_state(bus, chat_id, STATE_HUMANO, {"user_id": user_id, "user_name": user_name})
        return (
            "<b>Atendimento Humano</b>\n\n"
            "Descreva brevemente sua questão. Vou criar um ticket e um escrevente "
            "entrará em contato em até 2 horas úteis.\n\n"
            "<i>(Digite sua mensagem ou /cancelar)</i>"
        ), True

    if cmd == "/documento":
        return (
            "<b>Documentos</b>\n\n"
            "1. Para <b>2ª via</b>: responda /protocolo e informe o número\n"
            "2. Para <b>upload</b> de documento assinado: use o portal "
            "<a href='https://app.2notasudi.com.br/documentos'>app.2notasudi.com.br/documentos</a>\n"
            "3. Para <b>autenticação</b>: responda /agendar e escolha opção 2\n\n"
            "/cancelar para voltar ao menu"
        ), True

    return "", False  # nao eh comando


# === STATE HANDLERS (state machine com tools) ===


async def _handle_state(
    text: str,
    state: str,
    state_data: dict,
    bus: Any,
    chat_id: int,
    user_id: int,
    user_name: str,
) -> tuple[str, str]:
    """Processa mensagem baseado no estado atual. Retorna (resposta, novo_estado)."""

    if state == STATE_AGENDAR_SERVICO:
        if text in SERVICOS:
            codigo, nome, valor = SERVICOS[text]
            state_data["servico"] = codigo
            state_data["servico_nome"] = nome
            state_data["valor"] = valor
            await _set_state(bus, chat_id, STATE_AGENDAR_DATA, state_data)
            return (
                f"<b>{nome}</b> - {valor}\n\n"
                "Qual a data desejada? (formato: DD/MM/AAAA ou 'hoje' / 'amanhã')"
            ), STATE_AGENDAR_DATA
        return "Opção inválida. Responda 1-5 ou /cancelar.", state

    if state == STATE_AGENDAR_DATA:
        data_iso = _parse_date(text)
        if not data_iso:
            return "Data inválida. Use DD/MM/AAAA (ex: 15/07/2026) ou 'hoje'/'amanhã'.", state
        state_data["data"] = data_iso
        await _set_state(bus, chat_id, STATE_AGENDAR_HORA, state_data)
        return (
            f"Data: <b>{data_iso}</b>\n\nQual horário? (08:00 - 17:00, formato HH:MM)"
        ), STATE_AGENDAR_HORA

    if state == STATE_AGENDAR_HORA:
        hora = _parse_time(text)
        if not hora:
            return "Horário inválido. Use HH:MM (ex: 14:00).", state
        state_data["hora"] = hora
        await _set_state(bus, chat_id, STATE_AGENDAR_CONFIRMAR, state_data)

        cliente_id = user_id  # mapeamento simples - em prod, hash/lookup
        result = await _tool_agendar(
            cliente_id=cliente_id,
            data=state_data["data"],
            hora=state_data["hora"],
            servico=state_data["servico"],
        )
        await _clear_state(bus, chat_id)
        if "erro" in result:
            return (
                f"⚠️ Falha ao criar agendamento: {result['erro']}\n\n"
                "Tente novamente mais tarde ou /humano para atendimento."
            ), STATE_IDLE
        protocolo = result.get("numero", "N/A")
        return (
            f"✅ <b>Agendamento confirmado!</b>\n\n"
            f"📋 Protocolo: <code>{protocolo}</code>\n"
            f"📅 Data: {state_data['data']}\n"
            f"🕐 Hora: {state_data['hora']}\n"
            f"📝 Serviço: {state_data.get('servico_nome', '')}\n"
            f"💰 Valor: {state_data.get('valor', '')}\n\n"
            f"Apresente-se no cartório 15min antes.\n"
            f"/menu para outras opções"
        ), STATE_IDLE

    if state == STATE_PROTOCOLO:
        resultado = await _tool_consultar_protocolo(text.strip())
        await _clear_state(bus, chat_id)
        if "erro" in resultado or resultado.get("status") == "not_found":
            return (
                f"❌ Protocolo <b>{text.strip()}</b> não encontrado.\n"
                "Verifique o número e tente novamente."
            ), STATE_IDLE
        return (
            f"📋 <b>Protocolo {text.strip()}</b>\n\n"
            f"Status: {resultado.get('status', 'N/A')}\n"
            f"Serviço: {resultado.get('servico', 'N/A')}\n"
            f"Data: {resultado.get('data', 'N/A')}\n\n"
            f"/menu para voltar"
        ), STATE_IDLE

    if state == STATE_EMOLUMENTO_TIPO:
        if text in SERVICOS:
            codigo, nome, valor = SERVICOS[text]
            resultado = await _tool_calcular_emolumento(codigo)
            await _clear_state(bus, chat_id)
            valor_final = resultado.get("valor", valor)
            return (
                f"💰 <b>{nome}</b>\n\n"
                f"Valor: <b>{valor_final}</b>\n\n"
                f"Forma de pgto: PIX, cartão ou dinheiro no local.\n"
                f"/menu para voltar"
            ), STATE_IDLE
        return "Opção inválida. Responda 1-5 ou /cancelar.", state

    if state == STATE_LGPD:
        direitos = {
            "1": (
                "Acesso",
                "Seus dados estão em nosso sistema. Para acesso completo, "
                "solicite em /humano ou via portal.",
            ),
            "2": (
                "Correção",
                "Para corrigir dados: responda com o dado a corrigir (ex: 'nome: João Silva').",
            ),
            "3": (
                "Portabilidade",
                "Download em até 15 dias (LGPD art. 18 V). Solicite em /humano ou portal.",
            ),
            "4": ("Oposição", "Parar tratamento: confirmado. Prazo legal: 15 dias."),
            "5": (
                "Anonimização",
                "Esquecimento (LGPD art. 18 VI): dados serão anonimizados "
                "em até 15 dias. Solicite em /humano.",
            ),
            "6": ("Revogação", "Consentimento revogado. Para confirmar, responda 'sim'."),
        }
        if text in direitos:
            nome, msg = direitos[text]
            await _clear_state(bus, chat_id)
            return f"<b>LGPD - {nome}</b>\n\n{msg}\n\n/menu para voltar", STATE_IDLE
        return "Opção inválida. Responda 1-6 ou /cancelar.", state

    if state == STATE_HUMANO:
        topico = text.strip()
        result = await _tool_criar_atendimento(
            cliente_id=user_id,
            topico=topico,
            contato=f"telegram:{chat_id}",
        )
        await _clear_state(bus, chat_id)
        ticket_id = result.get("id", "N/A")
        return (
            f"✅ <b>Ticket criado: #{ticket_id}</b>\n\n"
            f"Um escrevente entrará em contato em até 2h úteis.\n\n"
            f"/menu para voltar"
        ), STATE_IDLE

    return "", state


# === HELPERS ===


def _parse_date(text: str) -> str | None:
    """Parse 'hoje', 'amanhã' ou DD/MM/AAAA → YYYY-MM-DD."""
    t = text.strip().lower()
    hoje = datetime.now()
    if t in ("hoje", "hj"):
        return hoje.strftime("%Y-%m-%d")
    if t in ("amanhã", "amanha", "am"):
        return (hoje + timedelta(days=1)).strftime("%Y-%m-%d")
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", t)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def _parse_time(text: str) -> str | None:
    """Parse HH:MM → HH:MM."""
    m = re.match(r"^(\d{1,2}):(\d{2})$", text.strip())
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return f"{h:02d}:{mi:02d}"
    return None


# === LLM RAPIDO - Apenas para intent não-mapeado ===


async def _call_fast_llm(text: str, context: str = "") -> str:
    """LLM rapido (Groq compound / Mistral) - SEM thinking blocks.

    Usado APENAS quando o usuario envia texto livre que nao casa com comando/state.
    Retorna resposta curta (< 500 chars).
    """
    system = (
        "Voce eh o assistente do Cartorio 2 Oficio de Notas de Uberlandia/MG.\n"
        "Responda em ate 2 frases, de forma direta e profissional.\n"
        "Se a pergunta for sobre: agendamento, protocolo, emolumento, documento ou "
        "direitos LGPD, oriente a usar /menu. Para questoes juridicas complexas, "
        "oriente /humano. NUNCA invente valores ou prazos."
    )
    if context:
        system += f"\n\nContexto: {context}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ]

    # Tenta providers em ordem de velocidade (free rapidos)
    providers = [
        (
            "groq",
            "groq/compound",
            settings.groq_api_key if hasattr(settings, "groq_api_key") else None,
            settings.groq_base_url
            if hasattr(settings, "groq_base_url")
            else "https://api.groq.com/openai/v1",
        ),
        (
            "mistral",
            "devstral-small-latest",
            settings.mistral_api_key if hasattr(settings, "mistral_api_key") else None,
            "https://api.mistral.ai/v1",
        ),
        (
            "openrouter",
            "google/gemma-4-31b-it:free",
            settings.openrouter_api_key if hasattr(settings, "openrouter_api_key") else None,
            "https://openrouter.ai/api/v1",
        ),
    ]

    for prov_name, model, api_key, base_url in providers:
        if not api_key:
            continue
        try:
            # Per-provider timeout 4s — total worst-case 12s vs 30s antes (Lesson 113).
            # httpx.AsyncClient aceita timeout granular; usamos connect=2 read=4 write=4 pool=4.
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=2.0, read=4.0, write=4.0, pool=4.0)
            ) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": 0.2,
                        "max_tokens": 200,
                    },
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    return content[:500]  # limite duro
        except Exception as e:
            logger.warning("LLM %s falhou: %s", prov_name, type(e).__name__)
            continue
    return ""


# === TELEGRAM SEND ===


async def _send_telegram_message(chat_id: int, text: str) -> bool:
    """Envia msg via Telegram API. Retorna True se 200."""
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Timeout agressivo 5s — Telegram normalmente responde <500ms. Se passar,
    # é problema de rede e o retry do Telegram entrega depois.
    # Lesson 113: webhook latency 14-52s era cumulativo de httpx timeouts.
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=1.5, read=5.0, write=1.5, pool=1.5)
    ) as client:
        try:
            resp = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            if resp.status_code == 200:
                return True
            logger.error("Telegram send %d: %s", resp.status_code, resp.text[:300])
            return False
        except Exception as e:
            logger.exception("Telegram send falhou: %s", e)
            return False


# === MAIN WEBHOOK ===


@router.post("/webhook", status_code=200)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Processa update Telegram. SEMPRE retorna 200 (evita retry infinito)."""
    body_bytes = await request.body()
    update = await request.json()

    _verify_telegram_secret(body_bytes, x_telegram_bot_api_secret_token)

    message = update.get("message", {})
    callback = update.get("callback_query", {})
    chat_id = (message.get("chat", {}) or callback.get("message", {}).get("chat", {})).get("id")
    text = message.get("text", "") or callback.get("data", "")
    user = message.get("from", {}) or callback.get("from", {})

    if not chat_id or not text:
        return {"status": "ignored", "reason": "non-text update"}

    user_id = user.get("id", 0)
    user_name = user.get("first_name", "cliente")

    logger.info("TG msg chat=%s user=%s text=%.80s", chat_id, user_id, text)

    # PII scrub (camada 1 - antes de tudo)
    scrub_result = scrub(text)
    text_scrubbed = scrub_result.text

    # Buscar estado no Redis
    bus = get_bus()
    state_obj = await _get_state(bus, chat_id)
    state = state_obj.get("state", STATE_IDLE)
    state_data = state_obj.get("data", {})

    response_text = ""

    # 1. Tentar comando nativo
    if text.startswith("/"):
        response_text, _ = await _handle_command(text, state_data, bus, chat_id, user_id, user_name)

    # 2. Se nao eh comando, processar estado atual
    if not response_text:
        if state != STATE_IDLE:
            response_text, new_state = await _handle_state(
                text_scrubbed, state, state_data, bus, chat_id, user_id, user_name
            )
            if response_text and new_state == STATE_IDLE:
                await _clear_state(bus, chat_id)
            elif response_text:
                await _set_state(bus, chat_id, new_state, state_data)

    # 3. Se ainda nao tem resposta, usar LLM rapido
    if not response_text:
        response_text = await _call_fast_llm(text_scrubbed, context=f"user={user_name}")
        if not response_text:
            response_text = (
                "Não entendi. Use /menu para ver opções ou /humano para falar com escrevente."
            )
        await _clear_state(bus, chat_id)

    # 4. PII scrub resposta (camada 3)
    response_scrubbed = scrub(response_text).text

    # 5. Enviar resposta
    response_sent = await _send_telegram_message(chat_id, response_scrubbed)

    # 6. Audit
    logger.info(
        "TG response chat=%s sent=%s len=%d",
        chat_id,
        response_sent,
        len(response_scrubbed),
    )

    return {
        "status": "ok" if response_sent else "partial",
        "chat_id": chat_id,
        "response_sent": response_sent,
    }


@router.get("/webhook/info")
async def telegram_webhook_info() -> dict[str, Any]:
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        return resp.json()


__all__ = ["router", "TELEGRAM_BOT_TOKEN"]
