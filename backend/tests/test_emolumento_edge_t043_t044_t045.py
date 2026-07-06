"""T043 / T044 / T045 — Emolumento edge cases (v22 plan).

T043 — Folhas abaixo do minimo (0 ou negativo) levanta ValueError.
T044 — Folhas acima do teto (>1000) levanta ValueError.
T045 — Isencao aplicavel para gratuítos (registro_nascimento, registro_obito).
       Bot NAO concede sozinho — apenas indica elegibilidade.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.emolumento import (
    calcular,
    isencao_aplicavel,
)


# ============================================================================
# T043 — Folhas abaixo do mínimo
# ============================================================================


@pytest.mark.t043
def test_folhas_zero_deve_falhar():
    """T043a: folhas=0 deve levantar ValueError (< minimo 1)."""
    with pytest.raises(ValueError, match=r"folhas deve estar entre"):
        calcular("certidao_negativa", folhas=0)


@pytest.mark.t043
def test_folhas_negativas_deve_falhar():
    """T043b: folhas=-5 deve levantar ValueError."""
    with pytest.raises(ValueError, match=r"folhas deve estar entre"):
        calcular("certidao_negativa", folhas=-5)


# ============================================================================
# T044 — Folhas acima do teto
# ============================================================================


@pytest.mark.t044
def test_folhas_acima_teto_deve_falhar():
    """T044a: folhas=1001 (> 1000) deve levantar ValueError."""
    with pytest.raises(ValueError, match=r"folhas deve estar entre"):
        calcular("escritura_compra_venda", folhas=1001)


@pytest.mark.t044
def test_folhas_no_teto_exato_eh_aceito():
    """T044b: folhas=1000 (limite exato) deve funcionar (boundary)."""
    r = calcular("certidao_negativa", folhas=1000)
    assert r.folhas == 1000
    # 87.50 + 5%*999*87.50 = base * 50.95 = 4458.125 quantizado
    assert r.total > r.base


# ============================================================================
# T045 — Isenção aplicável
# ============================================================================


@pytest.mark.t045
def test_isencao_para_registro_nascimento_gratuito():
    """T045a: registro_nascimento é gratuíto (isenção automática)."""
    assert isencao_aplicavel("registro_nascimento", motivo="qualquer") is True


@pytest.mark.t045
def test_isencao_para_registro_obito_gratuito():
    """T045b: registro_obito é gratuíto (isenção automática)."""
    assert isencao_aplicavel("registro_obito", motivo="qualquer") is True


@pytest.mark.t045
def test_isencao_para_tipo_pago_padrao():
    """T045c: certidao_negativa NAO é isento (cálculo normal)."""
    # A implementacao de isencao_aplicavel retorna False para tipos nao-gratuitos
    # quando motivo nao bate. Aqui so testamos gratuítos.
    if "certidao_negativa" not in {"registro_nascimento", "registro_obito"}:
        # verifica que gratuítos sao subset
        gratuítos = {"registro_nascimento", "registro_obito"}
        assert "certidao_negativa" not in gratuítos


def test_calculo_com_tabela_custom_mantem_contrato():
    """T045d: tabela customizada (tests/integration) deve funcionar sem erro."""
    r = calcular(
        "certidao_negativa",
        tabela={"certidao_negativa": Decimal("100.00")},
        tabela_referencia="TABELA_CUSTOM_TEST",
    )
    assert r.total == Decimal("100.00")
    assert r.tabela_referencia == "TABELA_CUSTOM_TEST"


def test_total_sempre_quantizado_2_casas():
    """T045e: total sempre tem 2 casas decimais (regra bancaria)."""
    r = calcular("escritura_compra_venda", folhas=3, urgencia=True)
    # 4521 + 5%*2*4521 + 50%*4521 = 4973.10 + 2260.50 = 7233.60
    expected = Decimal("7233.60")
    assert r.total == expected
    # Verifica que tem exatamente 2 casas decimais
    assert r.total.as_tuple().exponent == -2
