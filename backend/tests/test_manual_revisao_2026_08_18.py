"""Fatia restante do manual revisado 18/08/2026 (após a issue #199).

Cobre o que ainda reintroduzia valor inventado ou classificava mal:
- certidão de inteiro teor / conforme quesitos;
- desambiguação de certidão e autenticação genéricas;
- apostilamento;
- canned responses de escritura/RC/horário sem número inventado;
- resposta offline que não oferece pré-agendamento em ato de balcão.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.cartorio_agent import (
    SERVICOS_CATALOGO,
    _autenticacao_requer_contexto,
    _bloqueia_agendamento_balcao,
    _certidao_requer_contexto,
    _detect_intent,
    _match_servico,
    _offline_reply,
)
from app.services.chatwoot_canned_responses import get_by_short_code
from app.services.emolumento_operacional_balcao import GENERAL_ITEMS


def test_catalogo_publico_inclui_certidoes_e_apostilamento() -> None:
    assert SERVICOS_CATALOGO["certidao_inteiro_teor"][1] == "R$ 42,49"
    assert SERVICOS_CATALOGO["certidao_quesitos"][1] == "R$ 66,30"
    assert SERVICOS_CATALOGO["apostilamento"][1] == "R$ 189,38"
    assert GENERAL_ITEMS["certidao_inteiro_teor"].total == Decimal("42.49")
    assert GENERAL_ITEMS["certidao_quesitos"].total == Decimal("66.30")
    assert GENERAL_ITEMS["apostilamento"].total == Decimal("189.38")


@pytest.mark.parametrize(
    "texto,servico_esperado",
    [
        ("quanto custa certidão de inteiro teor", "certidao_inteiro_teor"),
        ("certidão conforme quesitos", "certidao_quesitos"),
        ("apostilamento de diploma", "apostilamento"),
        ("apostila de Haia", "apostilamento"),
    ],
)
def test_match_servico_certidao_e_apostilamento(texto: str, servico_esperado: str) -> None:
    assert _match_servico(texto) == servico_esperado


def test_certidao_generica_pede_tipo_antes_do_preco() -> None:
    assert _certidao_requer_contexto("quanto custa uma certidão?") is True
    assert _certidao_requer_contexto("certidão de inteiro teor") is False
    assert _certidao_requer_contexto("certidão conforme quesitos") is False

    intent = _detect_intent("quanto custa uma certidão?")
    reply = _offline_reply("quanto custa uma certidão?", intent, [])
    low = reply.text.lower()
    assert "42,49" in reply.text
    assert "66,30" in reply.text
    assert "5 dias" in low
    assert "87,50" not in reply.text
    assert "inteiro teor" in low
    assert "quesito" in low


def test_autenticacao_generica_pede_fisico_ou_digital() -> None:
    assert _autenticacao_requer_contexto("quanto custa autenticação?") is True
    assert _autenticacao_requer_contexto("autenticar cópia física") is False
    assert _autenticacao_requer_contexto("autenticação de documento eletrônico") is False

    intent = _detect_intent("quanto custa autenticar um documento?")
    reply = _offline_reply("quanto custa autenticar um documento?", intent, [])
    assert "11,61" in reply.text
    assert "13,91" in reply.text
    assert "físico" in reply.text.lower() or "fisico" in reply.text.lower()
    assert "digital" in reply.text.lower() or "eletrôn" in reply.text.lower()


def test_livre_com_historico_nao_oferece_agendar_balcao() -> None:
    history = ["bot: Oi. Em que posso te ajudar agora?"]
    intent = _detect_intent("reconhecimento de firma")
    reply = _offline_reply("reconhecimento de firma", intent, history)
    low = reply.text.lower()
    assert "quero agendar" not in low
    assert _bloqueia_agendamento_balcao("reconhecimento de firma") is True
    assert "ordem de chegada" in low or "11,61" in reply.text


def test_canned_certidao_teor_usa_total_operacional() -> None:
    item = get_by_short_code("certidao_teor")
    assert item is not None
    assert "42,49" in item.content
    assert "45,80" not in item.content
    assert "5 dias" in item.content.lower()


def test_canned_nao_inventa_valores_fora_do_manual() -> None:
    stale = (
        "87,50",
        "92,30",
        "105,40",
        "45,80",
        "4.521,00",
        "3.205,50",
        "2.876,40",
        "3.245,80",
        "1.876,20",
        "08h00 às 17h00",
        "Sábado: 08h00",
    )
    codes = (
        "certidao_negativa",
        "certidao_positiva",
        "certidao_casamento",
        "certidao_nascimento",
        "certidao_obito",
        "certidao_teor",
        "escritura_compra_venda",
        "escritura_doacao",
        "usufruto",
        "hipoteca",
        "convencao_condominio",
        "horario_atendimento",
        "certidao_pronta",
    )
    for code in codes:
        item = get_by_short_code(code)
        assert item is not None, code
        for token in stale:
            assert token not in item.content, f"{code} ainda cita {token}"


def test_canned_horario_segue_perfil_publico() -> None:
    item = get_by_short_code("horario_atendimento")
    assert item is not None
    low = item.content.lower()
    assert "09h" in low or "9h" in low
    assert "sábado:" not in low and "sabado:" not in low
    assert "08h00 às 12h00" not in item.content


def test_canned_registro_civil_nao_finge_ser_deste_cartorio() -> None:
    for code in ("certidao_nascimento", "certidao_casamento", "certidao_obito"):
        item = get_by_short_code(code)
        assert item is not None
        low = item.content.lower()
        assert "registro civil" in low or "não é emitida nesta serventia" in low
        assert "tabelionato de notas" in low or "notas" in low


def test_canned_escritura_nao_fecha_preco_sem_faixa() -> None:
    for code in ("escritura_compra_venda", "escritura_doacao"):
        item = get_by_short_code(code)
        assert item is not None
        low = item.content.lower()
        assert "setor" in low or "escrevente" in low or "análise" in low or "analise" in low
        assert "itbi" in low or "itcd" in low or "itcmd" in low
