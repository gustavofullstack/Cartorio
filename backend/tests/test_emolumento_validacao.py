"""G8.11.T3 + G8.20.T4 — Regression tests de validação fiscal de emolumentos.

Cobre o contrato fiscal isolado em `app/services/emolumento_validacao.py`.
Cada teste falha se a regra fiscal correspondente REGREDIR (mudança de
percentual, perda de gratuidade, mudança de range de folhas, etc).

Princípios:
- Decimal para precisão financeira (nunca float).
- Pure functions (sem I/O, sem DB, sem Redis) — módulos testáveis em isolado.
- Honesty Gate (Lesson 216 / 225): testa comportamento REAL do código, não features
  prometidas que não existem. Onde a descrição da task divergia do código
  (ex.: "abaixo do mínimo retorna mínimo" vs. atual "levanta ValueError"),
  o teste documenta o comportamento atual explicitamente no docstring.

Markers:
- `t047` (Wave 43 G8.11.T3 — cartorio-dev 2026-07-18): split SOLID + 19 testes base.
- `t048` (Wave 47+ G8.20.T4 — cartorio-dev 2026-07-18): 15 testes adicionais
  — parametrização de bordas, sentinelas de constantes fiscais e regressão.
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
    aplicar_limite_faixa,
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


# ============================================================================
# T048 — Limites parametrizados, sentinelas de constantes e regressão fiscal
# ============================================================================
# G8.20.T4 (cartorio-dev 2026-07-18): cada teste documenta a regra MG 2026
# ATUAL e falha silenciosamente se a constante fiscal correspondente mudar.
#
# Escopo:
# - Parametrização de bordas de folhas (MIN/MAX boundary)
# - Parametrização de quantize_bancario (todos os arredondamentos críticos)
# - Parametrização de isencao_aplicavel (todos MOTIVOS_ISENCAO × atos pagos)
# - Sentinelas de constantes (regression: TIPOS_GRATUITOS, MOTIVOS_ISENCAO,
#   ADICIONAL_*, MIN/MAX_FOLHAS imutáveis)
# - Casos de borda da regra de urgência (base=0, base=máxima)
# - Onde a descrição da task diverge (ex.: "retorna mínimo" vs. atual
#   "ValueError"), o teste documenta explicitamente o comportamento real.
# ============================================================================


@pytest.mark.t048
@pytest.mark.parametrize(
    "folhas_validas",
    [1, 2, 5, 100, 999, 1000],
    ids=["min_exato", "min_mais_um", "faixa_media", "centenares", "limite_menos_um", "teto_exato"],
)
def test_folhas_validas_boundary_parametrizado(folhas_validas):
    """T048.1a: folhas em [MIN_FOLHAS=1, MAX_FOLHAS=1000] são aceitas.

    Regra MG 2026: range fechado. Boundary 1 e 1000 inclusivos.
    Cobre TODOS os pontos críticos de borda via parametrize (cartorio-dev
    2026-07-18 — Wave 47+). Garante que mudança acidental de
    MIN_FOLHAS/MAX_FOLHAS falhe com casos específicos.
    """
    validar_quantidade_folhas(folhas_validas)  # nao levanta
    # tambem via orquestrador
    r = calcular("certidao_negativa", folhas=folhas_validas)
    assert r.folhas == folhas_validas


@pytest.mark.t048
@pytest.mark.parametrize(
    "folhas_invalidas",
    [0, -1, -100, 1001, 5000, 100_000],
    ids=["abaixo_zero", "menos_um", "neg_centenares", "acima_teto", "ordem_grande", "muito_acima"],
)
def test_folhas_invalidas_levanta_value_error_parametrizado(folhas_invalidas):
    """T048.1b: folhas fora de [1, 1000] levanta ValueError.

    Regra MG 2026 (comportamento atual — Honesty Gate Lesson 216/225):
    - ABAIXO do minimo: levanta ValueError (NAO retorna minimo nem faz clamp)
    - ACIMA do teto:    levanta ValueError (NAO cap no teto nem faz clamp)

    Note: a task description original G8.20.T4 mencionava "valor abaixo
    -> retorna minimo" e "valor acima -> cap no teto", mas o codigo
    atual RAISE ValueError (decisao do Wave 43 — ver Lesson 225). Este
    teste documenta o comportamento REAL e falha se a implementacao
    mudar para clamp/return-min sem atualizacao consciente (decisao
    arquitetural separada, nao toca em fiscal rules).
    """
    with pytest.raises(ValueError, match=r"folhas deve estar entre"):
        validar_quantidade_folhas(folhas_invalidas)
    with pytest.raises(ValueError, match=r"folhas deve estar entre"):
        calcular("escritura_compra_venda", folhas=folhas_invalidas)


@pytest.mark.t048
@pytest.mark.parametrize(
    "motivo",
    [
        "justica_gratuita",
        "entidade_filantropica",
        "programa_social",
    ],
)
def test_isencao_motivo_whitelist_aceito_todos_tipos_pagos(motivo):
    """T048.2a: cada motivo da whitelist MOTIVOS_ISENCAO e valido para
    QUALQUER ato pago (nao gratuíto).

    Regra MG 2026 (Lei 6.830/1980 + provimentos CNJ): motivo + validacao
    humana do tabeliao (P0 — bot nunca aplica sozinho). Aqui so testamos
    a elegibilidade (funcao pura `isencao_aplicavel`), nao a concessao.
    """
    # Cobrimos todos os 3 atos pagos principais
    for tipo_pago in ("escritura_compra_venda", "procuracao", "autenticacao"):
        assert isencao_aplicavel(tipo_pago, motivo=motivo) is True, (
            f"motivo {motivo!r} deveria ser whitelist para {tipo_pago}"
        )


@pytest.mark.t048
@pytest.mark.parametrize(
    "motivo_invalido",
    [
        "porque_eu_quero",
        "JUSTICA_GRATUITA",  # case-sensitive
        "justica gratuita",  # espaco invalido
        " ",  # whitespace
        "x" * 1000,  # estressar tamanho
        "😀",  # unicode nao mapeado
    ],
    ids=[
        "arbitrario",
        "case_diferente",
        "com_espaco",
        "whitespace",
        "estresse_tamanho",
        "unicode",
    ],
)
def test_isencao_motivo_invalido_rejeitado_tipos_pagos(motivo_invalido):
    """T048.2b: motivo fora da whitelist EM ato pago retorna False.

    Regra MG 2026: whitelist EXATA, case-sensitive, sem normalizacao
    automatica (HITL tabeliao decide, bot nao normaliza).
    """
    assert isencao_aplicavel("escritura_compra_venda", motivo=motivo_invalido) is False
    assert isencao_aplicavel("procuracao", motivo=motivo_invalido) is False


@pytest.mark.t048
@pytest.mark.parametrize(
    "tipo_gratuito",
    ["registro_nascimento", "registro_obito"],
    ids=["nascimento", "obito"],
)
def test_isencao_gratuito_predomina_sobre_motivo_invalido(tipo_gratuito):
    """T048.2c: gratuidade LEI (TIPOS_GRATUITOS) predomina sobre motivo.

    Regra MG 2026 (art. 7 Lei 6.015/73 + CNJ): atos gratuitos por lei
    sao isentos INDEPENDENTEMENTE do motivo informado. Ordem de checagem
    na implementacao: gratuidade primeiro, motivo depois.
    """
    # motivo invalido NAO cancela gratuidade LEI
    assert isencao_aplicavel(tipo_gratuito, motivo="invalido") is True
    # motivo vazio NAO cancela gratuidade LEI
    assert isencao_aplicavel(tipo_gratuito, motivo="") is True
    # motivo valido da whitelist + gratuidade = True (redundante)
    assert isencao_aplicavel(tipo_gratuito, motivo="justica_gratuita") is True


@pytest.mark.t048
@pytest.mark.parametrize(
    "valor,esperado",
    [
        (Decimal("0.00"), Decimal("0.00")),
        (Decimal("0.004"), Decimal("0.00")),  # round-down
        (Decimal("0.005"), Decimal("0.01")),  # ROUND_HALF_UP canonico
        (Decimal("0.006"), Decimal("0.01")),  # round-up
        (Decimal("0.014"), Decimal("0.01")),
        (Decimal("0.015"), Decimal("0.02")),
        (Decimal("0.025"), Decimal("0.03")),
        (Decimal("1.0049"), Decimal("1.00")),  # edge perto de meio
        (Decimal("1.005"), Decimal("1.01")),  # canonico
        (Decimal("1.0051"), Decimal("1.01")),  # logo acima de meio
        (Decimal("2.725"), Decimal("2.73")),  # tres casas
        (Decimal("99.999"), Decimal("100.00")),  # carry-over
        (Decimal("-0.005"), Decimal("-0.01")),  # sinal negativo half-up
    ],
    ids=[
        "zero",
        "004_round_down",
        "005_half_up",
        "006_round_up",
        "014_round_down",
        "015_half_up",
        "025_half_up",
        "0049_perto_meio",
        "1005_canonico",
        "0051_acima_meio",
        "2725_tres_casas",
        "99999_carry",
        "negativo_half_up",
    ],
)
def test_quantize_bancario_parametrizado_round_half_up_canonico(valor, esperado):
    """T048.3a: quantize_bancario usa ROUND_HALF_UP canonico (TABELA MG 2026).

    Regra bancaria brasileira: arredondamento sempre para cima em caso
    de empate (.5 exato). Cobre 13 bordas criticas via parametrize
    (cartorio-dev 2026-07-18). Qualquer alteracao do modo de
    arredondamento (ex.: ROUND_HALF_EVEN / banker's rounding)
    falharia com multiplos casos.
    """
    assert quantize_bancario(valor) == esperado


@pytest.mark.t048
@pytest.mark.parametrize(
    "folhas,esperado",
    [
        (1, Decimal("0")),  # boundary exato
        (2, Decimal("226.05")),  # 4521 * 0.05 * 1
        (3, Decimal("452.10")),  # 4521 * 0.05 * 2
        (5, Decimal("904.20")),  # 4521 * 0.05 * 4
        (10, Decimal("2034.45")),  # 4521 * 0.05 * 9
        (100, Decimal("22378.95")),  # 4521 * 0.05 * 99 = 22378.95
    ],
    ids=[
        "min_exato",
        "uma_extra",
        "duas_extras",
        "quatro_extras",
        "nove_extras",
        "noventa_nove_extras",
    ],
)
def test_adicional_folhas_puro_parametrizado_escritura(folhas, esperado):
    """T048.4a: `calcular_adicional_folhas` para escritura_compra_venda.

    Regra MG 2026: 5% por folha adicional a partir da 2a (extras = max(0,
    folhas - 1)). Base ficticia R$ 4521.00 (escritura_compra_venda da
    tabela placeholder — quando carga oficial chegar, este teste
    falhara conscientemente se tabela nao tiver `escritura_compra_venda`).
    """
    base = Decimal("4521.00")
    assert calcular_adicional_folhas(base, folhas) == esperado


@pytest.mark.t048
@pytest.mark.parametrize(
    "base,urgencia,esperado",
    [
        (Decimal("0.00"), True, Decimal("0")),
        (Decimal("0.00"), False, Decimal("0")),
        (Decimal("28.90"), True, Decimal("14.45")),  # autenticacao + urgencia
        (Decimal("28.90"), False, Decimal("0")),
        (Decimal("4521.00"), True, Decimal("2260.50")),  # escritura + urgencia
        (Decimal("10000.00"), True, Decimal("5000.00")),
    ],
    ids=[
        "zero_urgente",
        "zero_normal",
        "aut_urgente",
        "aut_normal",
        "escritura_urgente",
        "dez_mil_urgente",
    ],
)
def test_adicional_urgencia_parametrizado_valor_extremo(base, urgencia, esperado):
    """T048.4b: `calcular_adicional_urgencia` cobre base 0 e valores grandes.

    Regra MG 2026: 50% do valor base se urgencia justificada. Cobre base=0
    (atos gratuitos com urgencia — embora raros), base=28.90 (autenticacao)
    e bases de 5 casas para confirmar precisao sem perda.
    """
    assert calcular_adicional_urgencia(base, urgencia) == esperado


@pytest.mark.t048
def test_adicional_folhas_zero_folhas_extras_zero_clamps():
    """T048.4c: 0 folhas clampadas para 0 extras (defensiva).

    Honesty Gate: `calcular_adicional_folhas` nao levanta ValueError
    quando folhas=0 (e defensive puro: clamp para 0 extras). A
    validacao de range [1, 1000] e feita em `validar_quantidade_folhas`
    antes. Aqui testamos a funcao pura isoladamente.
    """
    base = Decimal("4521.00")
    assert calcular_adicional_folhas(base, 0) == Decimal("0")
    assert calcular_adicional_folhas(base, -1) == Decimal("0")  # clamp defensivo


@pytest.mark.t048
def test_sentinela_tipos_gratuitos_estavel():
    """T048.5a: TIPOS_GRATUITOS nao muda silenciosamente.

    Regra MG 2026 (Lei 6.015/73 + CNJ): gratuidade LEI e fixa
    (registro_nascimento, registro_obito). Mudar este conjunto exige:
    - alteracao da tabela MG oficial publicada no Diario Oficial
    - review cartorio-lgpd
    - audit log entry

    Mudar este sentinel sem passar pelo fluxo LGPD = regressao grave.
    """
    assert TIPOS_GRATUITOS == frozenset({"registro_nascimento", "registro_obito"})
    assert len(TIPOS_GRATUITOS) == 2  # nao cresce sem justificativa


@pytest.mark.t048
def test_sentinela_motivos_isencao_estavel():
    """T048.5b: MOTIVOS_ISENCAO nao cresce silenciosamente.

    Regra MG 2026: whitelist EXATA de motivos legais. Adicionar novo
    motivo exige publicacao oficial + review cartorio-lgpd.
    """
    assert MOTIVOS_ISENCAO == frozenset(
        {"justica_gratuita", "entidade_filantropica", "programa_social"},
    )
    assert len(MOTIVOS_ISENCAO) == 3


@pytest.mark.t048
def test_sentinela_adicionais_percentuais_estavel():
    """T048.5c: ADICIONAL_FOLHA_PERCENTUAL=5% e ADICIONAL_URGENCIA_PERCENTUAL=50%.

    Regra MG 2026 — tabula de emolumentos: 5% por folha extra e 50% por
    urgencia justificada. Mudar estes valores sem publicacao oficial
    quebra a consistencia fiscal.
    """
    assert ADICIONAL_FOLHA_PERCENTUAL == Decimal("0.05"), "5% por folha extra"
    assert ADICIONAL_URGENCIA_PERCENTUAL == Decimal("0.50"), "50% por urgencia"


@pytest.mark.t048
def test_sentinela_min_max_folhas_estavel():
    """T048.5d: MIN_FOLHAS=1 e MAX_FOLHAS=1000 imutaveis sem revisao.

    Regra MG 2026: range de folhas consistente com pratica cartoraria.
    Acima de 1000 folhas exige `particao em lotes` (workflow juridico
    separado, nao ato unico). Mudar este range sem revisao = quebra
    do contrato fiscal.
    """
    assert MIN_FOLHAS == 1
    assert MAX_FOLHAS == 1000
    assert MAX_FOLHAS >= MIN_FOLHAS


@pytest.mark.t048
@pytest.mark.parametrize(
    "tipo_invalido",
    ["", "foo", "CERTIDAO_NEGATIVA", "certidao_negativa ", "None", "<script>"],
    ids=["vazio", "foo", "case_alto", "trailing_space", "string_none", "xss"],
)
def test_validar_tipo_rejeicao_parametrizada(tipo_invalido):
    """T048.6a: tipo fora de TIPOS_VALIDOS levanta ValueError.

    Cobre 6 bordas de tipo invalido, incluindo tentativas maliciosas
    (XSS via nome). A implementacao nao normaliza/limpa input —
    strict match.
    """
    with pytest.raises(ValueError, match=r"tipo desconhecido"):
        validar_tipo(tipo_invalido, TIPOS_VALIDOS)


@pytest.mark.t048
def test_validar_tipo_aceita_todos_tipos_validos():
    """T048.6b: TODOS os 10 tipos em TIPOS_VALIDOS sao aceitos sem erro.

    Cobertura parametrica completa: garante que tabela placeholder
    do MG 2026 esta sincronizada com a funcao de validacao. Regressao
    silenciosa se tabela crescer sem adicionar ao frozenset TIPOS_VALIDOS.
    """
    assert len(TIPOS_VALIDOS) == 10  # sentinel: 10 atos placeholders
    for tipo in TIPOS_VALIDOS:
        validar_tipo(tipo, TIPOS_VALIDOS)  # nao levanta


@pytest.mark.t048
def test_calcular_integracao_quantize_2_casas_total():
    """T048.7a: `calcular()` retorna total SEMPRE com 2 casas decimais.

    Regra bancaria brasileira: mesmo valores 'redondos' tem que ter
    `.00` explicito (ex.: R$ 100 vira R$ 100.00 em Decimal). Confirma
    que quantize_bancario esta sendo aplicado no campo `total`.
    """
    r = calcular("escritura_compra_venda")  # base redonda R$ 4521
    assert r.total.as_tuple().exponent == -2
    assert r.base.as_tuple().exponent == -2


@pytest.mark.t048
def test_calcular_isencao_gratuito_total_zero():
    """T048.7b: ato gratuíto tem base=0 E total=0 (mesmo com urgencia/folhas).

    Validacao de invariante fiscal: gratuidade LEI zera TODOS os
    componentes (base, adicionais, total). Teste complementar a
    `test_isencao_gratuito_*` — confirma a materializacao financeira.
    """
    # Mesmo com urgencia True + folhas 5, gratuidade LEI zera tudo
    r = calcular("registro_nascimento", folhas=5, urgencia=True)
    assert r.base == Decimal("0.00")
    assert r.adicional_folhas == Decimal("0.00")
    assert r.adicional_urgencia == Decimal("0.00")
    assert r.total == Decimal("0.00")


# ============================================================================
# G8.20.T1 — Faixas placeholder MG 2026 (função pura, sem regra automática)
# ============================================================================


def test_aplicar_limite_abaixo_min():
    """G8.20.T1: valor abaixo de zero respeita o mínimo placeholder da certidão."""
    assert aplicar_limite_faixa("certidao_negativa", Decimal("-0.01")) == Decimal("0.00")


def test_aplicar_limite_acima_max():
    """G8.20.T1: valor acima da faixa respeita o máximo placeholder da certidão."""
    assert aplicar_limite_faixa("certidao_negativa", Decimal("9999")) == Decimal("200.00")


def test_aplicar_limite_dentro_faixa():
    """G8.20.T1: valor dentro da faixa permanece inalterado."""
    assert aplicar_limite_faixa("certidao_negativa", Decimal("100")) == Decimal("100")


def test_aplicar_limite_tipo_desconhecido():
    """G8.20.T1: tipo sem faixa permanece inalterado para preservar compatibilidade."""
    assert aplicar_limite_faixa("tipo_desconhecido", Decimal("100")) == Decimal("100")


def test_calcular_usa_limite_faixa():
    """G8.20.T1: limite puro compõe com calcular sem automatizar decisão jurídica."""
    valor_limitado = aplicar_limite_faixa("certidao_negativa", Decimal("9999"))
    resultado = calcular("certidao_negativa", tabela={"certidao_negativa": valor_limitado})

    assert resultado.base == Decimal("200.00")
    assert resultado.total == Decimal("200.00")
