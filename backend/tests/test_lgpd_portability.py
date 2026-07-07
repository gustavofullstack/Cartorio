"""Testes para export de dados (LGPD Art. 18 V)."""

from app.services.lgpd.portability import export_cliente_data, export_to_json


def test_export_cliente_data_schema():
    data = export_cliente_data(cliente_id=123)
    assert data["cliente_id"] == 123
    assert "dados_pessoais" in data
    assert "conversas" in data
    assert "protocolos" in data
    assert "documentos" in data
    assert "auditoria" in data
    assert data["formato"] == "JSON"


def test_export_to_json_valido():
    data = {"a": 1, "b": "teste"}
    result = export_to_json(data)
    assert '"a": 1' in result
    assert '"b": "teste"' in result


def test_export_to_json_utf8():
    data = {"nome": "José da Silva"}
    result = export_to_json(data)
    assert "José" in result
