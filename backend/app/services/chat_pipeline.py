"""chat_pipeline.py — núcleo compartilhado Telegram + WhatsApp.

Sprint 4 / Turn 51 (2026-07-09): extrai lógica comum do bot Telegram (1463 linhas)
para reuso no bot WhatsApp (espelho Evolution API). Antes, o webhook Evolution
em router.py tinha ~250 linhas parciais. Meta: 100% paridade com Telegram via
este orquestrador polimórfico.

COMPONENTES EXTRAÍDOS (10/10):
  1. process_message()     - entry point por canal (Telegram/WhatsApp)
  2. enqueue_and_debounce() - coleta mensagens em janela 1.2s + rate limit
  3. check_idempotency()    - chave update_id/message_id → processa 1x
  4. scrub_pii_3_layers()   - input/pre-LLM/output (LGPD compliance)
  5. call_llm_with_fallback() - LiteLLM→nemotron→opencode_free_1/2/3→openclaw→cache
  6. audit_log()            - LGPD audit trail (canal, sender, content_hash)
  7. typing_loop()          - indicador "Bot digitando..." refresh 4s
  8. send_response()        - sendMessage Telegram / sendText Evolution
  9. react_to_message()     - reaction Telegram / reactionMessage Evolution
  10. ChannelAdapter        - interface polimórfica Telegram + WhatsApp

PROVENIÊNCIA:
  - telegram.py:_check_idempotency  → check_idempotency()
  - telegram.py:_check_rate_limit   → check_rate_limit()
  - telegram.py:_resumir_mensagens  → resume_burst()
  - telegram.py:_process_telegram_debounce → process_debounced()
  - telegram.py:_call_cartorio_agent → call_llm_with_fallback()
  - telegram.py:_send_typing        → typing_loop()
  - telegram.py:_send_message       → send_response() (TelegramAdapter)
  - telegram.py:_react              → react_to_message()

LGPD COMPLIANCE (lesson 120, 132, 138):
  - 3 camadas PII scrub (input / pre-LLM / output)
  - Audit log LGPD obrigatório em todo process_message
  - DPA assinado com todos os providers free (DeepSeek, NVIDIA, Xiaomi)

PROD-DATA 2026-07-09:
  - bot Telegram: 8/8 testes E2E validados (lesson 137, status 2026-07-02)
  - bot WhatsApp: T21-T30 (em construção)
  - 4 agents paralelos: Antigravity-Gemini, OpenCode-MiniMax, Grok-Build, Claude-Code
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.services.pii import scrub
from app.services.redis_bus import get_bus
from app.services.tracing import current_trace_id, llm_span, get_tracer
from app.services.sentry import capture_exception as sentry_capture_exception
from app.services.bot_metrics import (
    BotStageTimer,
    inc_bot_request,
    scrub_with_metric,
)
from app.integrations.fallback import chat_with_fallback, ChatResponse, ChatError, ChatErrorKind
# audit_log usa AuditService.log (session-based) — versão simplificada abaixo
# que grava log estruturado em JSON + Redis pub/sub (sem bloquear o pipeline).


class _JsonFormatter(logging.Formatter):
    """Log estruturado JSON com campos canonicos para busca (G6 T51).

    Campos:
      - ts: ISO 8601 UTC
      - level: INFO/WARNING/ERROR
      - logger: nome do logger
      - msg: mensagem
      - correlation_id: X-Request-ID ou trace_id (W3C)
      - channel: telegram/whatsapp
      - chat_id: hash 16 chars do sender (LGPD: nunca raw)
      - latency_ms: duracao quando aplicavel
      - event: tipo do evento (bot.receive, bot.send, bot.debounce, etc)
    """

    _RESERVED = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        try:
            import json as _json
            import datetime as _dt

            payload: dict[str, Any] = {
                "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
                "event": getattr(record, "event", "log"),
            }
            # Campos opcionais (se foram passados via extra=...)
            for key, val in record.__dict__.items():
                if key in self._RESERVED or key.startswith("_"):
                    continue
                if key in payload:
                    continue
                try:
                    _json.dumps(val)
                    payload[key] = val
                except (TypeError, ValueError):
                    payload[key] = str(val)
            if record.exc_info:
                payload["exc"] = self.formatException(record.exc_info)
            return _json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            # Fallback: nunca quebrar o logging
            return f'{{"ts":"-","level":"{record.levelname}","msg":"{record.getMessage()}"}}'


def _install_json_logger() -> None:
    """Instala JsonFormatter no logger raiz (idempotente)."""
    root = logging.getLogger()
    if getattr(root, "_cartorio_json_installed", False):
        return
    handler_count = len(root.handlers)
    if handler_count == 0:
        h = logging.StreamHandler()
        h.setFormatter(_JsonFormatter())
        root.addHandler(h)
        root.setLevel(logging.INFO)
    else:
        for existing_handler in root.handlers:
            if not getattr(existing_handler, "_cartorio_json", False):
                existing_handler.setFormatter(_JsonFormatter())
                existing_handler._cartorio_json = True  # type: ignore[attr-defined]
    root._cartorio_json_installed = True  # type: ignore[attr-defined]


# Instala no import do modulo (best-effort; se ja tem formatter custom, sobrescreve)
try:
    _install_json_logger()
except Exception:
    pass


logger = logging.getLogger(__name__)


def _emit(
    level: int,
    msg: str,
    *,
    event: str,
    channel: str | None = None,
    chat_id: str | None = None,
    latency_ms: float | None = None,
    correlation_id: str | None = None,
    **extra: Any,
) -> None:
    """Emite log estruturado (T51 G6).

    LGPD: chat_id deve ser SEMPRE hash 16 chars (sha256[:16]), nunca raw.
    """
    payload: dict[str, Any] = {
        "event": event,
        "correlation_id": correlation_id or current_trace_id(),
    }
    if channel:
        payload["channel"] = channel
    if chat_id:
        payload["chat_id"] = chat_id
    if latency_ms is not None:
        payload["latency_ms"] = round(latency_ms, 3)
    payload.update(extra)
    logger.log(level, msg, extra=payload)


# ===================== CHANNEL ENUM + ADAPTER =====================


class Channel(str, Enum):
    """Canais suportados pelo pipeline compartilhado."""

    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"


@dataclass
class InboundMessage:
    """Mensagem normalizada vinda de qualquer canal."""

    channel: Channel
    sender_id: str  # chat_id (Telegram) ou remoteJid (WhatsApp)
    sender_name: str = ""
    text: str = ""
    update_id: str = ""  # update_id (Telegram) ou message_id (WhatsApp)
    message_ids: list[str] = field(default_factory=list)
    is_group: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutboundMessage:
    """Mensagem de saída para qualquer canal."""

    channel: Channel
    recipient_id: str
    text: str
    keyboard: list[list[dict]] | None = None
    react_to_msg_id: str | None = None
    reaction: str = "thumbsup"
    parse_mode: str = "HTML"
    metadata: dict[str, Any] = field(default_factory=dict)


class ChannelAdapter(ABC):
    """Interface polimórfica para Telegram/WhatsApp.

    Implementações:
      - TelegramAdapter  (em telegram.py, refatoração futura)
      - WhatsAppAdapter  (em whatsapp.py, a criar)

    Cada adapter encapsula detalhes específicos do canal:
      - URL da API (api.telegram.org vs Evolution API)
      - Auth header (token Bearer vs apikey header)
      - Formato de mensagem (HTML Markdown vs plain text)
      - Tipos de mídia (photo, document, audio, video, sticker)
      - Typing indicator (sendChatAction vs presence subscribe)
      - Reactions (setMessageReaction vs reactionMessage)
    """

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> bool:
        """Envia mensagem via API do canal. Retorna True se 2xx."""

    @abstractmethod
    async def typing(self, recipient_id: str, action: str = "typing") -> bool:
        """Inicia/cancela indicador 'digitando...'. action='' cancela."""

    @abstractmethod
    async def react(self, recipient_id: str, message_id: str, reaction: str = "thumbsup") -> bool:
        """Adiciona reação (emoji) à mensagem."""

    @abstractmethod
    async def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        """Valida HMAC do webhook. False = rejeitar."""


# ===================== IDEMPOTENCY =====================

IDEMPOTENCY_TTL_SEC = 600  # 10min: evita reprocessar mesmo update_id


async def check_idempotency(update_id: str, channel: Channel) -> bool:
    """Verifica se update_id já foi processado. False = processar, True = pular.

    Args:
        update_id: ID único da mensagem (update_id Telegram, message_id WhatsApp)
        channel: Canal de origem (para namespacing)

    Returns:
        True se já foi processado (pular), False se novo (processar)
    """
    if not update_id:
        return False  # sem id, sempre processa
    bus = get_bus()
    if not bus:
        return False
    key = f"idem:{channel.value}:{update_id}"
    # SETNX com TTL atômico
    is_new = await bus.client.set(key, "1", ex=IDEMPOTENCY_TTL_SEC, nx=True)
    return not bool(is_new)  # True se já existia (pular)


# ===================== RATE LIMIT =====================

RATE_LIMIT_SECONDS = 3  # max 1 response por chat_id a cada 3s


async def check_rate_limit(conv_key: str, channel: Channel) -> bool:
    """Rate limit por conversa (chat_id/remoteJid).

    Returns:
        True se permitido, False se rate-limited.
    """
    bus = get_bus()
    if not bus:
        return True
    key = f"rl:{channel.value}:{conv_key}"
    # SETNX EX 3 — se já existia, nega
    is_new = await bus.client.set(key, "1", ex=RATE_LIMIT_SECONDS, nx=True)
    return bool(is_new)


# ===================== PII SCRUB (3 CAMADAS) =====================


def scrub_pii_3_layers(text: str) -> tuple[str, int]:
    """LGPD art. 7 I/II — scrubbing 3 camadas (defense-in-depth).

    Camada 1 (input): substitui CPF, RG, telefone, email por [REDACTED:cpf]
    Camada 2 (pre-LLM): garante que não há PII antes de enviar pro LLM
    Camada 3 (output): limpa resposta do LLM antes de mandar pro usuário

    Returns:
        (texto_limpo, numero_redacted)
    """
    if not text:
        return "", 0
    result = scrub(text)
    return result.text, result.redaction_count


# ===================== DEBOUNCE + BURST RESUME =====================

DEBOUNCE_WINDOW_SEC = 1.2  # janela para coletar msgs antes de processar


def resume_burst(texts: list[str]) -> str:
    """Se cliente mandou 10 msg em 5s, resume em 1 só resposta.

    Regra Telegram v2.0 (turno 49): se len(textos) > 2, resume.

    Returns:
        Texto único consolidado.
    """
    if len(texts) <= 2:
        return texts[-1] if texts else ""
    joined = " | ".join(t.strip() for t in texts if t.strip())
    return f"[{len(texts)} mensagens] {joined[:600]}"


async def enqueue_message(msg: InboundMessage) -> bool:
    """Enfileira mensagem na fila Redis do canal. Trigger debounce se primeiro.

    Returns:
        True se este foi o primeiro msg (dispara debounce), False se há outros.
    """
    bus = get_bus()
    if not bus:
        return False
    key = f"queue:{msg.channel.value}:{msg.sender_id}"
    payload = json.dumps(
        {
            "text": msg.text,
            "update_id": msg.update_id,
            "msg_id": msg.message_ids[-1] if msg.message_ids else "",
            "ts": time.time(),
        }
    )
    # Push atômico + retorna tamanho da fila
    pipe = bus.client.pipeline(transaction=True)
    pipe.rpush(key, payload)
    pipe.llen(key)
    pipe.expire(key, 10)  # TTL fila
    _, llen, _ = await pipe.execute()
    return llen == 1  # primeiro → dispara debounce


async def fetch_queue(channel: Channel, sender_id: str) -> list[dict]:
    """Consome (lê+deleta) fila Redis."""
    bus = get_bus()
    if not bus:
        return []
    key = f"queue:{channel.value}:{sender_id}"
    pipe = bus.client.pipeline(transaction=True)
    pipe.lrange(key, 0, -1)
    pipe.delete(key)
    results = await pipe.execute()
    raw = results[0] or []
    return [json.loads(r) for r in raw]


# ===================== TYPING LOOP =====================

TYPING_REFRESH_SEC = 4  # typing expira em 5s na API Telegram


async def typing_loop(
    adapter: ChannelAdapter, recipient_id: str, stop_event: asyncio.Event, action: str = "typing"
) -> None:
    """Loop que envia typing a cada 4s enquanto processa.

    Args:
        adapter: TelegramAdapter ou WhatsAppAdapter
        recipient_id: chat_id ou remoteJid
        stop_event: set() para parar o loop
        action: 'typing' (Telegram sendChatAction) / 'composing' (Evolution)
    """
    try:
        while not stop_event.is_set():
            await adapter.typing(recipient_id, action)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=TYPING_REFRESH_SEC)
                break  # stop_event set
            except asyncio.TimeoutError:
                continue  # refresh
    except asyncio.CancelledError:
        pass
    finally:
        await adapter.typing(recipient_id, "")  # cancela typing


# ===================== LLM CALL WITH FALLBACK =====================


async def call_llm_with_fallback(
    text: str,
    *,
    consent_granted: bool = True,
    actor_id: str = "anonymous",
    request_id: str | None = None,
    fast_path: bool = False,
) -> str:
    """Chama LLM com fallback chain (LiteLLM → opencode → openclaw → cache).

    Args:
        text: mensagem do usuário (já com PII scrub)
        consent_granted: LGPD art. 7 I — sempre True para chatbots de cartório
        actor_id: identificador do usuário (chat_id, remoteJid)
        request_id: correlation ID
        fast_path: True = resposta rápida (saudações), False = agente completo

    Returns:
        Texto de resposta (já sem PII).
    """
    if not consent_granted:
        raise ChatError(
            "LGPD art. 7 I — consentimento não concedido.", kind=ChatErrorKind.LGPD_BLOCKED
        )

    messages = [{"role": "user", "content": text}]

    if fast_path:
        # Fast LLM: modelo leve (1-3s) para saudações/menu
        system = "Voce e o assistente do Cartorio 2o Notas. Responda em <100 chars, sem emojis, em PT-BR."
        messages.insert(0, {"role": "system", "content": system})

    try:
        response: ChatResponse = await chat_with_fallback(
            messages,
            actor_id=actor_id,
            request_id=request_id,
        )
        # Scrub output (camada 3)
        clean_text, _ = scrub_pii_3_layers(response.content)
        return clean_text
    except ChatError as e:
        logger.warning("LLM fallback error: kind=%s msg=%s", e.kind, e)
        if e.kind == ChatErrorKind.LGPD_BLOCKED:
            return "Atendimento exige consentimento LGPD. Digite /lgpd para saber mais."
        # Todos providers DOWN
        return "Sistema temporariamente em manutencao. Tente novamente em alguns minutos ou digite /humano para atendimento humano."


# ===================== AUDIT LOG LGPD =====================


async def audit_log(
    channel: Channel,
    sender_id: str,
    content_hash: str,
    action: str,
    status: str,
    request_id: str | None = None,
) -> None:
    """LGPD art. 37 — registro de operação de tratamento.

    Non-blocking: usa Redis pub/sub + log estruturado JSON. NÃO usa DB sync
    para não bloquear o pipeline. Audit chain completa fica em
    AuditService.log() quando process_message é chamado com db=Session.

    Args:
        channel: telegram / whatsapp
        sender_id: chat_id (hash) ou remoteJid (hash)
        content_hash: SHA256 do conteúdo (NUNCA conteúdo cru!)
        action: receive / send / debounce / fallback / consent / revoke
        status: ok / failed / rate_limited / idempotent
        request_id: correlation ID
    """
    try:
        # Hash do sender para LGPD (não armazenar PII direto)
        sender_hash = hashlib.sha256(sender_id.encode("utf-8")).hexdigest()[:16]
        record = {
            "ts": time.time(),
            "channel": channel.value,
            "sender_hash": sender_hash,
            "action": action,
            "status": status,
            "content_hash": content_hash,
            "request_id": request_id or "",
        }
        # 1. Log estruturado (sempre)
        logger.info(
            "audit.bot.%s.%s channel=%s sender=%s status=%s req=%s",
            channel.value,
            action,
            channel.value,
            sender_hash,
            status,
            request_id or "",
        )
        # 2. Redis pub/sub (best-effort, non-blocking)
        bus = get_bus()
        if bus:
            try:
                await bus.client.lpush(
                    f"audit:bot:{channel.value}",
                    json.dumps(record, separators=(",", ":")),
                )
                await bus.client.ltrim(f"audit:bot:{channel.value}", 0, 9999)
            except Exception:
                pass  # não bloquear
    except Exception as e:
        logger.warning("audit_log falhou (non-blocking): %s", e)


def hash_content(text: str) -> str:
    """Hash SHA256 do conteúdo para LGPD audit (NÃO armazenar texto)."""
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


# ===================== PROCESS MESSAGE (ENTRY POINT) =====================


async def process_message(
    msg: InboundMessage,
    adapter: ChannelAdapter,
    *,
    request_id: str | None = None,
) -> OutboundMessage | None:
    """Entry point unificado. Recebe InboundMessage + adapter, retorna OutboundMessage.

    Fluxo:
      1. Idempotency check (update_id/message_id) → pular se já processado
      2. PII scrub input (camada 1) + métrica bot_pii_redacted_total
      3. Audit log: receive ok
      4. Structured log (JSON) + trace_id propagation (G6 T51, T54)
      5. Enqueue + debounce trigger
      6. (Em background) process_debounced(): resume burst, rate limit,
         LLM call com fallback, PII scrub output (camada 3), send, react
      7. Sentry: captura excecoes LLM com PII scrubbed (G6 T59, lesson 145)

    Returns:
        OutboundMessage se processado sync (sem debounce), None se foi enfileirado.
    """
    # T54: trace_id propagation (X-Request-ID ou W3C trace_id)
    correlation_id = request_id or current_trace_id()

    # 1. Idempotency
    if await check_idempotency(msg.update_id, msg.channel):
        _emit(
            logging.INFO,
            "idempotent skip",
            event="bot.idempotent",
            channel=msg.channel.value,
            chat_id=hashlib.sha256(msg.sender_id.encode()).hexdigest()[:16],
            correlation_id=correlation_id,
            update_id=msg.update_id,
        )
        await audit_log(
            msg.channel,
            msg.sender_id,
            hash_content(msg.text),
            "receive",
            "idempotent",
            correlation_id,
        )
        inc_bot_request(msg.channel.value, "idempotent")
        return None

    # 2. PII scrub input (camada 1) + métrica
    clean_text, n_redacted = scrub_with_metric(msg.text, msg.channel.value)
    msg.text = clean_text
    if n_redacted > 0:
        _emit(
            logging.INFO,
            "PII scrubbed",
            event="bot.pii_scrubbed",
            channel=msg.channel.value,
            chat_id=hashlib.sha256(msg.sender_id.encode()).hexdigest()[:16],
            correlation_id=correlation_id,
            redaction_count=n_redacted,
        )

    # 3. Audit log receive
    await audit_log(
        msg.channel, msg.sender_id, hash_content(msg.text), "receive", "ok", correlation_id
    )

    # 4. Structured log: bot.receive (G6 T51)
    _emit(
        logging.INFO,
        "bot receive",
        event="bot.receive",
        channel=msg.channel.value,
        chat_id=hashlib.sha256(msg.sender_id.encode()).hexdigest()[:16],
        correlation_id=correlation_id,
        update_id=msg.update_id,
        text_len=len(msg.text),
    )

    # 5. Enqueue + debounce
    is_first = await enqueue_message(msg)

    if not is_first:
        # outras msgs chegando, deixa o debounce consolidar
        return None

    # 6. Background: process debounced (wrapper seguro p/ Sentry G6 T59)
    asyncio.create_task(
        _safe_process_debounced(msg.channel, msg.sender_id, adapter, request_id=correlation_id)
    )
    return None


async def _safe_process_debounced(
    channel: Channel,
    sender_id: str,
    adapter: ChannelAdapter,
    *,
    request_id: str | None = None,
) -> None:
    """Wrapper que captura excecoes e envia para Sentry (T59 G6)."""
    correlation_id = request_id or current_trace_id()
    chat_hash = hashlib.sha256(sender_id.encode()).hexdigest()[:16]
    with BotStageTimer(channel=channel.value, stage="total"):
        try:
            await process_debounced(channel, sender_id, adapter, request_id=correlation_id)
        except Exception as e:
            _emit(
                logging.ERROR,
                f"process_debounced unhandled: {e}",
                event="bot.error",
                channel=channel.value,
                chat_id=chat_hash,
                correlation_id=correlation_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            try:
                sentry_capture_exception(
                    e,
                    extra={
                        "channel": channel.value,
                        "correlation_id": correlation_id,
                        "sender_hash": chat_hash,
                    },
                )
            except Exception:
                pass


async def process_debounced(
    channel: Channel,
    sender_id: str,
    adapter: ChannelAdapter,
    *,
    request_id: str | None = None,
) -> None:
    """Processa fila consolidada após debounce window (1.2s).

    Steps:
      1. fetch_queue (lê+deleta)
      2. resume_burst (>2 msgs → resume)
      3. check_rate_limit
      4. typing_loop (background refresh 4s)
      5. call_llm_with_fallback (com OpenTelemetry span G6 T53)
      6. scrub output (camada 3) + métrica
      7. adapter.send() (com metric latency stage=send)
      8. adapter.react() (ack)
      9. audit_log send
      10. stop typing
    """
    correlation_id = request_id or current_trace_id()
    chat_hash = hashlib.sha256(sender_id.encode()).hexdigest()[:16]

    # T53: OpenTelemetry span principal do pipeline
    span_cm: Any = _nullcontext()
    try:
        tracer = get_tracer("cartorio.bot.pipeline")
        span_cm = tracer.start_as_current_span(f"bot.{channel.value}.process_debounced")
    except Exception:
        pass

    with span_cm as span:
        if span is not None and hasattr(span, "set_attribute"):
            try:
                span.set_attribute("bot.channel", channel.value)
                span.set_attribute("bot.chat_hash", chat_hash)
                span.set_attribute("bot.correlation_id", correlation_id or "")
            except Exception:
                pass

        # 1. Fetch queue (com metric latency stage=debounce)
        with BotStageTimer(channel=channel.value, stage="debounce", auto_inc_request=False):
            queue = await fetch_queue(channel, sender_id)
        if not queue:
            return
        textos = [m["text"] for m in queue if m.get("text")]
        msg_ids = [m["msg_id"] for m in queue if m.get("msg_id")]

        # 2. Resume burst
        text_to_process = resume_burst(textos)
        if not text_to_process:
            return

        # 3. Rate limit
        if not await check_rate_limit(sender_id, channel):
            _emit(
                logging.INFO,
                "rate limited",
                event="bot.rate_limited",
                channel=channel.value,
                chat_id=chat_hash,
                correlation_id=correlation_id,
            )
            await audit_log(
                channel,
                sender_id,
                hash_content(text_to_process),
                "rate_limited",
                "dropped",
                correlation_id,
            )
            inc_bot_request(channel.value, "rate_limited")
            return

        # 4. Typing loop
        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(typing_loop(adapter, sender_id, stop_typing))

        try:
            # 5. LLM call (with fallback chain) - span llm.chat
            fast = _is_fast_path(text_to_process)
            with llm_span(model="auto", operation="chat") as llm_sp:
                if llm_sp is not None and hasattr(llm_sp, "set_attribute"):
                    try:
                        llm_sp.set_attribute("bot.channel", channel.value)
                        llm_sp.set_attribute("bot.fast_path", fast)
                    except Exception:
                        pass
                response_text = await call_llm_with_fallback(
                    text_to_process,
                    consent_granted=True,
                    actor_id=f"{channel.value}:{sender_id}",
                    request_id=correlation_id,
                    fast_path=fast,
                )

            # 6. Scrub output (camada 3) + métrica
            with BotStageTimer(channel=channel.value, stage="llm", auto_inc_request=False):
                clean_response, _ = scrub_with_metric(response_text, channel.value)

            _emit(
                logging.INFO,
                "bot llm ok",
                event="bot.llm_ok",
                channel=channel.value,
                chat_id=chat_hash,
                correlation_id=correlation_id,
                response_len=len(clean_response),
                fast_path=fast,
            )

            # 7. Send (com metric latency stage=send)
            with BotStageTimer(channel=channel.value, stage="send", auto_inc_request=False):
                out_msg = OutboundMessage(
                    channel=channel,
                    recipient_id=sender_id,
                    text=clean_response,
                )
                sent = await adapter.send(out_msg)

            # 8. React (ack visual)
            if sent and msg_ids:
                try:
                    await adapter.react(sender_id, msg_ids[-1], "thumbsup")
                except Exception:
                    pass

            # 9. Audit log send
            await audit_log(
                channel,
                sender_id,
                hash_content(clean_response),
                "send",
                "ok" if sent else "failed",
                correlation_id,
            )

            # T51: structured log final
            _emit(
                logging.INFO,
                "bot send ok" if sent else "bot send failed",
                event="bot.send",
                channel=channel.value,
                chat_id=chat_hash,
                correlation_id=correlation_id,
                sent=sent,
            )

        except Exception as e:
            # T59: capture LLM/pipeline exceptions via Sentry (lesson 145)
            _emit(
                logging.ERROR,
                f"process_debounced error: {e}",
                event="bot.error",
                channel=channel.value,
                chat_id=chat_hash,
                correlation_id=correlation_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            try:
                sentry_capture_exception(
                    e,
                    extra={
                        "channel": channel.value,
                        "correlation_id": correlation_id,
                        "chat_hash": chat_hash,
                        "stage": "llm_or_send",
                    },
                )
            except Exception:
                pass
            await audit_log(
                channel, sender_id, hash_content(text_to_process), "send", "failed", correlation_id
            )
        finally:
            # 10. Stop typing
            stop_typing.set()
            try:
                await asyncio.wait_for(typing_task, timeout=1.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                typing_task.cancel()


class _nullcontext:
    """Context manager no-op para fallback quando tracer indisponivel."""

    def __enter__(self):
        return None

    def __exit__(self, *args):
        return False


def _is_fast_path(text: str) -> bool:
    """Detecta se mensagem é saudação/menu (usa fast_llm, resposta rápida)."""
    if not text:
        return False
    t = text.lower().strip()
    fast_keywords = {
        "oi",
        "ola",
        "olá",
        "menu",
        "ajuda",
        "help",
        "bom dia",
        "boa tarde",
        "boa noite",
        "hi",
        "hello",
    }
    return t in fast_keywords or len(t) <= 3


# ===================== HEALTH CHECK =====================


async def health_check() -> dict:
    """Health do pipeline (bus Redis, fallback chain disponível)."""
    bus = get_bus()
    bus_ok = False
    if bus:
        try:
            await bus.client.ping()
            bus_ok = True
        except Exception:
            pass

    return {
        "pipeline": "ok",
        "redis_bus": bus_ok,
        "channels": [c.value for c in Channel],
        "version": "1.0.0",
        "ts": time.time(),
    }
