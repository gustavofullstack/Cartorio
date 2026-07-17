"""Chatwoot Canned Responses v3 (G6.B.T2) — 10 respostas para atos especificos.

Expande chatwoot_canned_responses.py com 10 respostas juridicas adicionais:
- 2a via (documento, certidao)
- Protesto (consulta, baixa, cancelamento)
- Divorcio / inventário (atos especiais)
- Averbacoes

Total de respostas no sistema apos merge: 28 (v2) + 10 (v3) = 38.

Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 5.
"""

from __future__ import annotations

from app.services.chatwoot_canned_responses import CannedResponse

# =============================================================================
# 2a via (3 respostas)
# =============================================================================

CANNED_2VIA_INSTRUCOES = CannedResponse(
    short_code="2via_instrucoes",
    content=(
        "Para solicitar 2a via de documentos, voce pode:\n\n"
        "1. **Pelo portal**: https://2notasudi.com.br/2via (autenticacao CPF)\n"
        "2. **Por este chat**: digite o numero do protocolo (formato: PROT-2026-XXXXX)\n"
        "3. **Presencialmente**: Av. XXXX, XXX, Uberlandia/MG (seg-sex 8h-17h)\n\n"
        "Prazo: PDF disponivel em ate 24h uteis apos solicitacao.\n"
        "Validade: URL assinada SHA256 com expiracao em 24h."
    ),
    tags=("2via", "instrucoes", "documento"),
)

CANNED_2VIA_PRONTA = CannedResponse(
    short_code="2via_pronta",
    content=(
        "Seu documento esta disponivel para download!\n\n"
        "URL: {{url_documento}}\n"
        "Validade: 24 horas\n"
        "SHA256: {{hash_documento}}\n\n"
        "Caso a URL expire, solicite novamente pelo portal ou chat."
    ),
    tags=("2via", "pronto", "download"),
)

CANNED_2VIA_DOCUMENTOS_NECESSARIOS = CannedResponse(
    short_code="2via_docs",
    content=(
        "Para solicitar 2a via, voce precisa de:\n\n"
        "- CPF do titular (validacao automatica)\n"
        "- Numero do protocolo original (se nao tiver, pode buscar por CPF)\n"
        "- Para terceiros: procuracao + CPF do procurador\n\n"
        "Se voce nao tem o numero do protocolo, posso buscar pelos seus dados. "
        "Confirma o CPF?"
    ),
    tags=("2via", "documentos"),
)

# =============================================================================
# Protesto (3 respostas)
# =============================================================================

CANNED_PROTESTO_CONSULTA = CannedResponse(
    short_code="protesto_consulta",
    content=(
        "Para consultar titulos em protesto:\n\n"
        "1. **Por CPF/CNPJ**: https://2notasudi.com.br/protesto/consulta\n"
        "2. **Por numero do titulo**: necessario numero do protocolo + data protesto\n"
        "3. **Presencialmente**: Av. XXXX, XXX, Uberlandia/MG (seg-sex 8h-17h)\n\n"
        "Prazo: consulta gratuita ate 5 titulos/CPF/dia.\n"
        "LGPD: o CPF NAO eh armazenado na consulta (LGPD art. 18 IV)."
    ),
    tags=("protesto", "consulta"),
)

CANNED_PROTESTO_BAIXA = CannedResponse(
    short_code="protesto_baixa",
    content=(
        "Para solicitar baixa de protesto:\n\n"
        "Documentos necessarios:\n"
        "- **Titulo original** quitado (ou comprovante de pagamento)\n"
        "- **CPF/CNPJ** do devedor\n"
        "- **Numero do protesto** (se nao souber, busque pela data + valor)\n\n"
        "Prazo legal: 5 dias uteis apos quitacao.\n"
        "Custo: emolumento tabela MG 2026 + taxa cartorio.\n\n"
        "Posso iniciar o atendimento, voce confirma?"
    ),
    tags=("protesto", "baixa"),
)

CANNED_PROTESTO_CANCELAMENTO = CannedResponse(
    short_code="protesto_cancel",
    content=(
        "Cancelamento judicial de protesto requer:\n\n"
        "1. **Determinacao judicial** (ordem do juiz)\n"
        "2. **CPF/CNPJ** do devedor + numero do protesto\n"
        "3. **Peticao** assinada por advogado\n\n"
        "Prazo: 24h apos recebimento da ordem judicial.\n"
        "Auditoria: gravado em audit_log (LGPD art. 37).\n\n"
        "Este atendimento NAO pode ser feito pelo bot. "
        "Vou transferir para um escrevente humano. Aguarde."
    ),
    tags=("protesto", "cancelamento", "judicial", "handoff"),
)

# =============================================================================
# Divorcio / Inventario (2 respostas)
# =============================================================================

CANNED_DIVORCIO_CONSENSUAL = CannedResponse(
    short_code="divorcio_consensual",
    content=(
        "Divorcio consensual (extrajudicial em cartorio) exige:\n\n"
        "- Partes maiores e capazes\n"
        "- Sem filhos menores ou incapazes (ou com assistencia)\n"
        "- Assistencia de advogado (obrigatoria)\n"
        "- Partilha consensual de bens\n\n"
        "Documentos:\n"
        "- Certidao de casamento atualizada (90 dias)\n"
        "- CPF + RG de ambos\n"
        "- Certidao de bens/imoveis (se houver)\n"
        "- Comprovante de residencia\n\n"
        "Prazo: escrituracao em 1-2 sessoes (apos documentos OK).\n"
        "Custo: emolumento tabela MG 2026 + taxa ITBI (se houver imovel)."
    ),
    tags=("divorcio", "consensual", "extrajudicial"),
)

CANNED_INVENTARIO_EXTRAJUDICIAL = CannedResponse(
    short_code="inventario_extra",
    content=(
        "Inventario extrajudicial so eh possivel quando:\n\n"
        "- Todos os herdeiros sao maiores e capazes\n"
        "- Ha concordancia entre todos (sem testamento, OU testamento sem conflito)\n"
        "- Assistencia de advogado\n\n"
        "Documentos:\n"
        "- Certidao de obito (90 dias)\n"
        "- CPF + RG de todos os herdeiros + conjuge\n"
        "- Certidao de casamento do falecido (se aplicavel)\n"
        "- Certidao de bens (imoveis, veiculos, contas)\n"
        "- Testamento (se houver)\n\n"
        "Prazo: variavel (1-6 meses dependendo complexidade).\n"
        "Custo: emolumento tabela MG 2026 + ITBI + ITCMD.\n\n"
        "Vou transferir para um escrevente especialista. Aguarde."
    ),
    tags=("inventario", "extrajudicial", "handoff"),
)

# =============================================================================
# Averbacoes (2 respostas)
# =============================================================================

CANNED_AVERBACAO_EMANCIPACAO = CannedResponse(
    short_code="averbacao_emancipacao",
    content=(
        "Averbacao de emancipacao:\n\n"
        "Documentos:\n"
        "- Certidao de nascimento atualizada (90 dias)\n"
        "- Documento que justifica emancipacao (sentenca judicial, escritura, etc.)\n"
        "- CPF + RG do emancipando + responsavel\n\n"
        "Prazo: 5 dias uteis apos conferencia.\n"
        "Custo: emolumento tabela MG 2026.\n\n"
        "Posso iniciar o atendimento, confirma?"
    ),
    tags=("averbacao", "emancipacao", "menor"),
)

CANNED_AVERBACAO_CASAMENTO = CannedResponse(
    short_code="averbacao_casamento",
    content=(
        "Averbacao de casamento na certidao de nascimento:\n\n"
        "Como funciona: apos o casamento civil, o cartorio de registro civil "
        "encaminha a certidao para o cartorio de origem do nascimento. "
        "Esse cartorio faz a averbacao automaticamente em ate 30 dias.\n\n"
        "Se precisar de copia atualizada (com a averbacao):\n"
        "- Solicite no cartorio de registro civil\n"
        "- Ou pelo portal https://registrocivil.org.br\n\n"
        "LGPD: o ato NAO altera dados pessoais (apenas estado civil)."
    ),
    tags=("averbacao", "casamento", "registro civil"),
)

# =============================================================================
# Lista consolidada para registro
# =============================================================================

V3_CANNED_RESPONSES: tuple[CannedResponse, ...] = (
    CANNED_2VIA_INSTRUCOES,
    CANNED_2VIA_PRONTA,
    CANNED_2VIA_DOCUMENTOS_NECESSARIOS,
    CANNED_PROTESTO_CONSULTA,
    CANNED_PROTESTO_BAIXA,
    CANNED_PROTESTO_CANCELAMENTO,
    CANNED_DIVORCIO_CONSENSUAL,
    CANNED_INVENTARIO_EXTRAJUDICIAL,
    CANNED_AVERBACAO_EMANCIPACAO,
    CANNED_AVERBACAO_CASAMENTO,
)


def get_v3_short_codes() -> tuple[str, ...]:
    """Retorna short codes das v3 canned responses."""
    from app.services.chatwoot_canned_responses import extract_short_codes
    return extract_short_codes(V3_CANNED_RESPONSES)


__all__ = [
    "V3_CANNED_RESPONSES",
    "get_v3_short_codes",
] + [r.short_code.upper() for r in V3_CANNED_RESPONSES]
