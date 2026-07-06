"""T010 — validate_cpf_cnpj composite (Lesson 110 Pydantic literal hardening)."""

from __future__ import annotations

import pytest

from app.models.cpf_cnpj_validator import (
    validate_cnpj,
    validate_cpf,
    validate_cpf_cnpj,
)


VALID_CPFS = (
    "529.982.247-25",
    "52998224725",
    "111.444.777-35",
    "123.456.789-09",
)

VALID_CNPJS = (
    "11.222.333/0001-81",
    "11222333000181",
)

INVALID_VALUES = (
    "",
    "123",
    "12345",
    "abc.def.ghi-jk",
    "111.111.111-11",  # CPF todos iguais (ja coberto por validate_cpf)
    "11111111111111",  # CNPJ todos iguais (14 mesmo digito)
    "529.982.247-26",  # DV errado
    "11.222.333/0001-82",  # CNPJ DV errado
)


@pytest.mark.parametrize("cpf", VALID_CPFS)
def test_validate_cpf_cnpj_cpf_valido(cpf: str) -> None:
    assert validate_cpf_cnpj(cpf) is True


@pytest.mark.parametrize("cnpj", VALID_CNPJS)
def test_validate_cpf_cnpj_cnpj_valido(cnpj: str) -> None:
    assert validate_cpf_cnpj(cnpj) is True


@pytest.mark.parametrize("bad", INVALID_VALUES)
def test_validate_cpf_cnpj_invalido(bad: str) -> None:
    assert validate_cpf_cnpj(bad) is False


def test_validate_cpf_cnpj_export_in_all() -> None:
    """Garantir que validate_cpf_cnpj esta no __all__ do modulo."""
    from app.models import cpf_cnpj_validator as mod

    assert "validate_cpf_cnpj" in mod.__all__


def test_composite_dispatcher_matches_individual() -> None:
    """Composite deve dar a mesma resposta que chamar validate_cpf OU validate_cnpj."""
    for cpf in VALID_CPFS:
        assert validate_cpf_cnpj(cpf) == validate_cpf(cpf)
    for cnpj in VALID_CNPJS:
        assert validate_cpf_cnpj(cnpj) == validate_cnpj(cnpj)


def test_composite_length_boundary() -> None:
    """11 = CPF; 14 = CNPJ; outro = False."""
    assert validate_cpf_cnpj("1" * 11) is False  # todos iguais
    assert validate_cpf_cnpj("1" * 12) is False  # tamanho invalido
    assert validate_cpf_cnpj("1" * 13) is False
    assert validate_cpf_cnpj("1" * 14) is False  # todos iguais CNPJ
