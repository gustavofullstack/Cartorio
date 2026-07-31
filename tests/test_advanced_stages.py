import pytest
from brain.enotariado_engine import ENotariadoEngine
from brain.usucapiao_adjudicacao_workflow import ExtrajudicialWorkflowEngine
from brain.estremacao_engine import EstremacaoEngine
from brain.succession_engine import SuccessionEngine

def test_enotariado_jurisdiction():
    res = ENotariadoEngine.verify_territorial_jurisdiction("Uberlândia/MG", "Uberlândia/MG", "Uberlândia")
    assert res["is_competent"] is True

    res2 = ENotariadoEngine.verify_territorial_jurisdiction("Belo Horizonte/MG", "São Paulo/SP", "Uberlândia")
    assert res2["is_competent"] is False

def test_usucapiao_adjudicacao_workflow():
    u_res = ExtrajudicialWorkflowEngine.get_usucapiao_stage_info(3)
    assert u_res["stage_info"]["name"] == "Lavratura da Ata Notarial"

    a_res = ExtrajudicialWorkflowEngine.get_adjudicacao_stage_info(4)
    assert a_res["stage_info"]["name"] == "Lavratura da Ata Notarial de Adjudicação"

def test_estremacao_validation():
    appr = EstremacaoEngine.validate_estremacao_requirements(6.0, True, True, True)
    assert appr["is_approved"] is True

    pend = EstremacaoEngine.validate_estremacao_requirements(3.0, False, True, True)
    assert pend["is_approved"] is False
    assert len(pend["issues"]) >= 2

def test_succession_shares():
    res = SuccessionEngine.calculate_succession_shares(1000000.0, "Comunhão Parcial de Bens", num_children=2, spouse_alive=True)
    assert res["meacao_spouse"] == 500000.0
    assert res["child_share_each"] == 250000.0

def test_justa_causa_legitima():
    val = SuccessionEngine.validate_justa_causa_legitima(True, "O herdeiro possui histórico comprovado de pródigo e dilapidador de bens.")
    assert val["is_valid"] is True

    inval = SuccessionEngine.validate_justa_causa_legitima(False, "")
    assert inval["is_valid"] is False
