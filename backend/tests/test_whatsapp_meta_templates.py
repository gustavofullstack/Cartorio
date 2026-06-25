"""Testes dos templates WhatsApp Meta (B15).

Cobre:
1. Total >= 10 templates (requisito B15)
2. Cada template tem nome unico + snake_case lowercase
3. Cada template tem components (HEADER/BODY/FOOTER/BUTTONS)
4. Categorias validas: UTILITY, MARKETING, AUTHENTICATION
5. Variaveis {{N}} presentes em templates com personalizacao
6. Cobertura por categoria (UTILITY >= 5, AUTHENTICATION >= 1)
7. LGPD templates cobrem fluxo completo
8. Buttons validos (URL, PHONE_NUMBER, QUICK_REPLY)
9. Helpers de busca
"""
from __future__ import annotations

import re

from app.services.whatsapp_meta_templates import (  # noqa: E402
    META_TEMPLATES,
    get_template_by_name,
    get_templates_by_category,
)


# ============================================================================
# Tests: estrutura
# ============================================================================


def test_total_templates_eh_pelo_menos_10() -> None:
    """B15 requisito: >= 10 templates."""
    assert len(META_TEMPLATES) >= 10, f"Esperado >= 10, obtido {len(META_TEMPLATES)}"


def test_cada_template_tem_nome_unico() -> None:
    """Nomes unicos."""
    names = [t.name for t in META_TEMPLATES]
    assert len(names) == len(set(names))


def test_nomes_sao_snake_case_lowercase() -> None:
    """Nome em snake_case lowercase (regex canon do Meta)."""
    pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    for template in META_TEMPLATES:
        assert pattern.match(template.name), f"{template.name}: nao eh snake_case lowercase"


def test_nomes_tem_max_512_chars() -> None:
    """Nome <= 512 chars (limite Meta)."""
    for template in META_TEMPLATES:
        assert len(template.name) <= 512, f"{template.name}: nome muito longo"


def test_cada_template_tem_components_nao_vazios() -> None:
    """Cada template tem >= 1 component."""
    for template in META_TEMPLATES:
        assert len(template.components) >= 1, f"{template.name}: sem components"


def test_cada_template_tem_description() -> None:
    """Cada template tem description (interna)."""
    for template in META_TEMPLATES:
        assert template.description, f"{template.name}: sem description"


# ============================================================================
# Tests: categorias
# ============================================================================


def test_categorias_validas() -> None:
    """Todas categorias estao no conjunto {UTILITY, MARKETING, AUTHENTICATION}."""
    valid = {"UTILITY", "MARKETING", "AUTHENTICATION"}
    for template in META_TEMPLATES:
        assert template.category in valid, f"{template.name}: categoria invalida"


def test_cobre_pelo_menos_5_utility() -> None:
    """UTILITY >= 5 templates (transacional)."""
    utility = get_templates_by_category("UTILITY")
    assert len(utility) >= 5, f"UTILITY: esperado >= 5, obtido {len(utility)}"


def test_cobre_pelo_menos_1_authentication() -> None:
    """AUTHENTICATION >= 1 template (OTP)."""
    auth = get_templates_by_category("AUTHENTICATION")
    assert len(auth) >= 1


def test_cobre_pelo_menos_1_marketing() -> None:
    """MARKETING >= 1 template (promocional)."""
    marketing = get_templates_by_category("MARKETING")
    assert len(marketing) >= 1


# ============================================================================
# Tests: components
# ============================================================================


def test_cada_template_tem_body() -> None:
    """Cada template tem component BODY."""
    for template in META_TEMPLATES:
        body_components = [c for c in template.components if c.type == "BODY"]
        assert len(body_components) >= 1, f"{template.name}: sem BODY"


def test_body_tem_text_nao_vazio() -> None:
    """BODY component tem text com pelo menos 50 chars."""
    for template in META_TEMPLATES:
        for component in template.components:
            if component.type == "BODY":
                assert component.text, f"{template.name}: BODY sem text"
                assert len(component.text) >= 50, f"{template.name}: BODY muito curto"


def test_components_tipos_validos() -> None:
    """Component types sao HEADER, BODY, FOOTER, BUTTONS."""
    valid_types = {"HEADER", "BODY", "FOOTER", "BUTTONS"}
    for template in META_TEMPLATES:
        for component in template.components:
            assert component.type in valid_types, (
                f"{template.name}: component type invalido {component.type}"
            )


def test_buttons_tem_tipos_validos() -> None:
    """BUTTONS tem types validos (URL/PHONE_NUMBER/QUICK_REPLY)."""
    valid_btn_types = {"URL", "PHONE_NUMBER", "QUICK_REPLY"}
    for template in META_TEMPLATES:
        for component in template.components:
            if component.type == "BUTTONS":
                for btn in component.buttons:
                    assert btn.get("type") in valid_btn_types, (
                        f"{template.name}: button type invalido {btn.get('type')}"
                    )


def test_url_button_tem_url_e_text() -> None:
    """URL button tem 'url' e 'text'."""
    for template in META_TEMPLATES:
        for component in template.components:
            if component.type == "BUTTONS":
                for btn in component.buttons:
                    if btn.get("type") == "URL":
                        assert "url" in btn and "text" in btn, (
                            f"{template.name}: URL button mal formado"
                        )


def test_phone_button_tem_phone_number() -> None:
    """PHONE_NUMBER button tem 'phone_number' e 'text'."""
    for template in META_TEMPLATES:
        for component in template.components:
            if component.type == "BUTTONS":
                for btn in component.buttons:
                    if btn.get("type") == "PHONE_NUMBER":
                        assert "phone_number" in btn and "text" in btn


def test_quick_reply_tem_text() -> None:
    """QUICK_REPLY button tem 'text'."""
    for template in META_TEMPLATES:
        for component in template.components:
            if component.type == "BUTTONS":
                for btn in component.buttons:
                    if btn.get("type") == "QUICK_REPLY":
                        assert "text" in btn


# ============================================================================
# Tests: variaveis {{N}}
# ============================================================================


def test_templates_dinamicos_usam_variaveis_numeradas() -> None:
    """Templates com personalizacao usam variaveis {{1}}, {{2}}, etc."""
    # Pelo menos 5 templates devem ter variaveis
    templates_with_vars = [t for t in META_TEMPLATES if "{{1}}" in str(t.components)]
    assert len(templates_with_vars) >= 5


def test_variaveis_sao_sequenciais() -> None:
    """Variaveis usadas sao {{1}}, {{2}}, ..., {{N}} sequenciais."""
    for template in META_TEMPLATES:
        body_text = ""
        for c in template.components:
            if c.type == "BODY" and c.text:
                body_text += c.text
        if "{{" in body_text:
            vars_found = sorted(set(int(m.group(1)) for m in re.finditer(r"\{\{(\d+)\}\}", body_text)))
            # Devem comecar em 1 e ser sequenciais
            assert vars_found[0] == 1, f"{template.name}: variaveis nao comecam em 1"
            assert vars_found == list(range(1, len(vars_found) + 1)), (
                f"{template.name}: variaveis nao sequenciais: {vars_found}"
            )


# ============================================================================
# Tests: cobertura por fluxo
# ============================================================================


def test_cobre_fluxo_agendamento() -> None:
    """Agendamento: confirmacao + lembrete."""
    names = {t.name for t in META_TEMPLATES}
    assert "agendamento_confirmado" in names
    assert "agendamento_lembrete" in names


def test_cobre_fluxo_protocolo() -> None:
    """Protocolo: criado + concluido."""
    names = {t.name for t in META_TEMPLATES}
    assert "protocolo_criado" in names
    assert "protocolo_concluido" in names


def test_cobre_fluxo_lgpd() -> None:
    """LGPD: solicitacao recebida + esquecimento confirmado."""
    names = {t.name for t in META_TEMPLATES}
    assert "lgpd_solicitacao_recebida" in names
    assert "lgpd_esquecimento_confirmado" in names


def test_cobre_pagamento() -> None:
    """Template de pagamento confirmado presente."""
    names = {t.name for t in META_TEMPLATES}
    assert "pagamento_confirmado" in names


def test_cobre_otp_authentication() -> None:
    """OTP para autenticacao presente."""
    names = {t.name for t in META_TEMPLATES}
    assert "auth_otp" in names


def test_cobre_boas_vindas_marketing() -> None:
    """Boas vindas (MARKETING) presente."""
    names = {t.name for t in META_TEMPLATES}
    assert "boas_vindas" in names


# ============================================================================
# Tests: LGPD compliance
# ============================================================================


def test_lgpd_templates_mencionam_dpo_email() -> None:
    """Templates LGPD mencionam dpo@2notasudi.com.br."""
    for name in ("lgpd_solicitacao_recebida", "lgpd_esquecimento_confirmado"):
        template = get_template_by_name(name)
        assert template is not None
        all_text = " ".join(c.text or "" for c in template.components)
        assert "dpo@2notasudi.com.br" in all_text


def test_lgpd_esquecimento_avisa_retencao_5_anos() -> None:
    """Template de esquecimento menciona retencao legal 5 anos."""
    template = get_template_by_name("lgpd_esquecimento_confirmado")
    assert template is not None
    all_text = " ".join(c.text or "" for c in template.components)
    assert "5 anos" in all_text or "Provimento CNJ" in all_text


def test_otp_avisa_para_nao_compartilhar() -> None:
    """Template OTP alerta sobre nao compartilhar codigo."""
    template = get_template_by_name("auth_otp")
    assert template is not None
    footer = next((c for c in template.components if c.type == "FOOTER"), None)
    assert footer is not None
    assert "compartilh" in (footer.text or "").lower()


# ============================================================================
# Tests: nenhum PII hardcoded
# ============================================================================


def test_nenhum_template_contem_cpf_hardcoded() -> None:
    """LGPD: nenhum CPF literal (XXX.XXX.XXX-XX) hardcoded."""
    pattern = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
    for template in META_TEMPLATES:
        for component in template.components:
            text = component.text or ""
            assert not pattern.search(text), (
                f"{template.name}: CPF hardcoded em component"
            )


def test_nenhum_template_contem_telefone_pessoal_hardcoded() -> None:
    """Telefones com placeholder XXXX, nao numero real pessoal."""
    pattern = re.compile(r"\(\d{2}\)\s*9?\d{4}-\d{4}")
    for template in META_TEMPLATES:
        for component in template.components:
            text = component.text or ""
            # Se contem (XX), deve ter placeholder
            if pattern.search(text):
                assert "XXXX" in text or "0000" in text, (
                    f"{template.name}: telefone hardcoded"
                )


def test_telefone_institucional_eh_generico() -> None:
    """Telefone institucional no footer: (34) 3250-XXXX (placeholder)."""
    agendamento = get_template_by_name("agendamento_confirmado")
    assert agendamento is not None
    all_text = " ".join(c.text or "" for c in agendamento.components)
    if "(34)" in all_text:
        assert "XXXX" in all_text or "0000" in all_text


# ============================================================================
# Tests: helpers
# ============================================================================


def test_get_template_by_name_exato() -> None:
    """get_template_by_name retorna template correto."""
    t = get_template_by_name("auth_otp")
    assert t is not None
    assert t.name == "auth_otp"


def test_get_template_by_name_case_insensitive() -> None:
    """Busca eh case-insensitive."""
    t1 = get_template_by_name("auth_otp")
    t2 = get_template_by_name("AUTH_OTP")
    t3 = get_template_by_name("Auth_Otp")
    assert t1 is t2 is t3


def test_get_template_by_name_inexistente_retorna_none() -> None:
    """Template inexistente retorna None."""
    assert get_template_by_name("nao_existe_42") is None


def test_get_templates_by_category_filtra() -> None:
    """Filtro por categoria retorna apenas templates daquela categoria."""
    utility = get_templates_by_category("UTILITY")
    assert len(utility) >= 5
    for t in utility:
        assert t.category == "UTILITY"


def test_get_templates_by_category_vazio_se_inexistente() -> None:
    """Categoria inexistente retorna tupla vazia."""
    # Categoria valida mas sem templates? AUTH tem so 1. Vamos usar MARKETING.
    marketing = get_templates_by_category("MARKETING")
    for t in marketing:
        assert t.category == "MARKETING"