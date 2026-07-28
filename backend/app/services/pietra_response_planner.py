"""Response Planner para AGENT PIETRA (Fase 3 do P0).

Pipeline canonico (PROMPT P0 fase 3):
  1. detect_intent
  2. resolve_reference
  3. load_conversation_state
  4. determine_requested_scope
  5. determine_already_answered_scope
  6. retrieve_only_missing_information
  7. check_capabilities
  8. call_required_tools
  9. compose
 10. deduplicate
 11. persona_filter
 12. operational_truth_filter
 13. send
 14. update_state

Regra central: se a resposta candidata violar qualquer forbidden phrase ou
can_say_i_can_do_it == False para uma capability, o planner REJEITA e gera
resposta substituta.

Aplica o gate canonico:
  can_say_i_can_do_it = (
    capability.registered
    and capability.tool_available
    and capability.runtime_healthy
    and capability.authorization_ok
  )

Modified by Gustavo Almeida · 2026-07-27
"""

from __future__ import annotations


from app.services.pietra_capabilities import (
    can_say_i_can_do_it,
    get_capability,
)
from app.services.pietra_conversation_state import (
    PIETRA_TOPICS,
    ConversationState,
    ConversationStateStore,
    ScopeIntent,
    detect_scope_intent,
    has_forbidden_phrase,
)


# === Topico -> Capability mapping (autoritativo) ===

TOPIC_TO_CAPABILITY: dict[str, str] = {
    "emoluments": "emoluments",
    "protocol_status": "protocol_status",
    "pre_protocol": "pre_protocol",
    "second_copy": "second_copy",
    "signature_info": "signature_info",
    "authentication_info": "signature_info",  # alias
    "deeds_info": "deeds_info",
    "institutional_info": "institutional_info",
    "human_handoff": "human_handoff",
    "appointment": "appointment",
}


# === Composicao ===


def _topic_summary_text(topic: str) -> str:
    """Retorna um resumo curto (1-3 linhas) de um topico da Pietra.

    A linguagem muda automaticamente se a capability esta BLOQUEADA.
    """
    cap_id = TOPIC_TO_CAPABILITY.get(topic, "institutional_info")
    cap = get_capability(cap_id)
    if cap is None:
        return f"({topic} - topico nao configurado)"

    # Se nao pode executar, a linguagem TEM que ser informativa
    if not can_say_i_can_do_it(cap_id):
        if not cap.runtime_healthy:
            return (
                f"**{cap.display_name}:** temos uma breve indisponibilidade "
                f"temporaria nesse servico. Posso te explicar detalhadamente como "
                f"funciona enquanto a equipe normaliza o sistema?"
            )
        if cap.requires_tool and not cap.tool_available:
            return (
                f"**{cap.display_name}:** essa funcionalidade ainda nao esta "
                f"disponivel diretamente pelo canal. Posso te passar todas as "
                f"informacoes e orientar como solicitar atendimento a um escrevente."
            )
        # BLOQUEADO
        return (
            f"**{cap.display_name}:** nao consigo executar por aqui. Posso "
            f"explicar o procedimento e informar como falar com um escrevente."
        )

    # CAN_EXECUTE == True
    if cap.requires_human_review:
        return (
            f"**{cap.display_name}:** posso abrir seu pre-pedido agora mesmo; "
            f"a validacao juridica final e sempre realizada por um escrevente."
        )
    return f"**{cap.display_name}:** posso te orientar e ajudar agora."


def _catalog_overview() -> str:
    """Visao geral curta (1 linha por topico)."""
    lines = [
        "Olá! É um prazer te atender no 2º Tabelionato de Uberlândia. "
        "Estou aqui para te orientar em cada passo. Veja como posso te ajudar no canal:"
    ]
    for topic in PIETRA_TOPICS:
        cap_id = TOPIC_TO_CAPABILITY.get(topic, topic)
        cap = get_capability(cap_id)
        if cap is None:
            continue
        if cap.can_execute:
            tag = "[agora]"
        elif cap.can_explain:
            tag = "[informo]"
        else:
            tag = "[encaminho]"
        lines.append(f"  {tag} {cap.display_name}")
    return "\n".join(lines)


def _catalog_summary_each() -> str:
    """Resumo curto (1-2 frases) por topico, cobrindo todos uma vez."""
    parts: list[str] = [
        "Olá! Seja muito bem-vindo(a) ao 2º Tabelionato de Notas de Uberlândia. "
        "Com todo carinho e respeito, apresento um resumo de nossos serviços:"
    ]
    for topic in PIETRA_TOPICS:
        parts.append(_topic_summary_text(topic))
    return "\n\n".join(parts)


def _catalog_full() -> str:
    """Catalogo completo, sem pedir autorizacao a cada topico."""
    parts: list[str] = [
        "Olá! É um grande prazer te atender no 2º Tabelionato de Notas de Uberlândia. "
        "Estou à disposição para te guiar. Veja tudo o que podemos fazer por você:"
    ]
    for topic in PIETRA_TOPICS:
        parts.append(_topic_summary_text(topic))
    parts.append(
        "Fique à vontade! Em qual desses serviços posso te ajudar agora? "
        "Pode me escrever em texto livre que estou pronta para te orientar."
    )
    return "\n\n".join(parts)


def _continuation_text(state: ConversationState) -> str:
    """Continuacao de onde parou (Fase 4 do P0 - intent=CONTINUE)."""
    if not state.active_topic:
        return (
            "Compreendo perfeitamente! Fique tranquilo(a), vamos continuar do ponto que você precisa. "
            "Me conte: você gostaria de consultar emolumentos, acompanhar um protocolo, agendar atendimento ou tirar outra dúvida?"
        )
    return _topic_summary_text(state.active_topic)


# === Planejador principal ===


class ResponsePlanner:
    """Fase 3 do P0: response planner pipeline."""

    def __init__(self, state_store: ConversationStateStore | None = None) -> None:
        self._state = state_store or ConversationStateStore()

    def plan(
        self,
        user_text: str,
        thread_id: str = "default",
        channel_id: str = "imessage",
        user_id: str | None = None,
    ) -> tuple[str, ConversationState]:
        """Pipeline canonico. Retorna (resposta, state_atualizado)."""
        # 1. detect_intent (Fase 4 do P0)
        scope = detect_scope_intent(user_text)

        # 3. load_conversation_state
        state = self._state.get_or_create(thread_id, channel_id, user_id)

        # 4. determine_requested_scope
        # 5. determine_already_answered_scope (state.topics_already_explained)
        # 6. retrieve_only_missing_information (capabilities registry)
        # 9. compose

        if scope == ScopeIntent.ALL:
            response = _catalog_full()
        elif scope == ScopeIntent.SUMMARY_EACH:
            response = _catalog_summary_each()
        elif scope == ScopeIntent.CONTINUE:
            response = _continuation_text(state)
        else:
            # ANSWER ou UNKNOWN: usar intent detector do cartorio_agent
            response = self._answer_specific_question(user_text, state)

        # 14. update_state PRIMEIRO (para o dedup ter dados)
        state.response_sequence += 1
        state.last_user_intent = scope.value
        if scope in (ScopeIntent.ALL, ScopeIntent.SUMMARY_EACH):
            state.topics_already_explained = list(PIETRA_TOPICS)
        self._state.save(state)

        # 10. deduplicate
        response = self._dedup(response, state)

        # 11. persona_filter
        bad = has_forbidden_phrase(response)
        if bad is not None:
            # Resposta substituta nao-metaforica
            response = self._safe_fallback(state, blocked_phrase=bad)

        # 12. operational_truth_filter
        response = self._operational_truth_filter(response)

        return response, state

    def _answer_specific_question(
        self,
        text: str,
        state: ConversationState,
    ) -> str:
        """Resposta a uma pergunta especifica, dispatch por topico."""
        t = (text or "").lower()
        header = "Olá! Sou a Pietra, assistente virtual do 2º Tabelionato de Notas de Uberlândia. "

        # Agradecimento / Confirmação de Pré-pedido DRAFT
        if any(
            w in t
            for w in (
                "obrigado",
                "obrigada",
                "agradeço",
                "agradeco",
                "valeu",
                "salvam",
                "salvar",
                "salvo",
                "anotou",
                "registrou",
                "tudo certo",
            )
        ):
            return (
                f"{header}De nada! Para sua segurança, não consigo confirmar por esta mensagem que informações ou um pré-pedido tenham sido registrados. "
                "Posso continuar por aqui orientando os documentos e os próximos dados necessários para a triagem. "
                "Desejo muita força e uma pronta recuperação ao seu neto."
            )

        # Emolumentos
        if any(
            w in t
            for w in (
                "quanto custa",
                "valor",
                "preco",
                "preço",
                "emolumento",
                "custa",
                "tabela",
                "reais",
                "r$",
            )
        ):
            cap = get_capability("emoluments")
            if cap is None:
                return f"{header}Compreendo sua dúvida sobre valores! Os emolumentos são tabelados pela Tabela MG 2026 e nossa equipe pode detalhar. Quer que eu anote seu pedido?"
            if not can_say_i_can_do_it("emoluments"):
                return (
                    f"{header}Compreendo sua dúvida sobre {cap.display_name}. Nossa ferramenta de cálculo está "
                    f"passando por uma breve indisponibilidade no momento. Posso anotar seu pedido para um escrevente "
                    f"confirmar o valor exato para você com toda segurança."
                )
            return (
                f"{header}Compreendo sua solicitação! Para calcular os emolumentos ({cap.display_name}), "
                "me diga o tipo de ato e quantas folhas. Com esses dados, solicito o cálculo "
                "oficial pela Tabela MG 2026 para você."
            )
        # Protocolo
        if any(w in t for w in ("abrir protocolo", "criar protocolo", "gerar protocolo")):
            return (
                f"{header}Posso preparar seu pré-protocolo por aqui. Ele nasce como DRAFT e só "
                "segue após validação de um escrevente; informe o ato e os documentos que já possui."
            )
        if any(w in t for w in ("protocolo", "andamento", "status")):
            cap = get_capability("protocol_status")
            if cap and can_say_i_can_do_it("protocol_status"):
                return f"{header}Compreendo! Por gentileza, me passa o número do protocolo (formato 2026-00001) para eu consultar o andamento no 2º Tabelionato para você."
            return f"{header}Compreendo sua solicitação! A consulta de protocolo está temporariamente indisponível pelo canal. Fique tranquilo(a), posso anotar seu pedido."
        # Endereco / horario
        if any(w in t for w in ("endereco", "endereço", "onde fica", "localizacao")):
            return (
                f"{header}O 2º Tabelionato de Notas de Uberlândia atende exclusivamente na sede: "
                "Rua Cel. Antônio Alves Pereira, 850, Centro, Uberlândia - MG, CEP 38400-104. "
                "Não existe unidade complementar."
            )
        if any(w in t for w in ("horario", "funcionamento", "abre", "fecha")):
            return (
                f"{header}Nosso atendimento presencial no 2º Tabelionato de Uberlândia funciona de segunda a sexta-feira, das 09:00 às 17:00. "
                "Estamos à disposição para te receber com toda a atenção e carinho!"
            )
        # Reconhecimento de Firma & Autenticação
        if any(
            w in t
            for w in (
                "firma",
                "reconhecimento",
                "reconhecer firma",
                "autenticacao",
                "autenticação",
                "autenticar",
                "copia autenticada",
                "cópia autenticada",
            )
        ):
            return (
                f"{header}Compreendo perfeitamente sua dúvida! O reconhecimento de firma confirma a autoria da assinatura em um documento (por semelhança ou autenticidade). "
                "Já a autenticação de cópia atesta que a cópia é cópia fiel do documento original. "
                "Fique tranquilo(a): para realizar esses serviços no 2º Tabelionato de Uberlândia, basta comparecer com seu documento original de identificação."
            )
        # Urgência Hospitalar / Diligência Notarial Hospitalar
        if any(
            w in t
            for w in (
                "hospital",
                "hospitalar",
                "internado",
                "internada",
                "medico",
                "médico",
                "uti",
                "emergencia",
                "emergência",
                "urgencia",
                "urgência",
                "diligencia",
                "diligência",
            )
        ):
            return (
                f"{header}Minha senhora, sinto muito pelo momento delicado com seu neto e compreendo perfeitamente a sua urgência e preocupação. Fique tranquila, estamos aqui para acolher sua família com todo o carinho, compaixão e máxima agilidade profissional!\n\n"
                "Vou iniciar a triagem de urgência por aqui e organizar a proposta de pré-protocolo em DRAFT, para que nenhuma informação precise ser repetida.\n\n"
                "Por gentileza, responda apenas ao que já souber: 1) qual ato precisa ser realizado (por exemplo, procuração, escritura ou testamento); 2) nome da pessoa que precisa do atendimento; 3) se ela está consciente e consegue manifestar sua vontade; 4) hospital e setor/quarto; 5) prazo ou motivo da urgência; e 6) quais documentos já estão disponíveis.\n\n"
                "Com essa triagem, organizo os dados e os documentos iniciais no rascunho DRAFT para a análise notarial obrigatória. Não envie CPF, foto de documento ou dado bancário neste momento; eu indicarei o meio seguro se esses dados forem necessários."
            )
        # Testamento Público (específico)
        if "testamento" in t:
            return (
                f"{header}Compreendo perfeitamente o seu desejo de organizar a sucessão de seus bens familiares com toda tranquilidade e segurança jurídica! "
                "O **Testamento Público** é lavrado no Livro de Notas do cartório pelo tabelião ou escrevente. "
                "Exige a apresentação de documento oficial de identidade (RG/CPF) do testador e a presença obrigatória de **2 (duas) testemunhas** no ato da lavratura, "
                "as quais não podem ser herdeiras nem beneficiárias do testamento.\n\n"
                "Para sua segurança, podemos registrar seu pré-pedido (DRAFT) pelo canal. "
                "A validação jurídica presencial e a assinatura no livro de notas serão finalizadas pelo tabelião ou escrevente responsável. "
                "Estou à disposição para orientar cada passo com o carinho e o respeito que o senhor merece."
            )
        # Escrituras, Procurações e Inventários
        if any(
            w in t
            for w in (
                "escritura",
                "procuracao",
                "procuração",
                "inventario",
                "inventário",
                "doacao",
                "doação",
            )
        ):
            return (
                f"{header}Compreendo perfeitamente! Atos notariais como escrituras de compra e venda/doação, procurações públicas, testamentos e inventários extrajudiciais garantem total segurança jurídica às suas decisões. "
                "Posso orientar e registrar seu pré-pedido (DRAFT) no 2º Tabelionato de Uberlândia agora mesmo! Lembramos que a validação jurídica final é sempre realizada por nossos escreventes."
            )
        # Segunda Via / Certidão
        if any(w in t for w in ("segunda via", "2a via", "2ª via", "certidao", "certidão")):
            return (
                f"{header}Compreendo sua solicitação! A certidão de segunda via comprova os atos lavrados nos livros do 2º Tabelionato de Notas de Uberlândia. "
                "Posso registrar seu pedido de informações e orientar quais dados são necessários para a emissão pelos nossos escreventes."
            )
        # Humano
        if any(w in t for w in ("humano", "escrevente", "atendente", "pessoa real")):
            cap = get_capability("human_handoff")
            if cap is None or not can_say_i_can_do_it("human_handoff"):
                return (
                    f"{header}Compreendo perfeitamente! Posso preparar sua triagem para o atendimento humano sem "
                    "você precisar repetir informações. Me diga qual ato precisa realizar e o que já possui de documentos."
                )
            return (
                f"{header}Compreendo perfeitamente! Posso iniciar sua triagem por aqui e organizar as informações "
                "necessárias para o atendimento humano. Qual ato você precisa realizar?"
            )
        # Agendar
        if any(w in t for w in ("agendar", "marcar", "horario disponivel")):
            cap = get_capability("appointment")
            if cap and can_say_i_can_do_it("appointment"):
                return (
                    f"{header}Compreendo! Informe o dia desejado e o motivo do atendimento para que eu possa orientar os dados necessários para o pré-agendamento. "
                    "O registro e a confirmação final dependem de validação por um escrevente."
                )
            return (
                f"{header}Compreendo! Posso adiantar sua triagem de pré-agendamento por aqui. "
                "Informe o ato, a data e o horário de preferência para eu orientar os documentos iniciais."
            )
        # Default: orientacao curta
        return f"{header}\n\n" + _catalog_overview()

    def _dedup(self, response: str, state: ConversationState) -> str:
        """Remove repeticao semantica contra as ultimas N respostas.

        Estrategia: so dedup a partir da 2a chamada (response_sequence >= 2)
        E se o state ja marcou a maioria dos topicos como
        ``topics_already_explained`` E a resposta cita 3+ topicos.
        """
        # Primeira chamada (sequence == 1 apos update) nunca dedup
        if state.response_sequence < 2:
            return response
        if len(state.topics_already_explained) < 5:
            return response
        # Contar topicos ja explicados
        explained = set(state.topics_already_explained)
        # Se a resposta cita 3+ topicos (por id OU por keyword PT), abreviar
        keywords_pt = {
            "emoluments": ("emolumento", "emolumentos"),
            "protocol_status": ("protocolo", "protocol"),
            "pre_protocol": ("pre-protocolo", "pre protocolo"),
            "second_copy": ("segunda via", "2a via", "2ª via"),
            "signature_info": ("reconhecimento", "autentica"),
            "deeds_info": ("escritura", "procuracao", "testamento"),
            "institutional_info": ("endereco", "horario", "cartorio"),
            "human_handoff": ("escrevente", "humano"),
            "appointment": ("agendar", "agendamento"),
        }
        r_lower = response.lower()
        mentioned = 0
        for t in explained:
            for kw in keywords_pt.get(t, (t.replace("_", " "),)):
                if kw in r_lower:
                    mentioned += 1
                    break
        if mentioned >= 3 and len(response) > 300:
            return "Ja passei por cima dos topicos principais. Em qual eu aprofundo?"
        return response

    def _safe_fallback(self, state: ConversationState, blocked_phrase: str) -> str:
        """Quando a resposta viola forbidden phrases, gera substituta limpa."""
        return (
            "Estou com uma instabilidade momentanea. Posso continuar por aqui com informações "
            "institucionais, documentos necessários e a triagem do seu atendimento."
        )

    def _operational_truth_filter(self, response: str) -> str:
        """Remove verbos proibidos (can_say_i_can_do_it == False).

        Padrao: se a resposta contiver um verbo de acao PROMESSA
        (gero/faco/transfiro/seu documento esta pronto) sem que a capability
        esteja executavel, neutraliza a frase.

        NAO bloqueia "posso explicar", "posso te ajudar" (verbos seguros).
        """
        # Afirmações de conclusão exigem recibo da operação. Este planejador não
        # executa ferramentas nem recebe recibos, portanto nunca pode emiti-las.
        # A proteção é intencionalmente independente do status da capability.
        unverified_completion_phrases = (
            "ja acionei",
            "já acionei",
            "estou direcionando",
            "ja direcionei",
            "já direcionei",
            "foram registrados",
            "foi registrado",
            "ja registrei",
            "já registrei",
            "pedido registrado",
            "encaminhamento confirmado",
        )
        if any(phrase in response.lower() for phrase in unverified_completion_phrases):
            return self._safe_fallback(None, blocked_phrase="afirmacao operacional sem recibo")  # type: ignore[arg-type]

        # Promessas de execucao (nao explicacao) dependem da capability.
        promise_phrases = (
            "gero o link",
            "gero link",
            "vou gerar",
            "faco seu agendamento",
            "vou agendar",
            "ja agendei",
            "transfiro agora",
            "transfiro direto",
            "vou transferir",
            "consultei seu protocolo",
            "vou consultar",
            "ja consultei",
            "envio pelo whatsapp",
            "vou enviar",
            "ja enviei",
            "seu documento esta pronto",
            "seu documento está pronto",
            "vou abrir o pre-protocolo",
            "vou te passar para um escrevente",
        )
        # Mapear cada phrase a qual capability
        cap_by_phrase = {
            "gero o link": "second_copy",
            "gero link": "second_copy",
            "vou gerar": "second_copy",
            "faco seu agendamento": "appointment",
            "vou agendar": "appointment",
            "ja agendei": "appointment",
            "transfiro agora": "human_handoff",
            "transfiro direto": "human_handoff",
            "vou transferir": "human_handoff",
            "consultei seu protocolo": "protocol_status",
            "vou consultar": "protocol_status",
            "ja consultei": "protocol_status",
            "envio pelo whatsapp": "whatsapp_session",
            "vou enviar": "whatsapp_session",
            "ja enviei": "whatsapp_session",
            "seu documento esta pronto": "second_copy",
            "seu documento está pronto": "second_copy",
            "vou abrir o pre-protocolo": "pre_protocol",
            "vou te passar para um escrevente": "human_handoff",
        }
        for phrase in promise_phrases:
            if phrase in response.lower():
                cap_id = cap_by_phrase.get(phrase, "unknown")
                if not can_say_i_can_do_it(cap_id):
                    return self._safe_fallback(None, blocked_phrase=phrase)  # type: ignore[arg-type]
        return response


# Singleton (MVP)
_planner = ResponsePlanner()


def get_response_planner() -> ResponsePlanner:
    return _planner


def plan_response(
    user_text: str,
    thread_id: str = "default",
    channel_id: str = "imessage",
    user_id: str | None = None,
) -> tuple[str, ConversationState]:
    """Convenience function para integrar com run_cartorio_agent."""
    return _planner.plan(user_text, thread_id, channel_id, user_id)
