"""G8.02.T2 — Tratamento de erros de payload Telegram friendly + sem stack trace.

Camada que:
1. Detecta payloads inválidos/vazios/malformed ANTES de enviar para API Telegram
2. Converte erros técnicos (httpx, JSON, validation) em mensagens Telegram-friendly
3. NUNCA vaza stack trace, paths internos, schema, ou detalhes técnicos
4. LGPD: mensagens de erro não expõem PII

Pontos de uso:
    from app.services.telegram_error_handler import safe_telegram_reply

    try:
        await send_telegram_message(text=text, chat_id=chat_id)
    except Exception as exc:
        user_message = safe_telegram_reply(exc, chat_id=chat_id)
        return user_message

API:
- `safe_telegram_reply(exc, chat_id)` -> str (mensagem amigável)
- `validate_telegram_payload(text, max_length=4096)` -> tuple[bool, str | None]
- `classify_telegram_error(exc)` -> str (categoria: rate_limit, network, validation, unknown)
- `ERROR_MESSAGES` -> dict[str, str] mapeamento categoria → mensagem user-friendly

LGPD-by-design:
- Mensagens amigáveis NÃO mencionam paths, schemas, ou stack
- PII (cpf/telefone) é mascarada mesmo em mensagens de erro (defense-in-depth)
- Log estruturado (server-side) preserva contexto para SRE/debug

Modified by Gustavo Almeida — G8 Wave 34 A1.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.pii import scrub


# Mensagens amigáveis por categoria (LGPD-safe, sem leak técnico)
ERROR_MESSAGES: dict[str, str] = {
    "rate_limit": (
        "⏳ O sistema está recebendo muitas mensagens no momento. "
        "Por favor, aguarde alguns segundos e tente novamente."
    ),
    "network": (
        "🔌 Não consegui enviar a mensagem agora. "
        "Verifique sua conexão e tente novamente em instantes."
    ),
    "validation": (
        "⚠️ A mensagem enviada contém caracteres ou formato inválido. "
        "Por favor, tente novamente com texto simples."
    ),
    "payload_too_long": (
        "📝 Sua mensagem é muito longa. "
        "Por favor, envie em partes menores (máximo 4000 caracteres)."
    ),
    "payload_empty": (
        "🤔 Não recebi nenhuma mensagem. Por favor, envie uma mensagem de texto para continuar."
    ),
    "unknown": ("❌ Algo deu errado. Nossa equipe foi notificada e vamos resolver em breve."),
}


# Regex para classificar mensagens de erro comuns da API Telegram
_TELEGRAM_RATE_LIMIT_PATTERNS = (
    r"429",
    r"too many requests",
    r"retry after",
    r"flood",
)

_TELEGRAM_VALIDATION_PATTERNS = (
    r"400",
    r"bad request",
    r"can't parse",
    r"invalid",
    r"entity",
    r"markdown",
)

_TELEGRAM_NETWORK_PATTERNS = (
    r"timeout",
    r"connection",
    r"network",
    r"unreachable",
    r"reset",
    r"ssl",
)


def classify_telegram_error(exc: Exception) -> str:
    """Classifica erro Telegram em categoria canônica.

    Args:
        exc: Exception capturada ao enviar mensagem Telegram.

    Returns:
        String em ERROR_MESSAGES.keys(). Default: "unknown".
    """
    msg = str(exc).lower()
    # Rate limit tem prioridade (HTTP 429)
    for pat in _TELEGRAM_RATE_LIMIT_PATTERNS:
        if re.search(pat, msg, re.IGNORECASE):
            return "rate_limit"
    # Validation tem prioridade sobre network (400 = bad request)
    for pat in _TELEGRAM_VALIDATION_PATTERNS:
        if re.search(pat, msg, re.IGNORECASE):
            return "validation"
    # Network (timeout, connection reset)
    for pat in _TELEGRAM_NETWORK_PATTERNS:
        if re.search(pat, msg, re.IGNORECASE):
            return "network"
    return "unknown"


def validate_telegram_payload(
    text: str | None,
    *,
    max_length: int = 4096,
) -> tuple[bool, str | None]:
    """Valida payload antes de enviar para Telegram.

    Args:
        text: Texto a ser enviado (pode ser None).
        max_length: Limite Telegram (default 4096).

    Returns:
        Tuple (is_valid, error_category). Se válido, error_category é None.
    """
    if text is None or text == "":
        return False, "payload_empty"
    if len(text) > max_length:
        return False, "payload_too_long"
    # Markdown entities podem quebrar parse Telegram
    if text.count("*") % 2 != 0 or text.count("_") % 2 != 0:
        return False, "validation"
    return True, None


def safe_telegram_reply(
    exc: Exception,
    *,
    chat_id: int | str | None = None,
    log_context: dict[str, Any] | None = None,
) -> str:
    """Converte exceção em mensagem Telegram amigável (sem leak técnico).

    LGPD: mensagem resultante NUNCA contém paths, stack traces, ou PII raw.
    PII passada em log_context é scrubbed antes de logar.

    Args:
        exc: Exception capturada.
        chat_id: ID do chat (opcional, para log estruturado).
        log_context: Contexto extra para log server-side (não vai pro user).

    Returns:
        String pronta para enviar ao Telegram.
    """
    category = classify_telegram_error(exc)
    message = ERROR_MESSAGES.get(category, ERROR_MESSAGES["unknown"])

    # Log estruturado server-side preserva contexto SEM expor para o user.
    # PII em log_context é scrubbed antes de logar.
    safe_log = scrub(str(log_context)).text if log_context else ""
    safe_exc = scrub(str(exc)).text[:200]  # truncate
    print(
        f"[telegram_error_handler] category={category} chat_id={chat_id} "
        f"exc={safe_exc} context={safe_log}"
    )
    return message


def friendly_validation_error(
    payload: Any,
    *,
    max_length: int = 4096,
) -> str | None:
    """Retorna mensagem amigável se payload inválido, senão None.

    Args:
        payload: texto a ser validado.
        max_length: limite Telegram.

    Returns:
        Mensagem amigável se inválido, None se OK.
    """
    is_valid, category = validate_telegram_payload(payload, max_length=max_length)
    if is_valid:
        return None
    return ERROR_MESSAGES.get(category or "validation", ERROR_MESSAGES["validation"])


__all__ = [
    "ERROR_MESSAGES",
    "classify_telegram_error",
    "friendly_validation_error",
    "safe_telegram_reply",
    "validate_telegram_payload",
]


def _cli() -> None:
    """CLI smoke test."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="G8.02.T2 Telegram error handler")
    parser.add_argument("--demo", action="store_true", help="Run demo classification")
    args = parser.parse_args()

    if args.demo:
        test_cases: list[tuple[str, Exception]] = [
            ("429 Too Many Requests", Exception("429 retry_after 5")),
            ("400 Invalid markdown", Exception("400 can't parse entities")),
            ("Timeout", Exception("ReadTimeout: timeout=10")),
            ("Empty payload", ValueError("text is empty")),
            ("Generic", RuntimeError("something exploded")),
        ]
        for name, exc in test_cases:
            cat = classify_telegram_error(exc)
            reply = safe_telegram_reply(exc)
            print(f"{name}: category={cat} reply={reply[:80]}")
        return
    parser.print_help(sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    _cli()
