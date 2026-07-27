"""Testes de integração para os endpoints REST de emolumentos reais do 2º Ofício de Uberlândia."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_tabela_real_djalma():
    response = client.get("/api/v1/emolumentos/real/djalma")
    assert response.status_code == 200
    data = response.json()
    assert data["cartorio"] == "2º Serviço Notarial de Uberlândia"
    assert data["fonte"]["vigencia_inicio"] == "2026-01-01"
    assert data["fonte"]["sha256"]
    assert any(item["tipo_ato"] == "procuracao_geral" for item in data["itens"])


def test_painel_agent_ai_entrega_interface_sem_dados_de_cliente():
    response = client.get("/api/v1/painel/agent-ai")
    assert response.status_code == 200
    assert "Mesa de" in response.text
    assert "CPF" in response.text
    assert "111.222.333-44" not in response.text


def test_painel_consume_os_campos_do_catalogo_atual():
    catalogo = client.get("/api/v1/inteligencia-dados/agent-ai").json()
    painel = client.get("/api/v1/painel/agent-ai").text
    assert "f.nome" in painel
    assert "f.capturado_em" in painel
    assert "i.ato" in painel
    assert "i.item_portaria" in painel
    assert "i.status" in painel
    assert all({"ato", "item_portaria", "status"}.issubset(item) for item in catalogo["itens"])


def test_dados_agent_ai_expoe_apenas_uso_agregado():
    response = client.get("/api/v1/inteligencia-dados/agent-ai")
    assert response.status_code == 200
    data = response.json()
    assert "uso_ia" in data
    assert isinstance(data["uso_ia"]["extracoes_total"], int)
    assert data["uso_ia"]["rotulos"] == (
        "somente outcome categórico; sem texto, identificador ou dado pessoal"
    )


def test_post_calcular_emolumento_real():
    response = client.post(
        "/api/v1/emolumentos/real/calcular?tipo_ato=escritura_compra_venda&valor_declarado=450000.00&folhas=3"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tipo_ato"] == "escritura_compra_venda"
    assert data["status"] == "HITL_REQUIRED"
    assert data["total"] is None


def test_post_extrair_ai_endpoint():
    payload = {
        "texto_usuario": "Quero saber o valor para fazer uma procuração urgente para vender meu carro no CPF 111.222.333-44"
    }
    response = client.post("/api/v1/emolumentos/real/extrair-ai", json=payload)
    assert response.status_code == 200
    data = response.json()
    # PII sanitizado
    assert "111.222.333-44" not in data["texto_sanitizado"]
    assert data["tipo_ato_identificado"] in ("procuracao_imovel_veiculo", "procuracao_geral")
    assert data["urgencia_identificada"] is True
    assert data["calculo"]["status"] == "HITL_REQUIRED"
