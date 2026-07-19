from __future__ import annotations

import re
from typing import Annotated
from pydantic import AfterValidator


def validate_cpf(v: str) -> str:
    """Valida o dígito verificador e formato básico de um CPF (11 dígitos)."""
    if not isinstance(v, str):
        raise ValueError("CPF deve ser uma string.")

    # Limpa pontuação
    digits = re.sub(r"\D", "", v)

    if len(digits) != 11:
        raise ValueError("CPF deve conter exatamente 11 dígitos numéricos.")

    # Recusa todos os dígitos iguais
    if digits == digits[0] * 11:
        raise ValueError("CPF inválido (todos os dígitos são iguais).")

    # Algoritmo CPF
    # Primeiro dígito
    soma = sum(int(digits[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    d1 = 0 if resto in (10, 11) else resto
    if d1 != int(digits[9]):
        raise ValueError("Dígito verificador do CPF inválido.")

    # Segundo dígito
    soma = sum(int(digits[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    d2 = 0 if resto in (10, 11) else resto
    if d2 != int(digits[10]):
        raise ValueError("Dígito verificador do CPF inválido.")

    return v


def validate_cnpj(v: str) -> str:
    """Valida o dígito verificador e formato básico de um CNPJ (14 dígitos)."""
    if not isinstance(v, str):
        raise ValueError("CNPJ deve ser uma string.")

    # Limpa pontuação
    digits = re.sub(r"\D", "", v)

    if len(digits) != 14:
        raise ValueError("CNPJ deve conter exatamente 14 dígitos numéricos.")

    if digits == digits[0] * 14:
        raise ValueError("CNPJ inválido (todos os dígitos são iguais).")

    # Algoritmo CNPJ
    # Primeiro dígito
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(digits[i]) * weights_1[i] for i in range(12))
    resto = soma % 11
    d1 = 0 if resto < 2 else 11 - resto
    if d1 != int(digits[12]):
        raise ValueError("Primeiro dígito verificador do CNPJ inválido.")

    # Segundo dígito
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(digits[i]) * weights_2[i] for i in range(13))
    resto = soma % 11
    d2 = 0 if resto < 2 else 11 - resto
    if d2 != int(digits[13]):
        raise ValueError("Segundo dígito verificador do CNPJ inválido.")

    return v


# Tipos customizados Pydantic v2
CPFStr = Annotated[str, AfterValidator(validate_cpf)]
CNPJStr = Annotated[str, AfterValidator(validate_cnpj)]
