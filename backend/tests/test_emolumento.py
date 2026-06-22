"""Testes do calculo de emolumento."""

from decimal import Decimal

import pytest

from app.services.emolumento import (
    EMOLUMENTOS_2026,
    TIPOS_VALIDOS,
    calcular,
    isencao_aplicavel,
)


def test_calculo_basico_certidao_negativa():
    r = calcular("certidao_negativa")
    assert r.tipo == "certidao_negativa"
    assert r.base == Decimal("87.50")
    assert r.adicional_folhas == Decimal("0.00")
    assert r.adicional_urgencia == Decimal("0.00")
    assert r.total == Decimal("87.50")


def test_calculo_com_folhas_adicionais():
    """Cada folha extra alem da 1a adiciona 5%."""
    r = calcular("escritura_compra_venda", folhas=3)
    # 4521 + 5%*2*4521 = 4521 + 452.10 = 4973.10
    assert r.adicional_folhas == Decimal("452.10")
    assert r.total == Decimal("4973.10")


def test_calculo_com_urgencia():
    r = calcular("procuracao", urgencia=True)
    # 156.40 + 50% = 234.60
    assert r.adicional_urgencia == Decimal("78.20")
    assert r.total == Decimal("234.60")


def test_calculo_combinado_folhas_e_urgencia():
    r = calcular("autenticacao", folhas=2, urgencia=True)
    # base=28.90, folhas=1.45, urgencia=14.45 -> 44.80
    assert r.base == Decimal("28.90")
    assert r.adicional_folhas == Decimal("1.45")
    assert r.adicional_urgencia == Decimal("14.45")
    assert r.total == Decimal("44.80")


def test_calculo_tipo_invalido_raise():
    with pytest.raises(ValueError, match="tipo desconhecido"):
        calcular("tipo_que_nao_existe")


def test_calculo_folhas_negativas_raise():
    with pytest.raises(ValueError, match="folhas deve estar"):
        calcular("certidao_negativa", folhas=0)


def test_calculo_folhas_excessivas_raise():
    with pytest.raises(ValueError, match="folhas deve estar"):
        calcular("certidao_negativa", folhas=10000)


def test_calculo_tabela_customizada():
    """Permite override pra testes ou tabelas historicas."""
    tabela_2025 = {"certidao_negativa": Decimal("80.00")}
    r = calcular("certidao_negativa", tabela=tabela_2025, tabela_referencia="TABELA_2025_MG")
    assert r.base == Decimal("80.00")
    assert r.tabela_referencia == "TABELA_2025_MG"


def test_registros_gratuitos_isencao_automatica():
    """Nascimento e obito sao sempre gratuitos."""
    assert isencao_aplicavel("registro_nascimento", motivo="x") is True
    assert isencao_aplicavel("registro_obito", motivo="x") is True


def test_isencao_justica_gratuita():
    assert isencao_aplicavel("procuracao", motivo="justica_gratuita") is True


def test_isencao_motivo_invalido():
    """Bot NAO aplica sozinho - motivo fora da whitelist = nao eh isento."""
    assert isencao_aplicavel("procuracao", motivo="porque_eu_quero") is False


def test_tabela_contem_tipos_essenciais():
    """Smoke test da tabela."""
    essenciais = {
        "certidao_negativa",
        "certidao_positiva",
        "escritura_compra_venda",
        "procuracao",
        "autenticacao",
        "registro_nascimento",
    }
    assert essenciais.issubset(TIPOS_VALIDOS)
    # Todos os valores positivos exceto gratuitos
    for tipo, valor in EMOLUMENTOS_2026.items():
        if tipo not in {"registro_nascimento", "registro_obito"}:
            assert valor > 0, f"{tipo} deveria ter valor positivo"
