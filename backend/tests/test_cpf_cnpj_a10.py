"""Testes A10 — CPF/CNPJ validator (regex + digito verificador)."""
from __future__ import annotations

import pytest

from app.models.cpf_cnpj_validator import (
    mask_cnpj,
    mask_cpf,
    validate_cnpj,
    validate_cpf,
)


# CPFs validos (DV correto, gerados deterministicamente)
VALID_CPFS = (
    "529.982.247-25",
    "52998224725",
    "111.444.777-35",
    "123.456.789-09",
)

INVALID_CPFS = (
    "529.982.247-26",  # DV errado
    "111.111.111-11",  # todos iguais
    "123",  # muito curto
    "123456789012345",  # muito longo
    "abc.def.ghi-jk",  # nao-digitos
    "",
)


@pytest.mark.parametrize("cpf", VALID_CPFS)
def test_validate_cpf_valido(cpf: str) -> None:
    assert validate_cpf(cpf) is True


@pytest.mark.parametrize("cpf", INVALID_CPFS)
def test_validate_cpf_invalido(cpf: str) -> None:
    assert validate_cpf(cpf) is False


# CNPJs validos
VALID_CNPJS = (
    "11.222.333/0001-81",
    "11222333000181",
)

INVALID_CNPJS = (
    "11.222.333/0001-82",  # DV errado
    "11.111.111/1111-11",  # todos iguais
    "123",  # curto
    "",
)


@pytest.mark.parametrize("cnpj", VALID_CNPJS)
def test_validate_cnpj_valido(cnpj: str) -> None:
    assert validate_cnpj(cnpj) is True


@pytest.mark.parametrize("cnpj", INVALID_CNPJS)
def test_validate_cnpj_invalido(cnpj: str) -> None:
    assert validate_cnpj(cnpj) is False


def test_mask_cpf_formato_canonico() -> None:
    """mask_cpf retorna ***.***.***-**."""
    assert mask_cpf("52998224725") == "***.***.***-**"
    assert mask_cpf("529.982.247-25") == "***.***.***-**"


def test_mask_cpf_invalido_retorna_masked() -> None:
    """mask_cpf com valor invalido retorna [MASKED:cpf]."""
    assert mask_cpf("123") == "[MASKED:cpf]"


def test_mask_cnpj_formato_canonico() -> None:
    """mask_cnpj retorna **.***.***/****-**."""
    assert mask_cnpj("11222333000181") == "**.***.***/****-**"
