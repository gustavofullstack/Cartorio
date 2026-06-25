"""Testes das macros de handoff humano Chatwoot (B14).

Cobre:
1. Total >= 10 macros (requisito B14)
2. Cada macro tem nome unico
3. Cada macro tem actions nao-vazias
4. Cada macro tem summary_template
5. Cobrir casos canonicos: humano, juridico, supervisor, LGPD (3), identificar, transferir, resumir, encerrar
6. LGPD macros cobrem os 3 direitos principais (esquecimento, portabilidade, anonimizacao)
7. Action types validos (assign_team, add_label, etc)
8. Helpers de busca
"""
from __future__ import annotations

import pytest  # noqa: E402

from app.services.chatwoot_handoff_macros import (  # noqa: E402
    HANDOFF_MACROS,
    HandoffMacro,
    MacroAction,
    get_macro_by_name,
    get_macros_by_action,
)


# ============================================================================
# Tests: estrutura
# ============================================================================


def test_total_macros_eh_pelo_menos_10() -> None:
    """B14 requisito: >= 10 macros de handoff."""
    assert len(HANDOFF_MACROS) >= 10, f"Esperado >= 10, obtido {len(HANDOFF_MACROS)}"


def test_cada_macro_tem_nome_unico() -> None:
    """Nomes de macros sao unicos (slug-safe)."""
    names = [m.name for m in HANDOFF_MACROS]
    assert len(names) == len(set(names)), f"Nomes duplicados: {[n for n in names if names.count(n) > 1]}"


def test_cada_macro_tem_actions_nao_vazias() -> None:
    """Cada macro tem pelo menos 1 action."""
    for macro in HANDOFF_MACROS:
        assert len(macro.actions) >= 1, f"{macro.name}: sem actions"


def test_cada_macro_tem_summary_template() -> None:
    """Cada macro tem summary template nao-vazio."""
    for macro in HANDOFF_MACROS:
        assert len(macro.summary_template) >= 30, f"{macro.name}: summary curto"


def test_cada_macro_tem_title_e_description() -> None:
    """Cada macro tem title e description."""
    for macro in HANDOFF_MACROS:
        assert macro.title, f"{macro.name}: sem title"
        assert macro.description, f"{macro.name}: sem description"


def test_actions_tem_type_e_payload() -> None:
    """Cada MacroAction tem type (string) e payload (dict)."""
    for macro in HANDOFF_MACROS:
        for action in macro.actions:
            assert isinstance(action, MacroAction)
            assert isinstance(action.type, str)
            assert isinstance(action.payload, dict)


# ============================================================================
# Tests: cobertura funcional
# ============================================================================


def test_cobre_handoff_humano_generico() -> None:
    """Macro de handoff humano generico presente."""
    names = {m.name for m in HANDOFF_MACROS}
    assert "handoff_humano" in names


def test_cobre_handoff_juridico() -> None:
    """Macro para time juridico presente."""
    names = {m.name for m in HANDOFF_MACROS}
    assert "handoff_juridico" in names


def test_cobre_handoff_supervisor() -> None:
    """Macro de escalacao para supervisor presente."""
    names = {m.name for m in HANDOFF_MACROS}
    assert "handoff_supervisor" in names


def test_cobre_3_direitos_lgpd_principais() -> None:
    """LGPD: macros para esquecimento, portabilidade, anonimizacao."""
    names = {m.name for m in HANDOFF_MACROS}
    assert "lgpd_esquecimento" in names
    assert "lgpd_portabilidade" in names
    assert "lgpd_anonimizacao" in names


def test_cobre_identificar_cliente() -> None:
    """Macro de identificacao do cliente presente."""
    names = {m.name for m in HANDOFF_MACROS}
    assert "identificar_cliente" in names


def test_cobre_resumir_contexto() -> None:
    """Macro de resumo presente (essencial para handoff)."""
    names = {m.name for m in HANDOFF_MACROS}
    assert "resumir" in names


def test_cobre_encerrar_atendimento() -> None:
    """Macro de encerramento presente."""
    names = {m.name for m in HANDOFF_MACROS}
    assert "encerrar" in names


# ============================================================================
# Tests: LGPD compliance nas macros
# ============================================================================


def test_lgpd_esquecimento_avisa_sobre_retencao_legal() -> None:
    """LGPD art. 18 VI macro menciona retencao legal de 5 anos."""
    macro = get_macro_by_name("lgpd_esquecimento")
    assert macro is not None
    assert "5 anos" in macro.summary_template or "5y" in macro.summary_template.lower()
    assert "Provimento CNJ" in macro.summary_template or "CNJ" in macro.summary_template


def test_lgpd_anonimizacao_alerta_irreversibilidade() -> None:
    """LGPD anonimizacao macro alerta sobre irreversibilidade."""
    macro = get_macro_by_name("lgpd_anonimizacao")
    assert macro is not None
    assert "IRREVERS" in macro.summary_template.upper()


def test_lgpd_macros_atribuem_time_lgpd() -> None:
    """Todas as macros LGPD atribuem ao time 'lgpd'."""
    for name in ("lgpd_esquecimento", "lgpd_portabilidade", "lgpd_anonimizacao"):
        macro = get_macro_by_name(name)
        assert macro is not None
        # Verifica que alguma action atribui team lgpd
        assign_actions = [a for a in macro.actions if a.type == "assign_team"]
        assert any(a.payload.get("team") == "lgpd" for a in assign_actions), (
            f"{name}: nao atribui ao time lgpd"
        )


# ============================================================================
# Tests: action types validos
# ============================================================================


VALID_ACTION_TYPES = {
    "assign_team",
    "add_label",
    "remove_label",
    "send_message",
    "set_priority",
    "mute_conv",
}


def test_todos_action_types_sao_validos() -> None:
    """Todos action.type estao no conjunto conhecido."""
    for macro in HANDOFF_MACROS:
        for action in macro.actions:
            assert action.type in VALID_ACTION_TYPES, (
                f"{macro.name}: action.type invalido '{action.type}'"
            )


def test_lgpd_anonimizacao_prioridade_alta() -> None:
    """LGPD anonimizacao tem prioridade high (critico)."""
    macro = get_macro_by_name("lgpd_anonimizacao")
    assert macro is not None
    priorities = [a.payload.get("priority") for a in macro.actions if a.type == "set_priority"]
    assert "high" in priorities


# ============================================================================
# Tests: helpers de busca
# ============================================================================


def test_get_macro_by_name_exato() -> None:
    """get_macro_by_name retorna macro existente."""
    macro = get_macro_by_name("handoff_humano")
    assert macro is not None
    assert isinstance(macro, HandoffMacro)
    assert macro.name == "handoff_humano"


def test_get_macro_by_name_case_insensitive() -> None:
    """get_macro_by_name eh case-insensitive."""
    m1 = get_macro_by_name("handoff_humano")
    m2 = get_macro_by_name("HANDOFF_HUMANO")
    m3 = get_macro_by_name("Handoff_Humano")
    assert m1 is not None
    assert m1 is m2
    assert m2 is m3


def test_get_macro_by_name_inexistente_retorna_none() -> None:
    """Macro inexistente retorna None."""
    assert get_macro_by_name("nao_existe_42") is None


def test_get_macros_by_action_filtra() -> None:
    """get_macros_by_action retorna apenas macros com aquela action."""
    macros_assign = get_macros_by_action("assign_team")
    # Pelo menos handoff_humano, juridico, supervisor, lgpd (3) = 5+
    assert len(macros_assign) >= 5
    for macro in macros_assign:
        assert any(a.type == "assign_team" for a in macro.actions)


def test_get_macros_by_action_vazio_se_inexistente() -> None:
    """Action inexistente retorna tupla vazia."""
    resultado = get_macros_by_action("acao_inexistente_42")
    assert resultado == ()


# ============================================================================
# Tests: integridade payloads
# ============================================================================


def test_assign_team_payload_tem_team() -> None:
    """Actions assign_team sempre tem 'team' no payload."""
    for macro in HANDOFF_MACROS:
        for action in macro.actions:
            if action.type == "assign_team":
                assert "team" in action.payload, (
                    f"{macro.name}: assign_team sem 'team'"
                )
                assert action.payload["team"] in {
                    "atendimento",
                    "juridico",
                    "supervisao",
                    "lgpd",
                }, f"{macro.name}: team invalido '{action.payload['team']}'"


def test_set_priority_payload_tem_priority_valido() -> None:
    """Actions set_priority sempre tem 'priority' valido."""
    valid_priorities = {"low", "medium", "high", "urgent"}
    for macro in HANDOFF_MACROS:
        for action in macro.actions:
            if action.type == "set_priority":
                assert action.payload.get("priority") in valid_priorities


def test_send_message_tem_message_nao_vazio() -> None:
    """Actions send_message sempre tem 'message'."""
    for macro in HANDOFF_MACROS:
        for action in macro.actions:
            if action.type == "send_message":
                msg = action.payload.get("message", "")
                assert len(msg) >= 10, f"{macro.name}: message muito curto"