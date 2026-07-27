"""Contratos do perfil publico usado pelo agente de atendimento."""

from app.services.cartorio_agent import CARTORIO_INFO


def test_endereco_publico_canonico_nao_regride() -> None:
    """O agente usa o endereco corroborado pela pesquisa publica atual."""
    assert CARTORIO_INFO["endereco"] == "Rua Cel. Antonio Alves Pereira, 850 - Centro, Uberlandia/MG"
    assert CARTORIO_INFO["horario"] == "Segunda a sexta, 09h as 17h"
