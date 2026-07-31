"""Contrato unitário do contexto ConhecimentoInstitucional.

Os testes exercitam somente regras puras: nenhuma fonte real, I/O, LLM ou
integração externa participa destes cenários.
"""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.conhecimento_institucional import (
    EstadoConhecimento,
    FonteConhecimento,
    VersaoConhecimento,
)
from app.services.conhecimento_institucional import (
    ContextoCalculoInvalidoError,
    EstadoConhecimentoInvalidoError,
    RegraDeclarativaInvalidaError,
    calcular_regra_declarativa,
    gerar_chave_idempotencia,
)


def test_calcular_regra_fixa_publicada() -> None:
    resultado = calcular_regra_declarativa(
        {"operator": "fixed", "amount": "12.50"},
        {},
        estado=EstadoConhecimento.PUBLISHED,
    )

    assert resultado == Decimal("12.50")


def test_calcular_regra_percentual_e_soma_com_decimal() -> None:
    regra = {
        "operator": "sum",
        "items": [
            {"operator": "fixed", "amount": "10.01"},
            {"operator": "percentage", "base": "valor_declarado", "rate": "0.05"},
        ],
    }

    resultado = calcular_regra_declarativa(
        regra,
        {"valor_declarado": Decimal("100.10")},
        estado=EstadoConhecimento.PUBLISHED,
    )

    assert resultado == Decimal("15.02")


def test_calculo_falha_fechado_para_regra_nao_publicada() -> None:
    with pytest.raises(EstadoConhecimentoInvalidoError):
        calcular_regra_declarativa(
            {"operator": "fixed", "amount": "12.50"},
            {},
            estado=EstadoConhecimento.APPROVED,
        )


@pytest.mark.parametrize(
    ("regra", "contexto", "erro"),
    [
        (
            {"operator": "percentage", "base": "valor", "rate": "0.10"},
            {"valor": 1.5},
            ContextoCalculoInvalidoError,
        ),
        (
            {"operator": "percentage", "base": "ausente", "rate": "0.10"},
            {},
            ContextoCalculoInvalidoError,
        ),
        (
            {"operator": "python", "expression": "__import__('os')"},
            {},
            RegraDeclarativaInvalidaError,
        ),
    ],
)
def test_calculo_rejeita_contexto_ou_gramatica_insegura(
    regra: dict[str, object],
    contexto: dict[str, object],
    erro: type[ValueError],
) -> None:
    with pytest.raises(erro):
        calcular_regra_declarativa(regra, contexto, estado=EstadoConhecimento.PUBLISHED)


def test_calculo_e_chave_sao_idempotentes() -> None:
    regra = {"operator": "percentage", "base": "valor", "rate": "0.015"}
    contexto = {"valor": Decimal("100.00")}

    primeira = calcular_regra_declarativa(regra, contexto, estado=EstadoConhecimento.PUBLISHED)
    segunda = calcular_regra_declarativa(regra, contexto, estado=EstadoConhecimento.PUBLISHED)

    assert primeira == segunda == Decimal("1.50")
    assert gerar_chave_idempotencia("a" * 64, 1) == gerar_chave_idempotencia("a" * 64, 1)
    assert gerar_chave_idempotencia("a" * 64, 1) != gerar_chave_idempotencia("b" * 64, 1)


@pytest.mark.parametrize(
    ("regra", "contexto"),
    [
        ({"operator": "fixed", "amount": "-0.01"}, {}),
        (
            {"operator": "percentage", "base": "valor", "rate": "0.10"},
            {"valor": "-1.00"},
        ),
        (
            {"operator": "percentage", "base": "valor", "rate": "1.01"},
            {"valor": "10.00"},
        ),
        ({"operator": "fixed", "amount": "1000000000000.01"}, {}),
    ],
)
def test_calculo_rejeita_negativos_taxa_e_limites(
    regra: dict[str, object],
    contexto: dict[str, object],
) -> None:
    with pytest.raises((RegraDeclarativaInvalidaError, ContextoCalculoInvalidoError)):
        calcular_regra_declarativa(regra, contexto, estado=EstadoConhecimento.PUBLISHED)


def test_calculo_limita_quantidade_de_items() -> None:
    regra = {
        "operator": "sum",
        "items": [{"operator": "fixed", "amount": "0.01"}] * 101,
    }
    with pytest.raises(RegraDeclarativaInvalidaError, match="limite de items"):
        calcular_regra_declarativa(regra, {}, estado=EstadoConhecimento.PUBLISHED)


def test_schema_falha_fechado_e_impede_versao_duplicada(db_session: Session) -> None:
    fonte_invalida = FonteConhecimento(
        source_kind="OFFICIAL",
        canonical_uri="urn:source:invalid",
        content_sha256="c" * 64,
        state="UNSAFE",
    )
    db_session.add(fonte_invalida)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    fonte = FonteConhecimento(
        source_kind="OFFICIAL",
        canonical_uri="urn:source:1",
        content_sha256="d" * 64,
        state=EstadoConhecimento.INGESTED,
    )
    db_session.add(fonte)
    db_session.flush()
    chave = gerar_chave_idempotencia("d" * 64, 1)
    db_session.add_all(
        [
            VersaoConhecimento(
                source_id=fonte.id,
                version_number=1,
                content_sha256="d" * 64,
                state=EstadoConhecimento.INGESTED,
                idempotency_key=chave,
            ),
            VersaoConhecimento(
                source_id=fonte.id,
                version_number=1,
                content_sha256="e" * 64,
                state=EstadoConhecimento.INGESTED,
                idempotency_key=gerar_chave_idempotencia("e" * 64, 1),
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
