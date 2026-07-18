"""Validação fiscal de emolumentos notariais — funções puras.

Isola as regras de validação fiscal (isenção, quantidade de folhas,
adicionais de urgência/folha) da orquestração em `emolumento.py`.

Decisão de design (G8.11.T3 — cartorio-dev 2026-07-18):
- **Single Responsibility**: este módulo conhece APENAS regras fiscais.
  Não acessa DB, Redis, FastAPI ou audit_log.
- **Pure functions**: cada função recebe tipos primitivos / Decimal e
  retorna Decimal ou bool. Sem side effects, sem I/O.
- **Tabela MG 2026**: constantes fiscais (`ADICIONAL_*_PERCENTUAL`,
  `MIN_FOLHAS`, `MAX_FOLHAS`, `MOTIVOS_ISENCAO`, `TIPOS_GRATUITOS`)
  ficam aqui porque são o "contrato fiscal" — não o "contrato de cálculo".
- **HITL preservado**: `isencao_aplicavel()` apenas INDICA elegibilidade.
  A concessão real exige validação humana do tabelião (bot nunca aplica
  sozinho — regra P0 do AGENTS.md).

See also:
- `app/services/emolumento.py` (orchestration: CalculoEmolumento, calcular)
- `app/services/emolumento_cache.py` (cache Redis 24h)
- `.harness/STANDARDS.md` §2 (SOLID SRP)
- Lesson 225 (Wave 43 retry — cartorio-dev 2026-07-18)
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Final


# ============================================================================
# Constantes fiscais — Tabela MG 2026 (placeholder até carga oficial DO)
# ============================================================================

#: Percentual aplicado por folha adicional a partir da 2a (5%).
ADICIONAL_FOLHA_PERCENTUAL: Final[Decimal] = Decimal("0.05")

#: Percentual de adicional para ato em regime de urgência (50%).
ADICIONAL_URGENCIA_PERCENTUAL: Final[Decimal] = Decimal("0.50")

#: Quantidade mínima de folhas para um ato notarial válido.
MIN_FOLHAS: Final[int] = 1

#: Quantidade máxima de folhas (acima disso exige 분할 lavratura).
MAX_FOLHAS: Final[int] = 1000

#: Tipos de ato cuja gratuidade é automática por lei (não dependem de motivo).
TIPOS_GRATUITOS: Final[frozenset[str]] = frozenset(
    {"registro_nascimento", "registro_obito"},
)

#: Motivos válidos para requerer isenção (após validação humana do tabelião).
MOTIVOS_ISENCAO: Final[frozenset[str]] = frozenset(
    {
        "justica_gratuita",
        "entidade_filantropica",
        "programa_social",
    },
)


# ============================================================================
# Validação de tipo e quantidade
# ============================================================================


def validar_tipo(tipo: str, tipos_validos: frozenset[str]) -> None:
    """Levanta ``ValueError`` se ``tipo`` não consta em ``tipos_validos``.

    Args:
        tipo: identificador do ato (ex.: "escritura_compra_venda").
        tipos_validos: conjunto de tipos aceitos pela tabela ativa.

    Raises:
        ValueError: com lista ordenada dos tipos válidos para diagnóstico.
    """
    if tipo not in tipos_validos:
        raise ValueError(
            f"tipo desconhecido: {tipo!r}. Validos: {sorted(tipos_validos)}",
        )


def validar_quantidade_folhas(folhas: int) -> None:
    """Levanta ``ValueError`` se ``folhas`` está fora de [MIN_FOLHAS, MAX_FOLHAS].

    Args:
        folhas: número de folhas do ato notarial.

    Raises:
        ValueError: se folhas < 1 ou folhas > 1000 (T043/T044).
    """
    if folhas < MIN_FOLHAS or folhas > MAX_FOLHAS:
        raise ValueError(
            f"folhas deve estar entre {MIN_FOLHAS} e {MAX_FOLHAS}, recebeu {folhas}",
        )


def aplicar_limite_faixa(tipo: str, valor: Decimal) -> Decimal:
    """G8.20.T1: respeita limites MG 2026 (min/max por tipo).

    Se valor < min: retorna min.
    Se valor > max: retorna max.
    Caso contrário: retorna valor original.
    """
    from app.services.emolumento import FAIXAS_EMOLUMENTO_2026

    faixa = FAIXAS_EMOLUMENTO_2026.get(tipo)
    if faixa is None:
        return valor
    if valor < faixa["min"]:
        return faixa["min"]
    if valor > faixa["max"]:
        return faixa["max"]
    return valor


# ============================================================================
# Cálculos de adicionais (funções puras — sem I/O)
# ============================================================================


def calcular_adicional_folhas(base: Decimal, folhas: int) -> Decimal:
    """Retorna o adicional por folhas extras a partir da 2a.

    Regra MG 2026: 5% do valor base por folha adicional.

    Args:
        base: valor base do ato (Decimal, precisão monetária).
        folhas: número total de folhas (>=1).

    Returns:
        ``base * ADICIONAL_FOLHA_PERCENTUAL * max(0, folhas - 1)``.
    """
    return base * ADICIONAL_FOLHA_PERCENTUAL * max(0, folhas - 1)


def calcular_adicional_urgencia(base: Decimal, urgencia: bool) -> Decimal:
    """Retorna o adicional de urgência (50% do valor base) se ``urgencia``.

    Args:
        base: valor base do ato.
        urgencia: ``True`` se ato em regime de urgência justificada.

    Returns:
        ``base * ADICIONAL_URGENCIA_PERCENTUAL`` ou ``Decimal("0")``.
    """
    return base * ADICIONAL_URGENCIA_PERCENTUAL if urgencia else Decimal("0")


def quantize_bancario(valor: Decimal) -> Decimal:
    """Arredonda para 2 casas decimais com regra bancária (ROUND_HALF_UP)."""
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ============================================================================
# Validação fiscal de isenção
# ============================================================================


def isencao_aplicavel(tipo: str, *, motivo: str) -> bool:
    """Indica se um ato é elegível a isenção por motivo legal.

    ATENÇÃO: esta função APENAS indica elegibilidade. A concessão real
    exige validação humana do tabelião (regra P0 do AGENTS.md — bot NUNCA
    aplica sozinho).

    Args:
        tipo: identificador do ato.
        motivo: justificativa informada pelo escrevente.

    Returns:
        ``True`` se ``tipo`` é gratuíto por lei OU se ``motivo`` consta
        na whitelist ``MOTIVOS_ISENCAO``.
    """
    if tipo in TIPOS_GRATUITOS:
        return True
    return motivo in MOTIVOS_ISENCAO
