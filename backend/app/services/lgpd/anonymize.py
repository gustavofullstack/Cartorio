"""Anonimização irreversível de dados pessoais (LGPD Art. 12)."""
from __future__ import annotations

import hashlib
import re
from typing import Any


def anonymize_cpf(cpf: str) -> str:
    """CPF anonimizado preservando formato mas mascarando dígitos.
    
    >>> anonymize_cpf("123.456.789-09")
    '***.***.***-09'
    """
    if not cpf:
        return ""
    digits = re.sub(r"\D", "", cpf)
    if len(digits) != 11:
        return "***"
    return f"***.***.***-{digits[-2:]}"


def anonymize_email(email: str) -> str:
    """Email anonimizado preservando domínio.
    
    >>> anonymize_email("fulano@example.com")
    'f***@example.com'
    """
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def anonymize_phone(phone: str) -> str:
    """Telefone anonimizado preservando DDD.
    
    >>> anonymize_phone("(34) 99876-5432")
    "(**) *****-5432"
    """
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 8:
        return "***"
    return f"(**) *****-{digits[-4:]}"


def anonymize(data: str) -> str:
    """Auto-detecta tipo (CPF/email/telefone) e aplica anonimização."""
    if not data:
        return ""
    if "@" in data:
        return anonymize_email(data)
    if re.search(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", data):
        return anonymize_cpf(data)
    if re.search(r"\(?\d{2}\)?\s*\d{4,5}-?\d{4}", data):
        return anonymize_phone(data)
    return "***"


def anonymize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Anonimiza campos PII conhecidos em um dict."""
    pii_fields = {"cpf", "cnpj", "email", "telefone", "phone", "rg"}
    out = dict(record)
    for k, v in out.items():
        if k.lower() in pii_fields and isinstance(v, str):
            out[k] = anonymize(v)
    return out


def hash_pii(value: str) -> str:
    """Hash SHA256 determinístico (não reversível) para auditoria."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
