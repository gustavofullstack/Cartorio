"""Contratos do perfil publico usado pelo agente de atendimento."""

from app.services.cartorio_agent import CARTORIO_INFO


def test_endereco_publico_canonico_nao_regride() -> None:
    """O agente usa o endereco corroborado pela pesquisa publica atual."""
    assert (
        CARTORIO_INFO["endereco"] == "Rua Cel. Antonio Alves Pereira, 850 - Centro, Uberlandia/MG"
    )
    assert CARTORIO_INFO["horario"] == "Segunda a sexta, 09h as 17h"


def test_dados_institucionais_nao_contem_victor_hugo() -> None:
    """Victor Hugo nunca deve constar como substituto no perfil publico."""
    info_text = str(CARTORIO_INFO).lower()
    for forbidden in ("victor hugo", "bianchini", "victor_hugo"):
        assert forbidden not in info_text, f"perfil publico citou nome invalido: {forbidden}"


def test_substitutos_sao_apenas_felipe_e_alexandra() -> None:
    """A lista canonica de substitutos so inclui Felipe Pizarro e Alexandra Jose Beicker."""
    titular = CARTORIO_INFO["titular"].lower()
    assert "felipe pizarro" in titular
    assert "alexandra" in titular
    assert "victor" not in titular
    assert "bianchini" not in titular


def test_endereco_unico_sem_unidade_complementar() -> None:
    """O perfil publico reforca endereco unico e nega unidade complementar."""
    info_text = str(CARTORIO_INFO).lower()
    assert "rua cel. antonio alves pereira, 850" in info_text
    assert "nao existe unidade complementar" in info_text
