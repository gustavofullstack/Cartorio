"""Regras operacionais declaradas pela serventia, com forca de especificacao.

Fonte unica: `docs/MANUAL_TREINAMENTO_SERVENTIA_2026-08-12.md` — manual de
treinamento entregue por Felipe Pizarro (tabeliao substituto) em 2026-08-12,
complementado pelas correcoes que ele reportou em 2026-07-28 e 2026-08-12.

Por que aqui e nao no prompt direto: sao regras do cliente, nao da persona.
Mudam quando a serventia muda, precisam de teste de regressao e precisam ser
citaveis numa auditoria. O prompt consome ``bloco_prompt()``.

REGRA DE PRIORIDADE declarada pela serventia, em ordem:
1. Legislacao e normas vigentes
2. Normas e orientacoes oficiais competentes
3. Procedimentos internos expressos da serventia
4. Informacoes cadastradas pelo administrador
5. Orientacoes gerais de atendimento
Conflito nao resolvido nessa ordem => validacao humana obrigatoria.
"""

from __future__ import annotations

from typing import Final

# --- Balcao -----------------------------------------------------------------
# O atendimento presencial NAO e agendado. Oferecer horario contraria o
# funcionamento real da serventia (informado em 2026-08-12).
ATENDIMENTO_ORDEM_CHEGADA: Final[str] = (
    "O atendimento presencial e por ordem de chegada, sem pre-agendamento. "
    "Poucos servicos sao agendados; nao ofereca escolha de horario para atos de balcao."
)
SENHA_PREFERENCIAL: Final[tuple[str, ...]] = (
    "pessoa idosa",
    "pessoa autista",
    "pessoa com deficiencia",
    "advogado",
)

# --- Prazos e validades -----------------------------------------------------
CERTIDAO_PRAZO_DIAS_UTEIS: Final[int] = 5
VALIDADE_CERTIDAO_IMOVEL_DIAS: Final[int] = 30
VALIDADE_PROCURACAO_DIAS: Final[int] = 30
VALIDADE_JUNTA_COMERCIAL_DIAS: Final[int] = 30
VALIDADE_ESTADO_CIVIL_DIAS: Final[int] = 90
DOCUMENTO_PESSOAL_IDADE_MAXIMA_ANOS: Final[int] = 10

# --- Arquivamento -----------------------------------------------------------
# 1 ato de arquivamento por folha ou documento: um contrato PJ de 10 folhas
# sao 10 atos. Tratar como ato unico subestima o total ao cliente.
ARQUIVAMENTO_UNIDADE: Final[str] = "por folha ou documento"

# --- Regras juridicas sensiveis ---------------------------------------------
# Marcadas pela serventia com "ATENCAO PARA O CHATBOT": legitimidade restrita,
# nao ampliar nem interpretar.
TESTAMENTO_LEGITIMIDADE: Final[str] = (
    "Certidao de testamento tem legitimidade restrita: em vida do testador, somente "
    "o testador ou o legatario pode solicitar; apos o falecimento, o legatario deve "
    "comparecer e apresentar o atestado de obito. Em qualquer duvida sobre "
    "legitimidade, encaminhe para validacao humana em vez de interpretar a regra."
)
CERTIDAO_RETIRADA: Final[str] = (
    "Somente quem solicitou a certidao pode retira-la, salvo excecao admitida pela serventia."
)
NAO_PRESUMIR_INCAPACIDADE: Final[str] = (
    "Idade avancada e deficiencia NAO sao incapacidade. Nunca afirme que pessoa idosa "
    "precisa de atestado medico: a serventia pode adotar cautelas adicionais "
    "(entrevista previa, analise individualizada) caso a caso, e quem decide e a equipe."
)
FORMULARIO_INTERNO: Final[str] = (
    "Formulario interno e procedimento da serventia, nao obrigacao legal. Nunca diga "
    "que a lei obriga o preenchimento quando a informacao disponivel indicar apenas "
    "procedimento interno."
)
ENTREGA_DOCUMENTOS: Final[str] = (
    "Documentos de escritura sao entregues impressos na serventia para analise e agendamento."
)


def bloco_prompt() -> str:
    """Bloco compacto para o system prompt da Pietra.

    Mantido curto de proposito: o prompt ja e longo e cada linha aqui disputa
    atencao com as regras P0 de identidade e HITL.
    """
    preferencial = ", ".join(SENHA_PREFERENCIAL)
    return "\n".join(
        (
            "- Balcao: " + ATENDIMENTO_ORDEM_CHEGADA + f" Tem senha preferencial: {preferencial}.",
            (
                f"- Certidao: prazo de ate {CERTIDAO_PRAZO_DIAS_UTEIS} dias uteis -- NUNCA "
                f"prometa prazo inferior. {CERTIDAO_RETIRADA}"
            ),
            "- " + TESTAMENTO_LEGITIMIDADE,
            (
                "- Validades informadas pela serventia: certidao de imovel, procuracao e "
                f"certidao simplificada da Junta valem {VALIDADE_CERTIDAO_IMOVEL_DIAS} dias; "
                f"certidao de estado civil vale {VALIDADE_ESTADO_CIVIL_DIAS} dias. Documentos "
                f"pessoais expedidos ha mais de {DOCUMENTO_PESSOAL_IDADE_MAXIMA_ANOS} anos "
                "nao sao aceitos."
            ),
            (
                f"- Arquivamento e cobrado {ARQUIVAMENTO_UNIDADE}: um contrato de 10 folhas "
                "sao 10 atos de arquivamento. Nunca trate como ato unico."
            ),
            "- " + NAO_PRESUMIR_INCAPACIDADE,
            "- " + FORMULARIO_INTERNO,
            "- " + ENTREGA_DOCUMENTOS,
        )
    )
