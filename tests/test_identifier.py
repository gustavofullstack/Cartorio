import pytest
from brain.document_identifier import DocumentIdentifier

def test_identify_usucapiao():
    text = "Ata Notarial de Usucapião Extrajudicial referente ao imóvel urbano com posse mansa e pacífica."
    result = DocumentIdentifier.identify(text, filename="Ata Notarial Usucapião.docx")
    assert result["predicted_category"] == "Usucapião"
    assert result["confidence"] > 0.5

def test_identify_testamento():
    text = "Escritura Pública de Testamento dispondo da legítima dos herdeiros necessários com clausula restritiva."
    result = DocumentIdentifier.identify(text, filename="TESTAMENTO.docx")
    assert result["predicted_category"] == "Testamento"
    assert result["confidence"] > 0.5

def test_identify_inventario():
    text = "Relação de documentos para inventário e partilha de bens com certidão de óbito do de cujus."
    result = DocumentIdentifier.identify(text, filename="01. Relacao de documentos - Inventario.docx")
    assert result["predicted_category"] == "Inventário e Partilha"
    assert result["confidence"] > 0.5

def test_identify_unknown():
    text = "Texto genérico sem termos notariais específicos."
    result = DocumentIdentifier.identify(text, filename="documento_qualquer.txt")
    assert result["predicted_category"] in ["Geral / Outros", "Atos Notariais Diversos"]
