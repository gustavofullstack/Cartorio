"""Macros de handoff humano Chatwoot (B14).

Macros sao acoes pre-configuradas no Chatwoot que o agente executa
com 1 clique. Cada macro combina:
- Identificacao do tipo de handoff (humano, supervisor, juridico, etc)
- Acoes automaticas (atribuir time, adicionar label, enviar mensagem)
- Resumo do contexto (template com dados da conversa)

Estrutura: lista de HandoffMacro (name + actions + summary_template).
Actions seguem a API do Chatwoot (assign_team, add_label, send_message, etc).

Uso:
    from app.services.chatwoot_handoff_macros import HANDOFF_MACROS
    for macro in HANDOFF_MACROS:
        chatwoot_api.execute_macro(conversation_id, macro.name)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MacroAction:
    """Acao atomica executada pela macro."""

    type: str  # assign_team, add_label, remove_label, send_message, set_priority, mute_conv
    payload: dict  # dados especificos da acao


@dataclass(frozen=True)
class HandoffMacro:
    """Macro completa do Chatwoot."""

    name: str  # identificador unico (slug)
    title: str  # titulo exibido no UI do Chatwoot
    description: str  # o que a macro faz
    actions: tuple[MacroAction, ...]  # acoes executadas em ordem
    summary_template: str  # template do resumo adicionado a conversa


# ============================================================================
# 1. HANDOFF HUMANO GENERICO
# ============================================================================

MACRO_HANDOFF_HUMANO = HandoffMacro(
    name="handoff_humano",
    title="Transferir para Humano",
    description="Transfere a conversa para um escrevente humano, atribuindo ao time de atendimento.",
    actions=(
        MacroAction(type="assign_team", payload={"team": "atendimento"}),
        MacroAction(type="add_label", payload={"label": "handoff-humano"}),
        MacroAction(type="set_priority", payload={"priority": "medium"}),
        MacroAction(
            type="send_message",
            payload={
                "message": (
                    "👤 Estou transferindo sua conversa para um de nossos escreventes. "
                    "Por favor, aguarde alguns instantes."
                ),
                "private": False,
            },
        ),
    ),
    summary_template=(
        "🤖 **Handoff solicitado pelo Agent AI**\n\n"
        "Motivo: cliente solicitou atendimento humano\n"
        "Conversa: #{{conversation.id}}\n"
        "Mensagens: {{conversation.message_count}}\n"
        "Cliente: {{customer.name}} ({{customer.phone}})\n\n"
        "Contexto: revisar ultimas mensagens para entender o caso."
    ),
)


# ============================================================================
# 2. HANDOFF JURIDICO (escrevente juridico)
# ============================================================================

MACRO_HANDOFF_JURIDICO = HandoffMacro(
    name="handoff_juridico",
    title="Escalação para Jurídico",
    description="Encaminha para o time juridico (escrevente especializado). Use quando ha duvida legal.",
    actions=(
        MacroAction(type="assign_team", payload={"team": "juridico"}),
        MacroAction(type="add_label", payload={"label": "duvida-juridica"}),
        MacroAction(type="add_label", payload={"label": "alta-prioridade"}),
        MacroAction(type="set_priority", payload={"priority": "high"}),
        MacroAction(
            type="send_message",
            payload={
                "message": (
                    "⚖️ Sua solicitacao envolve questoes juridicas. Vou transferir para nosso time juridico "
                    "especializado, que podera orienta-lo adequadamente. Aguarde."
                ),
                "private": False,
            },
        ),
    ),
    summary_template=(
        "⚖️ **Handoff para Juridico**\n\n"
        "Cliente: {{customer.name}}\n"
        "Caso: duvida juridica identificada pelo Agent AI\n"
        "Conversa: #{{conversation.id}}\n\n"
        "**Contexto:**\n"
        "{{agent.last_summary}}\n\n"
        "**Sugestoes:**\n"
        "- Revisar legislacao aplicavel (LGPD art. 18 / Provimento CNJ 74/2018)\n"
        "- Consultar tabela de emolumentos vigente"
    ),
)


# ============================================================================
# 3. HANDOFF SUPERVISOR (escalacao)
# ============================================================================

MACRO_HANDOFF_SUPERVISOR = HandoffMacro(
    name="handoff_supervisor",
    title="Escalar para Supervisor",
    description="Escala para o supervisor do cartorio. Use em casos de reclamacao ou solicitacao VIP.",
    actions=(
        MacroAction(type="assign_team", payload={"team": "supervisao"}),
        MacroAction(type="add_label", payload={"label": "escalado-supervisor"}),
        MacroAction(type="set_priority", payload={"priority": "high"}),
        MacroAction(
            type="send_message",
            payload={
                "message": (
                    "🔔 Sua solicitacao foi escalada para nosso supervisor. "
                    "Ele entrara em contato em breve para garantir o melhor atendimento."
                ),
                "private": False,
            },
        ),
    ),
    summary_template=(
        "🔔 **Escalacao para Supervisor**\n\n"
        "Cliente VIP ou reclamacao grave.\n"
        "Conversa: #{{conversation.id}}\n"
        "Cliente: {{customer.name}}\n\n"
        "**Acao necessaria:**\n"
        "Supervisor deve ligar em ate 1h util."
    ),
)


# ============================================================================
# 4. MACRO LGPD - DIREITO ESQUECIMENTO
# ============================================================================

MACRO_LGPD_ESQUECIMENTO = HandoffMacro(
    name="lgpd_esquecimento",
    title="LGPD: Direito ao Esquecimento",
    description="Aciona o fluxo de direito ao esquecimento (LGPD art. 18 VI). Requer analise juridica.",
    actions=(
        MacroAction(type="assign_team", payload={"team": "lgpd"}),
        MacroAction(type="add_label", payload={"label": "lgpd-esquecimento"}),
        MacroAction(type="add_label", payload={"label": "alta-prioridade"}),
        MacroAction(type="set_priority", payload={"priority": "high"}),
        MacroAction(
            type="send_message",
            payload={
                "message": (
                    "🔒 Sua solicitacao de direito ao esquecimento (LGPD art. 18 VI) foi registrada. "
                    "Nossa equipe juridica ira analisar e retornar em ate 15 dias uteis."
                ),
                "private": False,
            },
        ),
    ),
    summary_template=(
        "🔒 **LGPD art. 18 VI — Direito ao Esquecimento**\n\n"
        "Cliente: {{customer.name}} (CPF: {{customer.cpf}})\n"
        "Conversa: #{{conversation.id}}\n\n"
        "**Acoes necessarias:**\n"
        "1. Confirmar identidade do titular (documento com foto)\n"
        "2. Verificar se ha retencao legal (protocolos concluidos = 5 anos)\n"
        "3. Se aplicavel: anonimizar dados na tabela `clientes`\n"
        "4. Responder formalmente em ate 15 dias uteis\n\n"
        "**Lembrete:** dados de protocolos CONCLUIDOS devem ser mantidos por 5 anos (Provimento CNJ 74/2018)."
    ),
)


# ============================================================================
# 5. MACRO LGPD - PORTABILIDADE
# ============================================================================

MACRO_LGPD_PORTABILIDADE = HandoffMacro(
    name="lgpd_portabilidade",
    title="LGPD: Portabilidade de Dados",
    description="Gera pacote de portabilidade (LGPD art. 18 V). Disponibiliza download por 30 dias.",
    actions=(
        MacroAction(type="assign_team", payload={"team": "lgpd"}),
        MacroAction(type="add_label", payload={"label": "lgpd-portabilidade"}),
        MacroAction(
            type="send_message",
            payload={
                "message": (
                    "📥 Sua solicitacao de portabilidade (LGPD art. 18 V) foi registrada. "
                    "Em ate 5 dias uteis, enviaremos o link para download dos seus dados."
                ),
                "private": False,
            },
        ),
    ),
    summary_template=(
        "📥 **LGPD art. 18 V — Portabilidade**\n\n"
        "Cliente: {{customer.name}}\n"
        "Conversa: #{{conversation.id}}\n\n"
        "**Acoes necessarias:**\n"
        "1. Verificar identidade\n"
        "2. Gerar JSON com dados (cliente, protocolos, atendimentos)\n"
        "3. Upload para storage temporario (TTL 30 dias)\n"
        "4. Enviar link assinado por canal seguro"
    ),
)


# ============================================================================
# 6. MACRO LGPD - ANONIMIZACAO
# ============================================================================

MACRO_LGPD_ANONIMIZACAO = HandoffMacro(
    name="lgpd_anonimizacao",
    title="LGPD: Anonimização",
    description="Anonimiza dados do cliente (LGPD art. 18 IV). Acao IRREVERSIVEL.",
    actions=(
        MacroAction(type="assign_team", payload={"team": "lgpd"}),
        MacroAction(type="add_label", payload={"label": "lgpd-anonimizacao"}),
        MacroAction(type="add_label", payload={"label": "alta-prioridade"}),
        MacroAction(type="set_priority", payload={"priority": "high"}),
        MacroAction(
            type="send_message",
            payload={
                "message": (
                    "🎭 Sua solicitacao de anonimizacao (LGPD art. 18 IV) foi registrada. "
                    "ATENCAO: este processo eh IRREVERSIVEL. Nossa equipe confirmara a solicitacao "
                    "por telefone antes de prosseguir."
                ),
                "private": False,
            },
        ),
    ),
    summary_template=(
        "🎭 **LGPD art. 18 IV — Anonimizacao**\n\n"
        "⚠️ **ACAO IRREVERSIVEL** — requer confirmacao telefonica obrigatoria\n\n"
        "Cliente: {{customer.name}}\n"
        "Conversa: #{{conversation.id}}\n\n"
        "**Protocolo obrigatorio:**\n"
        "1. Ligar para {{customer.phone}} AGORA\n"
        "2. Confirmar ciencia da irreversibilidade\n"
        "3. Documentar confirmacao em audio/ata\n"
        "4. Executar anonimizacao em batch (tabela `clientes`)\n"
        "5. Responder formalmente em ate 15 dias"
    ),
)


# ============================================================================
# 7. MACRO IDENTIFICAR CLIENTE (recolher dados)
# ============================================================================

MACRO_IDENTIFICAR_CLIENTE = HandoffMacro(
    name="identificar_cliente",
    title="Identificar Cliente",
    description="Adiciona label e ajusta prioridade apos cliente ser identificado.",
    actions=(
        MacroAction(type="add_label", payload={"label": "cliente-identificado"}),
        MacroAction(type="remove_label", payload={"label": "nao-identificado"}),
        MacroAction(type="set_priority", payload={"priority": "medium"}),
    ),
    summary_template=(
        "✅ **Cliente Identificado**\n\n"
        "Cliente: {{customer.name}}\n"
        "CPF: {{customer.cpf_hash}} (LGPD-safe)\n"
        "Telefone: {{customer.phone_hash}} (LGPD-safe)\n"
        "Email: {{customer.email}}"
    ),
)


# ============================================================================
# 8. MACRO TRANSFERIR (sem mudar time)
# ============================================================================

MACRO_TRANSFERIR = HandoffMacro(
    name="transferir",
    title="Transferir (sem mudança de time)",
    description="Apenas marca a conversa como transferida e adiciona label, sem mudar atribuicao.",
    actions=(MacroAction(type="add_label", payload={"label": "transferido"}),),
    summary_template=(
        "🔁 **Conversa Transferida**\n\n"
        "Conversa: #{{conversation.id}}\n"
        "Transferido por: {{agent.name}}\n"
        "Para: {{custom.target_agent}}"
    ),
)


# ============================================================================
# 9. MACRO RESUMIR (snapshot do contexto)
# ============================================================================

MACRO_RESUMIR = HandoffMacro(
    name="resumir",
    title="Resumir Contexto",
    description="Adiciona nota interna com resumo estruturado da conversa ate o momento.",
    actions=(MacroAction(type="add_label", payload={"label": "resumido"}),),
    summary_template=(
        "📝 **Resumo da Conversa**\n\n"
        "Conversa: #{{conversation.id}}\n"
        "Cliente: {{customer.name}}\n"
        "Mensagens trocadas: {{conversation.message_count}}\n"
        "Inicio: {{conversation.created_at}}\n"
        "Ultima atualizacao: {{conversation.updated_at}}\n\n"
        "**Resumo executivo:**\n"
        "{{agent.last_summary}}\n\n"
        "**Estado atual:**\n"
        "- Protocolos em andamento: {{custom.protocolos_count}}\n"
        "- Documentos pendentes: {{custom.documentos_pendentes}}"
    ),
)


# ============================================================================
# 10. MACRO ENCERRAR (finalizar atendimento)
# ============================================================================

MACRO_ENCERRAR = HandoffMacro(
    name="encerrar",
    title="Encerrar Atendimento",
    description="Encerra a conversa: marca como resolvida, adiciona label de fechamento, ajusta prioridade.",
    actions=(
        MacroAction(type="add_label", payload={"label": "encerrado-resolvido"}),
        MacroAction(type="set_priority", payload={"priority": "low"}),
        MacroAction(
            type="send_message",
            payload={
                "message": (
                    "✅ Atendimento encerrado com sucesso! Se precisar de algo mais, "
                    "é só me chamar. Cartório 2º Notas de Uberlândia — obrigado!"
                ),
                "private": False,
            },
        ),
    ),
    summary_template=(
        "✅ **Atendimento Encerrado**\n\n"
        "Conversa: #{{conversation.id}}\n"
        "Encerrado por: {{agent.name}}\n"
        "Resolvido em: {{conversation.updated_at}}\n"
        "Duracao total: {{conversation.duration}}\n\n"
        "**Resumo final:**\n"
        "{{agent.last_summary}}"
    ),
)


# ============================================================================
# CATALOGO COMPLETO (10 macros)
# ============================================================================

HANDOFF_MACROS: tuple[HandoffMacro, ...] = (
    MACRO_HANDOFF_HUMANO,
    MACRO_HANDOFF_JURIDICO,
    MACRO_HANDOFF_SUPERVISOR,
    MACRO_LGPD_ESQUECIMENTO,
    MACRO_LGPD_PORTABILIDADE,
    MACRO_LGPD_ANONIMIZACAO,
    MACRO_IDENTIFICAR_CLIENTE,
    MACRO_TRANSFERIR,
    MACRO_RESUMIR,
    MACRO_ENCERRAR,
)


def get_macro_by_name(name: str) -> HandoffMacro | None:
    """Busca macro por nome (case-insensitive)."""
    name_lower = name.lower()
    for macro in HANDOFF_MACROS:
        if macro.name.lower() == name_lower:
            return macro
    return None


def get_macros_by_action(action_type: str) -> tuple[HandoffMacro, ...]:
    """Filtra macros que executam determinada acao."""
    return tuple(m for m in HANDOFF_MACROS if any(a.type == action_type for a in m.actions))
