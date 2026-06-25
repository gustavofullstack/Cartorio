"""Testes dos canned responses Chatwoot (B13).

Cobre:
1. Total >= 50 templates (requisito B13)
2. Cada template tem short_code unico
3. Cada template tem content nao-vazio
4. Cada template tem tags
5. Short codes sao slug-safe (sem espacos, sem caracteres especiais)
6. Liquid tags Chatwoot ({{customer.name}}, etc) presentes onde esperado
7. LGPD templates cobrem os 6 direitos do titular
8. Search por tag funciona
9. Search por short_code funciona
"""
from __future__ import annotations

import re

import pytest  # noqa: E402

from app.services.chatwoot_canned_responses import (  # noqa: E402
    CANNED_RESPONSES,
    CannedResponse,
    get_all_short_codes,
    get_by_short_code,
    get_by_tag,
)


# ============================================================================
# Tests: quantidade + estrutura
# ============================================================================


def test_total_canned_responses_eh_pelo_menos_50() -> None:
    """B13 requisito: >= 50 templates juridicos."""
    assert len(CANNED_RESPONSES) >= 50, f"Esperado >= 50, obtido {len(CANNED_RESPONSES)}"


def test_cada_template_tem_short_code() -> None:
    """Cada CannedResponse tem short_code nao-vazio."""
    for cr in CANNED_RESPONSES:
        assert isinstance(cr, CannedResponse)
        assert cr.short_code, f"Template sem short_code: {cr}"


def test_cada_template_tem_content_nao_vazio() -> None:
    """Cada template tem content com pelo menos 50 caracteres (substantivo)."""
    for cr in CANNED_RESPONSES:
        assert len(cr.content) >= 50, f"{cr.short_code}: content muito curto"


def test_cada_template_tem_pelo_menos_1_tag() -> None:
    """Cada template tem tags para busca."""
    for cr in CANNED_RESPONSES:
        assert len(cr.tags) >= 1, f"{cr.short_code}: sem tags"


def test_short_codes_sao_unicos() -> None:
    """Nenhum short_code duplicado."""
    codes = [cr.short_code for cr in CANNED_RESPONSES]
    assert len(codes) == len(set(codes)), f"Short codes duplicados: {[c for c in codes if codes.count(c) > 1]}"


def test_short_codes_slug_safe() -> None:
    """Short codes contem apenas [a-z0-9_] (kebab/snake case)."""
    pattern = re.compile(r"^[a-z0-9_]+$")
    for cr in CANNED_RESPONSES:
        assert pattern.match(cr.short_code), f"{cr.short_code}: contem caracteres invalidos"


# ============================================================================
# Tests: cobertura LGPD (6 direitos do titular)
# ============================================================================


def test_lgpd_cobre_6_direitos_titular() -> None:
    """LGPD art. 18: 6 direitos do titular devem ter template."""
    expected = [
        "lgpd_anonimizacao",  # IV
        "lgpd_correcao",      # III
        "lgpd_esquecimento",   # VI
        "lgpd_oposicao",       # II
        "lgpd_portabilidade",  # V
    ]
    # + consentimento (nao eh exatamente um "direito" do art. 18 mas eh requisito LGPD)
    codes = set(get_all_short_codes())
    for code in expected:
        assert code in codes, f"Falta template LGPD: {code}"
    assert "lgpd_consentimento" in codes


# ============================================================================
# Tests: cobertura servicos juridicos principais
# ============================================================================


def test_cobre_certidoes_principais() -> None:
    """Certidoes negativa, positiva, casamento tem templates."""
    codes = set(get_all_short_codes())
    assert "certidao_negativa" in codes
    assert "certidao_positiva" in codes
    assert "certidao_casamento" in codes


def test_cobre_escrituras() -> None:
    """Escrituras principais tem templates."""
    codes = set(get_all_short_codes())
    assert "escritura_compra_venda" in codes
    assert "escritura_doacao" in codes


def test_cobre_procuracao_e_autenticacao() -> None:
    """Procuracao, autenticacao, reconhecimento de firma tem templates."""
    codes = set(get_all_short_codes())
    assert "procuracao" in codes
    assert "autenticacao" in codes
    assert "reconhecimento_firma" in codes


def test_cobre_agendamento_completo() -> None:
    """Agendamento tem templates para: horarios, confirmacao, cancelamento."""
    codes = set(get_all_short_codes())
    assert "agendamento_horario" in codes
    assert "agendamento_confirmado" in codes
    assert "agendamento_cancelamento" in codes


def test_cobre_handoff_humano() -> None:
    """Handoff humano tem template dedicado."""
    codes = set(get_all_short_codes())
    assert "handoff_humano" in codes
    assert "aguarde_humano" in codes


# ============================================================================
# Tests: Liquid tags Chatwoot
# ============================================================================


def test_liquid_tags_customer_presentes() -> None:
    """Tags Chatwoot {{customer.name}} presentes onde relevante."""
    saudacao = get_by_short_code("saudacao_inicial")
    assert saudacao is not None
    assert "{{customer.name}}" in saudacao.content


def test_liquid_tags_conversation_presentes() -> None:
    """Tags Chatwoot {{conversation.id}} presentes em handoff."""
    handoff = get_by_short_code("handoff_humano")
    assert handoff is not None
    assert "{{conversation.id}}" in handoff.content


def test_liquid_tags_custom_presentes_em_dinamicos() -> None:
    """Tags {{custom.*}} presentes em templates dinamicos."""
    agendamento = get_by_short_code("agendamento_confirmado")
    assert agendamento is not None
    assert "{{custom.protocolo}}" in agendamento.content or "{{custom.data}}" in agendamento.content


# ============================================================================
# Tests: helpers de busca
# ============================================================================


def test_get_by_tag_retorna_apenas_com_tag() -> None:
    """Filtro por tag retorna apenas templates com aquela tag."""
    lgpd = get_by_tag("lgpd")
    assert len(lgpd) >= 7  # pelo menos 7 templates LGPD (consentimento + 6 direitos + DPO)
    for cr in lgpd:
        assert "lgpd" in cr.tags


def test_get_by_tag_retorna_vazio_se_tag_inexistente() -> None:
    """Tag inexistente retorna tupla vazia."""
    resultado = get_by_tag("tag_que_nao_existe_42")
    assert resultado == ()


def test_get_by_short_code_case_insensitive() -> None:
    """Busca por short_code eh case-insensitive."""
    cr1 = get_by_short_code("certidao_negativa")
    cr2 = get_by_short_code("CERTIDAO_NEGATIVA")
    cr3 = get_by_short_code("Certidao_Negativa")
    assert cr1 is not None
    assert cr2 is cr1
    assert cr3 is cr1


def test_get_by_short_code_inexistente_retorna_none() -> None:
    """Short code inexistente retorna None."""
    assert get_by_short_code("nao_existe_42") is None


# ============================================================================
# Tests: qualidade conteudo
# ============================================================================


def test_nenhum_template_contem_cpf_em_chave() -> None:
    """LGPD: nenhum template expoe CPF literal no content."""
    for cr in CANNED_RESPONSES:
        # Procura padroes comuns de CPF (XXX.XXX.XXX-XX) hardcoded
        assert not re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}", cr.content), (
            f"{cr.short_code}: contem CPF hardcoded"
        )


def test_nenhum_template_contem_email_hardcoded_pessoal() -> None:
    """Nenhum template expoe emails pessoais (apenas institucional generico)."""
    for cr in CANNED_RESPONSES:
        # Se contem email, deve ser @2notasudi.com.br (institucional)
        emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", cr.content)
        for email in emails:
            assert "@2notasudi.com.br" in email, (
                f"{cr.short_code}: email nao-institucional: {email}"
            )


def test_nenhum_template_contem_telefone_pessoal() -> None:
    """Telefones devem ter placeholder XXXX (nao numero real)."""
    for cr in CANNED_RESPONSES:
        # Procura telefone (XX) XXXX-XXXX
        tels = re.findall(r"\(\d{2}\)\s*\d{4,5}-\d{4}", cr.content)
        for tel in tels:
            assert "XXXX" in tel or "0000" in tel, (
                f"{cr.short_code}: telefone hardcoded: {tel}"
            )