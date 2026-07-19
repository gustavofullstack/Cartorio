"""G8.23.T1 — filter de logging que strip secrets de qualquer output."""

from __future__ import annotations

import logging
import re

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[=:]\s*\S+"),
    re.compile(r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"),
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}"),
    re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
)

REDACTION = "[SECRET-REDACTED]"


class SecretScrubLogFilter(logging.Filter):
    """Remove credenciais conhecidas de mensagens de logging."""

    def __init__(self, name: str = "") -> None:
        super().__init__(name)

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
            for pattern in SECRET_PATTERNS:
                message = pattern.sub(REDACTION, message)
            record.msg = message
            record.args = ()
        except Exception:  # noqa: BLE001
            pass
        return True


__all__ = ["REDACTION", "SECRET_PATTERNS", "SecretScrubLogFilter"]
