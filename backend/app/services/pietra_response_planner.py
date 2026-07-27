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
                f"**{cap.display_name}:** inda temos indisponibilidade momentanea "
                f"nesse servico. Posso te explicar como funciona enquanto a equipe "
                f"normaliza o sistema?"
            )
        if cap.requires_tool and not cap.tool_available:
            return (
                f"**{cap.display_name}:** essa funcionalidade ainda nao esta "
                f"disponivel pelo canal. Posso te passar mais informacoes e, se "
                f"quiser, ja anotar seu pedido para um escrevente te atender."
            )
        # BLOQUEADO
        return (
            f"**{cap.display_name}:** nao consigo executar por aqui. Posso "
            f"explicar como funciona e, se preferir, encaminho para um escrevente."
        )

    # CAN_EXECUTE == True
    if cap.requires_human_review:
        return (
            f"**{cap.display_name}:** consigo abrir o pre-pedido agora; a "
            f"confirmacao final sempre fica com um escrevente."
        )
    return f"**{cap.display_name}:** consigo te ajudar agora."


def _catalog_overview() -> str:
    """Visao geral curta (1 linha por topico)."""
    lines = ["Aqui o que consigo fazer no canal:"]
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
    parts: list[str] = []
    for topic in PIETRA_TOPICS:
        parts.append(_topic_summary_text(topic))
    return "\n\n".join(parts)


def _catalog_full() -> str:
    """Catalogo completo, sem pedir autorizacao a cada topico."""
    parts: list[str] = []
    for topic in PIETRA_TOPICS:
        parts.append(_topic_summary_text(topic))
    parts.append(
        "\nEm qual desses eu te ajudo agora? (pode escrever em texto livre, "
        "que eu entendo)"
    )
    return "\n\n".join(parts)


def _continuation_text(state: ConversationState) -> str:
    """Continuacao de onde parou (Fase 4 do P0 - intent=CONTINUE)."""
    if not state.active_topic:
        return (
            "Vamos comecar do que voce precisa. Me conta, por exemplo: quer saber "
            "sobre emolumentos, consultar um protocolo, agendar atendimento ou "
            "outra coisa?"
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
        self, text: str, state: ConversationState,
    ) -> str:
        """Resposta a uma pergunta especifica, dispatch por topico."""
        t = (text or "").lower()
        # Emolumentos
        if any(w in t for w in (
            "quanto custa", "valor", "preco", "preço", "emolumento",
            "custa", "tabela", "reais", "r$",
        )):
            cap = get_capability("emoluments")
            if cap is None:
                return "Emolumento e com a equipe no balcao. Quer anotar seu pedido?"
            if not can_say_i_can_do_it("emoluments"):
                return (
                    f"{cap.display_name}: a ferramenta de calculo nao esta "
                    f"respondeu agora. Posso anotar seu pedido para um escrevente "
                    f"confirmar o valor exato."
                )
            return (
                f"{cap.display_name}: me diga o tipo de ato e quantas folhas. "
                f"Calculo o valor oficial da Tabela MG 2026 na hora."
            )
        # Protocolo
        if any(w in t for w in ("protocolo", "andamento", "status")):
            cap = get_capability("protocol_status")
            if cap and can_say_i_can_do_it("protocol_status"):
                return "Me passa o numero do protocolo (formato 2026-00001) que eu consulto."
            return "Consulta de protocolo indisponivel agora. Posso anotar seu pedido."
        # Endereco / horario
        if any(w in t for w in ("endereco", "endereço", "onde fica", "localizacao")):
            return _topic_summary_text("institutional_info")
        if any(w in t for w in ("horario", "funcionamento", "abre", "fecha")):
            return _topic_summary_text("institutional_info")
        # Humano
        if any(w in t for w in ("humano", "escrevente", "atendente", "pessoa real")):
            cap = get_capability("human_handoff")
            if cap is None or not can_say_i_can_do_it("human_handoff"):
                return (
                    "O encaminhamento para um escrevente nao esta disponivel "
                    "neste momento pelo canal. Posso te passar o telefone da "
                    "serventia: (34) 3216-0252."
                )
            return "Vou te passar para um escrevente. Aguarde um instante."
        # Agendar
        if any(w in t for w in ("agendar", "marcar", "horario disponivel")):
            cap = get_capability("appointment")
            if cap and can_say_i_can_do_it("appointment"):
                return (
                    "Me diga o dia e o motivo do atendimento que eu abro um "
                    "pre-agendamento. A confirmacao vem de um escrevente."
                )
            return "Pre-agendamento indisponivel agora. Quer ligar? (34) 3216-0252."
        # Default: orientacao curta
        return _catalog_overview()

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
            return (
                "Ja passei por cima dos topicos principais. "
                "Em qual eu aprofundo?"
            )
        return response

    def _safe_fallback(self, state: ConversationState, blocked_phrase: str) -> str:
        """Quando a resposta viola forbidden phrases, gera substituta limpa."""
        return (
            "Estou com uma instabilidade momentanea. Posso te passar informacoes "
            "institucionais e te ajudar com emolumentos pelo telefone (34) 3216-0252."
        )

    def _operational_truth_filter(self, response: str) -> str:
        """Remove verbos proibidos (can_say_i_can_do_it == False).

        Padrao: se a resposta contiver um verbo de acao PROMESSA
        (gero/faco/transfiro/seu documento esta pronto) sem que a capability
        esteja executavel, neutraliza a frase.

        NAO bloqueia "posso explicar", "posso te ajudar" (verbos seguros).
        """
        # Phrases PROMESSA de execucao (nao explicacao)
        promise_phrases = (
            "gero o link", "gero link", "vou gerar",
            "faco seu agendamento", "vou agendar", "ja agendei",
            "transfiro agora", "transfiro direto", "vou transferir",
            "consultei seu protocolo", "vou consultar", "ja consultei",
            "envio pelo whatsapp", "vou enviar", "ja enviei",
            "seu documento esta pronto", "seu documento está pronto",
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
