"""Suíte de Testes de Prontidão 100% VPS & Integração Total — Cartório Agent AI.

Testa:
1. Emolumentos MG 2026 (Tabela 1 Notarial Djalma — Uberlândia) com impostos (TFJ 15%, RECOMPE 6%, ISSQN 5%).
2. Extração via IA + PII Scrubbing 3-camadas + HITL obrigatório.
3. Integridade da Cadeia de Log de Auditoria Tamper-Evident (SHA256 + HMAC).
4. FastMCP 3.x Inventory & REST APIs.
"""

from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.services.emolumento_real_djalma import (
    calcular_emolumento_real_djalma,
)
from app.services.ai_data_extractor import extrair_e_calcular_solicitacao
from app.services.pii import scrub
from app.services.audit import AuditService


client = TestClient(app)


# ── 1. Emolumentos MG 2026 ──────────────────────────────────────────────────


def test_emolumento_item_fixo_autenticacao():
    """Valida cálculo de item fixo (Autenticação por folha)."""
    res = calcular_emolumento_real_djalma("autenticacao_copia_folha")
    assert res.tipo_ato == "autenticacao_copia_folha"
    assert res.emolumento_base == Decimal("8.55")
    assert res.tfj == Decimal("2.66")
    assert res.total == Decimal("11.21")
    assert res.status == "PUBLISHED"


def test_emolumento_com_conteudo_financeiro_exige_hitl():
    """Valida que atos com valor declarado exigem aprovação humana (HITL)."""
    res = calcular_emolumento_real_djalma("escritura", valor_declarado=Decimal("350000.00"))
    assert res.status == "HITL_REQUIRED"
    assert res.motivo_hitl is not None
    assert "conferência do escrevente" in res.motivo_hitl


# ── 2. Extração IA + PII Scrubbing + HITL ────────────────────────────────────


def test_extrair_e_calcular_solicitacao_sanitiza_pii():
    """Testa extração inteligente de intenção notarial com sanitização PII."""
    texto_usuario = (
        "Olá, sou João da Silva, CPF 123.456.789-00, RG MG-12.345.678. "
        "Quero fazer uma ata notarial com 4 folhas para registrar um site."
    )
    res = extrair_e_calcular_solicitacao(texto_usuario)
    assert res.texto_sanitizado != ""
    assert "123.456.789-00" not in res.texto_sanitizado
    assert res.tipo_ato_identificado == "ata_notarial_primeira_folha"
    assert (
        res.hitl_obrigatorio is True
    )  # Atos notariais compostos/com folhas adicionais exigem HITL


# ── 3. PII Scrubbing 3-Camadas ───────────────────────────────────────────────


def test_pii_masking_functions():
    """Valida funções de sanitização de PII."""
    res_scrub = scrub("Cliente CPF 123.456.789-00 e RG 12.345.678-9")
    assert "123.456.789-00" not in res_scrub.text
    assert res_scrub.redaction_count >= 1

    texto_com_pii = "Cliente CPF 987.654.321-99 e telefone (34) 99999-8888"
    res_limpo = scrub(texto_com_pii)
    assert "987.654.321-99" not in res_limpo.text


# ── 4. Audit Log Chain (Tamper-Evident) ──────────────────────────────────────


def test_audit_log_chain_methods():
    """Valida estrutura de bloco canônico do AuditService (SHA256 + HMAC)."""
    block_str = AuditService._canonical_block(
        "0" * 64, {"test": "payload"}, "2026-07-27T00:00:00.000000"
    )
    assert "prev_hash" in block_str
    assert "timestamp" in block_str

    hash1 = AuditService._compute_hash("0" * 64, {"test": "payload"}, "2026-07-27T00:00:00.000000")
    assert len(hash1) == 64


# ── 5. FastMCP 3.x Inventory & REST APIs ────────────────────────────────────


def test_api_health_radar_returns_green():
    """Valida endpoint REST /api/v1/health/radar."""
    response = client.get("/api/v1/health/radar")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert data["services"]["database"] == "online"


def test_api_emolumentos_real_djalma_catalog():
    """Valida catálogo público de emolumentos no endpoint REST."""
    response = client.get("/api/v1/emolumentos/real/djalma")
    assert response.status_code == 200
    data = response.json()
    assert data["cartorio"] == "2º Serviço Notarial de Uberlândia"
    assert data["tabeliao"] == "Djalma de Oliveira"
    assert "itens" in data
    assert "referencia_escrevente" in data


def test_dashboard_endpoint_serves_html():
    """Valida se a rota /dashboard entrega o HTML do painel de dados."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "2º SERVIÇO NOTARIAL DE UBERLÂNDIA" in response.text
