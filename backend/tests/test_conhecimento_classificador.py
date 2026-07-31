"""Classificador documental local — sem rede, sem LLM, HITL obrigatório."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.conhecimento_classificador import (
    catalogo_tipos_documento,
    classificar_texto_sanitizado,
)


def test_classifica_testamento_com_sinais() -> None:
    texto = (
        "Minuta de testamento publico com clausulas restritivas e nomeacao de "
        "testamenteiro. Revogacao de testamento anterior."
    )
    result = classificar_texto_sanitizado(texto, unit_id="a" * 64)
    assert result.document_type_code == "TESTAMENTO"
    assert result.requires_human_validation is True
    assert result.matched_signals >= 2
    assert Decimal("0") < result.confidence < Decimal("1")
    assert len(result.idempotency_key) == 64


def test_classifica_lista_documentos_inventario() -> None:
    texto = (
        "Relacao de documentos necessarios para inventario extrajudicial: "
        "certidoes, checklist e documentacao para partilha."
    )
    result = classificar_texto_sanitizado(texto, unit_id="b" * 64)
    assert result.document_type_code in {"LISTA_DOCUMENTOS", "INVENTARIO_PARTILHA"}
    assert result.requires_human_validation is True


def test_classifica_emolumentos() -> None:
    texto = "Tabela de emolumentos e taxa de fiscalizacao com selo de fiscalizacao ISSQN."
    result = classificar_texto_sanitizado(texto, unit_id="c" * 64)
    assert result.document_type_code == "EMOLUMENTOS"


def test_rejeita_texto_com_cpf_bruto() -> None:
    with pytest.raises(ValueError, match="PII bruta"):
        classificar_texto_sanitizado(
            "Titular CPF 529.982.247-25 presente no ato",
            unit_id="d" * 64,
        )


def test_aceita_texto_com_redacted_placeholder() -> None:
    texto = "Contato do outorgante [REDACTED:CPF] para procuraçao publica."
    result = classificar_texto_sanitizado(texto, unit_id="e" * 64)
    assert result.document_type_code == "PROCURACAO"
    assert result.requires_human_validation is True


def test_catalogo_fechado_nao_vazio() -> None:
    cat = catalogo_tipos_documento()
    assert "TESTAMENTO" in cat
    assert "NORMATIVO_CNJ" in cat
    assert len(cat) >= 10


def test_idempotencia_estavel() -> None:
    texto = "Provimento CNJ da Corregedoria Nacional sobre usucapiao extrajudicial."
    a = classificar_texto_sanitizado(texto, unit_id="f" * 64)
    b = classificar_texto_sanitizado(texto, unit_id="f" * 64)
    assert a.idempotency_key == b.idempotency_key
    assert a.document_type_code == b.document_type_code
