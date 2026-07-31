import pytest
from brain.calculations import EmolumentCalculations

def test_calculate_emoluments():
    res = EmolumentCalculations.calculate_emoluments(150000.0, "Escritura")
    assert res["base_emolument"] > 0
    assert res["total_emolument_fee"] > res["base_emolument"]
    assert res["asset_value"] == 150000.0

def test_compare_doacao_vs_compra_venda():
    res = EmolumentCalculations.compare_doacao_vs_compra_venda(500000.0, itcmd_rate=0.04, itbi_rate=0.02)
    assert res["property_value"] == 500000.0
    assert res["doacao"]["tax_amount"] == 20000.0 # 4% of 500k
    assert res["compra_e_venda"]["tax_amount"] == 10000.0 # 2% of 500k
    assert res["cheaper_option"] == "Compra e Venda (ITBI)"
    assert res["difference"] == 10000.0

def test_negative_value_error():
    with pytest.raises(ValueError):
        EmolumentCalculations.calculate_emoluments(-1000.0)
