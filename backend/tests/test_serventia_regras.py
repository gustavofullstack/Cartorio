"""Trava as regras declaradas pela serventia em 2026-08-12.

Fonte: `docs/MANUAL_TREINAMENTO_SERVENTIA_2026-08-12.md` (Felipe Pizarro).
Elas ficaram 21 dias fora do código; estes testes existem para que não saiam de
novo sem alguém ver.
"""

import pytest

from app.api.v1.pietra import PIETRA_SYSTEM_PROMPT
from app.services import serventia_regras as sr


class TestConstantes:
    def test_prazo_de_certidao_e_o_informado_pela_serventia(self):
        assert sr.CERTIDAO_PRAZO_DIAS_UTEIS == 5

    def test_validades_declaradas(self):
        assert sr.VALIDADE_CERTIDAO_IMOVEL_DIAS == 30
        assert sr.VALIDADE_PROCURACAO_DIAS == 30
        assert sr.VALIDADE_JUNTA_COMERCIAL_DIAS == 30
        assert sr.VALIDADE_ESTADO_CIVIL_DIAS == 90

    def test_documento_pessoal_caduca_em_dez_anos(self):
        assert sr.DOCUMENTO_PESSOAL_IDADE_MAXIMA_ANOS == 10

    def test_senha_preferencial_cobre_os_quatro_grupos(self):
        assert set(sr.SENHA_PREFERENCIAL) == {
            "pessoa idosa",
            "pessoa autista",
            "pessoa com deficiencia",
            "advogado",
        }

    def test_arquivamento_e_por_folha_ou_documento(self):
        # Um contrato PJ de 10 folhas sao 10 atos, nao 1.
        assert sr.ARQUIVAMENTO_UNIDADE == "por folha ou documento"


class TestBlocoPrompt:
    @pytest.fixture(scope="class")
    def bloco(self) -> str:
        return sr.bloco_prompt()

    def test_declara_ordem_de_chegada(self, bloco):
        assert "ordem de chegada" in bloco
        assert "pre-agendamento" in bloco

    def test_lista_os_grupos_preferenciais(self, bloco):
        for grupo in sr.SENHA_PREFERENCIAL:
            assert grupo in bloco, grupo

    def test_proibe_prometer_prazo_menor_de_certidao(self, bloco):
        assert "5 dias uteis" in bloco
        assert "NUNCA prometa" in bloco

    def test_carrega_a_legitimidade_restrita_do_testamento(self, bloco):
        # Marcada pela serventia com "ATENCAO PARA O CHATBOT".
        assert "legatario" in bloco
        assert "atestado de obito" in bloco
        assert "validacao humana" in bloco

    def test_nao_presume_incapacidade_por_idade_ou_deficiencia(self, bloco):
        assert "NAO sao incapacidade" in bloco
        assert "atestado medico" in bloco

    def test_distingue_formulario_interno_de_obrigacao_legal(self, bloco):
        assert "nao obrigacao legal" in bloco


class TestPromptDaPietra:
    def test_o_bloco_da_serventia_entra_no_system_prompt(self):
        assert "REGRAS DA SERVENTIA" in PIETRA_SYSTEM_PROMPT
        assert sr.bloco_prompt() in PIETRA_SYSTEM_PROMPT

    def test_prompt_nao_promete_mais_agendamento_de_balcao(self):
        # O texto antigo oferecia "como agendar atendimento (online ou
        # presencial)", contrariando o funcionamento real da serventia.
        assert "como agendar atendimento (online ou presencial)" not in PIETRA_SYSTEM_PROMPT
        assert "ordem de chegada" in PIETRA_SYSTEM_PROMPT

    def test_regras_p0_de_identidade_seguem_intactas(self):
        # O bloco novo nao pode ter deslocado o que ja era P0.
        assert "Sou a Pietra" in PIETRA_SYSTEM_PROMPT
        assert "HITL" in PIETRA_SYSTEM_PROMPT
        assert "cartorio_calcular_emolumento" in PIETRA_SYSTEM_PROMPT
