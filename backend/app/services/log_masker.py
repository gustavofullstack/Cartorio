"""Log masker - substitui PII em logs (A11).

LGPD art. 46: medidas tecnicas adequadas para proteger dados pessoais.
Em logs (stdout, file, log aggregation), nunca pode aparecer CPF/CNPJ/email/telefone em texto plano.

Uso:
    import logging
    from app.services.log_masker import MaskingFilter

    handler = logging.StreamHandler()
    handler.addFilter(MaskingFilter())
    logger.addHandler(handler)

OU: configurar globalmente em main.py via uvicorn LOGGING_CONFIG override.
"""

from __future__ import annotations

import logging
import re

# Padroes copiados de sentry.py para consistencia. Single source of truth
# seria extrair pra modulo comum; por ora mantemos 2x para evitar import
# circular (sentry -> log_masker -> sentry).
_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cpf", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b")),
    ("cnpj", re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("phone_br", re.compile(r"\(?\d{2}\)?\s?9?\d{4}-?\d{4}")),
    ("cns", re.compile(r"\b\d{15}\b")),
    ("ip", re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
)


def _scrub_string(value: str) -> str:
    """Substitui PII em string por [MASKED:kind]."""
    result = value
    for kind, pattern in _PII_PATTERNS:
        result = pattern.sub(f"[MASKED:{kind}]", result)
    return result


class MaskingFilter(logging.Filter):
    """Filtro logging que reescreve mensagem removendo PII.

    Aplica em record.getMessage() (msg apos format com args).
    Tambem aplica em record.msg se for string (caso sem format).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # getMessage() ja fez msg % args
            original = record.getMessage()
            masked = _scrub_string(original)
            if masked != original:
                # Substitui a mensagem. Cuidado: isso quebra formatadores
                # que dependem do record original, mas em pratica so
                # %-format esta em uso no projeto.
                record.msg = masked
                record.args = ()
        except Exception:  # noqa: BLE001 - nunca quebrar logging
            # Se algo der errado, deixa passar original (fail-open).
            pass
        return True


__all__ = ["MaskingFilter"]
