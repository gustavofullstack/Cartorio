"""Suite de regressao baseada nos screenshots reais do cliente (Fase 10 do P0).

REG-001 a REG-007 + 7 casos extras. Cada caso e um customer-facing failure
documentado e deve ser prevenido pelos modulos:
  - app.services.pietra_conversation_state
  - app.services.pietra_capabilities
  - app.services.pietra_response_planner
"""

from __future__ import annotations

import pytest

from app.services.pietra_capabilities import (
    all_capabilities,
    can_say_i_can_do_it,
    forbidden_action_verbs,
    get_capability,
)
from app.services.pietra_conversation_state import (
    ConversationState,
    ConversationStateStore,
    ScopeIntent,
    detect_scope_intent,
    has_forbidden_phrase,
    sanitize_response,
)
from app.services.pietra_response_planner import (
    plan_response,
)


# ============================================================
# REG-001 a REG-007: casos dos screenshots
# ============================================================

def test_reg_001_me_fale_tudo_nao_pede_autorizacao() -> None:
    """Screenshot: 'me fale tudo que pode fazer? tudo mesmo separado em varias mensagens'.

    Assert: planner retorna catalogo completo sem 'Quer continuar?' / 'Sigo?'.
    """
    response, state = plan_response(
        "me fale tudo que pode fazer? tudo mesmo separado em varias mensagens",
        thread_id="reg-001",
    )
    assert response, "planner retornou resposta vazia"
    # Nao pode pedir autorizacao
    for forbidden in ("quer que eu continue", "quer que eu siga", "sigo com o proximo", "quer continuar"):
        assert forbidden not in response.lower(), f"planner pediu autorizacao: '{forbidden}'"
    # Deve cobrir os topicos principais (verificar pelas display_names)
    caps = all_capabilities()
    covered = sum(1 for c in caps if c.display_name.lower() in response.lower())
    assert covered >= 5, f"planner cobriu apenas {covered}/{len(caps)} capabilities"


def test_reg_002_nao_repetir_conteudo_ja_enviado() -> None:
    """Screenshot: 'ja me envia tudo de uma vez separado por gentileza' (depois de REG-001).

    Assert: segunda chamada (mesmo thread_id) nao repete Emoluments/Protocol/etc.
    """
    plan_response("me fale tudo", thread_id="reg-002")
    response, _ = plan_response(
        "ja me envia tudo de uma vez separado por gentileza",
        thread_id="reg-002",
    )
    # Apos 2 chamadas, planner deve detectar ja explicado e abreviar
    assert response, "resposta vazia"
    # Nao pode repetir o catalogo inteiro novamente
    full_keywords = ["emolumentos", "protocolo", "pre-protocolo", "segunda via"]
    repeated = sum(1 for k in full_keywords if k in response.lower())
    assert repeated < 4, f"planner repetiu catalogo inteiro ({repeated}/4 keywords)"


def test_reg_003_recuperar_active_topic_e_continuar() -> None:
    """Screenshot: 'uai mais estavamos falando sobre isso'.

    Assert: detect_scope_intent retorna CONTINUE, planner continua de active_topic.
    """
    intent = detect_scope_intent("uai mais estavamos falando sobre isso")
    assert intent == ScopeIntent.CONTINUE, f"intent errado: {intent}"
    # Setup: topic ativo = emoluments
    state = ConversationState(
        thread_id="reg-003",
        channel_id="imessage",
        user_id_hash="anon",
        active_topic="emoluments",
    )
    ConversationStateStore().save(state)
    response, _ = plan_response(
        "uai mais estavamos falando sobre isso",
        thread_id="reg-003",
    )
    assert "emolument" in response.lower(), "planner nao continuou do active_topic"
    # NUNCA pode dizer 'minha memoria nao e grande'
    assert "minha memoria nao e grande" not in response.lower()
    assert "minha memória não é grande" not in response.lower()


def test_reg_004_resumo_curto_sem_reiniciar() -> None:
    """Screenshot: 'me fale um pouco de cada' (depois de catalogo).

    Assert: SUMMARY_EACH produz 1 sintese curta por topico.
    """
    intent = detect_scope_intent("me fale um pouco de cada")
    assert intent == ScopeIntent.SUMMARY_EACH
    response, _ = plan_response("me fale um pouco de cada", thread_id="reg-004")
    # Nao deve ter 'certidao - calculo ...' (recomeco do catalogo)
    assert "calculo os valores oficiais" not in response.lower(), "planner reiniciou catalogo"


def test_reg_005_oi_nunca_dizer_testes_confirmados() -> None:
    """Screenshot: 'Oiee! Tudo bem? ... Testes confirmados -- o canal ta respondendo bem'.

    Assert: sanitize_response bloqueia a frase.
    """
    bad = "Oiee! Tudo bem? Testes confirmados -- o canal ta respondendo bem. Como posso ajudar?"
    bad_phrase = has_forbidden_phrase(bad)
    assert bad_phrase is not None, "frase proibida nao foi detectada"
    assert "testes confirmados" in bad_phrase


def test_reg_006_quem_e_voce_nunca_dizer_hermes() -> None:
    """Screenshot: 'Sou o Hermes, atendente do 2o Cartorio...'.

    Assert: 'sou o hermes' detectado como forbidden.
    """
    bad = "Oi! Tudo bem? Sou o Hermes, atendente do 2o Cartorio de Notas de Uberlandia."
    bad_phrase = has_forbidden_phrase(bad)
    assert bad_phrase is not None
    assert "hermes" in bad_phrase.lower()


def test_reg_007_qual_ia_nao_revelar_arquitetura() -> None:
    """Screenshot: cliente pergunta 'qual IA voce usa?'.

    Assert: planner NAO revela modelo/provider/prompt.
    """
    bad = "Sou baseada no MiniMax M3, modelo de linguagem avancado da MiniMax."
    bad_phrase = has_forbidden_phrase(bad)
    assert bad_phrase is not None
    # O forbidden_phrase inclui 'minimax' e 'modelo'
    assert any(x in bad_phrase for x in ("minimax", "modelo", "kimi", "gpt", "claude"))


# ============================================================
# Capability Registry runtime-aware
# ============================================================

def test_capability_emoluments_runtime_check() -> None:
    """Emoluments: tool MCP disponivel + DB healthy => can_execute."""
    cap = get_capability("emoluments")
    assert cap is not None
    # 2026-07-27 runtime: DB+API+cache HEALTHY, tool cartorio_calcular_emolumento True
    assert can_say_i_can_do_it("emoluments"), f"emoluments deveria ser executavel: {cap}"


def test_capability_human_handoff_blocked_when_chatwoot_down() -> None:
    """Human handoff: chatwoot DOWN (2026-07-27) => can_execute == False."""
    cap = get_capability("human_handoff")
    assert cap is not None
    assert can_say_i_can_do_it("human_handoff") is False, (
        f"human_handoff NAO deveria ser executavel com chatwoot OFFLINE: {cap}"
    )


def test_capability_second_copy_blocked_when_tool_unavailable() -> None:
    """Second copy: tool cartorio_emitir_segunda_via NAO no inventory MCP => can_execute == False."""
    cap = get_capability("second_copy")
    assert cap is not None
    assert can_say_i_can_do_it("second_copy") is False, (
        f"second_copy NAO deveria ser executavel sem tool: {cap}"
    )


def test_capability_institutional_info_always_executable() -> None:
    """Informacoes institucionais: zero runtime dep, sempre executavel."""
    cap = get_capability("institutional_info")
    assert cap is not None
    assert can_say_i_can_do_it("institutional_info") is True


def test_forbidden_action_verbs_para_capability_bloqueada() -> None:
    """Capability bloqueada tem lista de verbos proibidos."""
    verbs_handoff = forbidden_action_verbs("human_handoff")
    assert "transfiro" in verbs_handoff
    assert "transferir" in verbs_handoff
    verbs_emol = forbidden_action_verbs("emoluments")
    assert verbs_emol == [], "emoluments NAO deveria ter verbos proibidos"


# ============================================================
# Scope intent detection
# ============================================================

def test_detect_scope_intent_all() -> None:
    assert detect_scope_intent("me fala tudo") == ScopeIntent.ALL
    assert detect_scope_intent("tudo mesmo") == ScopeIntent.ALL
    assert detect_scope_intent("manda tudo de uma vez") == ScopeIntent.ALL
    assert detect_scope_intent("lista completa") == ScopeIntent.ALL


def test_detect_scope_intent_continue() -> None:
    assert detect_scope_intent("continua") == ScopeIntent.CONTINUE
    assert detect_scope_intent("e o resto?") == ScopeIntent.CONTINUE
    assert detect_scope_intent("uai mas estavamos falando disso") == ScopeIntent.CONTINUE
    assert detect_scope_intent("proximo") == ScopeIntent.CONTINUE


def test_detect_scope_intent_summary_each() -> None:
    assert detect_scope_intent("um pouco de cada") == ScopeIntent.SUMMARY_EACH
    assert detect_scope_intent("resumo cada um") == ScopeIntent.SUMMARY_EACH


def test_detect_scope_intent_answer_default() -> None:
    assert detect_scope_intent("quanto custa uma procuracao?") == ScopeIntent.ANSWER
    assert detect_scope_intent("ola") == ScopeIntent.ANSWER


# ============================================================
# Forbidden phrases (regra anti-vazamento)
# ============================================================

def test_forbidden_phrases_block_emoji() -> None:
    """Zero emoji (P0)."""
    text_with_emoji = "Oi! Tudo bem? \U0001f60a Como posso ajudar?"
    assert has_forbidden_phrase(text_with_emoji) is not None


def test_forbidden_phrases_block_memory_excuse() -> None:
    """A frase 'minha memoria nao e grande' e bloqueada."""
    assert has_forbidden_phrase("Boa memoria minha nao e grande") is not None


def test_forbidden_phrases_block_internal_leak() -> None:
    """'deploy', 'mcp', 'gateway', 'provider' sao bloqueados."""
    for word in ("deploy", "mcp", "gateway", "provider", "openclaw", "kimi", "gpt", "claude", "minimax"):
        text = f"Estamos ajustando o {word} agora."
        assert has_forbidden_phrase(text) is not None, f"'{word}' nao foi bloqueado"


def test_forbidden_phrases_block_hallucinated_action() -> None:
    """Frases de hallucination operacional sao bloqueadas."""
    for phrase in (
        "Gero o link da segunda via",
        "Faco seu agendamento",
        "Transfiro agora para o escrevente",
        "Consultei seu protocolo",
        "Envio pelo WhatsApp",
        "Seu documento esta pronto",
    ):
        assert has_forbidden_phrase(phrase) is not None, f"'{phrase}' nao foi bloqueada"


def test_sanitize_response_blocks() -> None:
    """sanitize_response retorna '' quando ha forbidden phrase."""
    bad = "Ola! Testes confirmados -- o canal ta respondendo."
    sanitized = sanitize_response(bad)
    assert sanitized == "", f"sanitize deveria ter limpado: '{sanitized}'"


def test_sanitize_response_passes() -> None:
    """sanitize_response NAO altera texto sem forbidden phrase."""
    good = "Ola! Em que posso ajudar?"
    assert sanitize_response(good) == good


# ============================================================
# ConversationState
# ============================================================

def test_state_store_basic() -> None:
    store = ConversationStateStore()
    state = store.get_or_create("thread-x", "imessage", "user-123")
    assert state.thread_id == "thread-x"
    assert state.user_id_hash != "user-123", "user_id deveria ser hasheado (LGPD)"
    assert len(state.user_id_hash) == 16, "sha256[:16]"


def test_state_lru_eviction() -> None:
    """LRU eviction apos MAX_ENTRIES."""
    store = ConversationStateStore()
    store.MAX_ENTRIES = 3
    for i in range(5):
        store.get_or_create(f"thread-{i}")
    assert len(store._store) <= 3, f"LRU nao evictionou: {len(store._store)}"


def test_state_user_id_hash_consistent() -> None:
    """Mesmo user_id gera mesmo hash (sessoes cross-channel)."""
    store = ConversationStateStore()
    s1 = store.get_or_create("a", user_id="joao")
    s2 = store.get_or_create("b", user_id="joao")
    assert s1.user_id_hash == s2.user_id_hash


# ============================================================
# Integration: planner com state
# ============================================================

def test_planner_does_not_say_hermes_under_any_input() -> None:
    """PIETRA nunca pode dizer 'sou o hermes' em QUALQUER input."""
    inputs = [
        "oi",
        "tudo",
        "me fale tudo",
        "quanto custa uma procurao",
        "endereco",
        "horario",
        "humano",
        "agendar",
        "protocolo 2026-00001",
        "estou falando disso?",
    ]
    for user_text in inputs:
        response, _ = plan_response(user_text, thread_id=f"thread-{hash(user_text)}")
        assert "sou o hermes" not in response.lower(), (
            f"Pietra disse 'sou o hermes' para input '{user_text}': {response[:200]}"
        )
        assert "sou o Hermes" not in response
        # Sem emoji
        for ch in response:
            cp = ord(ch)
            if 0x1F000 < cp < 0x1FFFF:
                pytest.fail(f"Emoji U+{cp:04X} em resposta para '{user_text}': {response[:100]}")


def test_planner_handles_operational_honesty() -> None:
    """Pietra NAO promete executar capability bloqueada."""
    # Human handoff: chatwoot OFFLINE
    response, _ = plan_response("quero falar com um humano", thread_id="thread-handoff")
    # Pode usar 'encaminho' se quiser, mas NAO 'transfiro agora'
    assert "transfiro agora" not in response.lower(), (
        f"Pietra prometeu transfirir quando handoff OFFLINE: {response[:200]}"
    )
    # Deve oferecer alternativa
    assert "telefone" in response.lower() or "(34)" in response or "escrevente" in response.lower(), (
        f"Pietra nao ofereceu alternativa para handoff: {response[:200]}"
    )
