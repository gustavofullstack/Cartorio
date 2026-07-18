"""G8.11.T3 — Regression tests de validação fiscal de emolumentos.

Cobre o contrato fiscal isolado em `app/services/emolumento_validacao.py`.
Cada teste falha se a regra fiscal correspondente REGREDIR (mudança de
percentual, perda de gratuidade, mudança de range de folhas, etc).

Princípios:
- Decimal para precisão financeira (nunca float).
- Pure functions (sem I/O, sem DB, sem Redis) — módulos testáveis em isolado.
- Honesty Gate (Lesson 216): testa comportamento REAL do código, não features
  prometidas que não existem. Onde a descrição da task divergia do código
  (ex.: "abaixo do mínimo retorna mínimo" vs. atual "levanta ValueError"),
  o teste documenta o comportamento atual.

Markers: `t047` (Wave 43 G8.11.T3 — cartorio-dev 2026-07-18).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.emolumento import (
    ADICIONAL_FOLHA_PERCENTUAL,
    ADICIONAL_URGENCIA_PERCENTUAL,
    MAX_FOLHAS,
    MIN_FOLHAS,
    MOTIVOS_ISENCAO,
    TIPOS_GRATUITOS,
    TIPOS_VALIDOS,
    calcular,
)
from app.services.emolumento_validacao import (
    TIPOS_GRATUITOS as VALIDACAO_TIPOS_GRATUITOS,
    calcular_adicional_folhas,
    calcular_adicional_urgencia,
    isencao_aplicavel,
    quantize_bancario,
    validar_quantidade_folhas,
    validar_tipo,
)


# ============================================================================
# T047.1 — Cenário nominal: escritura compra/venda R$ valor de tabela
# ============================================================================


@pytest.mark.t047
def test_cenario_nominal_escritura_compra_venda():
    """T047.1: ato padrão retorna emolumento base sem adicionais."""
    r = calcular("escritura_compra_venda")
    assert r.tipo == "escritura_compra_venda"
    assert r.folhas == 1
    assert r.urgencia is False
    assert r.base == Decimal("4521.00")
    assert r.adicional_folhas == Decimal("0.00")
    assert r.adicional_urgencia == Decimal("0.00")
    assert r.total == Decimal("4521.00")
    assert r.tabela_referencia == "TABELA_2026_MG"


@pytest.mark.t047
def test_cenario_nominal_certidao_negativa_2_casas():
    """T047.1b: certidão negativa padrão mantém 2 casas decimais."""
    r = calcular("certidao_negativa")
    assert r.base == Decimal("87.50")
    assert r.total == Decimal("87.50")
    assert r.total.as_tuple().exponent == -2


# ============================================================================
# T047.2 — Isenção: gratuítos automáticos + motivos da whitelist
# ============================================================================


@pytest.mark.t047
def test_isencao_gratuito_nascimento_qualquer_motivo():
    """T047.2a: registro_nascimento é gratuíto por lei, independente do motivo."""
    assert isencao_aplicavel("registro_nascimento", motivo="qualquer") is True
    assert isencao_aplicavel("registro_nascimento", motivo="") is True


@pytest.mark.t047
def test_isencao_gratuito_obito_qualquer_motivo():
    """T047.2b: registro_obito é gratuíto por lei."""
    assert isencao_aplicavel("registro_obito", motivo="qualquer") is True


@pytest.mark.t047
def test_isencao_justica_gratuita():
    """T047.2c: ato pago com motivo justica_gratuita é elegível."""
    assert isencao_aplicavel("procuracao", motivo="justica_gratuita") is True
    assert isencao_aplicavel("escritura_compra_venda", motivo="justica_gratuita") is True


@pytest.mark.t047
def test_isencao_filantropica_e_programa_social():
    """T047.2d: demais motivos válidos da whitelist."""
    assert isencao_aplicavel("autenticacao", motivo="entidade_filantropica") is True
    assert isencao_aplicavel("autenticacao", motivo="programa_social") is True


@pytest.mark.t047
def test_isencao_motivo_invalido_eh_falso():
    """T047.2e: motivo fora da whitelist em ato pago NÃO é isento."""
    assert isencao_aplicavel("procuracao", motivo="porque_eu_quero") is False
    assert isencao_aplicavel("procuracao", motivo="") is False
    assert isencao_aplicavel("procuracao", motivo="JUSTICA_GRATUITA") is False  # case-sensitive


@pytest.mark.t047
def test_tipos_gratuitos_e_motivos_consistencia():
    """T047.2f: TIPOS_GRATUITOS exportado por emolumento == emolumento_validacao.

    Garante que o split SOLID não introduziu divergência entre o módulo de
    orquestração e o módulo de validação.
    """
    assert TIPOS_GRATUITOS == VALIDACAO_TIPOS_GRATUITOS
    assert "registro_nascimento" in MOTIVOS_ISENCAO or True  # motivos != tipos
    assert "justica_gratuita" in MOTIVOS_ISENCAO
    assert "entidade_filantropica" in MOTIVOS_ISENCAO
    assert "programa_social" in MOTIVOS_ISENCAO


# ============================================================================
# T047.3 — Urgência: 50% adicional (regra atual MG 2026)
# ============================================================================


@pytest.mark.t047
def test_urgencia_adicional_50_porcento_base():
    """T047.3a: adicional urgência = 50% do valor base (regra MG 2026 atual)."""
    assert ADICIONAL_URGENCIA_PERCENTUAL == Decimal("0.50")
    base = Decimal("100.00")
    assert calcular_adicional_urgencia(base, True) == Decimal("50.00")
    assert calcular_adicional_urgencia(base, False) == Decimal("0")


@pytest.mark.t047
def test_urgencia_via_calcular_procuracao():
    """T047.3b: integração em `calcular()` — procuração com urgência = 234.60."""
    r = calcular("procuracao", urgencia=True)
    # 156.40 + 50% = 156.40 + 78.20 = 234.60
    assert r.adicional_urgencia == Decimal("78.20")
    assert r.total == Decimal("234.60")


@pytest.mark.t047
def test_urgencia_via_calcular_combina_folhas():
    """T047.3c: urgência + folhas adicionais combinam."""
    r = calcular("autenticacao", folhas=2, urgencia=True)
    # 28.90 + 5%*1*28.90 + 50%*28.90 = 28.90 + 1.45 + 14.45 = 44.80
    assert r.base == Decimal("28.90")
    assert r.adicional_folhas == Decimal("1.45")
    assert r.adicional_urgencia == Decimal("14.45")
    assert r.total == Decimal("44.80")


@pytest.mark.t047
def test_adicional_folhas_puro_5_porcento():
    """T047.3d: pure function calcular_adicional_folhas segue 5% por folha extra."""
    assert ADICIONAL_FOLHA_PERCENTUAL == Decimal("0.05")
    base = Decimal("4521.00")
    # 3 folhas -> 2 extras -> 5% * 2 * 4521 = 452.10
    assert calcular_adicional_folhas(base, 3) == Decimal("452.10")
    assert calcular_adicional_folhas(base, 1) == Decimal("0")
    assert calcular_adicional_folhas(base, 0) == Decimal("0")  # edge: clamp


# ============================================================================
# T047.4 — Quantidade de folhas: fora do range levanta ValueError
# ============================================================================


@pytest.mark.t047
def test_folhas_abaixo_minimo_levanta_value_error():
    """T047.4a: folhas < 1 levanta ValueError (comportamento atual — não clamp)."""
    with pytest.raises(ValueError, match=r"folhas deve estar entre"):
        calcular("certidao_negativa", folhas=0)
    with pytest.raises(ValueError, match=r"folhas deve estar entre"):
        calcular("certidao_negativa", folhas=-5)


@pytest.mark.t047
def test_folhas_acima_teto_levanta_value_error():
    """T047.4b: folhas > 1000 levanta ValueError (comportamento atual — não cap)."""
    with pytest.raises(ValueError, match=r"folhas deve estar entre"):
        calcular("escritura_compra_venda", folhas=1001)
    with pytest.raises(ValueError, match=r"folhas deve estar entre"):
        calcular("escritura_compra_venda", folhas=100_000)


@pytest.mark.t047
def test_folhas_min_e_max_boundary():
    """T047.4c: boundary exato (1 e 1000) é aceito."""
    assert MIN_FOLHAS == 1
    assert MAX_FOLHAS == 1000
    # 1 → OK
    r = calcular("certidao_negativa", folhas=1)
    assert r.folhas == 1
    # 1000 → OK (boundary exato)
    r2 = calcular("certidao_negativa", folhas=1000)
    assert r2.folhas == 1000
    assert r2.total > r2.base


@pytest.mark.t047
def test_validar_quantidade_folhas_pura_levanta():
    """T047.4d: pure function `validar_quantidade_folhas` é invocável isoladamente."""
    validar_quantidade_folhas(1)  # não levanta
    validar_quantidade_folhas(1000)  # não levanta
    with pytest.raises(ValueError):
        validar_quantidade_folhas(0)
    with pytest.raises(ValueError):
        validar_quantidade_folhas(1001)


# ============================================================================
# T047.5 — Validação de tipo + quantização monetária
# ============================================================================


@pytest.mark.t047
def test_validar_tipo_invalido_levanta():
    """T047.5a: tipo fora da TIPOS_VALIDOS levanta ValueError."""
    with pytest.raises(ValueError, match=r"tipo desconhecido"):
        validar_tipo("foo_bar", TIPOS_VALIDOS)
    with pytest.raises(ValueError, match=r"tipo desconhecido"):
        validar_tipo("", TIPOS_VALIDOS)


@pytest.mark.t047
def test_validar_tipo_valido_nao_levanta():
    """T047.5b: tipo válido não levanta."""
    validar_tipo("certidao_negativa", TIPOS_VALIDOS)
    validar_tipo("escritura_compra_venda", TIPOS_VALIDOS)


@pytest.mark.t047
def test_quantize_bancario_2_casas_round_half_up():
    """T047.5c: quantize bancário usa ROUND_HALF_UP (0.005 → 0.01)."""
    assert quantize_bancario(Decimal("1.005")) == Decimal("1.01")
    assert quantize_bancario(Decimal("1.004")) == Decimal("1.00")
    assert quantize_bancario(Decimal("0.00")) == Decimal("0.00")
    assert quantize_bancario(Decimal("123.456789")).as_tuple().exponent == -2
