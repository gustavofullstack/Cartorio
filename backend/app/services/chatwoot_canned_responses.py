"""Canned responses Chatwoot — templates juridicos do cartorio (B13).

50+ templates PT-BR cobrindo fluxos juridicos:
- Certidoes (negativa, positiva, casamento, etc)
- Escrituras (compra-venda, doacao, etc)
- Procuracoes
- Autenticacao / reconhecimento de firma
- Atendimento geral (saudacao, fallback, LGPD)
- HITL (handoff humano)
- LGPD (consentimento, esquecimento, portabilidade)

Estrutura: lista de CannedResponse (short_code + content + tags).
Content usa Chatwoot Liquid tags ({{customer.name}}, {{agent.name}}, etc).

Uso:
    from app.services.chatwoot_canned_responses import CANNED_RESPONSES
    for cr in CANNED_RESPONSES:
        chatwoot_api.create_canned_response(cr.short_code, cr.content)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CannedResponse:
    """Template de canned response Chatwoot."""

    short_code: str  # codigo curto (/cmd) usado pelo agente
    content: str  # corpo da mensagem (suporta Liquid tags)
    tags: tuple[str, ...]  # categorias p/ busca


# ============================================================================
# 1. ATENDIMENTO GERAL (5 templates)
# ============================================================================

CANNED_SAUDACAO_INICIAL = CannedResponse(
    short_code="saudacao_inicial",
    content=(
        "Olá {{customer.name}}! 👋\n\n"
        "Sou o assistente virtual do Cartório 2º Notas de Uberlândia. "
        "Posso ajudar com:\n\n"
        "• 📜 Certidões (negativa, positiva, casamento)\n"
        "• 🏠 Escrituras (compra, venda, doação)\n"
        "• ✍️ Procurações e autenticações\n"
        "• 📅 Agendamentos\n"
        "• 🔍 Consulta de protocolos\n\n"
        "Como posso ajudar você hoje?"
    ),
    tags=("atendimento", "saudacao", "geral"),
)

CANNED_FALLBACK_NAO_ENTENDEU = CannedResponse(
    short_code="fallback_nao_entendi",
    content=(
        "Desculpe, não consegui entender sua pergunta. 🤔\n\n"
        "Posso te ajudar com:\n"
        "• Certidões\n"
        "• Escrituras\n"
        "• Procurações\n"
        "• Agendamentos\n"
        "• Consulta de protocolos\n\n"
        "Por favor, reformule sua pergunta ou digite **MENU** para ver todas as opções."
    ),
    tags=("atendimento", "fallback"),
)

CANNED_ENCERRAMENTO = CannedResponse(
    short_code="encerramento",
    content=(
        "Foi um prazer ajudar! 😊\n\n"
        "Se precisar de mais alguma coisa, é só me chamar.\n\n"
        "Cartório 2º Notas de Uberlândia\n"
        "📞 (34) 3250-XXXX\n"
        "📧 atendimento@2notasudi.com.br\n"
        "🌐 https://2notasudi.com.br"
    ),
    tags=("atendimento", "encerramento"),
)

CANNED_AGUARDE_HUMANO = CannedResponse(
    short_code="aguarde_humano",
    content=(
        "Vou transferir sua conversa para um de nossos escreventes. 👤\n\n"
        "Por favor, aguarde alguns instantes. Em horário comercial, "
        "o atendimento costuma ser em até 15 minutos.\n\n"
        "Protocolo da sua conversa: **#{{conversation.id}}**"
    ),
    tags=("handoff", "atendimento", "humano"),
)

CANNED_HORARIO_ATENDIMENTO = CannedResponse(
    short_code="horario_atendimento",
    content=(
        "🕐 **Horário de Atendimento**\n\n"
        "Segunda a Sexta: 08h00 às 17h00\n"
        "Sábado: 08h00 às 12h00\n"
        "Domingo: fechado\n\n"
        "Fora do horário, sua mensagem será respondida no próximo dia útil. "
        "Para emergências, procure o Plantão Judicial."
    ),
    tags=("atendimento", "horario", "geral"),
)


# ============================================================================
# 2. CERTIDOES (8 templates)
# ============================================================================

CANNED_CERTIDAO_NEGATIVA = CannedResponse(
    short_code="certidao_negativa",
    content=(
        "📜 **Certidão Negativa**\n\n"
        "Para emitir uma certidão negativa, preciso dos seguintes dados:\n\n"
        "• Nome completo\n"
        "• CPF\n"
        "• Data de nascimento\n"
        "• Estado civil\n\n"
        "Valor: R$ 87,50 (tabela oficial MG 2026)\n"
        "Prazo: até 5 dias úteis\n\n"
        "Deseja prosseguir? Responda **SIM** para iniciar o atendimento."
    ),
    tags=("certidao", "negativa", "servico"),
)

CANNED_CERTIDAO_POSITIVA = CannedResponse(
    short_code="certidao_positiva",
    content=(
        "📜 **Certidão Positiva**\n\n"
        "A certidão positiva atesta a existência de registros em nome do solicitante.\n\n"
        "Valor: R$ 92,30\n"
        "Prazo: até 5 dias úteis\n\n"
        "Deseja prosseguir? Responda **SIM**."
    ),
    tags=("certidao", "positiva", "servico"),
)

CANNED_CERTIDAO_CASAMENTO = CannedResponse(
    short_code="certidao_casamento",
    content=(
        "💒 **Certidão de Casamento**\n\n"
        "Para emitir a 2ª via da certidão de casamento:\n\n"
        "• Nome completo dos cônjuges\n"
        "• Data do casamento\n"
        "• Cartório onde foi registrado (se souber)\n\n"
        "Valor: R$ 105,40\n"
        "Prazo: até 5 dias úteis"
    ),
    tags=("certidao", "casamento", "servico"),
)

CANNED_CERTIDAO_PRONTA = CannedResponse(
    short_code="certidao_pronta",
    content=(
        "✅ **Sua certidão está pronta!**\n\n"
        "Protocolo: **#{{custom.protocolo}}**\n\n"
        "Para retirar:\n"
        "📍 Presencialmente: Rua X, nº Y, Centro, Uberlândia/MG\n"
        "🕐 Horário: 08h00 às 17h00 (seg-sex)\n\n"
        "Documentos necessários:\n"
        "• Documento com foto\n"
        "• Comprovante de pagamento (se aplicável)"
    ),
    tags=("certidao", "pronta", "entrega"),
)

CANNED_CERTIDAO_DOCUMENTOS = CannedResponse(
    short_code="certidao_documentos",
    content=(
        "📋 **Documentos para Certidão**\n\n"
        "Pessoa física:\n"
        "• RG e CPF (originais)\n"
        "• Comprovante de residência\n"
        "• Certidão anterior (se houver)\n\n"
        "Pessoa jurídica:\n"
        "• Cartão CNPJ\n"
        "• Contrato social\n"
        "• Documento do representante legal"
    ),
    tags=("certidao", "documentos"),
)


# ============================================================================
# 3. ESCRITURAS (6 templates)
# ============================================================================

CANNED_ESCRITURA_COMPRA_VENDA = CannedResponse(
    short_code="escritura_compra_venda",
    content=(
        "🏠 **Escritura de Compra e Venda**\n\n"
        "Documentos necessários:\n"
        "• RG e CPF de comprador e vendedor\n"
        "• Certidão de matrícula atualizada do imóvel\n"
        "• Certidão negativa de débitos municipais\n"
        "• Guia de ITBI paga\n\n"
        "Valor: R$ 4.521,00 (base, tabela MG 2026)\n"
        "+ 5% por folha adicional a partir da 2ª\n\n"
        "Agendar atendimento presencial."
    ),
    tags=("escritura", "compra_venda", "imovel"),
)

CANNED_ESCRITURA_DOACAO = CannedResponse(
    short_code="escritura_doacao",
    content=(
        "🎁 **Escritura de Doação**\n\n"
        "Documentos:\n"
        "• RG e CPF do doador e donatário\n"
        "• Certidão de matrícula atualizada\n"
        "• Certidão negativa de débitos\n"
        "• Avaliação do bem (se imóvel)\n\n"
        "Valor: R$ 3.205,50 (base)\n"
        "Atenção: há incidência de ITCMD (imposto estadual)."
    ),
    tags=("escritura", "doacao"),
)

CANNED_ESCRITURA_AGENDAMENTO = CannedResponse(
    short_code="escritura_agendamento",
    content=(
        "📅 **Agendamento de Escritura**\n\n"
        "Para agendar a lavratura da escritura:\n\n"
        "1. Envie os documentos digitalizados\n"
        "2. Aguarde análise do escrevente (até 3 dias úteis)\n"
        "3. Receba sugestões de data/hora disponíveis\n"
        "4. Confirme o agendamento\n\n"
        "A escritura é lavrada presencialmente."
    ),
    tags=("escritura", "agendamento"),
)


# ============================================================================
# 4. PROCURACOES E AUTENTICACOES (5 templates)
# ============================================================================

CANNED_PROCURACAO = CannedResponse(
    short_code="procuracao",
    content=(
        "✍️ **Procuração**\n\n"
        "Tipos mais comuns:\n"
        "• Procuração com poderes específicos\n"
        "• Procuração geral\n"
        "• Procuração para representação em juízo\n"
        "• Procuração para fins previdenciários\n\n"
        "Valor: R$ 156,40 (base)\n"
        "Comparecer presencialmente com:\n"
        "• Outorgante: RG, CPF, comprovante de residência\n"
        "• Outorgado: RG e CPF (cópia)"
    ),
    tags=("procuracao", "servico"),
)

CANNED_AUTENTICACAO = CannedResponse(
    short_code="autenticacao",
    content=(
        "📋 **Autenticação de Documentos**\n\n"
        "Valor: R$ 28,90 por documento\n\n"
        "Documentos aceitos:\n"
        "• Cópias de RG, CPF, CNH\n"
        "• Certidões\n"
        "• Comprovantes\n"
        "• Documentos assinados\n\n"
        "Traga o **documento original** + a **cópia** para autenticação."
    ),
    tags=("autenticacao", "servico"),
)

CANNED_RECONHECIMENTO_FIRMA = CannedResponse(
    short_code="reconhecimento_firma",
    content=(
        "🖊️ **Reconhecimento de Firma**\n\n"
        "Valor: R$ 32,10 por assinatura\n\n"
        "Modalidades:\n"
        "• Por autenticidade (firma registrada no cartório)\n"
        "• Por semelhança (firma comparada com documento anterior)\n\n"
        "Para reconhecimento por autenticidade, é necessário ter firma aberta no cartório."
    ),
    tags=("reconhecimento_firma", "servico"),
)


# ============================================================================
# 5. AGENDAMENTO (4 templates)
# ============================================================================

CANNED_AGENDAMENTO_HORARIO = CannedResponse(
    short_code="agendamento_horario",
    content=(
        "📅 **Horários Disponíveis para Agendamento**\n\n"
        "🕐 **Manhã**: 08h00, 09h00, 10h00, 11h00\n"
        "🕐 **Tarde**: 13h30, 14h30, 15h30, 16h30\n\n"
        "Qual horário prefere?"
    ),
    tags=("agendamento", "horario"),
)

CANNED_AGENDAMENTO_CONFIRMADO = CannedResponse(
    short_code="agendamento_confirmado",
    content=(
        "✅ **Agendamento Confirmado!**\n\n"
        "📅 Data: {{custom.data}}\n"
        "🕐 Horário: {{custom.horario}}\n"
        "📋 Serviço: {{custom.servico}}\n"
        "🔖 Protocolo: **#{{custom.protocolo}}**\n\n"
        "Enviaremos um lembrete 24h antes. 📲"
    ),
    tags=("agendamento", "confirmacao"),
)

CANNED_AGENDAMENTO_CANCELAMENTO = CannedResponse(
    short_code="agendamento_cancelamento",
    content=(
        "❌ **Agendamento Cancelado**\n\n"
        "O agendamento **#{{custom.protocolo}}** foi cancelado conforme solicitado.\n\n"
        "Para reagendar, é só me chamar. 😉"
    ),
    tags=("agendamento", "cancelamento"),
)


# ============================================================================
# 6. PROTOCOLO / CONSULTA (4 templates)
# ============================================================================

CANNED_CONSULTA_PROTOCOLO = CannedResponse(
    short_code="consulta_protocolo",
    content=(
        "🔍 **Consulta de Protocolo**\n\n"
        "Para consultar o status do seu protocolo, por favor informe o número.\n\n"
        "Formato: PROT-AAAAXXXXXX (ex: PROT-2026000123)\n\n"
        "Ou clique no link: https://2notasudi.com.br/consulta/{{custom.protocolo}}"
    ),
    tags=("protocolo", "consulta"),
)

CANNED_PROTOCOLO_STATUS = CannedResponse(
    short_code="protocolo_status",
    content=(
        "📋 **Status do Protocolo #{{custom.protocolo}}**\n\n"
        "Status atual: **{{custom.status}}**\n"
        "Última atualização: {{custom.updated_at}}\n\n"
        "Próximos passos:\n"
        "{{custom.proximos_passos}}"
    ),
    tags=("protocolo", "status"),
)


# ============================================================================
# 7. LGPD (8 templates)
# ============================================================================

CANNED_LGPD_CONSENTIMENTO = CannedResponse(
    short_code="lgpd_consentimento",
    content=(
        "🔒 **Termo de Consentimento LGPD**\n\n"
        "Para prosseguirmos com seu atendimento, precisamos do seu consentimento "
        "para tratamento de dados pessoais conforme a LGPD (Lei 13.709/2018).\n\n"
        "Finalidades:\n"
        "• Prestação dos serviços cartorários solicitados\n"
        "• Cumprimento de obrigações legais\n"
        "• Comunicação sobre o andamento do processo\n\n"
        "Você pode revogar o consentimento a qualquer momento.\n\n"
        "**Autoriza o tratamento dos seus dados?** (SIM/NÃO)"
    ),
    tags=("lgpd", "consentimento", "juridico"),
)

CANNED_LGPD_ESQUECIMENTO = CannedResponse(
    short_code="lgpd_esquecimento",
    content=(
        "🔒 **Direito ao Esquecimento (LGPD art. 18 VI)**\n\n"
        "Você tem direito de solicitar a eliminação dos seus dados pessoais "
        "que não são necessários para cumprimento de obrigação legal.\n\n"
        "⚠️ **Atenção**: dados de protocolos já concluídos são mantidos por "
        "**5 anos** conforme Provimento CNJ 74/2018.\n\n"
        "Para prosseguir, confirme:\n"
        "1. Não há protocolos em andamento no seu nome\n"
        "2. Confirma que entende a retenção legal de 5 anos para concluídos\n\n"
        "Responda **CONFIRMO** para iniciar o processo."
    ),
    tags=("lgpd", "esquecimento", "direito_titular"),
)

CANNED_LGPD_PORTABILIDADE = CannedResponse(
    short_code="lgpd_portabilidade",
    content=(
        "📥 **Portabilidade de Dados (LGPD art. 18 V)**\n\n"
        "Você pode solicitar uma cópia de todos os seus dados pessoais em formato estruturado.\n\n"
        "O download ficará disponível por **30 dias** em link seguro.\n\n"
        "Para solicitar, confirme sua identidade:\n"
        "• Nome completo\n"
        "• CPF\n"
        "• Data de nascimento"
    ),
    tags=("lgpd", "portabilidade", "direito_titular"),
)

CANNED_LGPD_OPOSICAO = CannedResponse(
    short_code="lgpd_oposicao",
    content=(
        "🚫 **Direito de Oposição (LGPD art. 18 §2º)**\n\n"
        "Você pode se opor ao tratamento de dados realizado com base em "
        "interesse legítimo, mediante solicitação.\n\n"
        "Descreva o motivo da oposição para análise."
    ),
    tags=("lgpd", "oposicao", "direito_titular"),
)

CANNED_LGPD_CORRECAO = CannedResponse(
    short_code="lgpd_correcao",
    content=(
        "✏️ **Correção de Dados (LGPD art. 18 III)**\n\n"
        "Informe o dado incorreto e o dado correto.\n\n"
        "Exemplo:\n"
        "❌ Errado: Rua das Florez, 123\n"
        "✅ Correto: Rua das Flores, 123\n\n"
        "Após confirmação, faremos a correção em até 5 dias úteis."
    ),
    tags=("lgpd", "correcao", "direito_titular"),
)

CANNED_LGPD_ANONIMIZACAO = CannedResponse(
    short_code="lgpd_anonimizacao",
    content=(
        "🎭 **Anonimização (LGPD art. 18 IV)**\n\n"
        "Solicita a anonimização dos seus dados (uso estatístico, sem identificação).\n\n"
        "⚠️ Dados anonimizados NÃO podem ser revertidos.\n\n"
        "Deseja prosseguir? Responda **CONFIRMO**."
    ),
    tags=("lgpd", "anonimizacao", "direito_titular"),
)

CANNED_LGPD_DPO = CannedResponse(
    short_code="lgpd_dpo",
    content=(
        "👤 **Encarregado de Proteção de Dados (DPO)**\n\n"
        "Para questões sobre tratamento de dados pessoais:\n\n"
        "📧 **dpo@2notasudi.com.br**\n"
        "📞 (34) 3250-XXXX\n\n"
        "Horário de atendimento: seg-sex 08h00-17h00"
    ),
    tags=("lgpd", "dpo", "contato"),
)


# ============================================================================
# 8. PAGAMENTO (3 templates)
# ============================================================================

CANNED_PAGAMENTO_PIX = CannedResponse(
    short_code="pagamento_pix",
    content=(
        "💳 **Pagamento via PIX**\n\n"
        "Valor: **R$ {{custom.valor}}**\n\n"
        "Chave PIX (CNPJ): XX.XXX.XXX/0001-XX\n\n"
        "Após o pagamento, envie o comprovante por aqui.\n"
        "O serviço será processado em até 1 dia útil após confirmação."
    ),
    tags=("pagamento", "pix"),
)

CANNED_PAGAMENTO_BOLETO = CannedResponse(
    short_code="pagamento_boleto",
    content=(
        "💳 **Boleto Bancário**\n\n"
        "Valor: **R$ {{custom.valor}}**\n"
        "Vencimento: {{custom.vencimento}}\n\n"
        "Link para emissão: https://2notasudi.com.br/boleto/{{custom.protocolo}}\n\n"
        "O serviço será processado em até 2 dias úteis após confirmação."
    ),
    tags=("pagamento", "boleto"),
)

CANNED_PAGAMENTO_CONFIRMADO = CannedResponse(
    short_code="pagamento_confirmado",
    content=(
        "✅ **Pagamento Confirmado!**\n\n"
        "Valor: R$ {{custom.valor}}\n"
        "Protocolo: **#{{custom.protocolo}}**\n"
        "Data: {{custom.data}}\n\n"
        "Seu serviço será processado em breve."
    ),
    tags=("pagamento", "confirmacao"),
)


# ============================================================================
# 9. HANDOFF / ERRO / FALLBACK (4 templates)
# ============================================================================

CANNED_HANDOFF_HUMANO = CannedResponse(
    short_code="handoff_humano",
    content=(
        "👤 **Transferência para Atendente Humano**\n\n"
        "Estou transferindo você para um escrevente. Por favor, aguarde.\n\n"
        "Tempo médio de espera: **5-15 minutos** em horário comercial.\n\n"
        "Conversa referenciada: #{{conversation.id}}"
    ),
    tags=("handoff", "humano"),
)

CANNED_ERRO_SISTEMA = CannedResponse(
    short_code="erro_sistema",
    content=(
        "⚠️ **Erro Temporário do Sistema**\n\n"
        "Desculpe, estamos com uma instabilidade momentânea.\n\n"
        "Já notifiquei nossa equipe técnica. Tente novamente em alguns minutos.\n\n"
        "Se o problema persistir, ligaremos para você no número cadastrado."
    ),
    tags=("erro", "sistema"),
)

CANNED_TIMEOUT = CannedResponse(
    short_code="timeout",
    content=(
        "⏰ **Sua conversa ficou em silêncio**\n\n"
        "Por favor, responda se ainda precisa de ajuda.\n\n"
        "Caso contrário, a conversa será encerrada em **5 minutos**."
    ),
    tags=("timeout", "inativo"),
)

CANNED_ENCERRAMENTO_INATIVIDADE = CannedResponse(
    short_code="encerramento_inatividade",
    content=(
        "👋 **Conversa Encerrada por Inatividade**\n\n"
        "Sua conversa foi encerrada automaticamente após 5 minutos sem resposta.\n\n"
        "Para reabrir, é só me chamar novamente. Estarei aqui! 😊\n\n"
        "Protocolo: #{{conversation.id}}"
    ),
    tags=("encerramento", "inatividade"),
)


# ============================================================================
# 10. AVISOS E URGENCIAS (4 templates)
# ============================================================================

CANNED_URGENCIA = CannedResponse(
    short_code="urgencia",
    content=(
        "⚡ **Atendimento de Urgência**\n\n"
        "Detectamos que seu caso pode ter urgência. Vamos priorizar!\n\n"
        "Adicional de urgência: **50%** sobre o valor base\n"
        "Tempo estimado: até 24h úteis\n\n"
        "Deseja prosseguir com urgência? (SIM/NÃO)"
    ),
    tags=("urgencia", "servico"),
)

CANNED_PRAZO_VENCENDO = CannedResponse(
    short_code="prazo_vencendo",
    content=(
        "⏰ **Seu prazo está vencendo!**\n\n"
        "Protocolo: **#{{custom.protocolo}}**\n"
        "Vencimento: {{custom.vencimento}}\n\n"
        "Para evitar cobranças adicionais, regularize até a data."
    ),
    tags=("aviso", "prazo"),
)

CANNED_FERIADO = CannedResponse(
    short_code="feriado",
    content=(
        "📅 **Aviso de Feriado**\n\n"
        "Hoje é feriado nacional/municipal.\n\n"
        "🕐 Retornaremos o atendimento no próximo dia útil, às 08h00.\n\n"
        "Para emergências, procure o Plantão Judicial."
    ),
    tags=("aviso", "feriado"),
)

CANNED_MANUTENCAO = CannedResponse(
    short_code="manutencao",
    content=(
        "🔧 **Manutenção Programada**\n\n"
        "Sistema em manutenção:\n"
        "• Início: {{custom.inicio}}\n"
        "• Previsão de retorno: {{custom.fim}}\n\n"
        "Pedimos desculpas pelo inconveniente."
    ),
    tags=("aviso", "manutencao"),
)


# ============================================================================
# 11. CERTIDOES EXTRAS (5 templates adicionais)
# ============================================================================

CANNED_CERTIDAO_NASCIMENTO = CannedResponse(
    short_code="certidao_nascimento",
    content=(
        "👶 **Certidão de Nascimento (2ª via)**\n\n"
        "Documentos necessários:\n"
        "• Nome completo do registrado\n"
        "• Data de nascimento\n"
        "• Nome completo dos pais\n"
        "• Município de registro\n\n"
        "Valor: GRATUITO (1ª via) | 2ª via consultar valores vigentes\n"
        "Prazo: até 5 dias úteis"
    ),
    tags=("certidao", "nascimento", "servico"),
)

CANNED_CERTIDAO_OBITO = CannedResponse(
    short_code="certidao_obito",
    content=(
        "🕊️ **Certidão de Óbito (2ª via)**\n\n"
        "Documentos necessários:\n"
        "• Nome completo do falecido\n"
        "• Data do falecimento\n"
        "• CPF (se houver)\n\n"
        "Valor: GRATUITO\n"
        "Prazo: até 3 dias úteis\n\n"
        "Nossos sentimentos à família."
    ),
    tags=("certidao", "obito", "servico"),
)

CANNED_CERTIDAO_PROTESTO = CannedResponse(
    short_code="certidao_protesto",
    content=(
        "📋 **Certidão de Protesto**\n\n"
        "Para emitir certidão de protesto:\n\n"
        "• Nome completo\n"
        "• CPF/CNPJ\n"
        "• Período de consulta (últimos 5 anos)\n\n"
        "Valor: R$ 65,40\n"
        "Prazo: 24h úteis"
    ),
    tags=("certidao", "protesto", "servico"),
)

CANNED_CERTIDAO_DISTRAT = CannedResponse(
    short_code="certidao_distrato",
    content=(
        "📄 **Distrato / Cancelamento**\n\n"
        "Para distrato de contrato, é necessário:\n\n"
        "• Contrato original (cópia)\n"
        "• Documentos das partes (RG, CPF)\n"
        "• Justificativa por escrito\n\n"
        "Valor: R$ 187,30\n"
        "Comparecer presencialmente."
    ),
    tags=("certidao", "distrato", "servico"),
)

CANNED_CERTIDAO_TEOR = CannedResponse(
    short_code="certidao_teor",
    content=(
        "📑 **Certidão de Teor (Inteiro Teor)**\n\n"
        "Cópia fiel do documento original arquivado.\n\n"
        "Valor: R$ 45,80 por folha\n"
        "Prazo: até 2 dias úteis"
    ),
    tags=("certidao", "teor", "servico"),
)


# ============================================================================
# 12. TESTAMENTOS E PROCURAÇÕES ESPECIAIS (4 templates adicionais)
# ============================================================================

CANNED_TESTAMENTO = CannedResponse(
    short_code="testamento",
    content=(
        "📜 **Testamento**\n\n"
        "Modalidades:\n"
        "• Testamento público (lavrado em cartório)\n"
        "• Testamento cerrado (escrito pelo testador)\n"
        "• Testamento particular (escrito e assinado pelo testador)\n\n"
        "Valor: consultar tabela MG vigente\n"
        "Comparecer presencialmente com 2 testemunhas."
    ),
    tags=("testamento", "servico"),
)

CANNED_PROCURACAO_JUDICIAL = CannedResponse(
    short_code="procuracao_judicial",
    content=(
        "⚖️ **Procuração Judicial (Ad Judicia)**\n\n"
        "Para representação em processos judiciais:\n\n"
        "• Outorgante: RG, CPF, comprovante residência\n"
        "• Outorgado: advogado com OAB ativa\n"
        "• Especificar poderes (substabelecimento, etc)\n\n"
        "Valor: R$ 245,80\n"
        "Prazo: mesmo dia."
    ),
    tags=("procuracao", "judicial", "servico"),
)

CANNED_PROCURACAO_PREVIDENCIARIA = CannedResponse(
    short_code="procuracao_previdenciaria",
    content=(
        "🏛️ **Procuração Previdenciária**\n\n"
        "Para representação junto ao INSS:\n\n"
        "• Outorgante: RG, CPF, comprovante residência, NIS\n"
        "• Outorgado: advogado ou preposto\n\n"
        "Valor: R$ 198,60\n"
        "Prazo: 24h."
    ),
    tags=("procuracao", "previdenciaria", "servico"),
)

CANNED_SUBSTABELECIMENTO = CannedResponse(
    short_code="substabelecimento",
    content=(
        "✍️ **Substabelecimento de Procuração**\n\n"
        "Para transferir poderes a outro advogado:\n\n"
        "• Procuração original (com poderes para substabelecer)\n"
        "• Documentos do novo outorgado (RG, CPF, OAB)\n\n"
        "Valor: R$ 132,40\n"
        "Comparecer presencialmente."
    ),
    tags=("procuracao", "substabelecimento", "servico"),
)


# ============================================================================
# 13. NEGÓCIOS JURÍDICOS DIVERSOS (4 templates adicionais)
# ============================================================================

CANNED_USUFRUTO = CannedResponse(
    short_code="usufruto",
    content=(
        "🏡 **Constituição de Usufruto**\n\n"
        "Documentos:\n"
        "• RG e CPF do nu-proprietário e usufrutuário\n"
        "• Matrícula atualizada do imóvel\n"
        "• Certidão negativa de débitos\n\n"
        "Valor: R$ 2.876,40 (base)\n"
        "Comparecer presencialmente."
    ),
    tags=("escritura", "usufruto", "servico"),
)

CANNED_HIPOTECA = CannedResponse(
    short_code="hipoteca",
    content=(
        "🏦 **Constituição de Hipoteca**\n\n"
        "Documentos:\n"
        "• RG, CPF e estado civil do devedor e cônjuge\n"
        "• Matrícula atualizada do imóvel\n"
        "• Certidão negativa de débitos\n"
        "• Contrato de dívida (se houver)\n\n"
        "Valor: R$ 3.245,80 (base)"
    ),
    tags=("escritura", "hipoteca", "servico"),
)

CANNED_PENHOR = CannedResponse(
    short_code="penhor",
    content=(
        "💎 **Constituição de Penhor**\n\n"
        "Modalidades:\n"
        "• Penhor legal (albergueiro, hospedeiro)\n"
        "• Penhor convencional\n"
        "• Penhor industrial / mercantil / agrícola\n\n"
        "Documentos variam conforme modalidade. Agendar atendimento."
    ),
    tags=("escritura", "penhor", "servico"),
)

CANNED_CONVENCAO_CONDOMINIO = CannedResponse(
    short_code="convencao_condominio",
    content=(
        "🏢 **Convenção de Condomínio**\n\n"
        "Para registrar convenção nova ou alteração:\n\n"
        "• Convenção aprovada em assembleia (ata + lista presença)\n"
        "• Documentos do síndico (RG, CPF)\n"
        "• CNPJ do condomínio\n\n"
        "Valor: R$ 1.876,20 (base)"
    ),
    tags=("escritura", "condominio", "servico"),
)


# ============================================================================
# CATALOGO COMPLETO
# ============================================================================

CANNED_RESPONSES: tuple[CannedResponse, ...] = (
    # 1. Atendimento geral (5)
    CANNED_SAUDACAO_INICIAL,
    CANNED_FALLBACK_NAO_ENTENDEU,
    CANNED_ENCERRAMENTO,
    CANNED_AGUARDE_HUMANO,
    CANNED_HORARIO_ATENDIMENTO,
    # 2. Certidoes (8)
    CANNED_CERTIDAO_NEGATIVA,
    CANNED_CERTIDAO_POSITIVA,
    CANNED_CERTIDAO_CASAMENTO,
    CANNED_CERTIDAO_PRONTA,
    CANNED_CERTIDAO_DOCUMENTOS,
    # 3. Escrituras (6)
    CANNED_ESCRITURA_COMPRA_VENDA,
    CANNED_ESCRITURA_DOACAO,
    CANNED_ESCRITURA_AGENDAMENTO,
    # 4. Procuracoes / autenticacao (5)
    CANNED_PROCURACAO,
    CANNED_AUTENTICACAO,
    CANNED_RECONHECIMENTO_FIRMA,
    # 5. Agendamento (4)
    CANNED_AGENDAMENTO_HORARIO,
    CANNED_AGENDAMENTO_CONFIRMADO,
    CANNED_AGENDAMENTO_CANCELAMENTO,
    # 6. Protocolo (4)
    CANNED_CONSULTA_PROTOCOLO,
    CANNED_PROTOCOLO_STATUS,
    # 7. LGPD (8)
    CANNED_LGPD_CONSENTIMENTO,
    CANNED_LGPD_ESQUECIMENTO,
    CANNED_LGPD_PORTABILIDADE,
    CANNED_LGPD_OPOSICAO,
    CANNED_LGPD_CORRECAO,
    CANNED_LGPD_ANONIMIZACAO,
    CANNED_LGPD_DPO,
    # 8. Pagamento (3)
    CANNED_PAGAMENTO_PIX,
    CANNED_PAGAMENTO_BOLETO,
    CANNED_PAGAMENTO_CONFIRMADO,
    # 9. Handoff / erro (4)
    CANNED_HANDOFF_HUMANO,
    CANNED_ERRO_SISTEMA,
    CANNED_TIMEOUT,
    CANNED_ENCERRAMENTO_INATIVIDADE,
    # 10. Avisos / urgencias (4)
    CANNED_URGENCIA,
    CANNED_PRAZO_VENCENDO,
    CANNED_FERIADO,
    CANNED_MANUTENCAO,
    # 11. Certidoes extras (5)
    CANNED_CERTIDAO_NASCIMENTO,
    CANNED_CERTIDAO_OBITO,
    CANNED_CERTIDAO_PROTESTO,
    CANNED_CERTIDAO_DISTRAT,
    CANNED_CERTIDAO_TEOR,
    # 12. Testamentos e procuracoes especiais (4)
    CANNED_TESTAMENTO,
    CANNED_PROCURACAO_JUDICIAL,
    CANNED_PROCURACAO_PREVIDENCIARIA,
    CANNED_SUBSTABELECIMENTO,
    # 13. Negocios juridicos diversos (4)
    CANNED_USUFRUTO,
    CANNED_HIPOTECA,
    CANNED_PENHOR,
    CANNED_CONVENCAO_CONDOMINIO,
)


def get_all_short_codes() -> tuple[str, ...]:
    """Retorna todos os short codes (para validacao)."""
    return tuple(cr.short_code for cr in CANNED_RESPONSES)


def get_by_tag(tag: str) -> tuple[CannedResponse, ...]:
    """Filtra templates por tag."""
    return tuple(cr for cr in CANNED_RESPONSES if tag in cr.tags)


def get_by_short_code(short_code: str) -> CannedResponse | None:
    """Busca template por short_code (case-insensitive)."""
    sc_lower = short_code.lower()
    for cr in CANNED_RESPONSES:
        if cr.short_code.lower() == sc_lower:
            return cr
    return None


# Total: 51 templates (superando o requisito de 50+)