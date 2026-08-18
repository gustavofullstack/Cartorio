"""Testes de regressão dedicados para a Issue #199.

Valida:
1. Correção de valores operacionais de balcão (autenticação eletrônica R$ 13,91, DUT/ATPV R$ 16,61, xerox).
2. Desambiguação obrigatória em consultas genéricas de procuração.
3. Roteamento refinado por finalidade (financeira R$ 226,14, INSS R$ 37,91, genérica R$ 71,38).
4. Bloqueio de pré-agendamento para atos simples de balcão (ordem de chegada + senhas preferenciais).
5. Suporte a pricing_layer no MCP cartorio_calcular_emolumento.
"""

from decimal import Decimal
import pytest

from app.services.emolumento_operacional_balcao import GENERAL_ITEMS
from app.services.cartorio_agent import (
    SERVICOS_CATALOGO,
    _match_servico,
    _procuracao_requer_contexto,
    _bloqueia_agendamento_balcao,
    _offline_reply,
    _detect_intent,
)
from app.services.chatwoot_canned_responses import get_by_short_code
from app.services.pietra_capabilities import get_capability
from mcp_server import cartorio_calcular_emolumento


def test_valores_operacionais_canonicos_2026() -> None:
    """Verifica todos os totais operacionais canônicos estabelecidos pelo manual 18/08/2026."""
    assert GENERAL_ITEMS["reconhecimento_firma"].total == Decimal("11.61")
    assert GENERAL_ITEMS["abertura_firma"].total == Decimal("11.61")
    assert GENERAL_ITEMS["arquivamento"].total == Decimal("13.91")
    assert GENERAL_ITEMS["autenticacao"].total == Decimal("11.61")
    assert GENERAL_ITEMS["autenticacao_documento_eletronico"].total == Decimal("13.91")
    assert GENERAL_ITEMS["reconhecimento_dut_atpv"].total == Decimal("16.61")
    assert GENERAL_ITEMS["xerox_1_face"].total == Decimal("1.80")
    assert GENERAL_ITEMS["xerox_2_faces"].total == Decimal("3.60")
    assert GENERAL_ITEMS["procuracao"].total == Decimal("71.38")
    assert GENERAL_ITEMS["procuracao_financeira"].total == Decimal("226.14")
    assert GENERAL_ITEMS["procuracao_inss"].total == Decimal("37.91")


@pytest.mark.parametrize(
    "texto,servico_esperado",
    [
        ("procuração para vender meu carro", "procuracao_financeira"),
        ("procuração para movimentar minha conta", "procuracao_financeira"),
        ("procuração para vender imóvel", "procuracao_financeira"),
        ("procuração para acerto trabalhista", "procuracao_financeira"),
        ("procuração para receber valores", "procuracao_financeira"),
        ("procuração para receber meu benefício do INSS", "procuracao_inss"),
        ("procuração previdenciária", "procuracao_inss"),
        ("procuração para aposentadoria", "procuracao_inss"),
        ("procuração para representação simples", "procuracao"),
        ("procuração ad judicia para advogado", "procuracao"),
        ("procuração para repartição pública", "procuracao"),
        ("reconhecimento em DUT", "reconhecimento_dut_atpv"),
        ("reconhecer firma no ATPV", "reconhecimento_dut_atpv"),
        ("autenticação de documento eletrônico", "autenticacao_documento_eletronico"),
        ("autenticação digital em pdf", "autenticacao_documento_eletronico"),
    ],
)
def test_match_servico_refinado(texto: str, servico_esperado: str) -> None:
    assert _match_servico(texto) == servico_esperado


def test_procuracao_requer_contexto_em_perguntas_genericas() -> None:
    assert _procuracao_requer_contexto("quanto custa uma procuração?") is True
    assert _procuracao_requer_contexto("quero fazer uma procuração") is True
    assert _procuracao_requer_contexto("qual o valor da procuração") is True

    # Quando há finalidade, não deve requerer contexto extra
    assert _procuracao_requer_contexto("procuração para vender carro") is False
    assert _procuracao_requer_contexto("procuração para o INSS") is False
    assert _procuracao_requer_contexto("procuração simples para advogado") is False


@pytest.mark.parametrize(
    "texto,bloqueado",
    [
        ("quero agendar reconhecimento de firma", True),
        ("preciso marcar horario para autenticar", True),
        ("agendar abertura de firma", True),
        ("agendamento para arquivamento", True),
        ("quero agendar dut", True),
        ("marcar horario para xerox", True),
        ("quero agendar escritura de compra e venda", False),
        ("agendar doacao de imovel", False),
        ("agendamento de divorcio", False),
    ],
)
def test_bloqueio_agendamento_balcao(texto: str, bloqueado: bool) -> None:
    assert _bloqueia_agendamento_balcao(texto) == bloqueado


def test_offline_desambiguacao_procuracao() -> None:
    """Quando o cliente pergunta 'quanto custa uma procuração?', a resposta deve fazer a desambiguação."""
    intent = _detect_intent("quanto custa uma procuração?")
    reply = _offline_reply("quanto custa uma procuração?", intent, [])
    assert "Qual será a finalidade da procuração?" in reply.text
    assert "representação simples" in reply.text
    assert "INSS" in reply.text
    assert "banco" in reply.text
    assert "venda de veículo" in reply.text


def test_offline_bloqueio_agendamento_balcao() -> None:
    """Tentativa de agendar ato de balcão informa ordem de chegada e senhas preferenciais."""
    intent = _detect_intent("quero agendar reconhecimento de firma")
    reply = _offline_reply("quero agendar reconhecimento de firma", intent, [])
    assert "não há pré-agendamento" in reply.text
    assert "presencial e por ordem de chegada" in reply.text
    assert "senha preferencial" in reply.text


@pytest.mark.asyncio
async def test_mcp_tool_camadas_regulatoria_e_operacional() -> None:
    # Camada regulatória (padrão)
    r_reg = await cartorio_calcular_emolumento("procuracao")
    assert r_reg["status"] == "PUBLISHED"
    assert r_reg["total"] == "68.94"
    assert r_reg["pricing_layer"] == "regulatory_tjmg"

    # Camada operacional
    r_op = await cartorio_calcular_emolumento("procuracao", pricing_layer="operational_pos_2notas")
    assert r_op["status"] == "PUBLISHED"
    assert r_op["total"] == "71.38"
    assert r_op["pricing_layer"] == "operational_pos_2notas"

    r_op_fin = await cartorio_calcular_emolumento("procuracao_financeira", pricing_layer="operational_pos_2notas")
    assert r_op_fin["status"] == "PUBLISHED"
    assert r_op_fin["total"] == "226.14"

    r_op_inss = await cartorio_calcular_emolumento("procuracao_inss", pricing_layer="operational_pos_2notas")
    assert r_op_inss["status"] == "PUBLISHED"
    assert r_op_inss["total"] == "37.91"

    r_op_aut = await cartorio_calcular_emolumento("autenticacao_documento_eletronico", pricing_layer="operational_pos_2notas")
    assert r_op_aut["status"] == "PUBLISHED"
    assert r_op_aut["total"] == "13.91"

    r_op_fisica = await cartorio_calcular_emolumento("autenticacao", pricing_layer="operational_pos_2notas")
    assert r_op_fisica["total"] == "11.61"


def test_canned_responses_sem_tabela_placeholder() -> None:
    stale = ("156,40", "28,90", "32,10")
    for code in ("procuracao", "autenticacao", "reconhecimento_firma", "agendamento_horario"):
        item = get_by_short_code(code)
        assert item is not None
        for token in stale:
            assert token not in item.content, f"{code} ainda cita {token}"


def test_canned_procuracao_desambigua_finalidade() -> None:
    item = get_by_short_code("procuracao")
    assert item is not None
    low = item.content.lower()
    assert "71,38" in item.content
    assert "226,14" in item.content
    assert "37,91" in item.content
    assert "finalidade" in low


def test_canned_agendamento_nao_oferece_horario_para_balcao() -> None:
    item = get_by_short_code("agendamento_horario")
    assert item is not None
    low = item.content.lower()
    assert "ordem de chegada" in low
    assert "08h00, 09h00" not in item.content


def test_capability_appointment_exclui_balcao_simples() -> None:
    cap = get_capability("appointment")
    assert cap is not None
    blob = " ".join(cap.evidence + [cap.display_name]).lower()
    assert "ordem de chegada" in blob
    emol = get_capability("emoluments")
    assert emol is not None
    emol_blob = " ".join(emol.evidence).lower()
    assert "operational" in emol_blob
    assert "nao e anunciada como preco de balcao" in emol_blob


def test_catalogo_publico_nao_anuncia_68_94_como_operacional() -> None:
    assert SERVICOS_CATALOGO["procuracao"][1] == "R$ 71,38"
    assert SERVICOS_CATALOGO["procuracao_financeira"][1] == "R$ 226,14"
    assert SERVICOS_CATALOGO["procuracao_inss"][1] == "R$ 37,91"
