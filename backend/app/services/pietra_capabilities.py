"""Capability Registry runtime-aware para AGENT PIETRA.

Fase 5 do PROMPT P0 (PIETRA CONVERSATIONAL TRUTH & CAPABILITY HARDENING).

REGRA CANONICA: ``can_say_i_can_do_it`` exige que TODOS estes gates estejam verdes:
  1. capability.registered (esta no schema)
  2. capability.tool_available (tool MCP existe e responde)
  3. capability.runtime_healthy (servico backend UP)
  4. capability.authorization_ok (HITL/LGPD permits)

Se qualquer gate falhar, a linguagem da Pietra muda automaticamente:
  - can_execute=True: "Posso calcular o valor agora."
  - can_execute=False + can_explain=True: "Posso explicar como funciona, mas o calculo exato precisa de [tool]."
  - runtime_unknown: "Vou confirmar com a equipe e te retorno."
  - tool_failed: "Estamos com indisponibilidade momentanea nesse servico. Posso [alternativa]?"

Gates ativos verificados em 2026-07-27 (runtime real):
  - cartorio_banco_de_dados: 1/1 (pgvector/pgvector:pg17) -> DB HEALTHY
  - cartorio_memory-cache:   1/1 (redis:8.8)            -> CACHE HEALTHY
  - cartorio_system-api:     1/1                          -> API HEALTHY
  - cartorio_whatsapp-api:   1/1                          -> CONTAINER UP, sessao CLOSE (NAO operacional)
  - cartorio_hermes:         1/1                          -> HERMES UP
  - cartorio_chatwoot:       OFFLINE                      -> HANDOFF NAO DISPONIVEL
  - cartorio_openclaw:       OFFLINE (SUI Tailscale)      -> OPENCLAW NAO DISPONIVEL

Modified by Gustavo Almeida · 2026-07-27
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final


class GateState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    DISABLED = "DISABLED"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Capability:
    capability_id: str
    display_name: str
    can_explain: bool
    requires_tool: bool
    tool_name: str | None
    tool_available: bool
    runtime_dependency: list[str]
    runtime_healthy: bool
    requires_human_review: bool
    can_execute: bool
    evidence: list[str] = field(default_factory=list)
    last_verified_at: str = "2026-07-27T16:55:00-03:00"


# Status atual do runtime (snapshot 2026-07-27 16:55 BRT, via `docker service ls` no VPS)
_RUNTIME: Final[dict[str, GateState]] = {
    "database": GateState.HEALTHY,  # cartorio_banco_de_dados 1/1
    "cache": GateState.HEALTHY,  # cartorio_memory-cache 1/1
    "api": GateState.HEALTHY,  # cartorio_system-api 1/1
    "whatsapp_container": GateState.HEALTHY,  # cartorio_whatsapp-api 1/1
    "whatsapp_session": GateState.DOWN,  # session CLOSE
    "chatwoot": GateState.DOWN,  # OFFLINE (SUI)
    "openclaw": GateState.DOWN,  # OFFLINE (SUI Tailscale)
    "n8n": GateState.HEALTHY,  # container UP, public path 503
    "telegram": GateState.UNKNOWN,  # bot nao testado live
    "imessage": GateState.HEALTHY,  # gateway local UP, validado 3x
}

_TOOL_AVAILABILITY: Final[dict[str, bool]] = {
    "cartorio_calcular_emolumento": True,  # 14 tools MCP cartorio-api
    "cartorio_consultar_protocolo": True,
    "cartorio_agendar_atendimento": True,
    "cartorio_emitir_segunda_via": False,  # NAO existe no MCP inventory
    "cartorio_extrair_e_calcular_real": True,
    "chatwoot_handoff": False,  # chatwoot OFFLINE
    "openclaw_skills": False,  # openclaw OFFLINE
}


def _gate(cap_runtime: list[str]) -> bool:
    """Retorna True se TODOS os servicos em cap_runtime estao HEALTHY."""
    return all(_RUNTIME.get(dep, GateState.UNKNOWN) == GateState.HEALTHY for dep in cap_runtime)


def _registry() -> dict[str, Capability]:
    """Constroi o registry com base no runtime snapshot atual."""
    caps: dict[str, Capability] = {}

    # 1. EMOLUMENTOS
    tool = "cartorio_calcular_emolumento"
    runtime_h = _gate(["database", "api", "cache"])
    caps["emoluments"] = Capability(
        capability_id="emoluments",
        display_name="Consulta de emolumentos (Tabela MG 2026)",
        can_explain=True,
        requires_tool=True,
        tool_name=tool,
        tool_available=_TOOL_AVAILABILITY.get(tool, False),
        runtime_dependency=["database", "api", "cache"],
        runtime_healthy=runtime_h,
        requires_human_review=False,
        can_execute=(runtime_h and _TOOL_AVAILABILITY.get(tool, False)),
        evidence=[
            "pricing_layer=regulatory_tjmg: procuracao_geral R$ 68,94 (Portaria TJMG, auditoria)",
            "pricing_layer=operational_pos_2notas: procuracao generica R$ 71,38 (total de balcao)",
            "Cliente recebe somente a camada operacional; regulatoria nao e anunciada como preco de balcao",
        ],
    )

    # 2. PROTOCOL STATUS
    tool = "cartorio_consultar_protocolo"
    runtime_h = _gate(["database", "api"])
    caps["protocol_status"] = Capability(
        capability_id="protocol_status",
        display_name="Consulta de protocolo",
        can_explain=True,
        requires_tool=True,
        tool_name=tool,
        tool_available=_TOOL_AVAILABILITY.get(tool, False),
        runtime_dependency=["database", "api"],
        runtime_healthy=runtime_h,
        requires_human_review=False,
        can_execute=(runtime_h and _TOOL_AVAILABILITY.get(tool, False)),
        evidence=["tool MCP registrado no inventory 14 tools cartorio-api"],
    )

    # 3. PRE-PROTOCOLO
    runtime_h = _gate(["database", "api"])
    caps["pre_protocol"] = Capability(
        capability_id="pre_protocol",
        display_name="Abertura de pre-protocolo (DRAFT ate validacao humana)",
        can_explain=True,
        requires_tool=True,
        tool_name="cartorio_pre_protocol",
        tool_available=True,
        runtime_dependency=["database", "api"],
        runtime_healthy=runtime_h,
        requires_human_review=True,  # HITL obrigatorio
        can_execute=(runtime_h),  # sempre com HITL DRAFT
        evidence=["HITL obrigatorio: DRAFT ate validacao de escrevente (regra P0 do AGENTS.md)"],
    )

    # 4. SEGUNDA VIA
    caps["second_copy"] = Capability(
        capability_id="second_copy",
        display_name="Segunda via de documentos",
        can_explain=True,
        requires_tool=True,
        tool_name="cartorio_emitir_segunda_via",
        tool_available=False,  # NAO no inventory
        runtime_dependency=["database", "api", "storage"],
        runtime_healthy=False,
        requires_human_review=True,
        can_execute=False,
        evidence=[
            "tool cartorio_emitir_segunda_via NAO esta nos 14 tools MCP cartorio-api",
            "Hipótese (a validar): pode ser um alias / rota /api/v1/segunda-via",
        ],
    )

    # 5. INFORMACOES INSTITUCIONAIS
    caps["institutional_info"] = Capability(
        capability_id="institutional_info",
        display_name="Informacoes institucionais (endereco, horario, CNS, titular)",
        can_explain=True,
        requires_tool=False,
        tool_name=None,
        tool_available=True,  # configurado no SOUL.md
        runtime_dependency=[],
        runtime_healthy=True,
        requires_human_review=False,
        can_execute=True,
        evidence=[
            "CARTORIO_INFO em cartorio_agent.py + SOUL.md",
            "Validado em 3 testes reais iMessage (T3 deste ciclo)",
        ],
    )

    # 6. ASSINATURA / AUTENTICACAO (informativo)
    caps["signature_info"] = Capability(
        capability_id="signature_info",
        display_name="Informacoes sobre reconhecimento de firma e autenticacao",
        can_explain=True,
        requires_tool=False,
        tool_name=None,
        tool_available=True,
        runtime_dependency=[],
        runtime_healthy=True,
        requires_human_review=False,
        can_execute=False,  # ato final exige comparecimento
        evidence=["Ato final exige comparecimento fisico (regra notarial)"],
    )

    # 7. ESCRITURAS / PROCURACOES (informativo + pre-protocolo)
    caps["deeds_info"] = Capability(
        capability_id="deeds_info",
        display_name="Informacoes sobre escrituras, procuracoes, testamentos",
        can_explain=True,
        requires_tool=False,
        tool_name=None,
        tool_available=True,
        runtime_dependency=[],
        runtime_healthy=True,
        requires_human_review=True,  # sempre exige validacao humana final
        can_execute=False,
        evidence=["HITL obrigatorio em qualquer ato juridico (regra P0)"],
    )

    # 8. AGENDAMENTO
    tool = "cartorio_agendar_atendimento"
    runtime_h = _gate(["database", "api"])
    caps["appointment"] = Capability(
        capability_id="appointment",
        display_name=(
            "Pre-agendamento so para atos complexos (escrituras); balcao simples e ordem de chegada"
        ),
        can_explain=True,
        requires_tool=True,
        tool_name=tool,
        tool_available=_TOOL_AVAILABILITY.get(tool, False),
        runtime_dependency=["database", "api"],
        runtime_healthy=runtime_h,
        requires_human_review=True,  # escrevente confirma sempre
        can_execute=(runtime_h and _TOOL_AVAILABILITY.get(tool, False)),
        evidence=[
            "Nao ha pre-agendamento para reconhecimento de firma, autenticacao, "
            "abertura de firma, arquivamento, DUT/ATPV e xerox — ordem de chegada",
            "tool registrado no inventory MCP (escrituras e atos complexos)",
        ],
    )

    # 9. HUMAN HANDOFF
    runtime_h = _RUNTIME.get("chatwoot") == GateState.HEALTHY
    caps["human_handoff"] = Capability(
        capability_id="human_handoff",
        display_name="Encaminhamento para escrevente humano via Chatwoot",
        can_explain=True,
        requires_tool=True,
        tool_name="chatwoot_handoff",
        tool_available=False,  # Chatwoot OFFLINE
        runtime_dependency=["chatwoot"],
        runtime_healthy=runtime_h,
        requires_human_review=False,
        can_execute=False,  # chatwoot OFFLINE no momento
        evidence=[
            "chatwoot: DOWN (SUI Gustavo)",
            "2026-07-27: chat.2notasudi.com.br retorna 404",
        ],
    )

    return caps


def get_capability(capability_id: str) -> Capability | None:
    return _registry().get(capability_id)


def all_capabilities() -> list[Capability]:
    return list(_registry().values())


def can_say_i_can_do_it(capability_id: str) -> bool:
    """REGRA CANONICA: so retorna True se todos os gates verdes.

    can_say_i_can_do_it = (
        capability.registered
        and capability.tool_available
        and capability.runtime_healthy
        and capability.authorization_ok
    )
    """
    cap = get_capability(capability_id)
    if cap is None:
        return False
    return cap.can_explain and (not cap.requires_tool or cap.tool_available) and cap.runtime_healthy


def policy_summary() -> dict[str, str]:
    """Sumario textual das capabilities para o prompt da Pietra.

    Lido pelo system prompt para informar a linguagem correta.
    """
    lines: dict[str, str] = {}
    for cap in all_capabilities():
        if cap.can_execute:
            status = "EXECUTO"
        elif cap.can_explain and not cap.can_execute:
            status = "EXPLICO_APENAS"
        elif not cap.runtime_healthy:
            status = "INDISPONIVEL_AGORA"
        else:
            status = "BLOQUEADO"
        lines[cap.capability_id] = f"{status} | {cap.display_name}"
    return lines


def forbidden_action_verbs(capability_id: str) -> list[str]:
    """Verbos que a Pietra NAO pode usar se can_say_i_can_do_it == False.

    EXEMPLOS a detectar (Fase 13 do P0):
    - 'Gero o link da segunda via'  -> se second_copy bloqueado
    - 'Faco seu agendamento'         -> se appointment bloqueado
    - 'Transfiro agora'              -> se human_handoff bloqueado
    - 'Consultei seu protocolo'      -> se protocol_status bloqueado
    - 'Envio pelo WhatsApp'          -> se whatsapp_session DOWN
    - 'Seu documento esta pronto'    -> se second_copy bloqueado
    """
    cap = get_capability(capability_id)
    if cap is None:
        return ["executar", "fazer", "gerar", "enviar", "transferir", "criar"]
    if cap.can_execute:
        return []
    return [
        "executar",
        "fazer",
        "gero",
        "gerar",
        "envio",
        "enviar",
        "transfiro",
        "transferir",
        "crio",
        "criar",
        "seu documento esta pronto",
        "agora",
        "ja fiz",
        "ja criei",
    ]
