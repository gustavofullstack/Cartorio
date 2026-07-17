"""Chatwoot Canned Responses v4 (G7.05.T4) — +10 respostas jurídicas MG.

Complementa v2+v3. Foco: autenticação, reconhecimento, escritura, LGPD,
horário, isenção (HITL), urgência (HITL), protocolo, FAQ.

Modified by Gustavo Almeida — G7 Wave 22.
"""

from __future__ import annotations

from app.services.chatwoot_canned_responses import CannedResponse

CANNED_AUTENTICACAO = CannedResponse(
    short_code="autenticacao_copia",
    content=(
        "Autenticacao de copia:\n\n"
        "- Leve o original e a copia (ou faca a copia no cartorio)\n"
        "- Documento precisa estar legivel e completo\n"
        "- Valor: emolumento tabela MG 2026 por folha (consultar bot: 'quanto custa autenticacao')\n"
        "- Prazo: na hora, em geral\n\n"
        "Isencoes e urgencias so com validacao do escrevente (HITL)."
    ),
    tags=("autenticacao", "copia", "faq"),
)

CANNED_RECONHECIMENTO_FIRMA = CannedResponse(
    short_code="reconhecimento_firma",
    content=(
        "Reconhecimento de firma:\n\n"
        "1. Abertura de firma (se ainda nao tiver): compareca com RG/CPF e faca padrao de assinatura\n"
        "2. Reconhecimento por autenticidade: assina na presenca do escrevente\n"
        "3. Por semelhanca: exige firma aberta e confere com cartao\n\n"
        "Nao faca reconhecimento 'sem a pessoa' — o cartorio nao valida isso."
    ),
    tags=("firma", "reconhecimento", "faq"),
)

CANNED_ESCRITURA_COMPRA_VENDA = CannedResponse(
    short_code="escritura_cv_docs",
    content=(
        "Escritura de compra e venda — documentos tipicos:\n\n"
        "- RG e CPF das partes\n"
        "- Certidao de estado civil atualizada\n"
        "- Matricula atualizada do imovel\n"
        "- Certidoes negativas (conforme caso)\n"
        "- Comprovante de ITBI / guias\n"
        "- Procuracao se houver representante\n\n"
        "Valores variam com o valor do imovel (tabela MG 2026). "
        "Vou transferir para escrevente para checklist completo (HITL)."
    ),
    tags=("escritura", "compra_venda", "handoff"),
)

CANNED_PROCURACAO = CannedResponse(
    short_code="procuracao_docs",
    content=(
        "Procuracao publica — o que trazer:\n\n"
        "- RG e CPF do outorgante (e outorgado, se possivel)\n"
        "- Poderes especificos (o que a pessoa pode fazer)\n"
        "- Dados do imovel/processo se for o caso\n\n"
        "Valor de referencia: consulte 'quanto custa procuracao'.\n"
        "Urgencia e isencao: apenas com validacao humana."
    ),
    tags=("procuracao", "docs", "faq"),
)

CANNED_HORARIO_ENDERECO = CannedResponse(
    short_code="horario_endereco",
    content=(
        "2o Servico Notarial de Uberlandia:\n\n"
        "- Horario: segunda a sexta, 09h as 17h\n"
        "- Endereco: conforme site oficial / placa do cartorio\n"
        "- Atendimento digital: este chat (Telegram/WhatsApp) com handoff humano\n\n"
        "Plantao e excecoes: confirme com escrevente."
    ),
    tags=("horario", "endereco", "faq"),
)

CANNED_LGPD_DIREITOS = CannedResponse(
    short_code="lgpd_direitos",
    content=(
        "Seus direitos LGPD (art. 18):\n\n"
        "- Acesso, correcao, anonimizacao, portabilidade, eliminacao, oposicao\n"
        "- Nao automatizacao de decisoes juridicas (HITL obrigatorio no cartorio)\n\n"
        "Para exercer: digite 'meus dados' / 'esqueci' / 'LGPD' ou fale com o DPO.\n"
        "Nao envie CPF no chat se puder evitar — preferimos fluxo seguro."
    ),
    tags=("lgpd", "direitos", "privacidade"),
)

CANNED_ISENCAO_HITL = CannedResponse(
    short_code="isencao_hitl",
    content=(
        "Isencao de emolumentos:\n\n"
        "O bot **nao concede isencao sozinho**. "
        "Elegibilidade depende de lei/CNJ e documentacao.\n\n"
        "Vou abrir atendimento com escrevente (HITL) para analisar o seu caso. "
        "Tenha em maos: documento de identidade e base legal/motivo da isencao."
    ),
    tags=("isencao", "hitl", "handoff"),
)

CANNED_URGENCIA_HITL = CannedResponse(
    short_code="urgencia_hitl",
    content=(
        "Pedido de urgencia:\n\n"
        "Urgencia pode gerar adicional (ex.: +50% em alguns atos) e "
        "depende de capacidade da serventia.\n\n"
        "O bot nao autoriza urgencia sozinho. "
        "Transferindo para escrevente validar prazo e valor (HITL)."
    ),
    tags=("urgencia", "hitl", "handoff"),
)

CANNED_PROTOCOLO_STATUS = CannedResponse(
    short_code="protocolo_status",
    content=(
        "Para consultar protocolo:\n\n"
        "1. Informe o numero (ex.: CART-2026-XXXXXX ou o formato do seu recibo)\n"
        "2. Posso consultar status no sistema (somente leitura)\n"
        "3. Alteracoes / cancelamentos / emissao: escrevente (HITL)\n\n"
        "Nao compartilhe dados de terceiros sem legitimidade."
    ),
    tags=("protocolo", "status", "consulta"),
)

CANNED_CERTIDAO = CannedResponse(
    short_code="certidao_orientacao",
    content=(
        "Certidoes (casamento, negativa, positiva, etc.):\n\n"
        "- Informe o tipo exato da certidao\n"
        "- Valores de referencia: tabela MG 2026 (ex.: certidao de casamento ~ R$ 105,40)\n"
        "- Prazo e documentos variam — escrevente confirma no atendimento\n\n"
        "Digite: 'quanto custa certidao de casamento' para simulacao."
    ),
    tags=("certidao", "emolumento", "faq"),
)

V4_CANNED_RESPONSES: tuple[CannedResponse, ...] = (
    CANNED_AUTENTICACAO,
    CANNED_RECONHECIMENTO_FIRMA,
    CANNED_ESCRITURA_COMPRA_VENDA,
    CANNED_PROCURACAO,
    CANNED_HORARIO_ENDERECO,
    CANNED_LGPD_DIREITOS,
    CANNED_ISENCAO_HITL,
    CANNED_URGENCIA_HITL,
    CANNED_PROTOCOLO_STATUS,
    CANNED_CERTIDAO,
)


def get_v4_short_codes() -> tuple[str, ...]:
    from app.services.chatwoot_canned_responses import extract_short_codes
    return extract_short_codes(V4_CANNED_RESPONSES)


def count_all_canned_v2_v3_v4() -> dict[str, int]:
    """Contagem consolidada para meta G7.05.T4 (20/50+)."""
    from app.services.chatwoot_canned_responses_v3 import V3_CANNED_RESPONSES
    from app.services.chatwoot_canned_responses import CANNED_RESPONSES as V2

    try:
        v2_n = len(V2) if V2 is not None else 0
    except Exception:
        v2_n = 0
    return {
        "v2": v2_n,
        "v3": len(V3_CANNED_RESPONSES),
        "v4": len(V4_CANNED_RESPONSES),
        "code_total": v2_n + len(V3_CANNED_RESPONSES) + len(V4_CANNED_RESPONSES),
    }


__all__ = [
    "V4_CANNED_RESPONSES",
    "get_v4_short_codes",
    "count_all_canned_v2_v3_v4",
]
