"""Regressoes da camada operacional de balcao, sem misturar o regulatorio."""

from decimal import Decimal

from app.services.emolumento_operacional_balcao import (
    ESCRITURA_FINANCEIRA_BANDS,
    GENERAL_ITEMS,
    TESTAMENTO_ALTERACAO_BANDS,
)
from app.services.emolumento_real_djalma import ATOS_PUBLICADOS_2026


def test_operational_general_table_has_all_29_rows() -> None:
    assert len(GENERAL_ITEMS) == 29
    assert GENERAL_ITEMS["autenticacao"].total == Decimal("11.61")
    assert GENERAL_ITEMS["procuracao"].total == Decimal("71.38")
    assert GENERAL_ITEMS["testamento"].total == Decimal("452.71")
    assert GENERAL_ITEMS["ata_notarial"].total == Decimal("226.15")


def test_regulatory_layer_remains_unchanged() -> None:
    assert ATOS_PUBLICADOS_2026["autenticacao_copia_folha"]["valor_final"] == Decimal("11.21")
    assert ATOS_PUBLICADOS_2026["procuracao_geral"]["valor_final"] == Decimal("68.94")


def test_financial_band_tables_are_complete_and_excess_is_explicit() -> None:
    assert len(ESCRITURA_FINANCEIRA_BANDS) == 25
    assert ESCRITURA_FINANCEIRA_BANDS[-2].ceiling == Decimal("3700000")
    assert ESCRITURA_FINANCEIRA_BANDS[-2].total == Decimal("13034.69")
    assert ESCRITURA_FINANCEIRA_BANDS[-1].per_excess_block
    assert ESCRITURA_FINANCEIRA_BANDS[-1].total == Decimal("2254.46")
    assert len(TESTAMENTO_ALTERACAO_BANDS) == 25
    assert TESTAMENTO_ALTERACAO_BANDS[-2].total == Decimal("6517.35")
    assert TESTAMENTO_ALTERACAO_BANDS[-1].total == Decimal("1127.24")
