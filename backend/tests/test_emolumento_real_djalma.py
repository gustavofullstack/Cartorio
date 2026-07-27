"""Testes unitários para o módulo de dados e preços reais do 2º Ofício de Uberlândia (Djalma)."""

from decimal import Decimal

from app.services.emolumento_real_djalma import (
    calcular_emolumento_real_djalma,
)
from app.services.ai_data_extractor import (
    extrair_e_calcular_solicitacao,
    extrair_folhas,
    extrair_tipo_ato,
    extrair_valor_monetario,
)


def test_obter_emolumento_escritura_declarado():
    res = calcular_emolumento_real_djalma("escritura_compra_venda", valor_declarado=5000)
    assert res.status == "HITL_REQUIRED"
    assert res.total is None


def test_calcular_emolumento_real_djalma_procuracao():
    res = calcular_emolumento_real_djalma("procuracao_geral", folhas=1)
    assert res.cartorio == "2º Serviço Notarial de Uberlândia"
    assert res.status == "PUBLISHED"
    assert res.emolumento_base == Decimal("52.43")
    assert res.tfj == Decimal("16.51")
    assert res.total == Decimal("68.94")


def test_calcular_emolumento_real_djalma_escritura_folhas_extras():
    res = calcular_emolumento_real_djalma(
        "escritura_compra_venda",
        valor_declarado=Decimal("380000.00"),
        folhas=3,
    )
    assert res.status == "HITL_REQUIRED"
    assert res.total is None


def test_ai_data_extractor_helpers():
    txt = "Gostaria de saber o valor de uma escritura de compra e venda de R$ 450.000,00 com 4 folhas"
    assert extrair_tipo_ato(txt) == "escritura_compra_venda"
    assert extrair_valor_monetario(txt) == Decimal("450000.00")
    assert extrair_folhas(txt) == 4


def test_extrair_e_calcular_solicitacao_flow():
    txt = "Preciso de uma procuração para a Sra. Maria CPF 123.456.789-00 urgente"
    res = extrair_e_calcular_solicitacao(txt)
    # CPF deve ter sido ocultado pelo PII scrub
    assert "123.456.789-00" not in res.texto_sanitizado
    assert res.urgencia_identificada is True
    assert res.calculo.tipo_ato == "procuracao_geral"
    assert res.status_auditoria == "NOT_PERSISTED"
