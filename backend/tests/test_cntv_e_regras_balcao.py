"""Regras de balcão informadas pela serventia em 2026-08-12 (Felipe Pizarro).

Cobre o erro de preço a menor no reconhecimento de firma em transferência
veicular: o ato exige consulta à CNTV/MG por signatário, e o agente respondia
apenas o selo (R$ 11,61) num ato que custa R$ 16,61 ao cliente.
"""

from decimal import Decimal

from app.services.cartorio_agent import (
    ATENDIMENTO_PRESENCIAL,
    SERVICOS_CATALOGO,
    _match_servico,
)
from app.services.emolumento_operacional_balcao import (
    CNTV_MG,
    GENERAL_ITEMS,
    REPROGRAFIA,
    reconhecimento_firma_dut_total,
)


def test_cntv_e_repasse_e_nao_emolumento():
    assert CNTV_MG.total == Decimal("5.00")
    assert CNTV_MG.destinatario == "CNB/MG"
    # Nunca pode entrar na tabela de selos: nao gera ISS/TFJ/RECOMPE.
    assert "cntv" not in {k.lower() for k in GENERAL_ITEMS}


def test_reconhecimento_firma_dut_soma_a_consulta_cntv():
    selo = GENERAL_ITEMS["reconhecimento_firma"].total
    assert selo == Decimal("11.61")
    assert reconhecimento_firma_dut_total() == Decimal("16.61")
    assert reconhecimento_firma_dut_total() == selo + CNTV_MG.total


def test_catalogo_publica_o_total_correto_do_dut():
    _nome, valor = SERVICOS_CATALOGO["reconhecimento_firma_dut"]
    assert valor == "R$ 16,61"
    # O ato comum continua intacto.
    assert SERVICOS_CATALOGO["reconhecimento_firma"][1] == "R$ 11,61"


def test_reprografia_tem_os_valores_da_serventia():
    assert REPROGRAFIA["xerox_1_face"].total == Decimal("1.80")
    assert REPROGRAFIA["xerox_2_faces"].total == Decimal("3.60")


class TestMatchServico:
    def test_firma_com_veiculo_vai_para_o_dut(self):
        for frase in (
            "quanto custa reconhecer firma para vender meu carro",
            "preciso de reconhecimento de firma no DUT",
            "reconhecimento de assinatura no ATPV da moto",
            "reconhecer firma na transferência de veículo",
        ):
            assert _match_servico(frase) == "reconhecimento_firma_dut", frase

    def test_firma_sem_veiculo_continua_no_ato_comum(self):
        for frase in (
            "quanto custa reconhecer firma",
            "preciso reconhecer firma num contrato de aluguel",
        ):
            assert _match_servico(frase) == "reconhecimento_firma", frase

    def test_procuracao_para_vender_carro_nao_e_dut(self):
        # Sem termo de firma nao ha consulta CNTV — e procuracao.
        assert _match_servico("quero uma procuração para meu filho vender meu carro") == (
            "procuracao"
        )

    def test_xerox(self):
        assert _match_servico("vocês fazem xerox?") == "xerox_1_face"
        assert _match_servico("preciso de cópia frente e verso") == "xerox_2_faces"


class TestAtendimentoPresencial:
    def test_declara_ordem_de_chegada_sem_agendamento(self):
        texto = ATENDIMENTO_PRESENCIAL["ordem"].lower()
        assert "ordem de chegada" in texto
        assert "pré-agendamento" in texto or "pre-agendamento" in texto

    def test_lista_todos_os_grupos_de_senha_preferencial(self):
        texto = ATENDIMENTO_PRESENCIAL["preferencial"].lower()
        for grupo in ("idosa", "autista", "deficiência", "advogado"):
            assert grupo in texto, grupo

    def test_explica_que_cntv_nao_e_emolumento(self):
        texto = ATENDIMENTO_PRESENCIAL["repasse_cntv"]
        assert "R$ 5,00" in texto
        assert "não constitui emolumento" in texto
