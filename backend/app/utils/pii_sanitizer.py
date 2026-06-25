"""PII Sanitizer (D8 - LGPD by design).

Sanitiza dados pessoais de strings antes de logar/exibir.
Detecta 5 tipos de PII brasileira:
1. CPF: 11 digitos com ou sem formatacao (123.456.789-00 ou 12345678900)
2. RG: 7-10 digitos com prefixo UF opcional (MG-12.345.678)
3. Email: padrao RFC 5322 simplificado
4. Phone BR: (XX) 9XXXX-XXXX ou XX9XXXXXXX
5. CNPJ: 14 digitos com ou sem formatacao

Substitui por placeholder mantendo contexto (ex: cpf=***123).
NAO quebra URL, JSON, ou outros formatos - apenas mascarado.

Uso:
    from app.utils.pii_sanitizer import sanitize_pii, sanitize_dict

    log_line = "Cliente cpf=123.456.789-00 criado"
    safe = sanitize_pii(log_line)  # "Cliente cpf=***789-00 criado"

    payload = {"name": "Gustavo", "cpf": "123.456.789-00"}
    safe = sanitize_dict(payload)  # {"name": "Gustavo", "cpf": "***789-00"}
"""
from __future__ import annotations

import re
from typing import Any

# CPF: 11 digitos, formato XXX.XXX.XXX-XX ou 11 digitos
_CPF_RE = re.compile(r"\b(\d{3}\.?\d{3}\.?\d{3}-?\d{2})\b")
# RG: prefixo UF opcional + 6-10 digitos + opcional . e digitos
_RG_RE = re.compile(r"\b(?:([A-Z]{2})-)?(\d{6,10})\b")
# Email: padrao simplificado
_EMAIL_RE = re.compile(r"\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b")
# Phone BR: (XX) 9XXXX-XXXX ou XX9XXXXXXX (celular com 9) ou XX XXXX-XXXX (fixo)
_PHONE_RE = re.compile(r"\b(\(?\d{2}\)?\s?9?\d{4}-?\d{4})\b")
# CNPJ: 14 digitos
_CNPJ_RE = re.compile(r"\b(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b")


def _mask_keep_last(value: str, keep: int = 4) -> str:
    """Mascara mantendo os ultimos N caracteres visiveis.

    Ex: 123.456.789-00 -> ***789-00 (keep=4 -> "789-00" visivel)
    """
    if len(value) <= keep:
        return "***"
    return "***" + value[-keep:]


def sanitize_cpf(text: str) -> str:
    """Mascara CPF mantendo ultimos 6 chars (XXX.789-00 - includes hyphen)."""
    return _CPF_RE.sub(lambda m: _mask_keep_last(m.group(1), 6), text)


def sanitize_rg(text: str) -> str:
    """Mascara RG mantendo ultimos 3 digitos."""
    def _repl(m: re.Match) -> str:
        uf = m.group(1) or ""
        digits = m.group(2)
        masked_digits = _mask_keep_last(digits, 3)
        return f"{uf}{masked_digits}"
    return _RG_RE.sub(_repl, text)


def sanitize_email(text: str) -> str:
    """Mascara email mantendo apenas dominio: 'gustavo@gmail.com' -> '***@gmail.com'."""
    return _EMAIL_RE.sub(lambda m: f"***@{m.group(2)}", text)


def sanitize_phone(text: str) -> str:
    """Mascara phone mantendo ultimos 4 digitos."""
    return _PHONE_RE.sub(lambda m: _mask_keep_last(m.group(1), 4), text)


def sanitize_cnpj(text: str) -> str:
    """Mascara CNPJ mantendo ultimos 8 chars (incluindo /XXXX-XX)."""
    return _CNPJ_RE.sub(lambda m: _mask_keep_last(m.group(1), 8), text)


def sanitize_pii(text: str) -> str:
    """Aplica todos os sanitizers em sequencia.

    Args:
        text: string potencialmente com PII (log line, message, etc)

    Returns:
        string com PII mascarada
    """
    if not text:
        return text
    text = sanitize_cpf(text)
    text = sanitize_cnpj(text)
    text = sanitize_email(text)
    text = sanitize_phone(text)
    text = sanitize_rg(text)
    return text


def sanitize_dict(data: dict[str, Any], _depth: int = 0) -> dict[str, Any]:
    """Sanitiza PII em todos os valores string de um dict (recursivo).

    Args:
        data: dict qualquer
        _depth: profundidade (interno, evita recursao infinita)

    Returns:
        novo dict com PII mascarada (NAO muta input)
    """
    if _depth > 5:  # Limite de seguranca
        return data
    result: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, str):
            result[k] = sanitize_pii(v)
        elif isinstance(v, dict):
            result[k] = sanitize_dict(v, _depth + 1)
        elif isinstance(v, list):
            result[k] = [
                sanitize_pii(item) if isinstance(item, str)
                else sanitize_dict(item, _depth + 1) if isinstance(item, dict)
                else item
                for item in v
            ]
        else:
            result[k] = v
    return result
