"""Regressoes da camada operacional de balcao, sem misturar o regulatorio."""

from decimal import Decimal

from app.services.emolumento_operacional_balcao import (
    ESCRITURA_FINANCEIRA_BANDS,
    GENERAL_ITEMS,
    TESTAMENTO_ALTERACAO_BANDS,
    calcular_emolumento_operacional,
)
from app.services.emolumento_real_djalma import ATOS_PUBLICADOS_2026


def test_operational_general_table_has_all_32_rows() -> None:
    assert len(GENERAL_ITEMS) == 32
    assert GENERAL_ITEMS["autenticacao"].total == Decimal("11.61")
    assert GENERAL_ITEMS["autenticacao_documento_eletronico"].total == Decimal("13.91")
    assert GENERAL_ITEMS["procuracao"].total == Decimal("71.38")
    assert GENERAL_ITEMS["procuracao_financeira"].total == Decimal("226.14")
    assert GENERAL_ITEMS["procuracao_inss"].total == Decimal("37.91")
    assert GENERAL_ITEMS["reconhecimento_firma"].total == Decimal("11.61")
    assert GENERAL_ITEMS["reconhecimento_dut_atpv"].total == Decimal("16.61")
    assert GENERAL_ITEMS["xerox_1_face"].total == Decimal("1.80")
    assert GENERAL_ITEMS["xerox_2_faces"].total == Decimal("3.60")
    assert GENERAL_ITEMS["testamento"].total == Decimal("452.71")
    assert GENERAL_ITEMS["ata_notarial"].total == Decimal("226.15")


def test_calcular_emolumento_operacional_published_e_hitl() -> None:
    r_proc = calcular_emolumento_operacional("procuracao")
    assert r_proc["status"] == "PUBLISHED"
    assert r_proc["total"] == "71.38"
    assert r_proc["pricing_layer"] == "operational_pos_2notas"

    r_proc_fin = calcular_emolumento_operacional("procuracao_financeira")
    assert r_proc_fin["status"] == "PUBLISHED"
    assert r_proc_fin["total"] == "226.14"

    r_proc_inss = calcular_emolumento_operacional("procuracao_inss")
    assert r_proc_inss["status"] == "PUBLISHED"
    assert r_proc_inss["total"] == "37.91"

    r_dut = calcular_emolumento_operacional("dut_atpv")
    assert r_dut["status"] == "PUBLISHED"
    assert r_dut["total"] == "16.61"

    r_aut_eletr = calcular_emolumento_operacional("autenticacao_documento_eletronico")
    assert r_aut_eletr["status"] == "PUBLISHED"
    assert r_aut_eletr["total"] == "13.91"

    r_urg = calcular_emolumento_operacional("procuracao", urgencia=True)
    assert r_urg["status"] == "HITL_REQUIRED"


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
