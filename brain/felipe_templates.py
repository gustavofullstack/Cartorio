import json
from typing import Dict, Any

class FelipeNotaryTemplates:
    """
    Curated notary templates and official guidelines established by
    Tabelião Substituto Felipe Pizarro for Cartório de Notas e RTD.
    """

    EMAIL_EXIGENCIA_MATRICULAS_TESTAMENTO = """
Assunto: Resposta a Exigência Notarial - Apresentação de Matrículas em Testamento Público

Prezado(a) Cliente,

Levando em conta que a própria Corregedoria de Justiça e a jurisprudência consolidada acenam no sentido de que os princípios jurídicos norteiam a aplicação das normas, reforçamos o cuidado com os atos lavrados nesta Serventia, observando rigorosamente os princípios do art. 1º da Lei 8.935/94 (segurança jurídica, publicidade, autenticidade e eficácia dos atos jurídicos).

Assim, com respaldo no Provimento Conjunto CGJ-MG nº 93/2020, exigimos a apresentação de cópia atualizada das matrículas dos imóveis indicados, a fim de:
1. Garantir a correta individualização dos bens e a segurança jurídica do ato;
2. Verificar se a parcela de 50% da parte disponível está sendo estritamente respeitada (art. 1.846 do Código Civil), prevenindo futuras demandas judiciais de anulação movidas por herdeiros necessários.

Caso o(a) testador(a) opte por não apresentar as matrículas, o testamento poderá ser lavrado mediante a menção de frações percentuais para cada herdeiro (sem especificação individualizada dos imóveis). Ressaltamos que a responsabilidade total pela declaração correta da parte disponível recai sobre o testador.

Ademais, relembramos que a Serventia é fiscalizada pela Corregedoria de Justiça quanto aos valores declarados, sobre os quais incidem emolumentos, Taxa de Fiscalização Judiciária (TFJ), Recompe e demais fundos institucionais.

Atenciosamente,
Felipe Pizarro
Tabelião Substituto
"""

    MINUTA_TESTAMENTO_DILIGENCIA = """
ESCRITURA PÚBLICA DE TESTAMENTO COM DILIGÊNCIA NOTARIAL

Aos {data_extenso}, nesta cidade de Uberlândia, Estado de Minas Gerais, em diligência notarial realizada no endereço {endereco_diligencia}, a pedido do(a) Testador(a), eu, Felipe Pizarro, Tabelião Substituto responsável pela Serventia Notarial, compareci ao local e encontrei o(a) Sr(a). {nome_testador}, {qualificacao_testador}, que se achava em seu perfeito juízo e no gozo pleno de suas faculdades mentais, segundo o meu parecer e das duas testemunhas idôneas ao final nomeadas e assinadas.

O(A) Testador(a) apresentou atestado médico emitido pelo(a) Dr(a). {nome_medico}, CRM/MG nº {crm_medico}, datado de {data_atestado}, atestando sua plena capacidade civil e mental para a prática deste ato, o qual fica arquivado nas pastas desta Serventia.

Perante mim e as duas (02) testemunhas idôneas ao final qualificadas, o(a) Testador(a) declarou a sua última vontade, nos seguintes termos:

1. DECLARAÇÕES INICIAIS:
- Estado civil: {estado_civil_detalhado};
- Inexistência de união estável (ou qualificação do companheiro);
- Filiação e ausência/presença de herdeiros necessários (ascendentes/descendentes).

2. DISPOSIÇÃO PATRIMONIAL E LEGÍTIMA:
Respeitada a legítima dos herdeiros necessários prevista no art. 1.846 do Código Civil, o(a) Testador(a) dispõe da sua PARTE DISPONÍVEL (50% do seu acervo patrimonial) em favor de {qualificacao_herdeiros_testamentarios}.

3. CLÁUSULA REVOGATÓRIA:
O(A) Testador(a) declara que por este instrumento REVOGA expressamente qualquer testamento anterior lavrado em qualquer cartório ou data.

4. DECLARAÇÃO DE IMPARCIALIDADE DAS TESTEMUNHAS (ART. 228 CC):
O(A) Testador(a) e o Tabelião declaram que as testemunhas presentes não são amigos íntimos, inimigos, cônjuges, ascendentes, descendentes nem colaterais até o 3º grau dos beneficiários, cumprindo o art. 228 do Código Civil e o art. 1.864 do CC.

5. CENSEC:
Certifico e dou fé que os dados deste ato serão transmitidos à CENSEC (Central Notarial de Serviços Eletrônicos Compartilhados).

Lido em voz alta, clara e pausada perante o testador e testemunhas.
Eu, Felipe Pizarro, Tabelião Substituto, digitei e assino.
"""

    USUCAPIAO_BEM_MOVEL_RTD = """
REQUERIMENTO E ORIENTAÇÃO NOTARIAL - USUCAPIÃO EXTRAJUDICIAL DE BEM MÓVEL (RTD)

Fundamentação Legal: Arts. 1.260 a 1.262 do Código Civil Brasileiro.

1. MODALIDADES:
- Usucapião Ordinária (Art. 1.260 CC): Posse contínua e incontestada por 3 (três) anos, com justo título e boa-fé.
- Usucapião Extraordinária (Art. 1.261 CC): Posse contínua e incontestada por 5 (cinco) anos, independente de justo título ou boa-fé.

2. COMPETÊNCIA E REGISTRO:
O ato de registro final da aquisição originária de bem móvel deve ser processado no Cartório de Registro de Títulos e Documentos (RTD), mediante acompanhamento de Advogado habilitado.

3. CHECKLIST DOCUMENTAL EXIGIDO:
- Documentos de identidade (RG/CPF ou CNH) e comprovante de residência do requerente;
- Documento oficial do bem (CRLV para veículos, nota fiscal ou contrato de compra e venda);
- Declaração detalhada comprovando posse mansa, pacífica e contínua;
- Provas de posse (recibos de manutenção, impostos/IPVA pagos, fotos, histórico);
- Certidões negativas tributárias e de ônus sobre o bem;
- Declarações de testemunhas com firma reconhecida.
"""

    @classmethod
    def get_template(cls, template_key: str) -> str:
        templates = {
            "email_matriculas": cls.EMAIL_EXIGENCIA_MATRICULAS_TESTAMENTO,
            "minuta_testamento": cls.MINUTA_TESTAMENTO_DILIGENCIA,
            "usucapiao_bem_movel": cls.USUCAPIAO_BEM_MOVEL_RTD
        }
        return templates.get(template_key, "Template não encontrado.")
