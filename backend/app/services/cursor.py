"""Cursor helpers compartilhados — Relay-style opaque cursor pagination.

Usado por todos endpoints v2 com paginacao (A24.2 clientes, A24.3 protocolos,
A24.4 emolumento, futuros).

Cursor format: base64 url-safe de JSON {id_after: int}.
Opaco para o cliente (decodificavel internamente para debugger).
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def encode_cursor(payload: dict[str, Any]) -> str:
    """Codifica cursor opaque base64 (Relay-style).

    Args:
        payload: dict a ser serializado em JSON.

    Returns:
        str base64 url-safe sem padding (=).
    """
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Decodifica cursor opaque.

    Raises:
        ValueError: cursor invalido (malformed base64 ou JSON).
    """
    padded = cursor + "=" * (-len(cursor) % 4)
    return json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))


def decode_cursor_safe(cursor: str, key: str) -> Any | None:
    """Decodifica cursor de forma fail-soft, retornando o valor de `key`.

    Args:
        cursor: cursor opaque.
        key: chave esperada no payload (ex: 'id_after', 'tipo_after').

    Returns:
        valor da chave (int | str | etc) ou None se cursor invalido.
    """
    try:
        decoded = decode_cursor(cursor)
        return decoded.get(key)
    except (ValueError, KeyError, TypeError) as e:
        logger.warning("cursor decode falhou: %s — fail-soft para primeira pagina", e)
        return None
