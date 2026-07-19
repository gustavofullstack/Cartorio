"""G8.10.T3 — Mascara PII em linhas de access log Traefik/nginx.

Modified by Gustavo Almeida — Wave 42.
"""

from __future__ import annotations

import re

_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE = re.compile(r"(?:\+?55)?\s*\(?\d{2}\)?\s*9?\d{4}[-\s]?\d{4}")
_TOKEN = re.compile(r"(?i)(authorization=|token=|apikey=)([^\s&]+)")


def mask_query_string(qs: str) -> str:
    if not qs:
        return qs
    out = _CPF.sub("***.***.***-**", qs)
    out = _EMAIL.sub("***@***.***", out)
    out = _PHONE.sub("(**)*****-****", out)
    out = _TOKEN.sub(r"\1***", out)
    return out


def mask_access_log_line(line: str) -> str:
    """Mascara PII em uma linha de log de acesso."""
    if not line:
        return line
    return mask_query_string(line)


__all__ = ["mask_access_log_line", "mask_query_string"]
