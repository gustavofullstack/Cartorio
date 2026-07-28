"""Conversation State Machine para AGENT PIETRA.

Fase 2 do PROMPT P0 (PIETRA CONVERSATIONAL TRUTH & CAPABILITY HARDENING).

Problema que resolve (visto nos screenshots reais do cliente):
  - Cliente: 'uai mais estavamos falando sobre isso'
  - Pietra: 'Boa memoria minha nao e grande'          (ERRADO - alucinacao)
  - Correto: recuperar active_topic e continuar de onde parou.

Camadas de memoria (L0-L4):
  L0: ultimas mensagens raw da thread (TTL curto)
  L1: rolling conversational summary (TTL medio)
  L2: structured conversation state (sessao)
  L3: knowledge retrieval (TJMG OCR, etc)
  L4: long-term allowed memory (consentimento explicito)

Estado estruturado (L2):
  - thread_id, channel_id, user_id_hash
  - last_user_intent, active_topic
  - topics_already_explained: list[str]    (deduplicacao semantica)
  - pending_topics: list[str]
  - last_tool_results: dict
  - last_handoff_state: str
  - conversation_summary: str
  - response_sequence: int

Backend: in-process LRU (TTL 30min) para MVP. Producao deve usar Redis SETEX
(ja existe no projeto em app/services/redis_bus.py) com chave
``pietra:state:{thread_id}``.

Regra absoluta (Fase 0 do P0):
  - Cliente diz 'me fala tudo' / 'tudo mesmo' / 'manda tudo de uma vez'
    -> entregar TUDO sem pedir autorizacao a cada topico.
  - Cliente diz 'continua' / 'e o resto?' / 'uai mas estavamos falando disso'
    -> recuperar active_topic e continuar.
  - Cliente diz 'um pouco de cada'
    -> resumo curto por topico, cobrindo todos uma unica vez.

Modified by Gustavo Almeida · 2026-07-27
"""

from __future__ import annotations

import hashlib
import re
import time

from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class ScopeIntent(StrEnum):
    """Intencao de escopo inferida do texto do usuario (Fase 4 do P0)."""

    ALL = "ALL"  # "me fala tudo", "tudo mesmo", "manda tudo de uma vez"
    CONTINUE = "CONTINUE"  # "continua", "e o resto?", "uai mas estavamos falando disso"
    SUMMARY_EACH = "SUMMARY_EACH"  # "um pouco de cada", "resume cada um"
    ANSWER = "ANSWER"  # resposta direta a uma pergunta
    UNKNOWN = "UNKNOWN"


# Topicos que a Pietra conhece e explica (canonicos, sem capacidade inventada)
PIETRA_TOPICS: tuple[str, ...] = (
    "emoluments",
    "protocol_status",
    "pre_protocol",
    "second_copy",
    "signature_info",
    "authentication_info",
    "deeds_info",
    "institutional_info",
    "human_handoff",
    "appointment",
)


@dataclass
class ConversationState:
    thread_id: str
    channel_id: str
    user_id_hash: str
    last_user_intent: str = ""
    active_topic: str = ""
    topics_already_explained: list[str] = field(default_factory=list)
    pending_topics: list[str] = field(default_factory=list)
    last_tool_results: dict[str, Any] = field(default_factory=dict)
    last_handoff_state: str = ""
    conversation_summary: str = ""
    response_sequence: int = 0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationState:
        # Tolerar keys faltantes
        return cls(
            thread_id=data.get("thread_id", "unknown"),
            channel_id=data.get("channel_id", "unknown"),
            user_id_hash=data.get("user_id_hash", "anon"),
            last_user_intent=data.get("last_user_intent", ""),
            active_topic=data.get("active_topic", ""),
            topics_already_explained=data.get("topics_already_explained", []),
            pending_topics=data.get("pending_topics", []),
            last_tool_results=data.get("last_tool_results", {}),
            last_handoff_state=data.get("last_handoff_state", ""),
            conversation_summary=data.get("conversation_summary", ""),
            response_sequence=data.get("response_sequence", 0),
            last_updated=data.get("last_updated", time.time()),
        )


class ConversationStateStore:
    """Store in-process LRU com TTL 30min.

    Producao: trocar por Redis SETEX (chave ``pietra:state:{thread_id}``)
    usando o cliente ja existente em app/services/redis_bus.py.
    """

    TTL_SECONDS = 1800  # 30 min
    MAX_ENTRIES = 1024

    def __init__(self) -> None:
        self._store: OrderedDict[str, ConversationState] = OrderedDict()

    def get_or_create(
        self,
        thread_id: str,
        channel_id: str = "unknown",
        user_id: str | None = None,
    ) -> ConversationState:
        user_hash = self._hash_user_id(user_id) if user_id else "anon"
        if thread_id in self._store:
            state = self._store[thread_id]
            # TTL check
            if time.time() - state.last_updated > self.TTL_SECONDS:
                # Expired -> recriar
                del self._store[thread_id]
            else:
                # Move to end (LRU touch)
                self._store.move_to_end(thread_id)
                return state
        # Create new
        state = ConversationState(
            thread_id=thread_id,
            channel_id=channel_id,
            user_id_hash=user_hash,
        )
        self._store[thread_id] = state
        # Evict oldest if needed
        while len(self._store) > self.MAX_ENTRIES:
            self._store.popitem(last=False)
        return state

    def save(self, state: ConversationState) -> None:
        state.last_updated = time.time()
        self._store[state.thread_id] = state
        self._store.move_to_end(state.thread_id)

    def reset(self, thread_id: str) -> None:
        self._store.pop(thread_id, None)

    @staticmethod
    def _hash_user_id(user_id: str) -> str:
        """Hash do user_id (LGPD-safe: nao armazena o id em claro)."""
        return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]


# Singleton (MVP)
_state_store = ConversationStateStore()


def get_state_store() -> ConversationStateStore:
    return _state_store


# === Scope intent detection (Fase 4 do P0) ===

_SCOPE_ALL_KEYS = (
    "me fala tudo",
    "tudo mesmo",
    "manda tudo",
    "tudo de uma vez",
    "manda tudo de uma vez",
    "tudo separado",
    "tudo em varias",
    "tudo em várias",
    "tudo que pode",
    "tudo o que pode",
    "tudo o que voce pode",
    "tudo o que você pode",
    "tudo que voce pode",
    "tudo que você pode",
    "me explica tudo",
    "lista completa",
    "catalogo completo",
    "catálogo completo",
    "tudo",
)

_SCOPE_CONTINUE_KEYS = (
    "continua",
    "continue",
    "continuar",
    "e o resto",
    "e o restante",
    "cadê o restante",
    "cade o restante",
    "o restante",
    "uai mas estavamos",
    "uai mais estavamos",  # variante coloquial: 'uai MAIS estavamos' (sem 'mas')
    "uai mas estavamos falando",
    "uai mais estavamos falando",
    "uai mas estavamos falando disso",
    "uai mais estavamos falando disso",
    "uai mas estávamos falando",
    "uai mais estávamos falando",
    "uai mas estavamos falando sobre isso",
    "uai mais estavamos falando sobre isso",
    "uai mas estávamos falando sobre isso",
    "uai mais estávamos falando sobre isso",
    "uai estamos falando",
    "mas estavamos falando disso",
    "mas estávamos falando disso",
    "estavamos falando disso",
    "estávamos falando disso",
    "estava falando disso",
    "estávamos falando",
    "proximo",
    "próximo",
    "falta",
    "so veio",
    "so mandou",
    "só veio",
    "só mandou",
    "so isso",
    "só isso",
    "so recebi",
    "só recebi",
    "acabei de pedir",
)

_SCOPE_SUMMARY_EACH_KEYS = (
    "um pouco de cada",
    "resumo cada um",
    "resume cada",
    "resuma cada",
    "pouco de cada",
    "resuma de cada",
    "resumo curto",
    "resumo de cada",
)


def detect_scope_intent(text: str) -> ScopeIntent:
    """Detecta a intencao de escopo do usuario (Fase 4 do P0)."""
    if not text:
        return ScopeIntent.UNKNOWN
    t = text.lower().strip()

    # Ignorar falsos positivos de 'tudo' em conversas normais ("salvam tudo", "obrigado por tudo", "tudo certo", etc.)
    non_all_tudo_patterns = (
        r"\b(salvam|salvar|salvo|registrou|anotou|obrigad[oa]|por|esta|está)\s+tudo\b",
        r"\btudo\s+(certo|bem|ok|anotado|registrado|entendido|certo)\b",
    )
    is_conversational_tudo = any(re.search(pat, t) for pat in non_all_tudo_patterns)

    # Ordem importa: ALL > CONTINUE > SUMMARY_EACH > ANSWER
    for key in _SCOPE_ALL_KEYS:
        if key == "tudo":
            if t == "tudo" or (
                not is_conversational_tudo
                and re.search(
                    r"\b(fala|fale|manda|mandar|ver|mostrar|listar|passar|diz|dizer|explicar|explica|quero|saber)\s+tudo\b",
                    t,
                )
            ):
                return ScopeIntent.ALL
            continue
        if re.search(r"\b" + re.escape(key) + r"\b", t):
            return ScopeIntent.ALL
    for key in _SCOPE_CONTINUE_KEYS:
        if re.search(r"\b" + re.escape(key) + r"\b", t):
            return ScopeIntent.CONTINUE
    for key in _SCOPE_SUMMARY_EACH_KEYS:
        if re.search(r"\b" + re.escape(key) + r"\b", t):
            return ScopeIntent.SUMMARY_EACH
    return ScopeIntent.ANSWER


# === Forbidden phrases (Fase 8 do P0) ===

# Frases que NUNCA devem aparecer na resposta da Pietra (vazamento / alucinacao).
# Ver tambem: pietra_capabilities.forbidden_action_verbs() (gates runtime-aware).
FORBIDDEN_PHRASES: tuple[str, ...] = (
    # Memoria
    "boa memoria minha nao e grande",
    "boa memoria minha nao é grande",
    "boa memória minha não é grande",
    "boa memoria minha e pequena",
    "boa memória minha é pequena",
    "minha memoria nao e grande",
    "minha memoria nao é grande",
    "minha memória não é grande",
    "minha memoria e pequena",
    "minha memória é pequena",
    "nao tenho muita memoria",
    "não tenho muita memória",
    "minha memoria nao permite",
    "minha memória não permite",
    "vou esquecer",
    # Identidade
    "sou o hermes",
    "sou o Hermes",
    "atendente hermes",
    "atendente Hermes",
    "agente Hermes",
    # Dev / infra
    "testes confirmados",
    "canal ta respondendo",
    "canal está respondendo",
    "canal tá respondendo",
    "deploy",
    "gateway",
    "mcp",
    "runtime",
    "modelo",
    "model",
    "provider",
    "prompt",
    "system prompt",
    "openclaw",
    "hermes",
    "minimax",
    "kimi",
    "gpt",
    "claude",
    "codex",
    "agy",
    "grok",
    "opencode",
    # Hallucination operacional (cobre as 6 do exemplo do P0)
    "gero o link",
    "gero link",
    "faco seu agendamento",
    "faço seu agendamento",
    "transfiro agora",
    "transfiro direto",
    "consultei seu protocolo",
    "envio pelo whatsapp",
    "seu documento esta pronto",
    "seu documento está pronto",
    "ja fiz",
    "já fiz",
    "ja criei",
    "já criei",
    # Emoji (caracteres unicode comuns; policy é zero emoji)
    "\U0001f600",
    "\U0001f601",
    "\U0001f602",
    "\U0001f603",
    "\U0001f604",
    "\U0001f605",
    "\U0001f606",
    "\U0001f607",
    "\U0001f608",
    "\U0001f609",
    "\U0001f60a",
    "\U0001f60b",
    "\U0001f60c",
    "\U0001f60d",
    "\U0001f60e",
    "\U0001f60f",
    "\U0001f61a",
    "\U0001f61b",
    "\U0001f61c",
    "\U0001f61d",
    "\u2705",
    "\u274c",
    "\u2b50",
    "\U0001f44d",
    "\U0001f64f",
)


def has_forbidden_phrase(text: str) -> str | None:
    """Retorna a primeira frase proibida encontrada, ou None."""
    if not text:
        return None
    t = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in t:
            return phrase
    # Detectar qualquer emoji
    for ch in text:
        cp = ord(ch)
        if cp > 0x1F000 and cp < 0x1FFFF:  # bloco emoji mais comum
            return f"emoji U+{cp:04X}"
    return None


def sanitize_response(
    text: str,
    state: ConversationState | None = None,
) -> str:
    """Sanitiza a resposta removendo/replace phrases proibidas (Fase 8 do P0)."""
    if not text:
        return text
    bad = has_forbidden_phrase(text)
    if bad is None:
        return text
    # Estratégia: se cair forbidden phrase, retornar string vazia (caller deve
    # gerar resposta substituta via response_planner).
    return ""
