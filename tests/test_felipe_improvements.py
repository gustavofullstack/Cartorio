import pytest
from brain.felipe_templates import FelipeNotaryTemplates
from brain.drafting_engine import DraftingEngine
from brain.jurisprudence_matrix import JurisprudenceMatrix

def test_felipe_templates_retrieval():
    tmpl = FelipeNotaryTemplates.get_template("email_matriculas")
    assert "Felipe Pizarro" in tmpl
    assert "Lei 8.935/94" in tmpl

def test_drafting_engine_testamento():
    engine = DraftingEngine()
    draft = engine.draft_testamento_diligencia({
        "nome_testador": "Carlos Eduardo",
        "qualificacao_testador": "brasileiro, maior, solteiro",
        "nome_medico": "Dr. Fernando Costa",
        "crm_medico": "54321-MG"
    })
    assert "Felipe Pizarro" in draft
    assert "Carlos Eduardo" in draft
    assert "Dr. Fernando Costa" in draft
    assert "CENSEC" in draft

def test_drafting_engine_email():
    engine = DraftingEngine()
    email = engine.generate_email_exigencia_matriculas()
    assert "Provimento Conjunto CGJ-MG nº 93/2020" in email
    assert "Felipe Pizarro" in email

def test_jurisprudence_matrix_search():
    res = JurisprudenceMatrix.search_precedents("Nancy Andrighi")
    assert len(res) > 0
    assert "REsp 1.836.584/MG" in res[0]["source"]
