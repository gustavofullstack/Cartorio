import pytest
from brain.validations import ActValidations

def test_checklist_validation_approved():
    provided = [
        "Certidão de Óbito",
        "RG e CPF das Partes",
        "Certidão de Casamento",
        "Certidão Receita Federal",
        "Certidão ITCMD",
        "Certidão Municipal IPTU",
        "Matrícula do Imóvel",
        "Certidão CENSEC Testamento"
    ]
    res = ActValidations.validate_document_checklist("Inventário e Partilha", provided)
    assert res["status"] == "APPROVED"
    assert len(res["missing_mandatory_documents"]) == 0

def test_checklist_validation_pending():
    provided = [
        "Certidão de Óbito",
        "RG e CPF das Partes"
    ]
    res = ActValidations.validate_document_checklist("Inventário e Partilha", provided)
    assert res["status"] == "PENDING_DOCS"
    assert len(res["missing_mandatory_documents"]) > 0

def test_mandatory_clauses():
    draft = "Sob as penas da lei, declaro que as afirmações prestadas são a exata expressão da verdade com posse mansa e pacífica."
    res = ActValidations.validate_mandatory_clauses("Usucapião", draft)
    assert res["is_valid"] is True
