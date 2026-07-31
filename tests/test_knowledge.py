import pytest
from brain.knowledge_base import KnowledgeBaseEngine

def test_query_knowledge():
    kb = KnowledgeBaseEngine()
    result = kb.query_knowledge("Testamento", category="Testamento", limit=5)
    assert "query" in result
    assert result["total_matches"] >= 0
    assert "results" in result

def test_provimento_summary():
    kb = KnowledgeBaseEngine()
    prov_103 = kb.get_provimento_summary("103")
    assert "103/2020" in prov_103["num"]
    assert "Autorização Eletrônica de Viagem" in prov_103["title"]

    prov_149 = kb.get_provimento_summary("149")
    assert "149/2023" in prov_149["num"]
    assert "Código Nacional de Normas" in prov_149["title"]
