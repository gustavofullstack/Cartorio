"""G8.07.T3 — PII scrub interceptor para saídas MCP.

Aplica a camada `pii.scrub` de forma recursiva em dict/list/str retornados
por tools MCP, para que CPF/telefone/email raw nunca saiam no protocolo MCP
(mesmo se um service interno vazar campo).

Uso:
    from app.services.mcp_pii import scrub_mcp_output
    return scrub_mcp_output(result_dict)

LGPD-by-design: defense-in-depth (não substitui scrub no service layer).

Modified by Gustavo Almeida — G8 Wave 33 A2.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.pii import scrub


def scrub_mcp_output(data: Any, *, max_depth: int = 12) -> Any:
    """Scrub recursivo de estruturas JSON-like retornadas por tools MCP.

    - str: aplica pii.scrub
    - dict: scrub keys values; chaves sensíveis conhecidas forçam mask se valor str
    - list/tuple: scrub cada item
    - outros: retorna como está (int/bool/None)
    """
    return _scrub_value(data, depth=0, max_depth=max_depth)


_SENSITIVE_KEYS = frozenset(
    {
        "cpf",
        "rg",
        "cnpj",
        "email",
        "telefone",
        "phone",
        "whatsapp",
        "nome",
        "name",
        "documento",
        "endereco",
        "address",
    }
)


def _scrub_value(data: Any, *, depth: int, max_depth: int) -> Any:
    if depth > max_depth:
        return data
    if data is None or isinstance(data, (bool, int, float)):
        return data
    if isinstance(data, str):
        return scrub(data).text
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for k, v in data.items():
            key_l = str(k).lower()
            if key_l in _SENSITIVE_KEYS and isinstance(v, str) and v:
                # scrub + se ainda parecer raw, redige genérico
                scrubbed = scrub(v).text
                if scrubbed == v and any(ch.isdigit() for ch in v):
                    out[k] = "[REDACTED]"
                else:
                    out[k] = scrubbed
            else:
                out[k] = _scrub_value(v, depth=depth + 1, max_depth=max_depth)
        return out
    if isinstance(data, (list, tuple)):
        items = [_scrub_value(x, depth=depth + 1, max_depth=max_depth) for x in data]
        return type(data)(items) if isinstance(data, tuple) else items
    # bytes / outros: stringifica seguro
    if isinstance(data, bytes):
        try:
            return scrub(data.decode("utf-8", errors="replace")).text
        except Exception:  # noqa: BLE001
            return "[BYTES_REDACTED]"
    return data


_cpf_re = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")


def mcp_output_has_raw_cpf(data: Any) -> bool:
    """True se ainda restar padrão de CPF não redigido (para testes)."""
    if isinstance(data, dict):
        return any(mcp_output_has_raw_cpf(k) or mcp_output_has_raw_cpf(v) for k, v in data.items())
    if isinstance(data, (list, tuple)):
        return any(mcp_output_has_raw_cpf(v) for v in data)

    blob = str(data)
    # redacted markers ok
    if "CPF_REDACTED" in blob or "[REDACTED]" in blob:
        # still search for unredacted
        pass
    for m in _cpf_re.finditer(blob):
        if "REDACTED" not in m.group(0):
            return True
    return False
