"""Testes unitários do catálogo real de emolumentos (Portaria CGJ/TJMG 8.664/2025).

Os valores esperados foram transcritos da Tabela 1 do PDF oficial
(SHA-256 84781a023d6d51d9cf68a4d2ecd0c78b7fa3b0c04ba800be4d7e085aa7173417).
Testes marcados como regressão FALHAM se qualquer valor oficial regredir.
"""

from decimal import Decimal

from app.services.emolumento_real_djalma import (
    ATOS_PUBLICADOS_2026,
    FAIXAS_ESCRITURA_COM_VALOR,
    NOTA_XXV_ACRESCIMO_PRIMEIRA,
    NOTA_XXV_ACRESCIMO_SUBSEQUENTE,
    NOTA_XXV_TFJ_FIXA,
    calcular_emolumento_real_djalma,
    catalogo_publico,
)
from app.services.ai_data_extractor import (
    extrair_e_calcular_solicitacao,
    extrair_folhas,
    extrair_tipo_ato,
    extrair_valor_monetario,
)

# --- Regressão: invariante aritmética da fonte oficial ---------------------


def test_regressao_todos_itens_publicados_somam_emolumentos_mais_tfj():
    """Falha se qualquer valor_final divergir de emolumentos + tfj (PDF oficial)."""
    for slug, item in ATOS_PUBLICADOS_2026.items():
        assert item["emolumentos"] + item["tfj"] == item["valor_final"], slug


def test_regressao_faixas_escritura_somam_emolumentos_mais_tfj():
    for faixa in FAIXAS_ESCRITURA_COM_VALOR:
        assert faixa["emolumentos"] + faixa["tfj"] == faixa["valor_final"]


def test_regressao_valores_nominais_do_pdf():
    """Amostra nominal transcrita da Tabela 1 (falha se o catálogo regredir)."""
    esperado = {
        "autenticacao_copia_folha": ("8.55", "2.66", "11.21"),
        "reconhecimento_firma_assinatura": ("8.55", "2.66", "11.21"),
        "procuracao_geral": ("52.43", "16.51", "68.94"),
        "procuracao_previdenciaria": ("27.86", "8.75", "36.61"),
        "testamento": ("332.64", "104.60", "437.24"),
        "ata_notarial_ate_2_folhas": ("166.18", "52.24", "218.42"),
        "escritura_sem_conteudo_financeiro": ("55.45", "17.45", "72.90"),
    }
    for slug, (emol, tfj, final) in esperado.items():
        item = ATOS_PUBLICADOS_2026[slug]
        assert item["emolumentos"] == Decimal(emol), slug
        assert item["tfj"] == Decimal(tfj), slug
        assert item["valor_final"] == Decimal(final), slug


def test_regressao_faixas_escritura_extremos_e_nota_xxv():
    primeira = FAIXAS_ESCRITURA_COM_VALOR[0]
    assert primeira["de"] == Decimal("0.00")
    assert primeira["ate"] == Decimal("1400.00")
    assert primeira["valor_final"] == Decimal("220.55")
    ultima = FAIXAS_ESCRITURA_COM_VALOR[-1]
    assert ultima["ate"] == Decimal("3200000.00")
    assert ultima["valor_final"] == Decimal("8582.97")
    assert len(FAIXAS_ESCRITURA_COM_VALOR) == 23
    assert NOTA_XXV_ACRESCIMO_PRIMEIRA == Decimal("3289.90")
    assert NOTA_XXV_ACRESCIMO_SUBSEQUENTE == Decimal("2193.27")
    assert NOTA_XXV_TFJ_FIXA == Decimal("4673.83")


def test_regressao_faixas_escritura_contiguas():
    """Faixas devem ser contíguas (fim de uma = início da próxima - 0,01)."""
    for anterior, proxima in zip(FAIXAS_ESCRITURA_COM_VALOR, FAIXAS_ESCRITURA_COM_VALOR[1:]):
        assert anterior["ate"] is not None
        assert proxima["de"] == anterior["ate"] + Decimal("0.01")


# --- Consulta pública -------------------------------------------------------


def test_calcular_procuracao_geral_publicada():
    res = calcular_emolumento_real_djalma("procuracao_geral", folhas=1)
    assert res.cartorio == "2º Serviço Notarial de Uberlândia"
    assert res.status == "PUBLISHED"
    assert res.emolumento_base == Decimal("52.43")
    assert res.tfj == Decimal("16.51")
    assert res.total == Decimal("68.94")
    assert res.item_portaria == "Tabela 1, item 4.f.1"


def test_calcular_autenticacao_alias_legado():
    res = calcular_emolumento_real_djalma("autenticacao_pagina")
    assert res.status == "PUBLISHED"
    assert res.tipo_ato == "autenticacao_copia_folha"
    assert res.total == Decimal("11.21")


def test_calcular_escritura_com_valor_sempre_hitl():
    res = calcular_emolumento_real_djalma("escritura_compra_venda", valor_declarado=5000)
    assert res.status == "HITL_REQUIRED"
    assert res.total is None
    assert res.motivo_hitl


def test_calcular_urgencia_sempre_hitl():
    res = calcular_emolumento_real_djalma("procuracao_geral", urgencia=True)
    assert res.status == "HITL_REQUIRED"
    assert res.total is None


def test_calcular_folhas_adicionais_sempre_hitl():
    res = calcular_emolumento_real_djalma(
        "escritura_compra_venda",
        valor_declarado=Decimal("380000.00"),
        folhas=3,
    )
    assert res.status == "HITL_REQUIRED"
    assert res.total is None


def test_calcular_ato_desconhecido_hitl():
    res = calcular_emolumento_real_djalma("certidao_inteiro_teor")
    assert res.status == "HITL_REQUIRED"
    assert res.total is None


def test_catalogo_publico_proveniencia():
    cat = catalogo_publico()
    assert cat["cartorio"] == "2º Serviço Notarial de Uberlândia"
    fonte = cat["fonte"]
    assert fonte["vigencia_inicio"] == "2026-01-01"
    assert fonte["sha256"] == ("84781a023d6d51d9cf68a4d2ecd0c78b7fa3b0c04ba800be4d7e085aa7173417")
    assert any(item["tipo_ato"] == "procuracao_geral" for item in cat["itens"])
    assert all(item["status"] == "PUBLISHED" for item in cat["itens"])
    faixas = cat["referencia_escrevente"]["escritura_com_conteudo_financeiro"]
    assert len(faixas) == 23
    assert all(f["status"] == "HITL_REQUIRED" for f in faixas)


# --- Extrator (regex + scrub) ------------------------------------------------


def test_ai_data_extractor_helpers():
    txt = (
        "Gostaria de saber o valor de uma escritura de compra e venda de R$ 450.000,00 com 4 folhas"
    )
    assert extrair_tipo_ato(txt) == "escritura_compra_venda"
    assert extrair_valor_monetario(txt) == Decimal("450000.00")
    assert extrair_folhas(txt) == 4


def test_extrair_e_calcular_solicitacao_flow():
    txt = "Preciso de uma procuração para a Sra. Maria CPF 123.456.789-00 urgente"
    res = extrair_e_calcular_solicitacao(txt)
    # CPF deve ter sido ocultado pelo PII scrub
    assert "123.456.789-00" not in res.texto_sanitizado
    assert res.urgencia_identificada is True
    assert res.calculo.tipo_ato == "procuracao_geral"
    assert res.calculo.status == "HITL_REQUIRED"
    assert res.hitl_obrigatorio is True
    assert res.status_auditoria == "NOT_PERSISTED"
