"""Modulo de integracao com OpenCode-Go (LLM provider low-cost).

API compativel com OpenAI Chat Completions.
Endpoint: POST {base_url}/chat/completions

Modelo padrao: deepseek-v4-flash (custo minimo para treinamento/inferencia).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx


# ============================================================================
# Tipos
# ============================================================================


@dataclass(frozen=True)
class ChatResponse:
    """Resposta de uma chamada de chat completion.

    Attributes:
        content: Texto gerado pelo modelo (choices[0].message.content).
        model: Modelo usado (echo da request ou do response).
        tokens_in: Prompt tokens consumidos (None se API nao retornou usage).
        tokens_out: Completion tokens consumidos (None se API nao retornou usage).
        latency_ms: Latencia da chamada em milissegundos.
        finish_reason: Razao de parada (stop/length/content_filter/etc).
        raw: Response bruto da API (para debug, NAO usar em producao).
    """

    content: str
    model: str
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int
    finish_reason: str | None = None
    raw: dict[str, Any] | None = None


class ChatErrorKind:
    """Constantes para classificar tipo de erro."""

    CONFIG = "CONFIG_ERROR"  # API key/base_url ausente
    HTTP_4XX = "HTTP_4XX"  # Request malformado, auth falhou
    HTTP_5XX = "HTTP_5XX"  # Erro do servidor OpenCode-Go
    TIMEOUT = "TIMEOUT"  # Timeout de rede
    NETWORK = "NETWORK"  # Conexao caiu, DNS falhou, etc
    PARSE = "PARSE_ERROR"  # Response nao e JSON valido


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
) -> ChatResponse:
    """Chama OpenCode-Go Chat Completions.

    Args:
        messages: Lista de mensagens no formato OpenAI ({role, content}).
                  Roles validos: system, user, assistant.
        model: Nome do modelo (ex: 'deepseek-v4-flash').
        api_key: API key do OpenCode-Go. Vazio => ChatError CONFIG.
        base_url: URL base do OpenCode-Go (sem /chat/completions).
                  Vazio => ChatError CONFIG.
        temperature: Sampling temperature (0.0-2.0). Default 0.2 (mais deterministico).
        timeout_seconds: Timeout da request HTTP. Default 30s.

    Returns:
        ChatResponse com content + metadata (tokens, latencia, etc).

    Raises:
        ChatError: Para qualquer falha de config, HTTP, timeout ou parse.

    Notes:
        - Toda saida DEVE passar pelo PII scrubber antes de chegar aqui.
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

    # ---- Monta request ----
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

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

    return ChatResponse(
        content=content,
        model=data.get("model", model),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
        raw=None,  # NAO retornar raw por padrao (LGPD: response pode ter PII eco)
    )


# ============================================================================
# Helper de convenience que usa settings (para casos que NAO querem injetar)
# ============================================================================


async def chat_with_settings(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
) -> ChatResponse:
    """Wrapper que le settings do app.config.

    Conveniente para o webhook Evolution (ja temos settings carregado).
    Para testes, prefira `chat(...)` direto com mocks.

    Raises:
        ChatError: CONFIG se OPENCODE_GO_API_KEY nao setado.
    """
    from app.config import settings

    return await chat(
        messages=messages,
        model=model or settings.opencode_go_model,
        api_key=settings.opencode_go_api_key or "",
        base_url=settings.opencode_go_base_url,
        temperature=temperature,
    )
