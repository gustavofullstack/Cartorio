"""Testes de contrato e anti-vazamento do painel de dados do Agent AI (Fase 4).

Cobre os 5 endpoints sob ``/api/v1/painel``: fonte, catalogo, extracao,
operacao e ia-usage. O painel e fail-open: TestClient sem seed de banco
exerce exatamente o caminho de fallback para as constantes versionadas.
"""

import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Padroes de PII que NUNCA podem aparecer em qualquer resposta do painel.
CPF_RE = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
TELEFONE_DDD_RE = re.compile(r"\(\d{2}\)\s?9?\d{4,5}-\d{4}")
TELEFONE_CELULAR_RE = re.compile(r"\b9\d{4}-\d{4}\b")

ENDPOINTS_PAINEL = [
    "/api/v1/painel/fonte",
    "/api/v1/painel/catalogo",
    "/api/v1/painel/extracao",
    "/api/v1/painel/operacao",
    "/api/v1/painel/ia-usage",
]


def test_painel_fonte_contrato():
    response = client.get("/api/v1/painel/fonte")
    assert response.status_code == 200
    data = response.json()
    for chave in (
        "nome",
        "url",
        "sha256",
        "capturado_em",
        "idade_dias",
        "vigencia_inicio",
        "estado",
        "aprovacao_humana",
        "origem",
    ):
        assert chave in data
    assert isinstance(data["idade_dias"], int)
    assert data["idade_dias"] >= 0
    assert data["origem"] in ("banco", "constantes")
    assert len(data["sha256"]) == 64
    aprovacao = data["aprovacao_humana"]
    assert {"revisado_por", "revisado_em", "mensagem"}.issubset(aprovacao)


def test_painel_catalogo_contrato():
    response = client.get("/api/v1/painel/catalogo")
    assert response.status_code == 200
    data = response.json()
    assert data["origem"] in ("banco", "constantes")
    assert isinstance(data["total"], int)
    assert data["total"] == len(data["itens"]) > 0
    assert data["escopo"]
    for item in data["itens"]:
        assert {
            "tipo_ato",
            "ato",
            "item_portaria",
            "emolumentos",
            "tfj",
            "valor_final",
            "status",
        }.issubset(item)
        assert item["status"] == "PUBLISHED"


def test_painel_extracao_contrato():
    response = client.get("/api/v1/painel/extracao")
    assert response.status_code == 200
    data = response.json()
    for chave in (
        "extracoes_por_outcome",
        "extracoes_total",
        "handoffs_por_reason",
        "handoffs_total",
        "llm_fallback_por_reason",
        "llm_fallback_total",
        "rotulos",
    ):
        assert chave in data
    assert isinstance(data["extracoes_total"], int)
    assert isinstance(data["handoffs_total"], int)
    assert data["extracoes_total"] == sum(data["extracoes_por_outcome"].values())
    assert data["handoffs_total"] == sum(data["handoffs_por_reason"].values())
    assert data["rotulos"] == "somente outcome categórico; sem texto, identificador ou dado pessoal"


def test_painel_operacao_contrato():
    response = client.get("/api/v1/painel/operacao")
    assert response.status_code == 200
    data = response.json()
    assert {"consultas_por_outcome", "consultas_total", "handoffs_total", "taxa_handoff"}.issubset(
        data
    )
    assert isinstance(data["consultas_total"], int)
    assert isinstance(data["taxa_handoff"], float)
    assert 0.0 <= data["taxa_handoff"]
    if data["consultas_total"] == 0:
        assert data["taxa_handoff"] == 0.0


def test_painel_ia_usage_contrato():
    response = client.get("/api/v1/painel/ia-usage")
    assert response.status_code == 200
    data = response.json()
    assert "disponivel" in data
    if data["disponivel"]:
        assert {"resumo", "por_modelo", "por_dia"}.issubset(data)
    else:
        assert "motivo" in data


def test_painel_ia_usage_janela_limitada():
    assert client.get("/api/v1/painel/ia-usage?dias=365").status_code == 200
    assert client.get("/api/v1/painel/ia-usage?dias=366").status_code == 422
    assert client.get("/api/v1/painel/ia-usage?dias=0").status_code == 422


def test_painel_operacao_reflete_consulta_real():
    """POST em /emolumentos/real/calcular incrementa o agregado (mesmo processo)."""
    antes = client.get("/api/v1/painel/operacao").json()
    published_antes = antes["consultas_por_outcome"].get("PUBLISHED", 0)

    resp = client.post("/api/v1/emolumentos/real/calcular?tipo_ato=testamento")
    assert resp.status_code == 200
    assert resp.json()["status"] == "PUBLISHED"

    depois = client.get("/api/v1/painel/operacao").json()
    assert depois["consultas_total"] == antes["consultas_total"] + 1
    assert depois["consultas_por_outcome"].get("PUBLISHED", 0) == published_antes + 1


def test_painel_operacao_conta_outcome_hitl():
    antes = client.get("/api/v1/painel/operacao").json()
    hitl_antes = antes["consultas_por_outcome"].get("HITL_REQUIRED", 0)

    resp = client.post("/api/v1/emolumentos/real/calcular?tipo_ato=testamento&urgencia=true")
    assert resp.status_code == 200
    assert resp.json()["status"] == "HITL_REQUIRED"

    depois = client.get("/api/v1/painel/operacao").json()
    assert depois["consultas_por_outcome"].get("HITL_REQUIRED", 0) == hitl_antes + 1


def test_painel_nao_vaza_pii():
    """Nenhuma resposta do painel contem CPF, telefone ou texto de cliente."""
    for endpoint in ENDPOINTS_PAINEL:
        response = client.get(endpoint)
        assert response.status_code == 200
        corpo = response.text
        assert not CPF_RE.search(corpo), f"CPF vazou em {endpoint}"
        assert not TELEFONE_DDD_RE.search(corpo), f"telefone vazou em {endpoint}"
        assert not TELEFONE_CELULAR_RE.search(corpo), f"telefone vazou em {endpoint}"
        assert "111.222.333-44" not in corpo
        assert "texto_usuario" not in corpo
        assert "texto_sanitizado" not in corpo


def test_painel_fallback_sem_dados_no_banco():
    """TestClient sem seed: endpoints respondem 200 via fallback (fail-open)."""
    for endpoint in ENDPOINTS_PAINEL:
        response = client.get(endpoint)
        assert response.status_code == 200, f"{endpoint} falhou sem seed de banco"
    fonte = client.get("/api/v1/painel/fonte").json()
    assert fonte["estado"] == "PUBLISHED"
    assert fonte["vigencia_inicio"] == "2026-01-01"
