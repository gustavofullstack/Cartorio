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
import html
import hashlib
import hmac
import json
import logging
import os
import re
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import require_cartorio_api_key
from app.config import settings
from app.db import get_db
from app.services.pii import scrub
from app.services.redis_bus import get_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Token do bot — SEMPRE via settings/env. NUNCA hardcoded (LGPD-P0 2026-07-09).
# Fallback vazio = endpoint responde 503 ate deploy correto. Sem segredo no repo.
TELEGRAM_BOT_TOKEN: str = (
    getattr(settings, "telegram_bot_token", None) or os.environ.get("TELEGRAM_BOT_TOKEN", "") or ""
)
TELEGRAM_API_BASE = "https://api.telegram.org"

TELEGRAM_WEBHOOK_SECRET: str | None = (
    getattr(settings, "telegram_webhook_secret", None)
    or os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    or None
)
TELEGRAM_BOT_USERNAME = (
    (
        getattr(settings, "telegram_bot_username", None)
        or os.environ.get("TELEGRAM_BOT_USERNAME", "")
        or "test_cartorio_bot"
    )
    .lstrip("@")
    .lower()
)

assert TELEGRAM_WEBHOOK_SECRET is None or isinstance(TELEGRAM_WEBHOOK_SECRET, str)

STATE_TTL = 3600
DEBOUNCE_WINDOW = 1.2  # agent path: menos atraso, ainda anti-spam
RATE_LIMIT_SECONDS = 3
MESSAGE_QUEUE_TTL = 10
MAX_RESPONSE_LEN = 3500  # respostas didaticas com espacamento (Telegram max 4096)
IDEMPOTENCY_TTL = 600  # 10min: evita reprocessar mesmo update_id
TYPING_REFRESH_SEC = 4  # refresh typing durante LLM (expira em 5s na API)
CLIENT_TTL = 60 * 60 * 24 * 30  # perfil do cliente no Redis: 30 dias

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
        "/voz",
    }
)

SERVICOS: dict[str, tuple[str, str]] = {
    "reconhecimento_firma": ("Reconhecimento de Firma", "R$ 11,61"),
    "autenticacao": ("Autenticacao de Documento", "R$ 11,61"),
    "procuracao": ("Procuracao (valor depende da finalidade)", "R$ 71,38 a R$ 226,14"),
    "testamento": ("Testamento", "R$ 452,71"),
    "ata_notarial": ("Ata Notarial", "R$ 226,15"),
}

BOT_COMMANDS = [
    {"command": "start", "description": "Iniciar (aviso LGPD + Agent AI)"},
    {"command": "menu", "description": "Atalhos (so se precisar)"},
    {"command": "agendar", "description": "Agendar atendimento"},
    {"command": "protocolo", "description": "Consultar protocolo"},
    {"command": "humano", "description": "Atendimento humano / HITL"},
    {"command": "cancelar", "description": "Cancelar e limpar conversa"},
    {"command": "lgpd", "description": "Privacidade e direitos LGPD"},
    {"command": "voz", "description": "Ouvir ultima resposta em audio (MiniMax TTS)"},
]

LGPD_NOTICE = (
    "AVISO DE PRIVACIDADE E LGPD (Lei 13.709/2018)\n"
    "\n"
    "Este canal e do 2o Oficio de Notas de Uberlandia/MG e trata dados pessoais "
    "para atendimento cartorario (agendamento, pre-qualificacao e encaminhamento).\n"
    "\n"
    "O que podemos receber neste chat\n"
    "- Nome, e-mail, telefone, CPF, RG e dados necessarios ao ato notarial\n"
    "- Documentos e informacoes de pre-qualificacao (com o seu consentimento)\n"
    "\n"
    "Como tratamos\n"
    "- Finalidade: atendimento do cartorio (base legal: execucao de procedimentos "
    "notariais / legítimo interesse administrativo e consentimento quando aplicavel)\n"
    "- Criptografia em transito (HTTPS/TLS) e controles de acesso no servidor\n"
    "- Dados sensiveis e documentos oficiais exigem validacao humana (HITL). "
    "O bot nao emite certidao nem escritura sozinho\n"
    "- Antes de processar com IA, aplicamos mascaramento de PII quando possivel; "
    "identificadores do cliente ficam no nosso Redis/banco vinculados ao seu "
    "Telegram (user id, username, chat id) e, quando informado, hash de CPF\n"
    "\n"
    "Seus direitos (LGPD)\n"
    "- Acesso, correcao, anonimizacao, portabilidade e exclusao: dpo@2notasudi.com.br\n"
    "- Voce pode digitar /lgpd a qualquer momento para reler este aviso\n"
    "\n"
    "Ao continuar a conversa, voce declara ciencia deste aviso e autoriza o "
    "tratamento dos dados necessarios ao atendimento."
)

LGPD_CONSENT_TTL = 60 * 60 * 24 * 30
LGPD_CONSENT_NOTICE_TTL = 600
LGPD_POLL_TTL = 60 * 60
LGPD_POLL_QUESTION = (
    "Voce concorda com o tratamento dos seus dados para realizacao "
    "do atendimento, conforme informado acima?"
)
LGPD_POLL_OPTIONS = ["Sim", "Nao"]


def _lgpd_consent_key(key: int | str) -> str:
    return f"tg:lgpd:consent:{key}"


def _lgpd_prompt_key(key: int | str) -> str:
    return f"tg:lgpd:prompt:{key}"


def _lgpd_poll_key(poll_id: str) -> str:
    return f"tg:lgpd:poll:{poll_id}"


def _lgpd_active_poll_key(key: int | str) -> str:
    return f"tg:lgpd:active_poll:{key}"


def _lgpd_poll_resolved_key(poll_id: str) -> str:
    return f"tg:lgpd:poll_resolved:{poll_id}"


async def _get_lgpd_consent(bus: Any, key: int | str | None = None) -> bool:
    if not bus or key is None:
        return False
    try:
        return bool(await bus.client.get(_lgpd_consent_key(key)))
    except Exception:
        return False


async def _set_lgpd_consent(bus: Any, key: int | str | None = None) -> bool:
    if not bus or key is None:
        return False
    try:
        await bus.client.set(_lgpd_consent_key(key), "1", ex=LGPD_CONSENT_TTL)
        await bus.client.delete(_lgpd_prompt_key(key))
        await bus.client.delete(_lgpd_active_poll_key(key))
        return True
    except Exception:
        return False


async def _clear_lgpd_consent(bus: Any, key: int | str | None = None) -> bool:
    if not bus or key is None:
        return False
    try:
        await bus.client.delete(_lgpd_consent_key(key))
        await bus.client.delete(_lgpd_prompt_key(key))
        await bus.client.delete(_lgpd_active_poll_key(key))
        return True
    except Exception:
        return False


def _normalize_lgpd_text_reply(text: str) -> str | None:
    if not text:
        return None
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
    if normalized in {"sim", "s", "aceito", "aceitar", "concordo", "autorizo"}:
        return "accept"
    if normalized in {"nao", "não", "n", "rejeito", "rejeitar", "nego", "nao aceito"}:
        return "reject"
    return None


# Contatos oficiais do cartorio — NUNCA mascarar no texto de SAIDA do bot
# (scrub generico de PII quebrava "dpo@2notasudi.com.br" → [EMAIL_REDACTED]).
_OFFICIAL_OUTBOUND_PROTECT: tuple[tuple[str, str], ...] = (
    ("dpo@2notasudi.com.br", "\x00DPO_EMAIL\x00"),
    ("DPO@2notasudi.com.br", "\x00DPO_EMAIL\x00"),
    ("contato@2notasudi.com.br", "\x00CONTATO_EMAIL\x00"),
    ("https://api.2notasudi.com.br", "\x00API_URL\x00"),
    ("https://2notasudi.com.br", "\x00SITE_URL\x00"),
)
_OFFICIAL_OUTBOUND_RESTORE: tuple[tuple[str, str], ...] = (
    ("\x00DPO_EMAIL\x00", "dpo@2notasudi.com.br"),
    ("\x00CONTATO_EMAIL\x00", "contato@2notasudi.com.br"),
    ("\x00API_URL\x00", "https://api.2notasudi.com.br"),
    ("\x00SITE_URL\x00", "https://2notasudi.com.br"),
)


def _protect_official_outbound(text: str) -> str:
    """Replace public contacts before a generic PII scrubber runs."""
    protected = text
    for real, token in _OFFICIAL_OUTBOUND_PROTECT:
        protected = re.sub(
            rf"(?<![\w.+-]){re.escape(real)}(?=$|[\s,;:!?\)\]\}}]|\.(?=\s|$))",
            token,
            protected,
        )
    return protected


def _restore_official_outbound(text: str) -> str:
    """Restore only allowlisted public contacts after output sanitization."""
    restored = text
    for token, real in _OFFICIAL_OUTBOUND_RESTORE:
        restored = restored.replace(token, real)
    return restored


def scrub_bot_outbound(text: str) -> str:
    """Scrub PII de SAIDA sem apagar contatos oficiais do cartorio.

    FIX 2026-07-10: usuario viu "Direitos LGPD: [EMAIL_REDACTED]" porque
    dpo@2notasudi.com.br passava por scrub() generico no path de resposta.
    """
    if not text:
        return text
    scrubbed = scrub(_protect_official_outbound(text)).text
    scrubbed = _restore_official_outbound(scrubbed)
    # Se ainda sobrou placeholder generico de email do DPO (edge case)
    scrubbed = scrubbed.replace(
        "Direitos LGPD: [EMAIL_REDACTED]",
        "Direitos LGPD: dpo@2notasudi.com.br",
    )
    scrubbed = scrubbed.replace(
        "DPO: [EMAIL_REDACTED]",
        "DPO: dpo@2notasudi.com.br",
    )
    return scrubbed


def format_bot_outbound(text: str) -> str:
    """Format, scrub and restore official contacts at the final outbound boundary."""
    protected = _protect_official_outbound(text)
    formatted = strip_emojis(format_bot_text(protected))
    return _restore_official_outbound(scrub(formatted).text)


def format_bot_text(text: str) -> str:
    """Normaliza espacamento para leitura humana (sem emoji, sem bloco robotico).

    - Garante quebras de linha reais entre blocos
    - Remove linhas vazias triplas
    - Nao esmaga paragrafos em uma unica linha
    - Remove URLs toxicas/spam se escaparem do agent
    """
    if not text:
        return text
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    # G7.03.T3: strip MiniMax <think>/<reasoning> ANTES de enviar (HTML-safe)
    try:
        from app.services.cartorio_agent import _strip_think_tags

        t = _strip_think_tags(t)
    except Exception:
        t = re.sub(r"<think>[\s\S]*?(?:</think>|$)", "", t, flags=re.I)
        t = re.sub(r"<reasoning>[\s\S]*?(?:</reasoning>|$)", "", t, flags=re.I)

    if not t.strip():
        return "..."

    # Camada de defesa: remove URLs nao oficiais (anti-spam / anti-porn)
    try:
        from app.services.cartorio_agent import sanitize_bot_output

        t = sanitize_bot_output(t) or t
    except Exception:
        # fallback local se import falhar
        t = re.sub(r"https?://\S+", "", t)
    # Se veio tudo numa linha com " - " repetido, quebra em itens
    if t.count(" - ") >= 3 and "\n" not in t.strip():
        t = t.replace(" - ", "\n- ")
    # Quebra "Palavra. Proxima" denso em paragrafos leves (so se sem newline)
    if "\n" not in t and len(t) > 180:
        t = re.sub(r"([.!?])\s+", r"\1\n\n", t)
    # Compacta 3+ newlines em 2 (uma linha em branco entre blocos)
    t = re.sub(r"\n{3,}", "\n\n", t)
    # Remove espacos no fim de cada linha
    t = "\n".join(line.rstrip() for line in t.split("\n"))
    return t.strip()


def telegram_html(text: str) -> str:
    """Render a deliberately small, safe Markdown subset for Telegram HTML.

    Agent output is untrusted: escape it first, then create only Telegram's
    documented formatting tags.  This prevents model-produced HTML (including
    ``<think>`` remnants) from breaking ``sendMessage`` while making the
    common ``**destaque**`` and ``*ênfase*`` output readable in clients.
    """
    escaped = html.escape(text, quote=False)

    def _link_repl(match: re.Match[str]) -> str:
        label, url = match.group(1), match.group(2)
        host = (urlparse(url).hostname or "").lower().rstrip(".")
        official = host in {"core.telegram.org", "telegram.org"} or host.endswith(
            ".2notasudi.com.br"
        )
        if not official:
            return match.group(0)
        return f'<a href="{html.escape(url, quote=True)}">{label}</a>'

    escaped = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", _link_repl, escaped)
    escaped = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", escaped)
    escaped = re.sub(r"__([^_\n]+)__", r"<u>\1</u>", escaped)
    escaped = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"<i>\1</i>", escaped)
    escaped = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", escaped)
    return escaped


def _truncate_html_safe(rendered: str, max_len: int) -> str:
    """Trunca HTML ja renderizado sem deixar tag malformada ou aberta.

    FIX E2.04 (2026-07-24): ``telegram_html(texto)[:MAX]`` podia cortar no meio
    de uma tag (``<b``, ``</cod``) ou deixar tag aberta — ambos causam 400
    "can't parse entities" na API Telegram. Como ``telegram_html`` escapa todo
    conteudo nao confiavel, as unicas tags literais aqui sao as do proprio
    formatter (b/i/u/code/a), entao basta um scanner simples.
    """
    if len(rendered) <= max_len:
        return rendered
    cut = max_len
    lt = rendered.rfind("<", 0, cut)
    gt = rendered.rfind(">", 0, cut)
    if lt > gt:  # corte cairia dentro de '<...>': recua ao inicio da tag
        cut = lt
    truncated = rendered[:cut]
    # Fecha tags conhecidas que ficaram abertas (LIFO nao importa p/ 1 nivel)
    for tag in ("b", "i", "u", "code", "a"):
        opens = len(re.findall(rf"<{tag}(?:\s[^>]*)?>", truncated))
        closes = truncated.count(f"</{tag}>")
        truncated += f"</{tag}>" * max(0, opens - closes)
    return truncated


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
    "callbacks_ok": 0,
    "agent_replies": 0,
    "agent_errors": 0,
}


def bump_metric(key: str, value: int = 1) -> None:
    """Incrementa contador in-process. Thread-safe pelo GIL do Python."""
    _METRICS[key] = _METRICS.get(key, 0) + value


# G9.S2.T4: inicio da janela webhook->resposta por chat (time.monotonic).
# A PRIMEIRA mensagem da janela de debounce marca o inicio (percepcao do
# usuario); o primeiro `_send_message` confirmado (200) consome a marca e
# observa o histograma `telegram_webhook_response_seconds` (que assim inclui
# a janela de debounce de 1.2s). LGPD: chat_id fica IN-PROCESS apenas —
# NUNCA vira label do Prometheus (gate: test_telegram_metrics_g9.py).
_RESPONSE_LATENCY_START: dict[int, float] = {}
_RESPONSE_LATENCY_START_MAX = 2048


def _mark_response_start(chat_id: int) -> None:
    """Marca o inicio da janela webhook->resposta (setdefault: 1a msg vence)."""
    if len(_RESPONSE_LATENCY_START) >= _RESPONSE_LATENCY_START_MAX:
        # Bound anti-leak: updates ignorados (sem resposta) nunca consomem a
        # marca. Estouro da tabela => reseta (perde observacoes da janela,
        # nunca o request). Metrica nao pode vazar memoria.
        _RESPONSE_LATENCY_START.clear()
    _RESPONSE_LATENCY_START.setdefault(chat_id, time.monotonic())


def _observe_response_sent(chat_id: int) -> None:
    """Observa `telegram_webhook_response_seconds` no 1o envio confirmado.

    Chamado por `_send_message` SOMENTE quando a API do Telegram retorna 200.
    A marca NAO eh consumida em falha de envio: se uma mensagem de erro de
    fallback for enviada depois, ela ainda eh a resposta (tardia) da janela.
    Marca sem sucesso algum expira pelo bound de `_mark_response_start`.
    """
    start = _RESPONSE_LATENCY_START.pop(chat_id, None)
    if start is None:
        return
    from app.services.metrics import store

    store.observe_telegram_webhook_response_seconds(time.monotonic() - start)


def classify_metric_for_status(status: str, kind: str) -> None:
    """FIX 2026-07-08: Gustavo reportou que /metrics nunca mexia em responses_ok.
    Status vindos do webhook: "ok", "partial", "ignored", "ignored_command",
    "duplicate". Mapeamos para os contadores corretos.

    FIX 2026-07-09: callbacks com status=ok TAMBEM contam em responses_ok
    (antes eram ignorados e o dashboard parecia vermelho mesmo com botoes OK).
    """
    if status == "ok":
        bump_metric("responses_ok")
        if kind == "callback":
            bump_metric("callbacks_ok")
    elif status == "partial":
        bump_metric("responses_partial")
    elif status in ("ignored", "ignored_command", "duplicate"):
        pass  # nao conta como falha
    else:
        bump_metric("responses_failed")


def strip_emojis(text: str) -> str:
    """Remove emojis de textos, preservando quebras de linha e espacamento."""
    if not text:
        return text
    cleaned = re.sub(
        "[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff"
        "\U0001f1e0-\U0001f1ff\U00002700-\U000027bf\U0001f900-\U0001f9ff"
        "\U00002600-\U000026ff\U0000fe00-\U0000fe0f]",
        "",
        text,
    )
    # Nao colapsar newlines: so multi-espaco horizontal na mesma linha
    cleaned = re.sub(r"[^\S\n]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    return format_bot_text(cleaned)


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
# FIX 2026-07-08 (mypy): _loop_id virou variavel de modulo em vez de attr de callable
# (mypy nao permite attr-defined em Callable[...] com strict).
_TG_HTTP_POOL: httpx.AsyncClient | None = None
_TG_HTTP_POOL_LOOP_ID: int = 0


def _get_tg_pool() -> httpx.AsyncClient:
    global _TG_HTTP_POOL, _TG_HTTP_POOL_LOOP_ID
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    current_loop_id = id(loop) if loop else 0

    if _TG_HTTP_POOL is None or _TG_HTTP_POOL_LOOP_ID != current_loop_id:
        _TG_HTTP_POOL = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
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


async def _enqueue_message(
    bus: Any,
    key: int | str | None = None,
    text: str | None = None,
    msg_id: int | None = None,
    chat_id: int | str | None = None,
    attachments: list[dict] | None = None,
) -> int:
    key = key if key is not None else chat_id
    if not bus:
        return 1
    try:
        raw = await bus.client.get(f"tg:queue:{key}")
        queue = json.loads(raw) if raw else []
        queue.append(
            {
                "text": text or "",
                "msg_id": msg_id or 0,
                "ts": time.time(),
                "attachments": attachments or [],
            }
        )
        await bus.client.set(f"tg:queue:{key}", json.dumps(queue), ex=MESSAGE_QUEUE_TTL)
        return len(queue)
    except Exception:
        return 1


async def _get_queued_messages(
    bus: Any, key: int | str | None = None, chat_id: int | str | None = None
) -> list[dict]:
    key = key if key is not None else chat_id
    if not bus:
        return []
    try:
        raw = await bus.client.get(f"tg:queue:{key}")
        return json.loads(raw) if raw else []
    except Exception:
        return []


async def _clear_queue(
    bus: Any, key: int | str | None = None, chat_id: int | str | None = None
) -> None:
    key = key if key is not None else chat_id
    if not bus:
        return
    try:
        await bus.client.delete(f"tg:queue:{key}")
    except Exception:
        pass


def _conv_key(chat_id: int, user_id: int | None = None, chat_type: str = "private") -> str:
    """Chave de conversa / estado.

    FIX 2026-07-09: em grupo/supergroup o estado DEVE ser por usuario
    (chat_id:user_id). Senao multiplos clientes compartilham o mesmo fluxo
    e o anti-spam do grupo engole respostas de data/hora/protocolo.
    """
    if chat_type in ("group", "supergroup") and user_id is not None:
        return f"{chat_id}:{user_id}"
    return str(chat_id)


async def _check_rate_limit(
    bus: Any, key: int | str | None = None, chat_id: int | str | None = None
) -> bool:
    key = key if key is not None else chat_id
    if not bus:
        return True
    try:
        if await bus.client.get(f"tg:ratelimit:{key}"):
            return False
        await bus.client.set(f"tg:ratelimit:{key}", "1", ex=RATE_LIMIT_SECONDS)
        return True
    except Exception:
        return True


async def _get_state(
    bus: Any, key: int | str | None = None, chat_id: int | str | None = None
) -> dict:
    key = key if key is not None else chat_id
    if not bus:
        return {"state": STATE_IDLE, "data": {}}
    try:
        raw = await bus.client.get(f"tg:state:{key}")
        return json.loads(raw) if raw else {"state": STATE_IDLE, "data": {}}
    except Exception:
        return {"state": STATE_IDLE, "data": {}}


async def _set_state(
    bus: Any,
    key: int | str | None = None,
    state: str | None = None,
    data: dict | None = None,
    chat_id: int | str | None = None,
) -> None:
    key = key if key is not None else chat_id
    if not bus:
        return
    payload = json.dumps({"state": state or STATE_IDLE, "data": data or {}}, ensure_ascii=False)
    try:
        # redis-py 5+: set(ex=) em vez de setex deprecado
        await bus.client.set(f"tg:state:{key}", payload, ex=STATE_TTL)
    except Exception as e:
        logger.warning("Falha state Redis: %s", e)


async def _clear_state(
    bus: Any, key: int | str | None = None, chat_id: int | str | None = None
) -> None:
    key = key if key is not None else chat_id
    if not bus:
        return
    try:
        await bus.client.delete(f"tg:state:{key}")
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


async def _tool_criar_atendimento(
    cliente_id: int,
    topico: str,
    contato: str,
    *,
    chatwoot_conversation_id: int | None = None,
) -> dict:
    """Cria ticket HITL. API retorna {ok, atendimento_id} — nao `id`.

    Payload alinhado a POST /api/v1/atendimento (router.criar_atendimento):
    canal + external_id obrigatorios; topico vira tipo/contexto scrubado.
    """
    external_id = (contato or str(cliente_id)).removeprefix("telegram:")
    payload: dict[str, Any] = {
        "canal": "telegram",
        "external_id": external_id,
        "tipo": "duvida",
        "contexto_scrubbed": scrub(topico).text,
        "handoff_para_humano": True,
    }
    if chatwoot_conversation_id is not None:
        payload["chatwoot_conversation_id"] = chatwoot_conversation_id
    return await _call_api(
        "POST",
        "/api/v1/atendimento",
        payload,
    )


def _menu_keyboard() -> list[list[dict]]:
    """Atalhos globais — usar SÓ quando o usuario pedir menu/atalhos.

    Labels 2026-07-09: menos informal, mais cartorio/HITL.
    """
    return [
        [{"text": "Agendar no cartorio", "callback_data": "cmd:agendar"}],
        [{"text": "Consultar protocolo", "callback_data": "cmd:protocolo"}],
        [{"text": "Atendimento humano (HITL)", "callback_data": "cmd:humano"}],
    ]


def _menu_keyboard_with_cancel() -> list[list[dict]]:
    """Menu + limpar conversa (grupo / saida explicita)."""
    kb = _menu_keyboard()
    kb.append([{"text": "Limpar conversa", "callback_data": "cmd:menu"}])
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


async def _send_voice_bytes(chat_id: int, mp3: bytes, caption: str | None = None) -> bool:
    """Envia audio OGG/MP3 via sendVoice (Telegram)."""
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
    try:
        client = _get_tg_pool()
        files = {"voice": ("reply.mp3", mp3, "audio/mpeg")}
        data: dict[str, Any] = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = strip_emojis(format_bot_text(caption))[:200]
        # httpx multipart
        resp = await client.post(url, data=data, files=files)
        if resp.status_code == 200:
            return True
        logger.warning("TG sendVoice %s %.200s", resp.status_code, resp.text)
        return False
    except Exception as exc:
        logger.exception("TG sendVoice error: %s", exc)
        return False


async def _send_message(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,  # noqa: ARG001 — aceito p/ compat, IGNORADO (no-buttons 2026-07-12)
    keyboard: list[list[dict]] | None = None,  # noqa: ARG001 — idem
) -> bool:
    """Envia mensagem ao Telegram.

    FIX 2026-07-12 (Gustavo directive): ZERO botoes inline. Cliente prefere texto puro.
    Mesmo se callers antigos passarem reply_markup/keyboard, sao ignorados.
    Apenas midia (foto/doc/video/audio) ainda eh aceita via sendPhoto/sendDocument etc.

    FIX 2026-07-09: se o grupo foi migrado a supergroup, a API retorna 400 com
    ``migrate_to_chat_id``. Reenvia automaticamente no ID novo.
    """
    # ``format_bot_text`` applies the generic scrubber. Restore official public
    # contacts only at the final outbound boundary, after that generic pass.
    cleaned_text = format_bot_outbound(text)
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # HTML is safe here because telegram_html escapes all agent content before
    # adding only documented Telegram tags.  Do not pass raw LLM HTML through.
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": _truncate_html_safe(telegram_html(cleaned_text), MAX_RESPONSE_LEN),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    # reply_markup/keyboard intencionalmente NAO adicionados ao payload
    try:
        # FIX v2: usa pool singleton (evita DNS+TLS+TCP a cada call)
        client = _get_tg_pool()
        resp = await client.post(url, json=payload)
        from app.services.metrics import store

        if resp.status_code == 200:
            store.inc_counter("cartorio_telegram_mensagens_total", labels={"direction": "out"})
            # G9.S2.T3/T4: resposta confirmada -> counter + latencia da janela
            store.inc_telegram_response_sent()
            _observe_response_sent(chat_id)
            return True
        # Auto-migrate supergroup
        try:
            body = resp.json()
            migrate_to = (body.get("parameters") or {}).get("migrate_to_chat_id")
            if resp.status_code == 400 and migrate_to:
                logger.warning("TG chat migrated %s -> %s; retrying send", chat_id, migrate_to)
                payload["chat_id"] = int(migrate_to)
                resp2 = await client.post(url, json=payload)
                if resp2.status_code == 200:
                    store.inc_counter(
                        "cartorio_telegram_mensagens_total", labels={"direction": "out"}
                    )
                    # G9.S2.T3/T4: resposta confirmada (apos migrate) -> idem
                    store.inc_telegram_response_sent()
                    _observe_response_sent(int(migrate_to))
                    return True
                logger.warning("TG send after migrate %d: %.200s", resp2.status_code, resp2.text)
                store.inc_counter("cartorio_telegram_erros_total")
                return False
        except Exception:
            pass
        logger.warning("TG send %d: %.200s", resp.status_code, resp.text)
        store.inc_counter("cartorio_telegram_erros_total")
        return False
    except Exception as e:
        from app.services.metrics import store

        store.inc_counter("cartorio_telegram_erros_total")
        logger.exception("TG send error: %s", e)
        return False


async def _send_poll(
    chat_id: int,
    question: str,
    options: list[str],
    bus: Any | None = None,
    *,
    conv_key: int | str | None = None,
) -> bool:
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    payload = {
        "chat_id": chat_id,
        "question": question,
        "options": options,
        "is_anonymous": False,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning(
                    "TG poll failed chat=%s status=%s body=%s",
                    chat_id,
                    resp.status_code,
                    resp.text[:200],
                )
                return False
            if bus and conv_key is not None:
                result = resp.json()
                payload_res = result.get("result", {}) if isinstance(result, dict) else {}
                poll_obj = payload_res.get("poll") or payload_res.get("message", {}).get("poll")
                poll_id = poll_obj.get("id") if isinstance(poll_obj, dict) else None
                if poll_id:
                    await bus.client.set(
                        _lgpd_poll_key(str(poll_id)), str(conv_key), ex=LGPD_POLL_TTL
                    )
                    await bus.client.set(
                        _lgpd_active_poll_key(conv_key), str(poll_id), ex=LGPD_POLL_TTL
                    )
            return True
    except Exception as e:
        logger.exception("TG poll error: %s", e)
        return False


async def _send_lgpd_consent_request(
    chat_id: int,
    bus: Any,
    conv_key: int | str,
) -> bool:
    """Envia aviso LGPD + enquete nativa. Nao reenvia se ja houver poll ativa."""
    if bus:
        try:
            if await bus.client.get(_lgpd_active_poll_key(conv_key)):
                return True
        except Exception:
            pass
        try:
            should_send = bool(
                await bus.client.set(_lgpd_prompt_key(conv_key), "1", nx=True, ex=LGPD_POLL_TTL)
            )
        except Exception:
            should_send = True
        if not should_send:
            return True

    notice_ok = await _send_message(
        chat_id,
        f"{LGPD_NOTICE}\n\nPara continuar, responda a enquete LGPD abaixo:",
    )
    if not notice_ok:
        await _send_message(
            chat_id,
            "Nao consigo abrir o aviso agora. Envie: SIM para autorizar ou NAO para cancelar.",
        )
        return False

    poll_ok = await _send_poll(
        chat_id,
        LGPD_POLL_QUESTION,
        LGPD_POLL_OPTIONS,
        bus=bus,
        conv_key=conv_key,
    )
    if poll_ok and bus:
        try:
            await bus.client.set(_lgpd_active_poll_key(conv_key), "1", ex=LGPD_POLL_TTL)
        except Exception:
            pass
    if not poll_ok:
        await _send_message(
            chat_id,
            "Nao consigo abrir a enquete no momento. Envie: SIM para autorizar ou NAO para cancelar.",
        )
    return poll_ok


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
    key: int | str | None = None,
    _user_name: str | None = None,
    chat_id: int | str | None = None,
) -> tuple[str, list | None]:
    key = key if key is not None else chat_id
    """key = conv_key (chat ou chat:user no grupo) para estado Redis."""
    cmd = text.strip().split()[0].lower().split("@")[0]
    if cmd == "/start":
        await _clear_state(bus, key)
        has_consent = await _get_lgpd_consent(bus, key)
        if bus and key is not None:
            try:
                await bus.client.delete(f"tg:hist:{key}")
            except Exception:
                pass
        if has_consent:
            if bus and key is not None:
                try:
                    await bus.client.delete(f"tg:hist:{key}")
                except Exception:
                    pass
            return (
                f"{LGPD_NOTICE}\n"
                "\n"
                "---\n"
                "\n"
                "Ola. Sou o assistente do Cartorio 2o Oficio de Notas — Uberlandia/MG.\n"
                "\n"
                "Posso ajudar com informacoes, valores de referencia, agendamento e "
                "pre-qualificacao. Atos oficiais passam por validacao humana.\n"
                "\n"
                "Exemplos do que voce pode digitar:\n"
                "\n"
                "- quanto custa autenticacao\n"
                "- quero agendar procuracao amanha\n"
                "- consultar protocolo 2026-000123\n"
                "- me fale cada servico em mensagens separadas\n"
                "\n"
                "A memoria desta conversa fica ativa neste chat (Redis), vinculada ao "
                "seu usuario Telegram.\n"
                "\n"
                "Atalhos: /menu · /humano · /lgpd · /cancelar",
                _menu_keyboard_with_cancel(),
            )
        return (
            "Cartorio 2o Oficio de Notas — Uberlandia/MG.\n"
            "\n"
            "Para continuar, preciso do seu consentimento LGPD.\n"
            "Responda: Sim para continuar ou Nao para interromper.\n"
            "\n"
            f"{LGPD_NOTICE}\n"
            "DPO: dpo@2notasudi.com.br",
            _menu_keyboard_with_cancel(),
        )
    if cmd == "/menu":
        await _set_state(bus, key, STATE_IDLE)
        return (
            "Atalhos opcionais do menu\n"
            "\n"
            "Use so se preferir botao em vez de texto:\n"
            "\n"
            "- Agendar no cartorio\n"
            "- Consultar protocolo\n"
            "- Atendimento humano (HITL)\n"
            "\n"
            "No dia a dia, digite livremente o que precisa.",
            _menu_keyboard_with_cancel(),
        )
    if cmd == "/agendar":
        await _set_state(bus, key, STATE_AGENDAR_SERVICO, {})
        return "Selecione o serviço desejado:", _servicos_keyboard()
    if cmd == "/protocolo":
        await _set_state(bus, key, STATE_PROTOCOLO, {})
        return "Informe o numero do protocolo (ex: 2026-000123):", None
    if cmd == "/humano":
        await _set_state(bus, key, STATE_HUMANO, {})
        return (
            "Descreva brevemente sua questao. Um escrevente entrara em contato em ate 2 horas uteis.",
            None,
        )
    if cmd == "/cancelar":
        await _clear_state(bus, key)
        if bus:
            try:
                await bus.client.delete(f"tg:hist:{key}")
            except Exception:
                pass
        return (
            "Conversa cancelada e memoria limpa. Pode continuar em linguagem natural.",
            _menu_keyboard_with_cancel(),
        )
    if cmd == "/lgpd":
        return (LGPD_NOTICE + "\n\nDPO: dpo@2notasudi.com.br", _menu_keyboard_with_cancel())
    if cmd == "/voz":
        return (
            "Gerando audio com MiniMax Speech…",
            None,
        )
    return "", None


async def _handle_callback(
    data: str,
    bus: Any,
    key: int | str | None = None,
    *,
    user_id: int | None = None,
    chat_id: int | str | None = None,
) -> tuple[str, list | None, bool]:
    key = key if key is not None else chat_id
    if data in {"lgpd:sim", "lgpd:s"}:
        if bus:
            await _set_lgpd_consent(bus, key)
        return (
            "Consentimento LGPD confirmado. Pode continuar com o atendimento.\n\n"
            "Como posso te ajudar?",
            _menu_keyboard_with_cancel(),
            True,
        )
    if data in {"lgpd:nao", "lgpd:n"}:
        if bus:
            await _clear_lgpd_consent(bus, key)
            await _clear_state(bus, key)
        return (
            "Entendido. Sem autorizacao LGPD, o atendimento por IA permanece desabilitado.\n"
            "Para recomeçar, digite /start.",
            _menu_keyboard_with_cancel(),
            True,
        )
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
            await _set_state(bus, key, STATE_AGENDAR_SERVICO, {})
            return "Selecione o serviço:", _servicos_keyboard(), True
        if c == "protocolo":
            await _set_state(bus, key, STATE_PROTOCOLO, {})
            return "Informe o numero do protocolo:", None, True
        if c == "humano":
            await _set_state(bus, key, STATE_HUMANO, {})
            return "Descreva sua questao:", None, True
        if c == "menu":
            await _clear_state(bus, key)
            return (
                "Atalhos opcionais do Menu. Pode digitar livremente se preferir.",
                _menu_keyboard(),
                True,
            )
    if data.startswith("servico:"):
        svc = data[8:]
        entry = SERVICOS.get(svc)
        if entry:
            nome, valor = entry
            await _set_state(
                bus,
                key,
                STATE_AGENDAR_DATA,
                {"servico": svc, "servico_nome": nome, "valor": valor},
            )
            return (
                f"Servico: {nome} - {valor}\n\nQual a data desejada? (DD/MM/AAAA, 'hoje' ou 'amanha')",
                None,
                True,
            )
        return "Opcao invalida.", _servicos_keyboard(), True
    if data == "agendar:confirmar":
        return await _confirmar_agendamento(bus, key, user_id=user_id)
    return "", None, False


async def _confirmar_agendamento(
    bus: Any, key: int | str | None, *, user_id: int | None = None
) -> tuple[str, list | None, bool]:
    # key may still be None if both conv_key and chat_id missing (mypy-safe guard)
    if key is None:
        return "Sessao invalida. Digite /start e tente novamente.", None, True
    state_obj = await _get_state(bus, key)
    sdata = state_obj.get("data", {})

    # HITL: uma confirmacao do cliente abre somente uma solicitacao para o
    # escrevente. O bot nunca cria o agendamento real nem reserva horario.
    servico_nome = sdata.get("servico_nome", "Atendimento")
    request_summary = (
        "Solicitacao de agendamento via Telegram: "
        f"servico={servico_nome}; data={sdata.get('data', '')}; hora={sdata.get('hora', '')}. "
        "Requer confirmacao de escrevente antes de qualquer reserva."
    )
    result = await _tool_criar_atendimento(
        int(user_id or 0),
        request_summary,
        f"telegram:{user_id or 'anon'}",
    )
    await _clear_state(bus, key)
    if "erro" in result or "detail" in result or result.get("status") in (400, 404, 409, 422, 500):
        erro_msg = result.get(
            "erro", result.get("detail", result.get("mensagem", "Erro desconhecido"))
        )
        if isinstance(erro_msg, dict):
            erro_msg = erro_msg.get("mensagem") or erro_msg.get("erro") or str(erro_msg)
        return (
            f"Falha ao registrar sua solicitacao: {erro_msg}\n\nTente novamente ou /humano.",
            _menu_keyboard(),
            True,
        )
    ticket_id = result.get("atendimento_id") or result.get("id") or "N/A"
    return (
        (
            f"Solicitacao registrada: #{ticket_id}\n\n"
            f"Data desejada: {sdata.get('data', '')} as {sdata.get('hora', '')}\n"
            f"Servico: {sdata.get('servico_nome', '')}\n"
            f"Valor de referencia: {sdata.get('valor', '')}\n\n"
            "Um escrevente confirmara a disponibilidade antes de qualquer agendamento."
        ),
        _menu_keyboard(),
        True,
    )


async def _handle_state(
    text: str,
    state: str,
    state_data: dict,
    bus: Any,
    key: int | str | None = None,
    *,
    user_id: int | None = None,
    chat_id: int | str | None = None,
) -> tuple[str, str, list | None]:
    key = key if key is not None else chat_id
    tl = text.strip().lower()
    if state == STATE_AGENDAR_SERVICO:
        for i, (svc, (nome, _)) in enumerate(SERVICOS.items(), 1):
            if tl == str(i) or tl == svc:
                state_data["servico"] = svc
                state_data["servico_nome"] = nome
                await _set_state(bus, key, STATE_AGENDAR_DATA, state_data)
                return (
                    f"Servico: {nome}\n\nQual a data? (DD/MM/AAAA, 'hoje' ou 'amanha')",
                    STATE_AGENDAR_DATA,
                    None,
                )
        return "Opcao invalida. Escolha 1-5:", state, _servicos_keyboard()
    if state == STATE_AGENDAR_DATA:
        d = _parse_date(text)
        if not d:
            if len(tl) > 10 or any(
                w in tl
                for w in (
                    "cancelar",
                    "sair",
                    "menu",
                    "voltar",
                    "parar",
                    "qual",
                    "como",
                    "onde",
                    "valor",
                    "procuracao",
                    "certidao",
                    "uai",
                    "kkk",
                    "funciona",
                    "beleza",
                    "obrigado",
                )
            ):
                await _clear_state(bus, key)
                return "", STATE_IDLE, None
            return (
                "Data invalida. Use DD/MM/AAAA (ex: 27/07/2026) ou digite /cancelar:",
                state,
                _menu_keyboard_with_cancel(),
            )
        state_data["data"] = d
        await _set_state(bus, key, STATE_AGENDAR_HORA, state_data)
        return (
            f"Data: {d}\n\nDigite o horario (08:00-17:00, formato HH:MM):",
            STATE_AGENDAR_HORA,
            None,
        )
    if state == STATE_AGENDAR_HORA:
        h = _parse_time(text)
        if not h:
            if len(tl) > 7 or any(
                w in tl
                for w in (
                    "cancelar",
                    "sair",
                    "menu",
                    "voltar",
                    "parar",
                    "qual",
                    "como",
                    "onde",
                    "valor",
                    "procuracao",
                    "certidao",
                    "uai",
                    "kkk",
                    "funciona",
                    "beleza",
                    "obrigado",
                )
            ):
                await _clear_state(bus, key)
                return "", STATE_IDLE, None
            return (
                "Horario invalido. Use HH:MM (ex: 14:30) ou digite /cancelar:",
                state,
                _menu_keyboard_with_cancel(),
            )
        state_data["hora"] = h
        await _set_state(bus, key, STATE_AGENDAR_CONFIRMAR, state_data)
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
            r, kb, _ = await _confirmar_agendamento(bus, key, user_id=user_id)
            return r, STATE_IDLE, kb
        if tl in ("nao", "n", "cancelar"):
            await _clear_state(bus, key)
            return "Agendamento cancelado.", STATE_IDLE, _menu_keyboard()
        return "Confirme com 'sim' ou 'nao':", state, _confirmar_keyboard()
    if state == STATE_PROTOCOLO:
        res_protocolo = await _tool_consultar_protocolo(text.strip())
        await _clear_state(bus, key)
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
        uid = user_id if user_id is not None else 0
        res_atendimento = await _tool_criar_atendimento(
            cliente_id=uid, topico=text.strip(), contato=f"telegram:{uid}"
        )
        await _clear_state(bus, key)
        # API devolve atendimento_id; aceita id legado se existir
        ticket_id = res_atendimento.get("atendimento_id") or res_atendimento.get("id")
        if "erro" in res_atendimento or res_atendimento.get("detail") or not ticket_id:
            erro = res_atendimento.get("erro") or res_atendimento.get("detail") or "falha"
            logger.warning("TG HITL create failed user=%s err=%s", uid, erro)
            return (
                "Nao consegui abrir o ticket agora. Tente /humano de novo em instantes "
                "ou fale no balcao do cartorio.",
                STATE_IDLE,
                _menu_keyboard(),
            )
        bump_metric("hitl_created")
        return (
            f"Ticket criado: #{ticket_id}\n\nUm escrevente entrara em contato em ate 2h uteis.",
            STATE_IDLE,
            _menu_keyboard(),
        )
    return "", state, None


def _parse_date(text: str) -> str | None:
    t = text.strip().lower()
    hoje = datetime.now()
    if t in ("hoje", "hj"):
        return hoje.strftime("%Y-%m-%d")
    if t in ("amanha", "amanhã", "am"):
        return (hoje + timedelta(days=1)).strftime("%Y-%m-%d")
    t_clean = re.sub(r"[.\-\s]+", "/", t)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", t_clean)
    if m:
        try:
            day, month, year_str = int(m.group(1)), int(m.group(2)), m.group(3)
            year = 2000 + int(year_str) if len(year_str) == 2 else int(year_str)
            return datetime(year, month, day).strftime("%Y-%m-%d")
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


HIST_TTL = 7200  # 2h de memoria multi-turn por conversa
HIST_MAX = 40  # entradas user/bot (~20 turnos)
# G8.02.T1: entry cap + dynamic token budget (not fixed HIST_MAX only)


async def _hist_get(bus: Any, key: int | str) -> list[str]:
    """Le historico multi-turn do Redis (lista de strings 'user:..' / 'bot:..')."""
    from app.services.dialog_history import hist_get

    return await hist_get(bus, key)


async def _hist_append(bus: Any, key: int | str, role: str, text: str) -> None:
    """Append turn no historico (LGPD: texto ja deve vir scrubado)."""
    from app.services.dialog_history import DialogHistoryConfig, hist_append

    if not text:
        return
    snippet = scrub(text).text
    cfg = DialogHistoryConfig(max_entries=HIST_MAX, ttl_sec=HIST_TTL, max_tokens=2000)
    try:
        await hist_append(bus, key, role, snippet, config=cfg)
    except Exception as exc:
        logger.warning("TG hist append fail key=%s: %s", key, exc)


async def _client_profile_upsert(
    bus: Any,
    key: int | str,
    *,
    user_id: int | str | None = None,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    chat_id: int | str | None = None,
    email: str | None = None,
    phone: str | None = None,
    cpf_raw: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Persiste perfil do cliente no Redis (por conversa/Telegram id).

    CPF nunca e gravado em claro: apenas hash SHA-256 truncado via pii.scrub helpers.
    """
    if not bus:
        return
    try:
        from app.services.pii import hash_cpf  # type: ignore
    except Exception:
        hash_cpf = None  # type: ignore
    try:
        raw = await bus.client.get(f"tg:client:{key}")
        profile: dict[str, Any] = {}
        if raw:
            try:
                profile = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode())
            except Exception:
                profile = {}
        if user_id is not None:
            profile["user_id"] = str(user_id)
        if username:
            profile["username"] = username.lstrip("@")
        if first_name:
            profile["first_name"] = first_name
        if last_name:
            profile["last_name"] = last_name
        if chat_id is not None:
            profile["chat_id"] = str(chat_id)
        if email:
            profile["email"] = email.strip().lower()
        if phone:
            profile["phone_last4"] = re.sub(r"\D", "", phone)[-4:]
        if cpf_raw and hash_cpf:
            try:
                profile["cpf_hash"] = hash_cpf(cpf_raw)
            except Exception:
                digits = re.sub(r"\D", "", cpf_raw)
                if len(digits) >= 11:
                    import hashlib

                    profile["cpf_hash"] = hashlib.sha256(digits.encode()).hexdigest()[:32]
        elif cpf_raw:
            digits = re.sub(r"\D", "", cpf_raw)
            if len(digits) >= 11:
                import hashlib

                profile["cpf_hash"] = hashlib.sha256(digits.encode()).hexdigest()[:32]
        if extra:
            profile.update(extra)
        profile["updated_at"] = datetime.now(UTC).isoformat() + "Z"
        profile["key"] = str(key)
        await bus.client.set(
            f"tg:client:{key}",
            json.dumps(profile, ensure_ascii=False),
            ex=CLIENT_TTL,
        )
        # indice auxiliar por user_id
        if profile.get("user_id"):
            await bus.client.set(
                f"tg:client:by_user:{profile['user_id']}",
                str(key),
                ex=CLIENT_TTL,
            )
    except Exception as exc:
        logger.warning("TG client profile upsert fail key=%s: %s", key, exc)


def _extract_client_fields(text: str) -> dict[str, str]:
    """Extrai campos comuns do texto livre (pre-qualificacao cartorio)."""
    out: dict[str, str] = {}
    if not text:
        return out
    # email
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if m:
        out["email"] = m.group(0)
    # cpf
    m = re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", text)
    if m:
        out["cpf_raw"] = m.group(0)
    # telefone BR simples
    m = re.search(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}\b", text)
    if m:
        out["phone"] = m.group(0)
    return out


async def _send_extra_messages(chat_id: int, messages: list[str]) -> int:
    """Envia mensagens extras do catalogo em sequencia (anti-flood leve)."""
    sent_n = 0
    for msg in messages[:8]:
        await asyncio.sleep(0.35)
        body = format_bot_outbound(msg)[:MAX_RESPONSE_LEN]
        if not body:
            continue
        ok = await _send_message(chat_id, body)
        if ok:
            sent_n += 1
    return sent_n


async def _publish_agent_event(bus: Any, event_type: str, payload: dict) -> None:
    """FIX 2026-07-12: publica evento no Redis 'cartorio:atendimentos' p/ WS realtime.

    Falha silenciosa — WS nao pode quebrar o fluxo do agent.
    """
    if not bus:
        return
    try:
        safe_payload = dict(payload)
        for field in ("text_preview",):
            if field in safe_payload:
                safe_payload[field] = scrub(str(safe_payload[field])).text
        for field in ("chat_id", "key"):
            if safe_payload.get(field) is not None:
                safe_payload[field] = hashlib.sha256(
                    str(safe_payload[field]).encode("utf-8")
                ).hexdigest()[:16]
        await bus.publish(
            "cartorio:atendimentos",
            {
                "type": event_type,
                "ts": __import__("time").time(),
                **safe_payload,
            },
        )
    except Exception as exc:
        logger.debug("TG ws publish fail type=%s: %s", event_type, exc)


def _persist_conversa(
    *,
    canal: str,
    external_id: str,
    raw_message_scrubbed: str,
    intent_detected: str | None,
    bot_response: str | None,
    llm_model: str | None = None,
    handoff_to_human: bool = False,
    handoff_reason: str | None = None,
) -> None:
    """FIX 2026-07-12: persiste turno na tabela `conversas` (Postgres).

    Roda em thread separada (sync DB op dentro de async). Falha silenciosa.
    """
    import hashlib
    from app.db import SessionLocal
    from app.models.conversa import Conversa

    if not raw_message_scrubbed:
        return
    payload_hash = hashlib.sha256(raw_message_scrubbed.encode("utf-8")).hexdigest()
    safe_message = scrub(raw_message_scrubbed).text
    safe_response = scrub(bot_response or "").text or None
    safe_intent = scrub(intent_detected or "").text[:64] or None

    def _write() -> None:
        try:
            with SessionLocal() as db:
                row = Conversa(
                    canal=canal,
                    external_id=external_id,
                    raw_message_hash=payload_hash,
                    raw_message_scrubbed=safe_message[:8000],
                    # Keep the indexed intent field within the legacy VARCHAR(64)
                    # schema; the full scrubbed turn remains in the text fields.
                    intent_detected=safe_intent,
                    bot_response=safe_response[:8000] if safe_response else None,
                    llm_model=llm_model,
                    handoff_to_human=handoff_to_human,
                    handoff_reason=handoff_reason,
                )
                db.add(row)
                db.commit()
        except Exception as exc:
            logger.warning("TG persist_conversa fail: %s", exc)

    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _write)
    except RuntimeError:
        _write()


async def _download_attachments(chat_id: int, attachments: list[dict]) -> None:
    """FIX 2026-07-12: baixa cada anexo via getFile Telegram API e salva local.

    Diretorio: /tmp/cartorio_media/{chat_id}/{file_unique_id}.{ext}
    Falha silenciosa — agente segue sem path local se getFile offline.
    """
    import os

    base_dir = f"/tmp/cartorio_media/{chat_id}"
    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception:
        pass

    async def _one(att: dict) -> None:
        file_id = att.get("file_id")
        if not file_id:
            return
        try:
            r = await _get_tg_pool().get(
                f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/getFile",
                params={"file_id": file_id},
            )
            if r.status_code != 200:
                logger.warning("TG getFile fail file_id=%s status=%s", file_id, r.status_code)
                return
            data = r.json()
            file_path = (data.get("result") or {}).get("file_path")
            if not file_path:
                logger.warning("TG getFile no path file_id=%s", file_id)
                return
            download_url = f"{TELEGRAM_API_BASE}/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
            r2 = await _get_tg_pool().get(download_url)
            if r2.status_code != 200:
                logger.warning("TG file download fail status=%s", r2.status_code)
                return
            ext = os.path.splitext(file_path)[1] or ""
            local_name = f"{att.get('file_unique_id', file_id)}{ext}"
            local_path = os.path.join(base_dir, local_name)
            with open(local_path, "wb") as f:
                f.write(r2.content)
            att["local_path"] = local_path
            att["telegram_file_path"] = file_path
            logger.info(
                "TG media saved chat=%s path=%s size=%d", chat_id, local_path, len(r2.content)
            )
        except Exception as exc:
            logger.warning("TG media download error file_id=%s: %s", file_id, exc)

    sem = asyncio.Semaphore(4)

    async def _wrapped(att: dict) -> None:
        async with sem:
            await _one(att)

    await asyncio.gather(*(_wrapped(a) for a in attachments), return_exceptions=True)


async def _call_cartorio_agent(
    text: str,
    bus: Any,
    key: int | str,
    *,
    chat_id: int | None = None,
    attachments: list[dict] | None = None,
) -> tuple[str, list | None]:
    """Agent AI Cartorio (MiniMax + tools) — NAO e so FSM de botoes.

    FIX 2026-07-12:
    - attachments: lista de midia recebida (foto/doc/video/audio) — passada ao LLM.
    - catalogo consolidado em 1 msg (sem spam multi-msg).
    - keyboard sempre None (no-buttons).

    FIX 2026-07-10: passa history Redis multi-turn.

    Retorna (texto, keyboard). Se o agent emitir ACTION, ajusta estado Redis
    (agendar/protocolo/humano) para o wizard continuar quando necessario.
    """
    from app.services.cartorio_agent import run_cartorio_agent

    try:
        history = await _hist_get(bus, key)
        await _hist_append(bus, key, "user", text)
        # WS: agent.start
        await _publish_agent_event(
            bus,
            "agent.start",
            {
                "chat_id": chat_id,
                "key": str(key),
                "text_preview": (text or "")[:120],
                "attachments": len(attachments or []),
                "history_len": len(history),
            },
        )
        reply = await run_cartorio_agent(
            text,
            history=history,
            attachments=attachments,
            chat_id=chat_id,
        )
        bump_metric("agent_replies")
        logger.info(
            "TG agent provider=%s action=%s tools=%s att=%s hist=%s",
            reply.provider,
            reply.action,
            reply.tools_used,
            len(attachments or []),
            len(history),
        )
        # WS: agent.reply
        await _publish_agent_event(
            bus,
            "agent.reply",
            {
                "chat_id": chat_id,
                "key": str(key),
                "provider": reply.provider,
                "action": reply.action,
                "tools": reply.tools_used,
                "text_preview": (reply.text or "")[:200],
                "extra_messages": len(getattr(reply, "extra_messages", None) or []),
            },
        )
        # Aplica acao estruturada do agent no estado da conversa
        # menu removido 2026-07-12; apenas agendar/protocolo/humano
        if reply.action == "agendar":
            await _set_state(bus, key, STATE_AGENDAR_SERVICO, {})
        elif reply.action == "protocolo":
            await _set_state(bus, key, STATE_PROTOCOLO, {})
        elif reply.action == "humano":
            await _set_state(bus, key, STATE_HUMANO, {})
            # FIX 2026-07-12: dispara handoff Chatwoot em background
            if chat_id:
                asyncio.create_task(_chatwoot_handoff(chat_id, text, attachments or [], history))
        text_out = strip_emojis(format_bot_text(reply.text)) if reply.text else ""
        if not text_out:
            text_out = (
                "Sou o assistente do cartorio.\n"
                "\n"
                "Pode digitar em linguagem natural o que precisa, ou enviar foto/doc/video/audio.\n"
                "\n"
                "Exemplos:\n"
                "- quanto custa autenticacao\n"
                "- quero agendar procuracao amanha as 10h\n"
                "- protocolo 2026-000123\n"
                "- falar com escrevente"
            )
        text_out = format_bot_text(text_out)[:MAX_RESPONSE_LEN]
        await _hist_append(bus, key, "bot", text_out)

        # FIX 2026-07-12: persistir turno no Postgres (conversas table)
        _persist_conversa(
            canal="telegram",
            external_id=str(chat_id or key),
            raw_message_scrubbed=text,
            intent_detected=", ".join(reply.tools_used[:3]) if reply.tools_used else None,
            bot_response=text_out,
            llm_model=reply.provider,
            handoff_to_human=(reply.action == "humano"),
            handoff_reason="agent_action_humano" if reply.action == "humano" else None,
        )

        return text_out, reply.keyboard  # keyboard sempre None (no-buttons 2026-07-12)
    except Exception as exc:
        logger.exception("TG agent error: %s", exc)
        bump_metric("agent_errors")
        return (
            "Tive uma falha momentanea no raciocinio. "
            "Tente de novo ou digite em texto livre (sem numero/botao).",
            None,
        )


async def _chatwoot_handoff(
    chat_id: int, text: str, attachments: list[dict], history: list[str] | None
) -> None:
    """FIX 2026-07-12: HITL real via Chatwoot.

    Cria/atualiza contato Chatwoot, abre conversa, envia contexto (texto + anexos).
    Falha silenciosa — se Chatwoot offline, escrevente cai via alerta Telegram.
    """
    try:
        from app.services.chatwoot_handoff import handoff_to_chatwoot

        ok, info = await handoff_to_chatwoot(
            chat_id=chat_id,
            text=text,
            attachments=attachments,
            history=history or [],
        )
        if ok:
            conversation_id = info.get("conversation_id")
            if isinstance(conversation_id, str) and conversation_id.isdigit():
                ticket = await _tool_criar_atendimento(
                    chat_id,
                    "Handoff Agent AI para escrevente via Chatwoot.",
                    str(chat_id),
                    chatwoot_conversation_id=int(conversation_id),
                )
                if not ticket.get("ok"):
                    logger.warning("TG chatwoot_handoff local mapping unavailable")
            await _send_message(
                chat_id,
                "Vou te conectar com um escrevente agora.\n"
                "\n"
                f"Conversa aberta no Chatwoot (#{info.get('conversation_id', '?')}). "
                "Ele responde em ate 2 horas uteis.\n"
                "\n"
                "Se preferir, continue aqui — registro tudo no seu historico.",
            )
            bump_metric("hitl_created")
        else:
            logger.warning(
                "TG chatwoot_handoff failed chat_hash=%s error=%s",
                hashlib.sha256(str(chat_id).encode("utf-8")).hexdigest()[:16],
                info.get("error", "unavailable"),
            )
    except Exception as exc:
        logger.exception("TG chatwoot_handoff error: %s", exc)


async def _call_fast_llm(text: str, context: str = "") -> str:
    """Compat: delega ao Agent AI Cartorio (texto puro)."""
    from app.services.cartorio_agent import run_cartorio_agent

    try:
        reply = await run_cartorio_agent(text if not context else f"{context}\n{text}")
        return (reply.text or "").strip()[:500]
    except Exception as exc:
        logger.warning("Fast LLM/agent falhou: %s", exc)
        return ""


# FIX 2026-07-20 (G9/A5): metadata chaveada pela MESMA conv_key usada na fila
# e no lock (chat_id:user_id em grupo). Antes era por chat_id — dois usuarios
# no mesmo grupo dentro da janela de debounce sobrescreviam a metadata e um
# deles nunca recebia resposta.
_DEBOUNCE_METADATA: dict[str, dict] = {}


async def _process_telegram_debounce(chat_id: int, conv_key: str | None = None) -> None:
    """Task em background para esperar o debounce, consolidar msgs e responder.

    NOTA: NAO recebe `db` (Session) — `background_tasks.add_task` do FastAPI
    executa APOS o response ser retornado, e a Session do `Depends(get_db)`
    ja foi fechada. Passar `db` aqui causaria "Session is closed" exception
    silenciosa (lesson-2026-07-02). Esta funcao usa apenas Redis, sem DB.

    FIX 2026-07-03 (loop-infinito): adiciona typing_loop em background para
    garantir que cliente sempre ve "Bot esta digitando..." enquanto processa.

    FIX 2026-07-09: conv_key = chat:user no grupo (estado/fila por usuario).

    FIX 2026-07-20 (G9/A5): recebe conv_key explicita (metadata/fila/lock
    chaveados por conv). conv_key=None so ocorre em callers legados.
    """
    key: str = conv_key or str(chat_id)
    metadata = _DEBOUNCE_METADATA.pop(key, {})
    user_id: int | None = metadata.get("user_id")
    await asyncio.sleep(DEBOUNCE_WINDOW)
    bus = get_bus()
    if not bus:
        logger.warning("TG debounce: bus indisponivel chat=%s", chat_id)
        return
    queue_key = f"tg:queue:{key}"
    lock_key = f"tg:lock:{key}"
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
            # FIX 2026-07-20 (G9/A6): fila vazia aqui e inesperado — o debounce
            # so e agendado quando ha lock novo, ou seja, deveria haver msg.
            # Antes retornava em silencio e o usuario ficava sem feedback.
            logger.warning("TG debounce fila vazia inesperada chat=%s key=%s", chat_id, key)
            bump_metric("responses_failed")
            try:
                await _send_message(
                    chat_id,
                    "Tive uma instabilidade tecnica ao processar sua mensagem.\n"
                    "\n"
                    "Por favor, reenvie em alguns instantes. "
                    "Se preferir, digite /humano para falar com a equipe.",
                )
            except Exception:
                logger.warning(
                    "TG debounce: falha ao enviar msg de erro fila vazia chat=%s", chat_id
                )
            return
        queue = json.loads(raw_queue)
        if not queue:
            logger.warning("TG debounce fila JSON vazia inesperada chat=%s key=%s", chat_id, key)
            bump_metric("responses_failed")
            try:
                await _send_message(
                    chat_id,
                    "Tive uma instabilidade tecnica ao processar sua mensagem.\n"
                    "\n"
                    "Por favor, reenvie em alguns instantes. "
                    "Se preferir, digite /humano para falar com a equipe.",
                )
            except Exception:
                logger.warning(
                    "TG debounce: falha ao enviar msg de erro fila JSON vazia chat=%s", chat_id
                )
            return
        textos = [m["text"] for m in queue]
        msg_ids = [m["msg_id"] for m in queue if m.get("msg_id")]
        text_to_process = _resumir_mensagens(textos) if len(textos) > 2 else textos[-1]
        # FIX 2026-07-12: coletar anexos de todas as mensagens do debounce
        attachments: list[dict] = []
        for m in queue:
            for att in m.get("attachments") or []:
                attachments.append(att)
        # Perfil do cliente (Redis) + extracao de campos informados no texto
        fields = _extract_client_fields(text_to_process)
        await _client_profile_upsert(
            bus,
            key,
            user_id=user_id,
            chat_id=chat_id,
            username=metadata.get("username"),
            first_name=metadata.get("first_name"),
            last_name=metadata.get("last_name"),
            email=fields.get("email"),
            phone=fields.get("phone"),
            cpf_raw=fields.get("cpf_raw"),
        )
        # Debounce ja consolidou mensagens. Rate limit e atualizado ao responder.
        await _check_rate_limit(bus, key)
        state_obj = await _get_state(bus, key)
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
                key,
                user_id=user_id,
            )
            if response_text and new_state == STATE_IDLE:
                await _clear_state(bus, key)
        if not response_text:
            # Agent AI Cartorio (MiniMax + tools) — conversa natural + memoria
            response_text, keyboard = await _call_cartorio_agent(
                text_to_process, bus, key, chat_id=chat_id, attachments=attachments
            )
            if not response_text:
                response_text = (
                    "Nao entendi completamente. Pode reformular em linguagem natural "
                    "ou digitar /menu se quiser atalhos."
                )
                keyboard = None
        # Mantem espacamento didatico; scrub PII de SAIDA sem apagar DPO oficial
        response_text = format_bot_text(strip_emojis(response_text))
        response_text = format_bot_outbound(response_text)
        sent = await _send_message(
            chat_id, response_text, reply_markup={"inline_keyboard": keyboard} if keyboard else None
        )
        if sent:
            bump_metric("responses_ok")
            if msg_ids:
                await _react(chat_id, msg_ids[-1], "check")
        else:
            bump_metric("responses_failed")
        logger.info("TG background response chat=%s key=%s sent=%s", chat_id, key, sent)
    except Exception as e:
        logger.exception("Erro na background task de debounce do Telegram: %s", e)
        # FIX 2026-07-20 (G9/A6): usuario NUNCA fica sem feedback — best-effort
        # de mensagem de erro amigavel. Falha aqui apenas loga, nao propaga.
        try:
            await _send_message(
                chat_id,
                "Tive uma instabilidade tecnica ao processar sua mensagem.\n"
                "\n"
                "Por favor, reenvie em alguns instantes. "
                "Se preferir, digite /humano para falar com a equipe.",
            )
        except Exception:
            logger.warning("TG debounce: falha ao enviar msg de erro chat=%s", chat_id)
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
            f"Agent AI Cartorio ativo em '{chat_title}'.\n\n"
            f"{LGPD_NOTICE}\n\n"
            "Comandos:\n"
            "/start - Aviso LGPD + inicio\n"
            "/menu - Atalhos opcionais\n"
            "/humano - Atendimento humano (HITL)\n"
            "/lgpd - Privacidade\n"
            "/cancelar - Limpar conversa\n\n"
            "Prefira linguagem natural (mencione @test_cartorio_bot no grupo)."
        )
        await _send_message(chat_id, welcome, keyboard=_menu_keyboard_with_cancel())
        return {"status": "ok", "kind": "my_chat_member_join", "chat_id": chat_id}

    if new_status in ("left", "kicked"):
        bump_metric("responses_failed")
        logger.warning("TG bot removido chat=%s new_status=%s", chat_id, new_status)
        return {"status": "ok", "kind": "my_chat_member_left", "chat_id": chat_id}

    return {"status": "ignored", "kind": "my_chat_member", "chat_id": chat_id}


@router.get("/health")
async def telegram_health() -> dict:
    # LGPD-P0 2026-07-09: token agora vem SEMPRE de settings/.env.
    # Reporta configurado somente se o token existe e nao e placeholder.
    token_configured = bool(TELEGRAM_BOT_TOKEN) and len(TELEGRAM_BOT_TOKEN) > 20
    return {
        "status": "ok" if token_configured else "degraded",
        "service": "telegram-bot",
        "bot": "test_cartorio_bot",
        "webhook_configured": token_configured,
        "token_source": "settings/env" if token_configured else "missing",
        "version": "v0.6.1-p0fix",
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


_LAST_UPDATES: list[dict] = []
_LAST_UPDATES_MAX = 20


def _record_update(update: dict, response: dict) -> None:
    """Registra metadados mínimos para diagnóstico autenticado.

    O buffer é deliberadamente livre de texto, chat ID e resposta do usuário:
    updates do Telegram podem conter dados pessoais e não devem permanecer em
    memória nem ser expostos por uma rota operacional.
    """
    response_status = response.get("status")
    outcome = (
        response_status
        if response_status in {"duplicate", "ignored", "ignored_command", "ok"}
        else "other"
    )
    _LAST_UPDATES.append(
        {
            "ts": int(__import__("time").time()),
            "update_id": update.get("update_id"),
            "kind": (
                "callback"
                if update.get("callback_query")
                else "message"
                if update.get("message")
                else "my_chat_member"
                if update.get("my_chat_member")
                else "other"
            ),
            "outcome": outcome,
        }
    )
    if len(_LAST_UPDATES) > _LAST_UPDATES_MAX:
        _LAST_UPDATES.pop(0)


@router.get("/debug/last-updates")
async def telegram_debug_last_updates(
    _api_key: str = Depends(require_cartorio_api_key),
) -> dict:
    """Exibe somente metadados de processamento para operador autorizado.

    Uso: ``GET /api/v1/telegram/debug/last-updates`` com ``X-API-Key``.
    """
    return {
        "service": "telegram-bot",
        "version": "v0.6.0",
        "last_updates": list(_LAST_UPDATES),
        "ts": int(__import__("time").time()),
    }


@router.post(
    "/webhook",
    status_code=200,
    summary="Webhook do Telegram Bot API (HMAC secret + idempotency + LGPD scrub)",
    description=(
        "Recebe updates do Telegram Bot API (https://core.telegram.org/bots/api#update).\n\n"
        "**Auth**: header `X-Telegram-Bot-Api-Secret-Token` validado contra "
        "`TELEGRAM_WEBHOOK_SECRET` (HMAC).\n\n"
        "**Idempotency**: `update_id` eh deduplicado via Redis SETNX (TTL 10min).\n\n"
        "**LGPD**: payload NAO eh persistido cru; `message.text`/`from` passam "
        "por scrubber antes de qualquer LLM call. Schema canonico documentado "
        "em `app.schemas.webhook_payloads.TelegramUpdate`.\n\n"
        "**Handler paths**:\n"
        "- `message` (texto/comando/midia) - flow principal\n"
        "- `callback_query` (botao inline) - callback handler\n"
        "- `edited_message` - re-processa edicao\n"
        "- `my_chat_member` - auto-detect entrada/saida de grupo\n"
    ),
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/TelegramUpdate"},
                    "examples": {
                        "text_message": {
                            "summary": "Mensagem de texto privada",
                            "value": {
                                "update_id": 123456789,
                                "message": {
                                    "message_id": 42,
                                    "date": 1721308800,
                                    "from": {
                                        "id": 987654321,
                                        "first_name": "Maria",
                                        "username": "mariacliente",
                                    },
                                    "chat": {"id": 987654321, "type": "private"},
                                    "text": "Quero agendar uma procura\u00e7\u00e3o amanh\u00e3",
                                },
                            },
                        },
                        "callback_button": {
                            "summary": "Clique em botao inline",
                            "value": {
                                "update_id": 123456790,
                                "callback_query": {
                                    "id": "cb_abc123",
                                    "from": {"id": 987654321, "first_name": "Maria"},
                                    "chat_instance": "chat_inst_xyz",
                                    "data": "cmd:agendar",
                                    "message": {
                                        "message_id": 41,
                                        "date": 1721308500,
                                        "chat": {"id": 987654321, "type": "private"},
                                    },
                                },
                            },
                        },
                        "group_command": {
                            "summary": "Comando em grupo",
                            "value": {
                                "update_id": 123456791,
                                "message": {
                                    "message_id": 50,
                                    "date": 1721308900,
                                    "from": {"id": 111, "first_name": "Joao"},
                                    "chat": {
                                        "id": -1004331849032,
                                        "type": "supergroup",
                                        "title": "Clientes Cartorio",
                                    },
                                    "text": "/menu",
                                },
                            },
                        },
                    },
                }
            }
        }
    },
)
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """Wrapper G9.S2.T3: contabiliza `telegram_webhook_total{result}` e delega.

    Observa o desfecho HTTP do webhook (200 | 401 | 5xx) e chama o handler
    real (`_telegram_webhook_impl`). Comportamento PRESERVADO: qualquer
    excecao (401 do secret token, excecao nao tratada) continua propagando —
    o wrapper apenas registra o resultado antes do re-raise.

    LGPD (S2.T5): o label `result` eh enum estrito; chat_id/username NUNCA
    viram label (gate: test_telegram_metrics_g9.py).
    """
    from app.services.metrics import store as _metrics_store

    try:
        resp = await _telegram_webhook_impl(
            request, background_tasks, x_telegram_bot_api_secret_token, db
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            result = "401"
        elif exc.status_code >= 500:
            result = "5xx"
        else:
            result = "unknown"  # fora do enum -> coercion fail-safe no store
        _metrics_store.inc_telegram_webhook_total(result)
        raise
    except Exception:
        # Excecao nao tratada -> FastAPI devolve 500. NUNCA deveria acontecer
        # (regra do bot: SEMPRE 200); se aparecer, vira sinal de alerta.
        _metrics_store.inc_telegram_webhook_total("5xx")
        raise
    _metrics_store.inc_telegram_webhook_total("200")
    return resp


async def _telegram_webhook_impl(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None,
    db: Session,
) -> dict:
    bump_metric("requests_total")
    from app.services.metrics import store

    store.inc_counter("cartorio_telegram_mensagens_total", labels={"direction": "in"})
    try:
        update = await request.json()
    except Exception as exc:
        # FIX 2026-07-20 (G9/A3): JSON invalido NUNCA vira 5xx — o Telegram faz
        # retry infinito em 5xx. Loga e responde 200 degraded.
        store.inc_counter("cartorio_telegram_erros_total")
        logger.warning("TG webhook invalid json: %s", type(exc).__name__)
        return {"status": "degraded", "reason": "invalid_json"}
    _verify_telegram_secret(x_telegram_bot_api_secret_token)
    message = update.get("message", {}) or update.get("edited_message", {})
    poll_answer = update.get("poll_answer", {})
    callback = update.get("callback_query", {})
    my_chat_member = update.get("my_chat_member", {})
    bus: Any = None
    try:
        bus = get_bus()
    except Exception as exc:
        logger.warning(
            "TG webhook: Redis indisponivel (%s) — fallback sincrono degraded",
            type(exc).__name__,
        )
        bus = None
    chat_id = (
        message.get("chat", {}).get("id")
        or callback.get("message", {}).get("chat", {}).get("id")
        or my_chat_member.get("chat", {}).get("id")
    )
    text = message.get("text", "") or callback.get("data", "")
    update_id = update.get("update_id", 0)

    if poll_answer and bus:
        poll_id = str(poll_answer.get("poll_id") or "")
        option_ids = poll_answer.get("option_ids") or []
        if not poll_id or not option_ids:
            return {
                "status": "ignored",
                "kind": "poll_answer",
                "poll_id": poll_id,
            }
        try:
            option = int(option_ids[0])
        except (TypeError, ValueError):
            option = None
        if option not in (0, 1):
            return {
                "status": "ignored",
                "kind": "poll_answer",
                "poll_id": poll_id,
            }
        conv_key_bytes = await bus.client.get(_lgpd_poll_key(poll_id))
        conv_key = (
            conv_key_bytes.decode()
            if isinstance(conv_key_bytes, (bytes, bytearray))
            else str(conv_key_bytes)
            if conv_key_bytes
            else None
        )
        if conv_key is None:
            voter_chat = poll_answer.get("voter_chat", {}) or {}
            voter_chat_id = voter_chat.get("id")
            voter_chat_type = voter_chat.get("type", "")
            poll_user_id = (poll_answer.get("user") or {}).get("id")
            if poll_user_id:
                if voter_chat_id and voter_chat_type in {"group", "supergroup"}:
                    conv_key = f"{voter_chat_id}:{poll_user_id}"
                else:
                    conv_key = str(poll_user_id)
        if not conv_key:
            return {
                "status": "ignored",
                "kind": "poll_answer",
                "poll_id": poll_id,
            }

        voter_chat = poll_answer.get("voter_chat", {}) or {}
        reply_chat = voter_chat.get("id") or (poll_answer.get("user") or {}).get("id")

        try:
            first_vote = bool(
                await bus.client.set(
                    _lgpd_poll_resolved_key(poll_id), "1", nx=True, ex=LGPD_POLL_TTL
                )
            )
        except Exception:
            first_vote = True
        if not first_vote:
            return {
                "status": "ok",
                "kind": "poll_answer",
                "poll_id": poll_id,
                "idempotent": True,
            }

        if option == 0:
            await _set_lgpd_consent(bus, conv_key)
            answer = (
                "Consentimento LGPD confirmado.\n\n"
                "Pode continuar com o atendimento. Envie sua pergunta."
            )
        else:
            await _clear_lgpd_consent(bus, conv_key)
            await _clear_state(bus, conv_key)
            await bus.client.delete(f"tg:hist:{conv_key}")
            answer = (
                "Consentimento nao registrado. Sem autorizacao LGPD, o atendimento por IA"
                " fica desabilitado para esta conversa.\n\n"
                "Para tentar novamente, envie /start."
            )
        sent = await _send_message(int(reply_chat), answer) if reply_chat else False
        return {
            "status": "ok" if sent else "partial",
            "kind": "poll_answer",
            "poll_id": poll_id,
        }

    if poll_answer and not bus:
        return {
            "status": "degraded",
            "kind": "poll_answer",
            "detail": "consent cache unavailable",
        }

    # G9.S2.T4: marca o inicio da janela webhook->resposta (1a msg da janela
    # de debounce vence via setdefault). Metrica NUNCA derruba o webhook:
    # payload malformado (chat.id nao-int) eh ignorado silenciosamente.
    try:
        if chat_id:
            _mark_response_start(int(chat_id))
    except (TypeError, ValueError):
        pass

    def _finish(resp: dict) -> dict:
        """Grava resposta final no buffer de debug (antes so gravava 'received')."""
        _record_update(update, resp)
        return resp

    # FIX 2026-07-08: auto-detecta quando bot entra/sai de grupo e responde.
    if my_chat_member:
        return _finish(await _handle_my_chat_member(my_chat_member))

    # Audio do usuario (Telegram voice/audio) — Agent MiniMax ainda sem STT oficial
    # no Coding Plan; orienta texto e oferece /voz (TTS de resposta).
    if chat_id and not text and not callback and message:
        voice = message.get("voice") or message.get("audio")
        if voice:
            await _send_typing_fast(int(chat_id))
            msg = (
                "Recebi seu audio.\n"
                "\n"
                "Por enquanto o Agent Cartorio processa texto "
                "(MiniMax-M3 + tools). Transcricao automatica de voz "
                "ainda esta em implantacao.\n"
                "\n"
                "Digite sua pergunta em texto, ou use /humano.\n"
                "Depois de uma resposta, digite /voz para ouvir em audio (TTS MiniMax)."
            )
            sent = await _send_message(int(chat_id), msg)
            return _finish(
                {
                    "status": "ok" if sent else "partial",
                    "chat_id": chat_id,
                    "kind": "voice_ack",
                    "response_sent": sent,
                }
            )

    # FIX 2026-07-12: extrai midia (foto/doc/video/audio) ANTES de checar text.
    # Aceita foto+caption, doc+caption, etc.
    attachments: list[dict] = []
    caption = message.get("caption", "")
    # Telegram mantém a legenda separada de ``text``; promovê-la preserva
    # perguntas anexadas a fotos e documentos para o Agent AI.
    text = text or caption
    if message.get("photo"):
        # photo vem como lista ordenada por tamanho; pegar maior
        photo = message["photo"][-1]
        attachments.append(
            {
                "type": "photo",
                "file_id": photo.get("file_id"),
                "file_unique_id": photo.get("file_unique_id"),
                "file_size": photo.get("file_size"),
                "width": photo.get("width"),
                "height": photo.get("height"),
                "caption": caption,
            }
        )
    if message.get("document"):
        doc = message["document"]
        attachments.append(
            {
                "type": "document",
                "file_id": doc.get("file_id"),
                "file_unique_id": doc.get("file_unique_id"),
                "file_name": doc.get("file_name"),
                "mime_type": doc.get("mime_type"),
                "file_size": doc.get("file_size"),
                "caption": caption,
            }
        )
    if message.get("video"):
        vid = message["video"]
        attachments.append(
            {
                "type": "video",
                "file_id": vid.get("file_id"),
                "file_unique_id": vid.get("file_unique_id"),
                "file_name": vid.get("file_name"),
                "mime_type": vid.get("mime_type"),
                "file_size": vid.get("file_size"),
                "duration": vid.get("duration"),
                "caption": caption,
            }
        )
    if message.get("audio"):
        aud = message["audio"]
        attachments.append(
            {
                "type": "audio",
                "file_id": aud.get("file_id"),
                "file_unique_id": aud.get("file_unique_id"),
                "file_name": aud.get("file_name"),
                "mime_type": aud.get("mime_type"),
                "file_size": aud.get("file_size"),
                "duration": aud.get("duration"),
                "caption": caption,
            }
        )
    # voice ja tratado em handler proprio acima
    # Download paralelo de cada attachment via getFile
    if attachments and chat_id:
        await _download_attachments(int(chat_id), attachments)
        logger.info(
            "TG media received chat=%s n=%d types=%s",
            chat_id,
            len(attachments),
            [a["type"] for a in attachments],
        )
        # Se veio so midia sem caption, gera um texto default
        if not text:
            text = f"[cliente enviou {len(attachments)} arquivo(s) sem legenda]"

    if not chat_id or (not text and not callback):
        return _finish({"status": "ignored", "reason": "non-text update"})

    user_id = message.get("from", {}).get("id") or callback.get("from", {}).get("id") or None
    chat_type = (
        message.get("chat", {}).get("type", "")
        or callback.get("message", {}).get("chat", {}).get("type", "")
        or "private"
    )
    orig_text = text or ""
    _fields_early = _extract_client_fields(orig_text)
    if text:
        text = re.sub(rf"@{re.escape(TELEGRAM_BOT_USERNAME)}", "", text, flags=re.I).strip()
        text = re.sub(r"@test_cartorio(_bot)?", "", text, flags=re.I).strip()
    scrub_res = scrub(text) if text else None
    text_scrubbed = scrub_res.text if scrub_res else ""
    conv = _conv_key(int(chat_id), int(user_id) if user_id else None, chat_type)
    has_lgpd_consent = await _get_lgpd_consent(bus, conv)

    # Avoid spam: ignore unrelated group free-text, but allow a direct reply to
    # this bot as a natural conversational turn (not only @-mentions/commands).
    if chat_type in ("group", "supergroup"):
        clean_first_word = text.strip().split()[0].lower().lstrip("/") if text.strip() else ""
        is_command = text.startswith("/") or clean_first_word in (
            "start",
            "menu",
            "agendar",
            "protocolo",
            "humano",
            "cancelar",
            "lgpd",
        )
        mentions_bot = (
            f"@{TELEGRAM_BOT_USERNAME}" in orig_text.lower()
            or "@test_cartorio" in orig_text.lower()
        )
        reply_from = message.get("reply_to_message", {}).get("from", {})
        is_reply_to_bot = str(reply_from.get("username", "")).lower() == TELEGRAM_BOT_USERNAME
        if not is_command and not mentions_bot and not is_reply_to_bot and not callback:
            mid_flow = False
            if bus:
                st = await _get_state(bus, conv)
                mid_flow = st.get("state", STATE_IDLE) != STATE_IDLE
            if not mid_flow:
                # FIX 2026-07-09: NAO spammar orientacao a cada msg do grupo.
                logger.info("TG group ignore chat=%s text=%.60s", chat_id, text_scrubbed)
                early_msg_id = message.get("message_id", 0)
                await _react(chat_id, early_msg_id, "eyes")
                should_orient = True
                if bus:
                    try:
                        orient_key = f"tg:orient:{chat_id}"
                        set_ok = await bus.client.set(orient_key, "1", nx=True, ex=300)
                        should_orient = bool(set_ok)
                    except Exception:
                        should_orient = False
                if should_orient:
                    orientacao = (
                        "No grupo, mencione @test_cartorio_bot ou use /start. "
                        "Pode digitar em linguagem natural. Aviso nao se repete por 5 min."
                    )
                    await _send_message(chat_id, orientacao, keyboard=_menu_keyboard_with_cancel())
                return _finish(
                    {"status": "ignored", "reason": "group message without command or mention"}
                )
            logger.info(
                "TG group mid-flow allow chat=%s conv=%s text=%.40s", chat_id, conv, text_scrubbed
            )

    msg_id = message.get("message_id", 0) or callback.get("message", {}).get("message_id", 0)
    logger.info("TG msg chat=%s conv=%s text=%.60s", chat_id, conv, text_scrubbed)

    # ====== ANTI-SPAM: idempotency check por update_id ======
    if bus and update_id:
        already_processed = await _check_idempotency(bus, update_id)
        if already_processed:
            logger.warning("TG DUPLICATE update_id=%s chat=%s - ignorando", update_id, chat_id)
            return _finish({"status": "duplicate", "update_id": update_id, "chat_id": chat_id})

    # ====== TYPING VISIVEL ======
    asyncio.create_task(_send_typing_fast(chat_id))

    # (PII extraction and scrub moved to the top of webhook)
    # Se mascarou CPF/RG/email, marca para o agent reconhecer pre-qualificacao
    if (
        (scrub_res and scrub_res.findings)
        or _fields_early.get("cpf_raw")
        or _fields_early.get("email")
    ):
        if "DADOS_PESSOAIS_RECEBIDOS" not in text_scrubbed:
            text_scrubbed = f"{text_scrubbed} [DADOS_PESSOAIS_RECEBIDOS]".strip()
    uid = int(user_id) if user_id else None
    if callback:
        data = callback.get("data", "")
        await _answer_callback_query(callback.get("id", ""))
        if bus and not has_lgpd_consent and not str(data).startswith("lgpd:"):
            lgpd_prompt_sent = await _send_lgpd_consent_request(int(chat_id), bus, conv)
            return _finish(
                {
                    "status": "ok" if lgpd_prompt_sent else "partial",
                    "chat_id": chat_id,
                    "kind": "lgpd_gate",
                    "response_sent": lgpd_prompt_sent,
                }
            )
        response_text, keyboard, _ = await _handle_callback(data, bus, conv, user_id=uid)
        if response_text:
            response_text = strip_emojis(response_text)
            await _react(chat_id, msg_id, "eyes")
            markup = {"inline_keyboard": keyboard} if keyboard else None
            sent = await _send_message(chat_id, response_text, reply_markup=markup)
            status = "ok" if sent else "partial"
            classify_metric_for_status(status, "callback")
            return _finish(
                {
                    "status": status,
                    "chat_id": chat_id,
                    "kind": "callback",
                    "response_sent": sent,
                }
            )
        return _finish({"status": "ignored", "kind": "callback", "chat_id": chat_id})
    raw_first_word = text.strip().split()[0].lower().split("@")[0] if text.strip() else ""
    if text.startswith("/") or raw_first_word in (
        "start",
        "menu",
        "agendar",
        "protocolo",
        "humano",
        "cancelar",
        "lgpd",
    ):
        cmd = raw_first_word if raw_first_word.startswith("/") else f"/{raw_first_word}"
        if cmd == "/start" and bus and not has_lgpd_consent:
            await _handle_command(text, bus, conv, "")
            lgpd_prompt_sent = await _send_lgpd_consent_request(int(chat_id), bus, conv)
            return _finish(
                {
                    "status": "ok" if lgpd_prompt_sent else "partial",
                    "chat_id": chat_id,
                    "kind": "lgpd_prompt",
                    "response_sent": lgpd_prompt_sent,
                }
            )
        if cmd not in ALLOWED_COMMANDS:
            await _react(chat_id, msg_id, "cross")
            markup = {"inline_keyboard": _menu_keyboard()}
            sent = await _send_message(
                chat_id, "Comando nao suportado. Use o menu de opcoes.", reply_markup=markup
            )
            classify_metric_for_status("ignored_command", "command")
            return _finish({"status": "ignored_command", "chat_id": chat_id})
        if bus and not has_lgpd_consent and cmd != "/lgpd":
            lgpd_prompt_sent = await _send_lgpd_consent_request(int(chat_id), bus, conv)
            return _finish(
                {
                    "status": "ok" if lgpd_prompt_sent else "partial",
                    "chat_id": chat_id,
                    "kind": "lgpd_gate",
                    "response_sent": lgpd_prompt_sent,
                }
            )
        bump_metric("commands_handled")
        # /voz → MiniMax TTS da ultima resposta do bot no historico
        if cmd == "/voz":
            hist = await _hist_get(bus, conv)
            last_bot = ""
            for h in reversed(hist):
                if h.lower().startswith("bot:"):
                    last_bot = h[4:].strip()
                    break
            if not last_bot:
                sent = await _send_message(
                    chat_id,
                    "Ainda nao ha resposta para narrar.\n\n"
                    "Faca uma pergunta primeiro; depois digite /voz.",
                )
                return _finish(
                    {
                        "status": "ok" if sent else "partial",
                        "chat_id": chat_id,
                        "kind": "command",
                        "response_sent": sent,
                    }
                )
            from app.services.cartorio_agent import minimax_tts_mp3

            mp3 = await minimax_tts_mp3(last_bot)
            if mp3:
                ok = await _send_voice_bytes(
                    chat_id, mp3, caption="Agent Cartorio (MiniMax Speech)"
                )
                classify_metric_for_status("ok" if ok else "partial", "command")
                return _finish(
                    {
                        "status": "ok" if ok else "partial",
                        "chat_id": chat_id,
                        "kind": "voice_tts",
                        "response_sent": ok,
                    }
                )
            sent = await _send_message(
                chat_id,
                "Nao consegui gerar o audio agora (TTS MiniMax).\n"
                "Texto da ultima resposta:\n\n" + last_bot[:800],
            )
            return _finish(
                {
                    "status": "ok" if sent else "partial",
                    "chat_id": chat_id,
                    "kind": "command",
                    "response_sent": sent,
                }
            )
        response_text, keyboard = await _handle_command(text, bus, conv, "")
        if response_text:
            response_text = format_bot_outbound(response_text)
            markup = {"inline_keyboard": keyboard} if keyboard else None
            sent = await _send_message(chat_id, response_text, reply_markup=markup)
            status = "ok" if sent else "partial"
            classify_metric_for_status(status, "command")
            return _finish(
                {
                    "status": status,
                    "chat_id": chat_id,
                    "kind": "command",
                    "response_sent": sent,
                }
            )

    # Free text: prefer SYNC path for mid-flow states (data/hora/protocolo/HITL)
    # so group multi-step flows don't wait debounce 3s.
    # FIX 2026-07-09: NAO aplicar rate limit no mid-flow — cliente manda
    # data+hora em <5s e o rate limit engolia a conversa (rate_limited:true
    # sem processar). Rate limit fica so no free-text IDLE / debounce.
    if bus and not has_lgpd_consent:
        lgpd_text_reply = _normalize_lgpd_text_reply(text_scrubbed)
        if lgpd_text_reply == "accept":
            await _set_lgpd_consent(bus, conv)
            try:
                await bus.client.delete(_lgpd_prompt_key(conv))
            except Exception:
                pass
            sent = await _send_message(
                int(chat_id),
                "Consentimento LGPD confirmado. Pode continuar com o atendimento.",
            )
            return _finish(
                {
                    "status": "ok" if sent else "partial",
                    "chat_id": chat_id,
                    "kind": "lgpd_consent",
                    "response_sent": sent,
                }
            )
        if lgpd_text_reply == "reject":
            await _clear_lgpd_consent(bus, conv)
            await _clear_state(bus, conv)
            try:
                await bus.client.delete(f"tg:hist:{conv}")
            except Exception:
                pass
            try:
                await bus.client.delete(_lgpd_prompt_key(conv))
            except Exception:
                pass
            sent = await _send_message(
                int(chat_id),
                "Consentimento não registrado. Sem autorizacao LGPD, o atendimento por IA "
                "fica desabilitado para esta conversa.",
            )
            return _finish(
                {
                    "status": "ok" if sent else "partial",
                    "chat_id": chat_id,
                    "kind": "lgpd_consent",
                    "response_sent": sent,
                }
            )
        lgpd_prompt_sent = await _send_lgpd_consent_request(int(chat_id), bus, conv)
        return _finish(
            {
                "status": "ok" if lgpd_prompt_sent else "partial",
                "chat_id": chat_id,
                "kind": "lgpd_gate",
                "response_sent": lgpd_prompt_sent,
            }
        )

    if bus:
        st_now = await _get_state(bus, conv)
        if st_now.get("state", STATE_IDLE) != STATE_IDLE:
            response_text, new_state, keyboard = await _handle_state(
                text_scrubbed,
                st_now.get("state", STATE_IDLE),
                st_now.get("data", {}),
                bus,
                conv,
                user_id=uid,
            )
            if response_text:
                if new_state == STATE_IDLE:
                    await _clear_state(bus, conv)
                response_text = format_bot_outbound(response_text)
                markup = {"inline_keyboard": keyboard} if keyboard else None
                sent = await _send_message(chat_id, response_text, reply_markup=markup)
                if sent:
                    await _react(chat_id, msg_id, "check")
                classify_metric_for_status("ok" if sent else "partial", "state")
                return _finish(
                    {
                        "status": "ok" if sent else "partial",
                        "chat_id": chat_id,
                        "kind": "state",
                        "response_sent": sent,
                    }
                )

    if not bus:
        # Fallback SINCRONO degraded (G9/A4 2026-07-20): alcancado quando o
        # Redis falhou de forma comprovada (get_bus levantou acima). Antes era
        # codigo morto, porque get_bus() nunca retornava None.
        if not await _check_rate_limit(bus, conv):
            logger.info("TG rate limit key=%s", conv)
            return _finish(
                {
                    "status": "ok",
                    "chat_id": chat_id,
                    "rate_limited": True,
                    "degraded": True,
                }
            )
        state_obj = await _get_state(bus, conv)
        state = state_obj.get("state", STATE_IDLE)
        state_data = state_obj.get("data", {})
        response_text = ""
        keyboard = None
        if state != STATE_IDLE:
            response_text, new_state, keyboard = await _handle_state(
                text_scrubbed, state, state_data, bus, conv, user_id=uid
            )
            if response_text and new_state == STATE_IDLE:
                await _clear_state(bus, conv)
        if not response_text:
            response_text, keyboard = await _call_cartorio_agent(
                text_scrubbed, bus, conv, chat_id=int(chat_id), attachments=attachments
            )
            if not response_text:
                response_text = (
                    "Pode me dizer em linguagem natural o que precisa, "
                    "ou digitar /menu se quiser atalhos."
                )
                keyboard = None
        response_text = format_bot_outbound(response_text)
        markup = {"inline_keyboard": keyboard} if keyboard else None
        sent = await _send_message(chat_id, response_text, reply_markup=markup)
        if sent:
            await _react(chat_id, msg_id, "check")
        return _finish(
            {
                "status": "ok" if sent else "partial",
                "chat_id": chat_id,
                "kind": "agent",
                "response_sent": sent,
                "degraded": True,
            }
        )

    # FIX 2026-07-20 (G9/A3): secao critica de enqueue/lock NUNCA pode derrubar
    # o webhook com 5xx (Telegram faz retry infinito). Qualquer falha aqui
    # (ex. Redis caindo no meio do request) vira 200 {"status": "degraded"}.
    lock_key = f"tg:lock:{conv}"
    try:
        await _enqueue_message(bus, conv, text_scrubbed, msg_id, attachments=attachments)
        await _react(chat_id, msg_id, "eyes")
        has_lock = await bus.client.get(lock_key)
        if not has_lock:
            await bus.client.set(lock_key, "1", ex=5)
            bump_metric("scheduled_debounce")
            # G9.S2.T3: 1 debounce agendado por janela (nao por mensagem)
            store.inc_telegram_debounce_scheduled()
            from_user = message.get("from", {}) or {}
            # G9/A5: metadata chaveada por conv (mesma chave da fila/lock).
            _DEBOUNCE_METADATA[conv] = {
                "user_id": uid,
                "username": from_user.get("username"),
                "first_name": from_user.get("first_name"),
                "last_name": from_user.get("last_name"),
            }
            # Perfil imediato (mesmo sem debounce longo)
            await _client_profile_upsert(
                bus,
                conv,
                user_id=uid,
                chat_id=chat_id,
                username=from_user.get("username"),
                first_name=from_user.get("first_name"),
                last_name=from_user.get("last_name"),
            )
            background_tasks.add_task(
                _process_telegram_debounce,
                chat_id,
                conv,
            )
            logger.info("TG scheduled background debounce chat=%s conv=%s", chat_id, conv)
            classify_metric_for_status("ok", "debounce")
            return _finish({"status": "ok", "chat_id": chat_id, "scheduled": True})
        return _finish({"status": "ok", "chat_id": chat_id, "accumulated": True})
    except Exception as exc:
        logger.exception("TG enqueue/lock failed chat=%s conv=%s: %s", chat_id, conv, exc)
        bump_metric("enqueue_degraded")
        return _finish({"status": "degraded", "chat_id": chat_id, "reason": "enqueue_failed"})


@router.get("/webhook/info")
async def telegram_webhook_info() -> dict:
    """Consulta o webhook usando a API canônica do Telegram com TLS verificado."""
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    try:
        client = _get_tg_pool()
        resp = await client.get(url)
        return resp.json()
    except Exception as exc:
        logger.exception("TG webhook/info failed: %s", exc)
        return {"ok": False, "error": str(exc)}


@router.post("/set-commands")
async def telegram_set_commands(
    _api_key: str = Depends(require_cartorio_api_key),
) -> dict:
    """Registra menu de comandos do bot (start/menu/humano/cancelar).

    FIX 2026-07-09: usava AsyncClient sem Host header no IP 149.154.166.110
    → SSL/roteamento falhava e endpoint retornava 500.
    """
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/setMyCommands"
    try:
        client = _get_tg_pool()
        resp = await client.post(url, json={"commands": BOT_COMMANDS})
        body = resp.json()
        if resp.status_code != 200 or not body.get("ok", True):
            logger.warning("TG setMyCommands %s: %s", resp.status_code, body)
        return body
    except Exception as exc:
        logger.exception("TG set-commands failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# URL publica do webhook (G9/A2 2026-07-20): configuravel via settings/env
# TELEGRAM_WEBHOOK_URL. O fallback preserva o dominio de prod atual.
TELEGRAM_WEBHOOK_URL_DEFAULT = "https://api.2notasudi.com.br/api/v1/telegram/webhook"


async def sync_telegram_webhook() -> dict:
    """Sincroniza setWebhook na Telegram API com secret_token e allowed_updates (FIX 2026-07-20).

    G9/A1 (2026-07-20): NUNCA registra o webhook sem secret_token. Um worker
    que subisse sem TELEGRAM_WEBHOOK_SECRET derrubava a verificacao de secret
    das demais replicas (tempestade 401). Nesse caso aborta com warning.
    G9/A2: URL via settings/env TELEGRAM_WEBHOOK_URL (sem hardcode).
    """
    if not TELEGRAM_BOT_TOKEN:
        return {"ok": False, "reason": "TELEGRAM_BOT_TOKEN not configured"}
    if not TELEGRAM_WEBHOOK_SECRET:
        logger.warning(
            "TG sync_telegram_webhook ABORT: TELEGRAM_WEBHOOK_SECRET vazio — "
            "webhook NAO sera registrado sem secret_token (protege demais replicas)"
        )
        return {"ok": False, "reason": "TELEGRAM_WEBHOOK_SECRET not configured"}
    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    webhook_url = (
        getattr(settings, "telegram_webhook_url", None)
        or os.environ.get("TELEGRAM_WEBHOOK_URL")
        or TELEGRAM_WEBHOOK_URL_DEFAULT
    )
    payload: dict[str, Any] = {
        "url": webhook_url,
        "allowed_updates": [
            "message",
            "edited_message",
            "callback_query",
            "my_chat_member",
            "poll_answer",
        ],
        "drop_pending_updates": False,
        "secret_token": TELEGRAM_WEBHOOK_SECRET,
    }
    try:
        client = _get_tg_pool()
        resp = await client.post(url, json=payload, timeout=10.0)
        body = resp.json()
        logger.info(
            "TG sync_telegram_webhook ok=%s desc=%s", body.get("ok"), body.get("description")
        )
        return body
    except Exception as exc:
        logger.warning("TG sync_telegram_webhook failed: %s", exc)
        return {"ok": False, "error": str(exc)}


@router.post("/set-webhook")
async def telegram_set_webhook(
    _api_key: str = Depends(require_cartorio_api_key),
) -> dict:
    """Configura/sincroniza o webhook do Telegram com secret_token e allowed_updates."""
    return await sync_telegram_webhook()


def _verify_telegram_secret(secret_token_header: str | None) -> None:
    if not TELEGRAM_WEBHOOK_SECRET:
        return
    # E3.06: 401 do webhook vira serie observavel (anti brute-force/scan).
    from app.services.metrics import store

    if not secret_token_header:
        store.inc_webhook_auth_failures("telegram")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing secret token")
    # O Telegram envia o secret_token de forma estática em texto claro.
    # Comparamos usando hmac.compare_digest para segurança contra timing attacks.
    if not hmac.compare_digest(secret_token_header.encode(), TELEGRAM_WEBHOOK_SECRET.encode()):
        store.inc_webhook_auth_failures("telegram")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret token")


__all__ = ["router", "TELEGRAM_BOT_TOKEN", "sync_telegram_webhook"]

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
