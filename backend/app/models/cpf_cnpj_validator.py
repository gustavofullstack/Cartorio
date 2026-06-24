"""CPF/CNPJ validators com digito verificador (DV).

Usado em constraints CHECK no DB (A10) e validacao Pydantic.
Algoritmo canonico de DV conforme Receita Federal / TCU.
"""
from __future__ import annotations

import re

CPF_PATTERN = re.compile(r"^\d{11}$")
CNPJ_PATTERN = re.compile(r"^\d{14}$")
CPF_MASK = "***.***.***-**"


def _only_digits(value: str) -> str:
    """Remove tudo que nao eh digito."""
    return re.sub(r"\D", "", value)


def validate_cpf(value: str) -> bool:
    """Valida CPF (11 digitos + DV correto). Aceita formatado ou nao."""
    digits = _only_digits(value)
    if not CPF_PATTERN.match(digits):
        return False
    # Rejeita CPFs com todos digitos iguais (ex: 111.111.111-11)
    if digits == digits[0] * 11:
        return False
    # Calcula DV
    soma = sum(int(digits[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    dv1 = 0 if resto == 10 else resto
    if int(digits[9]) != dv1:
        return False
    soma = sum(int(digits[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    dv2 = 0 if resto == 10 else resto
    return int(digits[10]) == dv2


def validate_cnpj(value: str) -> bool:
    """Valida CNPJ (14 digitos + DV correto). Aceita formatado ou nao."""
    digits = _only_digits(value)
    if not CNPJ_PATTERN.match(digits):
        return False
    if digits == digits[0] * 14:
        return False
    # DV1
    pesos_dv1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    soma = sum(int(digits[i]) * pesos_dv1[i] for i in range(12))
    resto = soma % 11
    dv1 = 0 if resto < 2 else 11 - resto
    if int(digits[12]) != dv1:
        return False
    # DV2
    pesos_dv2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    soma = sum(int(digits[i]) * pesos_dv2[i] for i in range(13))
    resto = soma % 11
    dv2 = 0 if resto < 2 else 11 - resto
    return int(digits[13]) == dv2


def mask_cpf(value: str) -> str:
    """Mascara CPF para log: 123.456.789-00 -> ***.***.***-**."""
    digits = _only_digits(value)
    if len(digits) != 11:
        return "[MASKED:cpf]"
    return CPF_MASK


def mask_cnpj(value: str) -> str:
    """Mascara CNPJ para log: 12.345.678/0001-90 -> **.***.***/****-**."""
    digits = _only_digits(value)
    if len(digits) != 14:
        return "[MASKED:cnpj]"
    return "**.***.***/****-**"


__all__ = [
    "CPF_MASK",
    "CPF_PATTERN",
    "CNPJ_PATTERN",
    "mask_cnpj",
    "mask_cpf",
    "validate_cnpj",
    "validate_cpf",
]
