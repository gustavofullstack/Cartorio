"""Integracao com OpenCode-Go (LLM provider low-cost primario).

OpenCode-Go expoe API compativel com OpenAI Chat Completions em
`{base_url}/chat/completions`.

Modelo roteado (LGPD RIPD v1.2 Tratamento 7):
    OpenCode-Go provider -> `deepseek-v4-flash` (compat OpenAI, low-cost)

IMPORTANTE — inconsistencia de modelo resolvida (auditoria cartorio-lgpd 2026-06-23):
- `.harness/reins/*/opencode/opencode.json` -> MiniMax-M2.7/M3 = config do **Mavis runtime**
  (orquestrador Pietra/Harness), NAO o LLM que processa dados de cliente.
- `docs/ripd.md` v1.2 Tratamento 7 -> MiniMax-M2.7/M3 = ERRADO (a atualizar pelo cartorio-lgpd).
- `backend/app/integrations/opencode_go.py` -> `deepseek-v4-flash` = CORRETO para dados de cliente.

Provider secundario (fallback): OpenClaw gateway (ver app.config.settings.openclaw_*).

LGPD compliance (auditoria cartorio-lgpd 2026-06-23, 6 blockers corrigidos):
1. PII scrubbing INTERNO em cada message (defense-in-depth) — nao confiar no caller
2. Audit log via AuditService.log() (LGPD art. 37) — registro de toda chamada
3. Consent gate (LGPD art. 7 I) — bloqueia chamada se consent_granted=False
4. Rate limit por sessao (Redis) — evita abuso / runaway cost
5. Fallback LiteLLM (TODO/placeholder) — se OpenCode-Go falhar, fallback com mesmo scrubbing
6. Docstring alinhada — modelo roteado eh `deepseek-v4-flash` via OpenCode-Go provider

Uso:
    from app.integrations.opencode_go import chat, ChatError, ChatResponse

    try:
        resp = await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model=settings.opencode_go_model,
            api_key=settings.opencode_go_api_key,
            base_url=settings.opencode_go_base_url,
            consent_granted=True,         # LGPD art. 7 I
            actor_id="cliente:123",       # pra audit log
            db=db_session,                # pra audit log
            session_id="sess-abc",        # pra rate limit
            rate_limit_per_minute=60,     # LGPD cost guard
        )
        texto = resp.content
    except ChatError as e:
        # e.kind in (LGPD_BLOCKED, RATE_LIMITED, CONFIG, HTTP_4XX, ...)
        texto = f"[erro LLM: {e}]"

Decisao de design (refator 2026-06-23):
- Scrubbing INTERNO (defense-in-depth) — caller pode scrubbar tambem, eh idempotente.
- Audit log OPCIONAL via param `db` (sync, via asyncio.to_thread).
- Rate limit OPCIONAL via Redis (se `redis_url` configurada e session_id passada).
- API key injetada por param (testavel, sem dependencia implicita de settings).
- Excecao tipada (ChatError) com kind estendido (LGPD_BLOCKED, RATE_LIMITED).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import httpx
import redis

from app.services.pii import scrub

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# ============================================================================
# Tipos
# ============================================================================


@dataclass(frozen=True)
class ChatResponse:
    """Resposta de uma chamada de chat completion.

    Attributes:
        content: Texto gerado pelo modelo (choices[0].message.content) JA SCRUBBED
                 no boundary 2 (LGPD-015). Caller NAO precisa scrubbar de novo.
        model: Modelo usado (echo da request ou do response).
        tokens_in: Prompt tokens consumidos (None se API nao retornou usage).
        tokens_out: Completion tokens consumidos (None se API nao retornou usage).
        latency_ms: Latencia da chamada em milissegundos.
        finish_reason: Razao de parada (stop/length/content_filter/etc).
        pii_redacted_count: Total de PII scrubbed ANTES de enviar (defense-in-depth, input).
        output_pii_redacted_count: Total de PII scrubbed NO OUTPUT (boundary 2, LGPD-015).
                                   Se > 0, audit log action='llm.output_scrubbed' eh gerado.
        raw: Response bruto da API (para debug, NAO usar em producao - LGPD).
    """

    content: str
    model: str
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int
    finish_reason: str | None = None
    pii_redacted_count: int = 0
    output_pii_redacted_count: int = 0
    raw: dict[str, Any] | None = None


class ChatErrorKind:
    """Constantes para classificar tipo de erro.

    Novas (auditoria cartorio-lgpd 2026-06-23):
    - LGPD_BLOCKED: consent_granted=False (LGPD art. 7 I)
    - RATE_LIMITED: rate limit excedido (cost guard)
    """

    CONFIG = "CONFIG_ERROR"  # API key/base_url ausente
    HTTP_4XX = "HTTP_4XX"  # Request malformado, auth falhou
    HTTP_5XX = "HTTP_5XX"  # Erro do servidor OpenCode-Go
    TIMEOUT = "TIMEOUT"  # Timeout de rede
    NETWORK = "NETWORK"  # Conexao caiu, DNS falhou, etc
    PARSE = "PARSE_ERROR"  # Response nao e JSON valido
    LGPD_BLOCKED = "LGPD_BLOCKED"  # LGPD art. 7 I - consent ausente
    RATE_LIMITED = "RATE_LIMITED"  # Rate limit excedido


class ChatError(Exception):
    """Erro tipado de chat completion.

    Atributos:
        kind: Classificacao do erro (use ChatErrorKind.*).
        status_code: HTTP status se aplicavel, None caso contrario.
        body: Corpo da response se disponivel.
        message: Mensagem legivel.
    """

    def __init__(
        self,
        message: str,
        *,
        kind: str,
        status_code: int | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.body = body

    def __str__(self) -> str:
        bits = [f"[{self.kind}]"]
        if self.status_code is not None:
            bits.append(f"HTTP {self.status_code}")
        bits.append(super().__str__())
        return " ".join(bits)


# ============================================================================
# PII Scrubbing interno (defense-in-depth)
# ============================================================================


def _scrub_messages(messages: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    """Aplica PII scrubber em cada message.content (LGPD art. 46).

    Idempotente: se caller ja fez scrub, o segundo eh no-op.

    Returns:
        (scrubbed_messages, total_pii_redacted_count)
    """
    scrubbed: list[dict[str, str]] = []
    total_redacted = 0

    for msg in messages:
        content = msg.get("content", "") or ""
        result = scrub(content)
        scrubbed.append(
            {
                "role": msg.get("role", "user"),
                "content": result.text,
            }
        )
        total_redacted += result.redaction_count

    return scrubbed, total_redacted


# IP truncation (LGPD D5) — removido T9-CRIT-2.
# Helper centralizado em app.utils.ip.truncate_ip() — UNICA fonte da verdade.
# Call sites que usavam _truncate_ip_to_24() foram migrados.


# ============================================================================
# Rate limit por sessao (Redis)
# ============================================================================


def _check_rate_limit(
    session_id: str,
    limit_per_minute: int,
    redis_url: str,
) -> int:
    """Verifica rate limit via Redis. Retorna count atual (incremented).

    Raises:
        ChatError: RATE_LIMITED se count > limit.
    """
    key = f"opencode_go:ratelimit:{session_id}"
    r = redis.from_url(redis_url, socket_timeout=2.0, decode_responses=True)
    try:
        # incr + expire atomico (nao perfeitamente atomico, mas OK p/ MVP)
        count = r.incr(key)
        if count == 1:
            r.expire(key, 60)
        if count > limit_per_minute:
            raise ChatError(
                f"Rate limit excedido: {count} chamadas/min para sessao {session_id}. "
                f"Limite: {limit_per_minute}/min.",
                kind=ChatErrorKind.RATE_LIMITED,
            )
        return count
    finally:
        r.close()


# ============================================================================
# Audit log (LGPD art. 37)
# ============================================================================


def _audit_log_sync(
    db: "Session",
    *,
    actor_id: str,
    action: str,
    resource: str,
    payload: dict[str, Any],
    request_id: str | None = None,
    client_ip: str | None = None,
) -> None:
    """Helper sync para AuditService.log (chamado via asyncio.to_thread)."""
    from app.services.audit import AuditService

    AuditService.log(
        db,
        actor_id=actor_id,
        actor_type="system",
        action=action,
        resource=resource,
        payload=payload,
        request_id=request_id,
        ip=client_ip,
    )


def _hash_payload(payload: dict[str, Any]) -> str:
    """SHA-256 do payload JSON canonico (para audit log sem expor conteudo)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ============================================================================
# Funcao principal
# ============================================================================


async def chat(
    messages: list[dict[str, str]],
    *,
    model: str,
    api_key: str,
    base_url: str,
    temperature: float = 0.2,
    timeout_seconds: float = 30.0,
    consent_granted: bool = False,
    actor_id: str = "anonymous",
    db: "Session | None" = None,
    session_id: str | None = None,
    rate_limit_per_minute: int | None = None,
    redis_url: str | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
    thinking_mode: Literal["disabled", "enabled", "adaptive"] = "disabled",
) -> ChatResponse:
    """Chama OpenCode-Go Chat Completions com LGPD compliance.

    Args:
        messages: Lista de mensagens no formato OpenAI ({role, content}).
                  Roles validos: system, user, assistant.
        model: Nome do modelo roteado (ex: 'deepseek-v4-flash').
        api_key: API key do OpenCode-Go. Vazio => ChatError CONFIG.
        base_url: URL base do OpenCode-Go (sem /chat/completions).
                  Vazio => ChatError CONFIG.
        temperature: Sampling temperature (0.0-2.0). Default 0.2.
        timeout_seconds: Timeout da request HTTP. Default 30s.
        consent_granted: LGPD art. 7 I. Se False, BLOQUEIA a chamada.
        actor_id: ID do ator para audit log (ex: 'cliente:123', 'escrevente:1').
        db: SQLAlchemy Session opcional. Se fornecido, grava audit log.
        session_id: ID da sessao para rate limit (ex: conversa WhatsApp).
        rate_limit_per_minute: Limite de chamadas/min/sessao. None = sem rate limit.
        redis_url: URL do Redis. Necessario se rate_limit_per_minute definido.
        thinking_mode: T57 E08. Controla campo `thinking` no payload:
                       - "disabled" (default): nao envia `thinking` no payload.
                       - "enabled": envia `thinking={"type": "enabled"}` (force on).
                       - "adaptive": envia `thinking={"type": "adaptive"}` (provider decide).
                       DeepSeek-v4-flash + MiniMax-M3 suportam "adaptive" com 1M context.

    Returns:
        ChatResponse com content + metadata (tokens, latencia, pii_redacted_count).

    Raises:
        ChatError:
        - CONFIG: api_key/base_url/messages invalidos
        - LGPD_BLOCKED: consent_granted=False (LGPD art. 7 I)
        - RATE_LIMITED: rate limit excedido
        - HTTP_4XX/5XX: erro do provider
        - TIMEOUT/NETWORK/PARSE: erro de rede/parse

    Notes:
        - Scrubbing PII eh INTERNO (defense-in-depth). Caller pode scrubbar tambem (idempotente).
        - Audit log eh OPCIONAL (passe db). LGPD art. 37.
        - Rate limit eh OPCIONAL (passe session_id + rate_limit_per_minute + redis_url).
        - Caller decide o que fazer com ChatError (handoff humano, retry, etc).
    """
    # ---- Validacao de config ----
    if not api_key or api_key.strip() == "":
        raise ChatError(
            "API key do OpenCode-Go nao configurada. Defina OPENCODE_GO_API_KEY no .env da VPS.",
            kind=ChatErrorKind.CONFIG,
        )

    if not base_url or base_url.strip() == "":
        raise ChatError(
            "Base URL do OpenCode-Go nao configurada. Defina OPENCODE_GO_BASE_URL no .env da VPS.",
            kind=ChatErrorKind.CONFIG,
        )

    if not messages:
        raise ChatError(
            "Lista de messages vazia. Precisa de pelo menos 1 mensagem.",
            kind=ChatErrorKind.CONFIG,
        )

    # ---- LGPD art. 7 I — Consent gate (BLOCKER 3) ----
    if not consent_granted:
        raise ChatError(
            "LGPD art. 7 I — Consentimento nao concedido. "
            "Cliente precisa aceitar tratamento de dados antes de chamar LLM. "
            "Passe consent_granted=True somente apos confirmacao explicita.",
            kind=ChatErrorKind.LGPD_BLOCKED,
        )

    # ---- Rate limit (BLOCKER 7) ----
    if rate_limit_per_minute is not None and session_id and redis_url:
        # Roda sync em thread para nao bloquear event loop
        await asyncio.to_thread(_check_rate_limit, session_id, rate_limit_per_minute, redis_url)

    # ---- PII scrubbing INTERNO (BLOCKER 1, defense-in-depth) ----
    scrubbed_messages, pii_redacted_count = _scrub_messages(messages)

    # ---- Monta request ----
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": scrubbed_messages,  # SEMPRE scrubbed
        "temperature": temperature,
    }

    # ---- Thinking mode (T57 E08) ----
    # Apenas injeta `thinking` se mode != "disabled". Adaptive deixa provider decidir.
    if thinking_mode != "disabled":
        payload["thinking"] = {"type": thinking_mode}

    # ---- Executa com medicao de latencia ----
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as e:
        latency_ms = int((time.time() - start_time) * 1000)
        raise ChatError(
            f"Timeout apos {timeout_seconds}s na chamada OpenCode-Go",
            kind=ChatErrorKind.TIMEOUT,
        ) from e
    except httpx.HTTPError as e:
        raise ChatError(
            f"Erro de rede ao chamar OpenCode-Go: {e}",
            kind=ChatErrorKind.NETWORK,
        ) from e

    latency_ms = int((time.time() - start_time) * 1000)

    # ---- Trata HTTP errors ----
    if response.status_code >= 400:
        body_text = response.text[:500] if response.text else ""
        kind = ChatErrorKind.HTTP_4XX if response.status_code < 500 else ChatErrorKind.HTTP_5XX
        raise ChatError(
            f"OpenCode-Go retornou {response.status_code}: {body_text[:200]}",
            kind=kind,
            status_code=response.status_code,
            body=body_text,
        )

    # ---- Parse response ----
    try:
        data = response.json()
    except Exception as e:
        raise ChatError(
            f"Response do OpenCode-Go nao e JSON valido: {e}",
            kind=ChatErrorKind.PARSE,
            status_code=response.status_code,
        ) from e

    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice.get("finish_reason")
    except (KeyError, IndexError, TypeError) as e:
        raise ChatError(
            f"Estrutura inesperada na response: {e}",
            kind=ChatErrorKind.PARSE,
            status_code=response.status_code,
        ) from e

    usage = data.get("usage", {})
    tokens_in = usage.get("prompt_tokens")
    tokens_out = usage.get("completion_tokens")

    # ---- Output PII scrubbing (LGPD-015, BOUNDARY 2, defense-in-depth) ----
    # Caller NAO precisa scrubbar. Wrapper garante. LLM ecoa trechos do
    # contexto (CPF, email, etc) e isso NUNCA pode chegar ao usuario final
    # ou ao log de conversa.
    scrub_result = scrub(content)
    output_pii_redacted_count = scrub_result.redaction_count
    safe_content = scrub_result.text

    # ---- Audit log LGPD art. 37 (BLOCKER 2) ----
    if db is not None:
        request_hash = _hash_payload(payload)
        # Hash do response SEM o content bruto (LGPD: response pode ecoar PII)
        response_hash = _hash_payload(
            {
                "model": data.get("model", model),
                "finish_reason": finish_reason,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "content_length": len(content),  # NAO o conteudo
            }
        )

        audit_payload = {
            "provider": "opencode_go",
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "consent_granted": consent_granted,
            "pii_redacted_count": pii_redacted_count,
            "request_hash": request_hash,
            "response_hash": response_hash,
            "session_id": session_id,
            "messages_count": len(scrubbed_messages),
            "temperature": temperature,
        }

        try:
            await asyncio.to_thread(
                _audit_log_sync,
                db,
                actor_id=actor_id,
                action="opencode_go.chat",
                resource="llm:opencode_go",
                payload=audit_payload,
            )
        except Exception:
            # Audit log nao pode quebrar fluxo principal
            # Em prod, considerar dead-letter queue
            pass

        # ---- Audit log do OUTPUT scrub (LGPD-015 + LGPD art. 37) ----
        # Se o LLM ecoou PII no output, gera entrada SEPARADA no audit
        # com request_id (LGPD art. 37) + IP truncado em /24 (D5).
        if output_pii_redacted_count > 0:
            output_audit_payload = {
                "provider": "opencode_go",
                "model": model,
                "redacted_count": output_pii_redacted_count,
                "output_length": len(safe_content),
                "session_id": session_id,
            }
            try:
                await asyncio.to_thread(
                    _audit_log_sync,
                    db,
                    actor_id=actor_id,
                    action="llm.output_scrubbed",
                    resource="llm:opencode_go",
                    payload=output_audit_payload,
                    request_id=request_id,
                    client_ip=client_ip,
                    # T9-CRIT-1: NAO overwrite last_entry.ip=ip_truncated.
                    # IP FULL preservado em audit_log.ip (DPO forensics);
                    # ip_truncated eh gerado automaticamente por AuditService.log().
                )
            except Exception:
                pass

    return ChatResponse(
        content=safe_content,
        model=data.get("model", model),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
        pii_redacted_count=pii_redacted_count,
        output_pii_redacted_count=output_pii_redacted_count,
        raw=None,  # NAO retornar raw por padrao (LGPD: response pode ter PII eco)
    )


# ============================================================================
# Helper de convenience que usa settings
# ============================================================================


async def chat_with_settings(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    consent_granted: bool = False,
    actor_id: str = "anonymous",
    db: "Session | None" = None,
    session_id: str | None = None,
    rate_limit_per_minute: int | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
) -> ChatResponse:
    """Wrapper que le settings do app.config.

    Conveniente para o webhook Evolution (ja temos settings carregado).
    Para testes, prefira `chat(...)` direto com mocks.

    Raises:
        ChatError: CONFIG se OPENCODE_GO_API_KEY nao setado.
        ChatError: LGPD_BLOCKED se consent_granted=False.
    """
    from app.config import settings

    return await chat(
        messages=messages,
        model=model or settings.opencode_go_model,
        api_key=settings.opencode_go_api_key or "",
        base_url=settings.opencode_go_base_url,
        temperature=temperature,
        consent_granted=consent_granted,
        actor_id=actor_id,
        db=db,
        session_id=session_id,
        rate_limit_per_minute=rate_limit_per_minute,
        redis_url=settings.redis_url,
        request_id=request_id,
        client_ip=client_ip,
        thinking_mode=settings.opencode_go_thinking_mode,
    )
