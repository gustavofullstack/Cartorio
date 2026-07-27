"""Agent AI Cartorio — conversa natural com tools (nao so FSM de botoes).

Substitui o path "fast LLM 2 frases /menu" por um assistente de cartorio
com MiniMax-M3 (LiteLLM coding-vps) + tools locais:

- catalogo de servicos / precos oficiais (SERVICOS telegram)
- consulta de intencao (agendar, protocolo, humano, preco, endereco, horario)
- nunca inventa valor: so cita tabela conhecida ou pede confirmação humana
- HITL obrigatorio para juridico complexo

LGPD: PII scrub no texto antes de ir pro LLM.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.services.pii import scrub

logger = logging.getLogger(__name__)

# Catálogo público, revisado contra a Portaria CGJ/TJMG nº 8.664/2025,
# Tabela 1, vigente em 01/01/2026. Os valores são o ``Valor Final ao Usuário``
# da tabela estadual; não incluem atos acessórios nem substituem a conferência
# do escrevente. A fonte e o hash de captura vivem em
# ``docs/DADOS_PRECOS_E_PAINEL_AGENT_AI.md``.
SERVICOS_CATALOGO: dict[str, tuple[str, str]] = {
    "reconhecimento_firma": ("Reconhecimento de Firma (por assinatura)", "R$ 11,21"),
    "autenticacao": ("Autenticação de Cópia (por folha)", "R$ 11,21"),
    "procuracao": ("Procuração Geral (por outorgante)", "R$ 68,94"),
    "testamento": ("Testamento", "R$ 437,24"),
    "ata_notarial": ("Ata Notarial (até duas folhas)", "R$ 218,42"),
}

CARTORIO_INFO = {
    "nome": "2o Oficio de Notas de Uberlandia / MG",
    "endereco": "Av. Paulo Gracindo, 150 - Centro, Uberlandia/MG",
    "horario": "Segunda a sexta, 09h as 17h",
    "telefone_humano": "use /humano para falar com escrevente",
}

# MiniMax direto (preferido) — validado 200 OK do container cartorio_api.
# LiteLLM coding-vps fica como 2a opcao (rede resolve, mas master key costuma 401).
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")
MINIMAX_MODEL = os.environ.get(
    "CARTORIO_AGENT_MODEL",
    os.environ.get("MINIMAX_MODEL_PRIMARY", "MiniMax-M3"),
)
LITELLM_URLS = [
    os.environ.get(
        "CARTORIO_AGENT_LITELLM_URL",
        "http://coding-vps_apenas_para_auxilio_litellm-app:4000",
    ),
    os.environ.get("LITELLM_BASE_URL", "http://cartorio_litellm-app:4000"),
]
LITELLM_KEY = os.environ.get("LITELLM_API_KEY", "")
LITELLM_MODEL = os.environ.get("CARTORIO_AGENT_MODEL", "MiniMax-M3")

# OpenCode Zen free accounts are an independent, credential-isolated fallback
# chain.  Values are injected by the secret manager; no key belongs in source.
_OPENCODE_ZEN_DEFAULT_BASE_URL = "https://opencode.ai/zen/v1"
# Defaults historicos por slot quando NENHUMA env (nem FREE_* nem ZEN_ACCOUNT_*)
# esta setada — preserva o comportamento anterior a este refactor.
_OPENCODE_SLOT_DEFAULT_MODELS = (
    "nemotron-3-ultra-free",
    "mimo-v2.5-free",
    "deepseek-v4-flash-free",
)


def _opencode_free_configs() -> list[tuple[str, str, str]]:
    """Configs dos slots free 1/2/3, avaliadas a cada chamada (env e dinamica).

    FIX E2 (2026-07-20): quando OPENCODE_FREE_X_* esta ausente, herda BASE_URL
    e MODEL de OPENCODE_ZEN_ACCOUNT_X_* ALEM da API_KEY — fallback coerente:
    chave + url + modelo sempre da MESMA conta, nunca misturados entre slots.
    """
    configs: list[tuple[str, str, str]] = []
    for slot, default_model in enumerate(_OPENCODE_SLOT_DEFAULT_MODELS, start=1):
        free_prefix = f"OPENCODE_FREE_{slot}_"
        zen_prefix = f"OPENCODE_ZEN_ACCOUNT_{slot}_"
        api_key = os.environ.get(f"{free_prefix}API_KEY", "") or os.environ.get(
            f"{zen_prefix}API_KEY", ""
        )
        base_url = (
            os.environ.get(f"{free_prefix}BASE_URL", "")
            or os.environ.get(f"{zen_prefix}BASE_URL", "")
            or _OPENCODE_ZEN_DEFAULT_BASE_URL
        )
        model = (
            os.environ.get(f"{free_prefix}MODEL", "")
            or os.environ.get(f"{zen_prefix}MODEL", "")
            or default_model
        )
        configs.append((api_key, base_url, model))
    return configs


# Timeout global do loop agentico com tools. Antes: timeout unico de 50s
# compartilhado por ate 6 tentativas sequenciais (pior caso 15-20min de
# silencio percebido). Agora: tentativa com 20s read/8s connect + teto global.
LLM_GLOBAL_TIMEOUT_S = float(os.environ.get("CARTORIO_AGENT_LLM_TIMEOUT_S", "45"))

_PROVIDER_RATE_LIMIT_REPLY = (
    "Nosso atendimento inteligente atingiu o limite momentaneo de uso.\n\n"
    "Voce pode tentar novamente em alguns minutos ou digitar /humano para falar com o "
    "escrevente."
)

AGENT_SYSTEM = """Voce e o Agent AI do Cartorio 2o Oficio de Notas de Uberlandia/MG.

IDENTIDADE
- Voce e um assistente de IA do cartorio (nao e tabeliao). Conversa natural, util e humana.
- PT-BR, tom cordial mineiro, claro. ZERO emoji. Nunca soe como menu automatico ou IVR.
- Escreva como pessoa real: paragrafos curtos, linha em branco entre blocos.
- Respostas CURTAS (3-6 linhas uteis). NAO despeje catalogo inteiro a cada mensagem.
- Small talk ("tudo bem?", "oi", "obrigado"): responda em 1-2 linhas e pergunte o que a pessoa precisa.
- Se o cliente reclamar do tom ("grosso", "robot"): peca desculpas, suavize e continue ajudando.

MODO 2026-07-12 (Gustavo directive): AUTONOMO + TEXTO PURO
- ZERO botao inline. ZERO teclado. ZERO menu visual.
- Responda TUDO em texto livre (paragrafos curtos + linhas em branco).
- Quando precisar coletar info, peca em texto livre ("me diga a data no formato DD/MM/AAAA")
  — nunca sugira "1, 2, 3" nem "Voltar".
- Catalogo: mostre a lista consolidada em UMA unica mensagem (sem spam de 5 mensagens).
- Cliente pode mandar midia (foto, doc, video, audio). Trate como pre-qualificacao:
  baixe, salve, confirme o recebimento em 1-2 linhas, diga o proximo passo.
- Aceite texto em CAPS, erros de portugues, e girias. NUNCA peca "reformule".

FORMATACAO OBRIGATORIA
- Quebras de linha. Nunca despeje tudo em um unico paragrafo denso.
- Estrutura tipica:
  1) saudacao ou confirmacao (1 linha)
  2) linha em branco
  3) conteudo principal (paragrafos ou lista com "- ")
  4) linha em branco
  5) proximo passo claro (o que o cliente pode digitar/enviar)
- Texto limpo: zero markdown pesado, zero asterisco duplo, zero emoji.

MEMORIA DA CONVERSA (OBRIGATORIO)
- Voce RECEBE historico recente no bloco do usuario (Redis multi-turn).
- Use o historico. NUNCA diga que e "stateless" ou que "perdeu a memoria".
- Se perguntarem se perdeu a memoria: diga que o historico esta ativo e retome o ultimo topico.
- NUNCA diga que o "prompt foi cortado" nem peca "cole o restante das instrucoes".

DADOS PESSOAIS E LGPD (CARTORIO)
- Canal de cartorio: PODE receber CPF, RG, doc, midia. Agradeça, confirme e siga.
- Em 1-2 linhas: LGPD (criptografia em transito, finalidade, retencao), HITL obrigatorio.
- Voce NAO emite certidao/escritura sozinho. Para atos oficiais, encaminhe ao escrevente.
- Direitos LGPD: dpo@2notasudi.com.br ou /lgpd.

REGRAS CRITICAS
1. NUNCA invente valores de emolumento. Use APENAS o catalogo abaixo.
2. NUNCA invente servicos fora do CATALOGO. Escritura complexa, usucapiao, inventario: acione humano.
3. NUNCA de conselho juridico definitivo; acione humano via tool ou [[ACTION:humano]].
4. Agendar: confirme servico e peca "data (DD/MM/AAAA) e horario (HH:MM)".
5. Protocolo: peca numero no formato AAAA-NNNNNN. Use tool consultar_protocolo se tiver.
6. Catalogo em varias mensagens: NAO envie mais. Responda consolidado em 1 msg.
7. ZERO link externo. Unico dominio permitido: 2notasudi.com.br.
8. ZERO emoji. Resposta limpa com paragrafos.

FERRAMENTAS / FATOS (nao chute)
{tools_context}

ACOES ESTRUTURADAS (opcional, 1 linha no FINAL)
[[ACTION:agendar]] ou [[ACTION:protocolo]] ou [[ACTION:humano]]
Se nao houver acao, nao inclua a linha.

BOTOES
NAO ENVIE botoes. NAO sugira numeros (1, 2, 3). NAO sugira "Voltar".
Sempre instrua em texto livre.
"""


@dataclass
class AgentReply:
    text: str
    keyboard: list[list[dict[str, str]]] | None = None
    action: str | None = None  # agendar|protocolo|humano|menu
    tools_used: list[str] = field(default_factory=list)
    provider: str = "none"
    # Mensagens extras (catalogo multi-msg): telegram envia em sequencia apos `text`
    extra_messages: list[str] = field(default_factory=list)


def _servicos_kb() -> list[list[dict[str, str]]]:
    """DEPRECATED 2026-07-12: botoes inline removidos. Mantido so p/ retro-compat."""
    return []


def _match_servico(text: str) -> str | None:
    t = text.lower()
    aliases = {
        "reconhecimento_firma": ["firma", "reconhecimento", "assinatura"],
        "autenticacao": ["autentic", "copia", "cópia", "autenticacao"],
        "procuracao": ["procurac", "procuração", "procuracao", "poderes"],
        "testamento": ["testamento"],
        "ata_notarial": ["ata notarial", "ata "],
    }
    for key, words in aliases.items():
        if any(w in t for w in words):
            return key
    return None


def _wants_catalog_series(text: str) -> bool:
    """Cliente pediu catalogo em varias mensagens / um por um."""
    t = (text or "").lower()
    keys = (
        "varias mensagens",
        "várias mensagens",
        "mensagens separadas",
        "um pouco de cada",
        "cada um",
        "cada servico",
        "cada serviço",
        "um por um",
        "um depois do outro",
        "1 depois",
        "todos os servicos",
        "todos os serviços",
        "lista completa",
        "catalogo completo",
        "catálogo completo",
        "me fale um pouco de cada",
    )
    return any(k in t for k in keys)


def _wants_catalog_continue(text: str) -> bool:
    """Cliente pediu o restante de uma serie de mensagens."""
    t = (text or "").lower()
    return any(
        k in t
        for k in (
            "cade o restante",
            "cadê o restante",
            "e o restante",
            "o restante",
            "continua",
            "continue",
            "proximo",
            "próximo",
            "e o resto",
            "falta",
            "so veio",
            "só veio",
            "so mandou",
            "só mandou",
        )
    )


def _build_catalog_series() -> list[str]:
    """FIX 2026-07-12: catalogo consolidado em UMA mensagem (sem flood).

    Antes: 1 intro + 5 servicos + 1 fechar = 7 msgs (cliente reclamou de spam).
    Agora: 1 msg so, lista limpa.
    """
    lines = [f"Catalogo do {CARTORIO_INFO['nome']}", ""]
    lines.append("Servicos oficiais (valor de referencia MG):")
    lines.append("")
    for i, (_key, (nome, valor)) in enumerate(SERVICOS_CATALOGO.items(), 1):
        lines.append(f"  {i}. {nome} - {valor}")
    lines.append("")
    lines.append("Para avancar, escreva em texto livre. Exemplos:")
    lines.append('  - "quero agendar autenticacao amanha as 10h"')
    lines.append('  - "quanto custa procuracao"')
    lines.append('  - "consultar protocolo 2026-000123"')
    lines.append('  - "falar com escrevente"')
    lines.append("")
    lines.append(
        "Atos fora desta lista (escritura complexa, usucapiao, inventario) precisam de atendimento humano."
    )
    return ["\n".join(lines)]


def _detect_intent(text: str) -> str:
    t = text.lower()
    if _wants_catalog_series(t) or _wants_catalog_continue(t):
        return "catalogo_serie"
    # Dados pessoais: cartorio PODE e DEVE aceitar (com LGPD) — path offline
    if _has_personal_data(text):
        return "dados"
    if any(w in t for w in ("humano", "escrevente", "atendente", "pessoa real", "falar com")):
        return "humano"
    if any(w in t for w in ("protocolo", "andamento", "status do", "consulta protocolo")):
        return "protocolo"
    if any(w in t for w in ("agendar", "marcar", "horario", "horário", "visita", "comparecer")):
        return "agendar"
    if any(
        w in t
        for w in (
            "quanto custa",
            "valor",
            "preco",
            "preço",
            "emolumento",
            "custa",
            "servicos",
            "serviços",
            "o que voces fazem",
            "o que vocês fazem",
        )
    ):
        return "preco"
    if any(w in t for w in ("endereco", "endereço", "onde fica", "localizacao", "localização")):
        return "endereco"
    if any(
        w in t
        for w in ("horario de funcionamento", "funciona", "abre", "fecha", "sabado", "sábado")
    ):
        return "horario"
    if any(
        w in t
        for w in (
            "memoria",
            "memória",
            "esqueceu",
            "perdeu a memoria",
            "perdeu a memória",
            "historico",
            "histórico",
        )
    ):
        return "memoria"
    if any(w in t for w in ("oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "hey")):
        return "saudacao"
    return "livre"


def _build_tools_context(text: str) -> tuple[str, list[str]]:
    """Roda tools locais e monta contexto factual para o LLM."""
    used: list[str] = []
    parts: list[str] = []
    intent = _detect_intent(text)
    used.append(f"intent:{intent}")

    # Catalogo sempre disponivel
    cat_lines = [f"- {k}: {n} — {v}" for k, (n, v) in SERVICOS_CATALOGO.items()]
    parts.append("CATALOGO_SERVICOS_BOT:\n" + "\n".join(cat_lines))
    parts.append(
        "INFO_CARTORIO:\n"
        f"- nome: {CARTORIO_INFO['nome']}\n"
        f"- endereco: {CARTORIO_INFO['endereco']}\n"
        f"- horario: {CARTORIO_INFO['horario']}"
    )

    svc = _match_servico(text)
    if svc:
        nome, valor = SERVICOS_CATALOGO[svc]
        parts.append(f"SERVICO_DETECTADO: {svc} | {nome} | {valor}")
        used.append(f"servico:{svc}")

    if intent == "preco" and not svc:
        parts.append(
            "PRECO: cliente perguntou valor sem especificar servico. "
            "Liste os 5 servicos do catalogo e peca qual deseja."
        )
        used.append("preco:list")

    if intent == "endereco":
        parts.append(f"ENDERECO_OFICIAL: {CARTORIO_INFO['endereco']}")
        used.append("endereco")

    if intent == "horario":
        parts.append(f"HORARIO_OFICIAL: {CARTORIO_INFO['horario']} (sem sabado comercial regular)")
        used.append("horario")

    # Protocolo number in text?
    m = re.search(r"\b(20\d{2}-\d{4,6})\b", text)
    if m:
        parts.append(
            f"PROTOCOLO_MENCIONADO: {m.group(1)} — diga que pode confirmar o status "
            "se o cliente usar /protocolo ou digitar o numero apos o comando."
        )
        used.append(f"protocolo:{m.group(1)}")

    return "\n\n".join(parts), used


def _strip_think_tags(text: str) -> str:
    """Remove blocos <think>/<reasoning> do MiniMax XMax Thinking."""
    if not text:
        return text
    cleaned = re.sub(
        r"<think>[\s\S]*?(?:</think>|$)",
        "",
        text,
        flags=re.I,
    )
    cleaned = re.sub(
        r"<reasoning>[\s\S]*?(?:</reasoning>|$)",
        "",
        cleaned,
        flags=re.I,
    )
    return cleaned.strip()


# Tools OpenAI-compatible (MiniMax-M3 tool use / agentic)
AGENT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "listar_servicos_precos",
            "description": "Lista servicos oficiais e precos de referencia do bot cartorio.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_preco_servico",
            "description": "Preco oficial de um servico do catalogo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "servico": {
                        "type": "string",
                        "description": "Nome ou chave do servico",
                    }
                },
                "required": ["servico"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "info_cartorio",
            "description": "Endereco e horario oficiais do cartorio.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "iniciar_fluxo",
            "description": "DEPRECATED 2026-07-12. Use acao estruturada [[ACTION:humano]] no lugar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fluxo": {
                        "type": "string",
                        "enum": ["agendar", "protocolo", "humano", "menu"],
                    }
                },
                "required": ["fluxo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_protocolo_real",
            "description": (
                "Consulta status real de um protocolo cartorio via API (Supabase/cartorio-api). "
                "Use quando o cliente informar numero AAAA-NNNNNN. "
                "Se API offline, retorna offline:true e instrui humano."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "numero": {
                        "type": "string",
                        "description": "Numero do protocolo no formato AAAA-NNNNNN (ex: 2026-000123)",
                    }
                },
                "required": ["numero"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "criar_agendamento_real",
            "description": (
                "Prepara um rascunho de agendamento para confirmacao humana. "
                "Use quando cliente informou servico, data e hora; nunca cria um "
                "agendamento real nem aciona o workflow sem um atendente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "servico": {
                        "type": "string",
                        "description": "Chave do servico (autenticacao, procuracao, etc)",
                    },
                    "data": {"type": "string", "description": "Data DD/MM/AAAA"},
                    "hora": {"type": "string", "description": "Hora HH:MM"},
                    "nome": {
                        "type": "string",
                        "description": "Nome do cliente (opcional, p/ pre-qualificacao)",
                    },
                },
                "required": ["servico", "data", "hora"],
            },
        },
    },
]


CARTORIO_API_BASE = os.environ.get("CARTORIO_API_BASE", "http://127.0.0.1:8000").rstrip("/")


async def _run_remote_tool(
    name: str, args: dict[str, Any]
) -> tuple[str, str | None, list[str]] | None:
    """FIX 2026-07-12: tools que batem em API/MCP real. Retorna None se nao for remote."""
    used = [f"tool_remote:{name}"]
    if name == "consultar_protocolo_real":
        numero = str(args.get("numero", "")).strip()
        if not re.match(r"^20\d{2}-\d{4,6}$", numero):
            return (
                json.dumps(
                    {"erro": "formato_invalido", "esperado": "AAAA-NNNNNN"}, ensure_ascii=False
                ),
                None,
                used,
            )
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
                r = await client.get(f"{CARTORIO_API_BASE}/api/v1/protocolo/{numero}")
                if r.status_code == 200:
                    # Tool output becomes LLM context; scrub before crossing
                    # the provider boundary even when the API contract changes.
                    safe_data = scrub(json.dumps(r.json(), ensure_ascii=False)).text
                    return safe_data, None, used
                if r.status_code == 404:
                    return (
                        json.dumps(
                            {"offline": False, "status": "nao_encontrado", "numero": numero},
                            ensure_ascii=False,
                        ),
                        None,
                        used,
                    )
                return (
                    json.dumps(
                        {"offline": True, "status": r.status_code, "hint": "API cartorio offline"},
                        ensure_ascii=False,
                    ),
                    None,
                    used,
                )
        except Exception:
            logger.warning("cartorio_agent consultar_protocolo_real unavailable")
            return (
                json.dumps(
                    {
                        "offline": True,
                        "erro": "indisponivel",
                        "hint": "cartorio-api offline, encaminhe a humano",
                    },
                    ensure_ascii=False,
                ),
                None,
                used,
            )

    if name == "criar_agendamento_real":
        servico = str(args.get("servico", ""))
        data = str(args.get("data", ""))
        hora = str(args.get("hora", ""))
        # HITL: modelo nunca cria um agendamento real. A confirmacao de um
        # atendente dispara o workflow com idempotencia fora desta tool.
        return (
            json.dumps(
                {
                    "status": "draft_requires_human_confirmation",
                    "servico": scrub(servico).text,
                    "data": data,
                    "hora": hora,
                    "hint": "encaminhar para atendente confirmar antes de agendar",
                },
                ensure_ascii=False,
            ),
            "humano",
            used,
        )

    return None


def _run_local_tool(name: str, args: dict[str, Any]) -> tuple[str, str | None, list[str]]:
    used = [f"tool:{name}"]
    if name == "listar_servicos_precos":
        items = [{"id": k, "nome": n, "valor": v} for k, (n, v) in SERVICOS_CATALOGO.items()]
        return json.dumps({"servicos": items}, ensure_ascii=False), None, used
    if name == "consultar_preco_servico":
        raw = str(args.get("servico", ""))
        key = _match_servico(raw)
        if not key and raw in SERVICOS_CATALOGO:
            key = raw
        if not key or key not in SERVICOS_CATALOGO:
            return (
                json.dumps(
                    {"erro": "servico_nao_encontrado", "opcoes": list(SERVICOS_CATALOGO.keys())},
                    ensure_ascii=False,
                ),
                None,
                used,
            )
        nome, valor = SERVICOS_CATALOGO[key]
        return (
            json.dumps({"id": key, "nome": nome, "valor": valor}, ensure_ascii=False),
            None,
            used,
        )
    if name == "info_cartorio":
        return json.dumps(CARTORIO_INFO, ensure_ascii=False), None, used
    if name == "iniciar_fluxo":
        fluxo = str(args.get("fluxo", "")).lower()
        # menu removido 2026-07-12 (no buttons)
        if fluxo in ("agendar", "protocolo", "humano"):
            return json.dumps({"ok": True, "fluxo": fluxo}), fluxo, used
        return json.dumps({"erro": "fluxo_invalido_ou_descontinuado"}), None, used
    return json.dumps({"erro": "tool_desconhecida"}), None, used


async def _circuit_skip(provider: str) -> bool:
    """True se o circuito do provider esta OPEN (pular slot).

    Reusa o CB Redis de ``app.integrations.fallback`` (threshold 3 / TTL 300s).
    Fail-open se Redis offline — nao bloquear atendimento por dependencia.
    """
    from app.integrations.fallback import _is_circuit_open
    from app.services.metrics import store

    try:
        open_ = await _is_circuit_open(provider)
    except Exception as exc:  # noqa: BLE001 — CB nunca derruba o agent
        logger.warning("cartorio_agent CB check fail-open %s: %s", provider, exc)
        return False
    if open_:
        store.inc_llm_calls_total(provider, "chat", "circuit_open")
        store.inc_llm_errors_total(provider, "chat", "CIRCUIT_OPEN")
        logger.info("cartorio_agent skip provider=%s circuit=open", provider)
    return open_


async def _circuit_success(provider: str) -> None:
    from app.integrations.fallback import _record_success

    try:
        await _record_success(provider)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cartorio_agent CB success record fail %s: %s", provider, exc)


async def _circuit_failure(provider: str) -> None:
    from app.integrations.fallback import _record_failure

    try:
        await _record_failure(provider, threshold=3, open_time_seconds=300)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cartorio_agent CB failure record fail %s: %s", provider, exc)


async def _chat_completion(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> tuple[dict[str, Any] | None, str, str]:
    """Chamada multi-provider com ordem deterministica + circuit breaker.

    Ordem: MiniMax_direct → litellm → opencode_free_1/2/3.
    Slot com circuito OPEN e pulado; falha registra CB; sucesso reseta CB.
    """
    import time

    from app.services.metrics import _classify_error, store

    last_err = ""
    provider_rate_limited = False
    payload_min: dict[str, Any] = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    payload_rich: dict[str, Any] = {**payload_min, "thinking": {"type": "adaptive"}}
    if tools:
        payload_rich["tools"] = tools
        payload_rich["tool_choice"] = "auto"

    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
        if MINIMAX_API_KEY and not await _circuit_skip("MiniMax_direct"):
            base = MINIMAX_BASE_URL
            url = (
                base
                if base.endswith("/chat/completions")
                else f"{base}/chat/completions"
                if base.endswith("/v1")
                else f"{base.rstrip('/')}/v1/chat/completions"
            )
            start_t = time.perf_counter()
            try:
                r = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {MINIMAX_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={**payload_rich, "model": MINIMAX_MODEL},
                )
                elapsed = time.perf_counter() - start_t
                store.observe_llm_call_seconds("MiniMax_direct", "chat", elapsed)
                if r.status_code == 200:
                    store.inc_llm_calls_total("MiniMax_direct", "chat", "success")
                    await _circuit_success("MiniMax_direct")
                    data = r.json()
                    msg = data.get("choices", [{}])[0].get("message") or {}
                    return msg, f"minimax_direct:{MINIMAX_MODEL}", ""
                status = "rate_limited" if r.status_code == 429 else "error"
                provider_rate_limited = provider_rate_limited or status == "rate_limited"
                store.inc_llm_calls_total("MiniMax_direct", "chat", status)
                store.inc_llm_errors_total(
                    "MiniMax_direct", "chat", "HTTP_4XX" if r.status_code < 500 else "HTTP_5XX"
                )
                await _circuit_failure("MiniMax_direct")
                last_err = f"minimax HTTP {r.status_code} {r.text[:160]}"
            except Exception as exc:
                elapsed = time.perf_counter() - start_t
                store.observe_llm_call_seconds("MiniMax_direct", "chat", elapsed)
                store.inc_llm_calls_total("MiniMax_direct", "chat", "error")
                store.inc_llm_errors_total("MiniMax_direct", "chat", _classify_error(exc))
                await _circuit_failure("MiniMax_direct")
                last_err = f"minimax {type(exc).__name__}: {exc}"
                logger.warning("cartorio_agent minimax_direct fail: %s", last_err)

        if LITELLM_KEY and not await _circuit_skip("litellm"):
            headers = {"Authorization": f"Bearer {LITELLM_KEY}", "Content-Type": "application/json"}
            for base in LITELLM_URLS:
                if not base:
                    continue
                url = f"{base.rstrip('/')}/v1/chat/completions"
                start_t = time.perf_counter()
                try:
                    r = await client.post(
                        url,
                        headers=headers,
                        json={**payload_min, "model": LITELLM_MODEL or MINIMAX_MODEL},
                    )
                    elapsed = time.perf_counter() - start_t
                    store.observe_llm_call_seconds("litellm", "chat", elapsed)
                    if r.status_code != 200:
                        status = "rate_limited" if r.status_code == 429 else "error"
                        provider_rate_limited = provider_rate_limited or status == "rate_limited"
                        store.inc_llm_calls_total("litellm", "chat", status)
                        store.inc_llm_errors_total(
                            "litellm", "chat", "HTTP_4XX" if r.status_code < 500 else "HTTP_5XX"
                        )
                        await _circuit_failure("litellm")
                        last_err = f"{base} HTTP {r.status_code} {r.text[:120]}"
                        continue
                    store.inc_llm_calls_total("litellm", "chat", "success")
                    await _circuit_success("litellm")
                    data = r.json()
                    msg = data.get("choices", [{}])[0].get("message") or {}
                    return msg, f"litellm:{LITELLM_MODEL}", ""
                except Exception as exc:
                    elapsed = time.perf_counter() - start_t
                    store.observe_llm_call_seconds("litellm", "chat", elapsed)
                    store.inc_llm_calls_total("litellm", "chat", "error")
                    store.inc_llm_errors_total("litellm", "chat", _classify_error(exc))
                    await _circuit_failure("litellm")
                    last_err = f"{base} {type(exc).__name__}: {exc}"
                    logger.warning("cartorio_agent litellm fail: %s", last_err)

        for slot, (api_key, base, model) in enumerate(_opencode_free_configs(), start=1):
            if not api_key or not base or not model:
                continue
            provider_label = f"opencode_free_{slot}"
            if await _circuit_skip(provider_label):
                continue
            url = (
                base
                if base.endswith("/chat/completions")
                else f"{base.rstrip('/')}/chat/completions"
                if base.rstrip("/").endswith("/v1")
                else f"{base.rstrip('/')}/v1/chat/completions"
            )
            start_t = time.perf_counter()
            try:
                r = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={**payload_min, "model": model},
                )
                elapsed = time.perf_counter() - start_t
                store.observe_llm_call_seconds(provider_label, "chat", elapsed)
                if r.status_code != 200:
                    status = "rate_limited" if r.status_code == 429 else "error"
                    provider_rate_limited = provider_rate_limited or status == "rate_limited"
                    store.inc_llm_calls_total(provider_label, "chat", status)
                    store.inc_llm_errors_total(
                        provider_label, "chat", "HTTP_4XX" if r.status_code < 500 else "HTTP_5XX"
                    )
                    await _circuit_failure(provider_label)
                    last_err = f"{provider_label} HTTP {r.status_code}"
                    continue
                store.inc_llm_calls_total(provider_label, "chat", "success")
                await _circuit_success(provider_label)
                data = r.json()
                msg = data.get("choices", [{}])[0].get("message") or {}
                return msg, f"{provider_label}:{model}", ""
            except Exception as exc:
                elapsed = time.perf_counter() - start_t
                store.observe_llm_call_seconds(provider_label, "chat", elapsed)
                store.inc_llm_calls_total(provider_label, "chat", "error")
                store.inc_llm_errors_total(provider_label, "chat", _classify_error(exc))
                await _circuit_failure(provider_label)
                last_err = f"{provider_label} {type(exc).__name__}"
                logger.warning("cartorio_agent %s fail: %s", provider_label, last_err)

    if provider_rate_limited:
        store.inc_llm_degraded_total("provider_rate_limited")
        return {"content": _PROVIDER_RATE_LIMIT_REPLY}, "offline:provider_rate_limited", ""
    return None, "none", last_err


async def _llm_minimax(system: str, user: str) -> tuple[str, str]:
    """Chat simples sem tools."""
    msg, provider, err = await _chat_completion(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        tools=None,
    )
    if not msg:
        logger.warning("cartorio_agent: MiniMax offline — fallback local. err=%s", err)
        return "", "none"
    return _strip_think_tags((msg.get("content") or "").strip()), provider


async def _llm_agent_with_tools(system: str, user: str) -> tuple[str, str, str | None, list[str]]:
    """Loop agentico MiniMax-M3 com tools (docs platform.minimax.io tool use)."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    tools_used: list[str] = []
    action: str | None = None
    provider = "none"

    for _ in range(3):
        msg, provider, err = await _chat_completion(
            messages, tools=AGENT_TOOLS, temperature=0.7, max_tokens=4096
        )
        if not msg:
            logger.warning("cartorio_agent tools fail: %s", err)
            return "", "none", action, tools_used

        tool_calls = msg.get("tool_calls") or []
        if tool_calls:
            messages.append(msg)
            for tc in tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name") or ""
                raw_args = fn.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                except Exception:
                    args = {}
                # FIX 2026-07-12: tenta tool remoto primeiro, depois local
                remote_result = await _run_remote_tool(name, args)
                if remote_result is not None:
                    result, act, used = remote_result
                else:
                    result, act, used = _run_local_tool(name, args)
                tools_used.extend(used)
                if act:
                    action = act
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id") or name,
                        "name": name,
                        "content": result,
                    }
                )
            continue

        text = _strip_think_tags((msg.get("content") or "").strip())
        return text, provider, action, tools_used

    return "", provider, action, tools_used


async def minimax_tts_mp3(text: str) -> bytes | None:
    """TTS MiniMax speech-2.6-turbo → MP3 bytes (Telegram sendVoice)."""
    if not MINIMAX_API_KEY or not text:
        return None
    snippet = text.strip()[:480]
    payload = {
        "model": "speech-2.6-turbo",
        "text": snippet,
        "stream": False,
        "language_boost": "Portuguese",
        "output_format": "hex",
        "voice_setting": {
            "voice_id": "Portuguese_CaptivatingStoryteller",
            "speed": 1.0,
            "vol": 1.0,
            "pitch": 0,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            r = await client.post(
                "https://api.minimax.io/v1/t2a_v2",
                headers={
                    "Authorization": f"Bearer {MINIMAX_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if r.status_code != 200:
                logger.warning("minimax_tts HTTP %s %.160s", r.status_code, r.text)
                return None
            data = r.json()
            hex_audio = (data.get("data") or {}).get("audio") or ""
            if not hex_audio:
                return None
            return bytes.fromhex(hex_audio)
    except Exception as exc:
        logger.warning("minimax_tts fail: %s", exc)
        return None


def _parse_action(text: str) -> tuple[str, str | None]:
    action = None
    m = re.search(r"\[\[ACTION:(agendar|protocolo|humano|menu)\]\]", text, re.I)
    if m:
        action = m.group(1).lower()
    # Strip SEMPRE qualquer tag ACTION (dentro ou fora da whitelist): markup
    # interno nunca vaza pro usuario — injection com action invalida vira
    # texto limpo + action=None (G9.S3 security).
    text = re.sub(r"\s*\[\[ACTION:[^\]]+\]\]\s*", "\n", text).strip()
    return text, action


def _keyboard_for_action(action: str | None, intent: str) -> list[list[dict[str, str]]] | None:
    """FIX 2026-07-12 (Gustavo directive): SEM botoes inline. Sempre None.

    Cliente prefere texto puro + conversa autonoma. Botoes removidos.
    Agendar/protocolo/humano: instrucoes em texto livre.
    """
    return None


def _is_clarification(text: str) -> bool:
    t = (text or "").lower().strip()
    keys = (
        "como assim",
        "tipo como",
        "tipo o que",
        "o que quer dizer",
        "nao entendi",
        "não entendi",
        "explica",
        "explique",
        "pode explicar",
        "??",
        "como?",
        "que isso",
        "huh",
        "hm",
        "hein",
    )
    if t in ("?", "??", "???"):
        return True
    return any(k in t for k in keys)


def _is_smalltalk(text: str) -> bool:
    t = (text or "").lower().strip()
    # remove pontuacao leve
    t = re.sub(r"[!?.,]+$", "", t).strip()
    exact = {
        "tudo bem",
        "tudo bom",
        "td bem",
        "blz",
        "beleza",
        "e ai",
        "e aí",
        "suave",
        "valeu",
        "obrigado",
        "obrigada",
        "obg",
        "thanks",
        "ok",
        "certo",
        "entendi",
        "show",
        "top",
        "bom dia",
        "boa tarde",
        "boa noite",
    }
    if t in exact:
        return True
    if t.startswith("tudo bem") or t.startswith("tudo bom"):
        return True
    return False


def _is_tone_complaint(text: str) -> bool:
    t = (text or "").lower()
    return any(
        k in t
        for k in (
            "grosso",
            "grosa",
            "rude",
            "robot",
            "robô",
            "automatico",
            "automático",
            "chato",
            "lixo",
            "merda",
            "pessimo",
            "péssimo",
            "ruim",
            "nao ajuda",
            "não ajuda",
        )
    )


def _last_bot_from_history(history: list[str] | None) -> str:
    if not history:
        return ""
    for h in reversed(history):
        if h.lower().startswith("bot:"):
            return h[4:].strip()
    return ""


def _offline_reply(
    text: str,
    intent: str,
    tools_used: list[str],
    *,
    history: list[str] | None = None,
    degraded: bool = False,
) -> AgentReply:
    """Resposta deterministica; SEMPRE scrub PII na saida (G9.S3.T8/T10)."""
    reply = _offline_reply_inner(text, intent, tools_used, history=history)
    if degraded:
        reply.text = (
            "Nosso sistema de inteligência artificial está com lentidão neste momento. "
            "Vou tentar te ajudar com o básico:\n\n" + reply.text
        )
    # 3a camada: output scrub — degraded/fallback nunca vazam PII
    reply.text = scrub(reply.text).text
    return reply


def _offline_reply_inner(
    text: str,
    intent: str,
    tools_used: list[str],
    *,
    history: list[str] | None = None,
) -> AgentReply:
    """Resposta deterministica se LLM cair — ainda e util, nao muda pra FSM cego.

    FIX 2026-07-10: NUNCA repetir o cartao de boas-vindas em loop.
    Saudacao curta 1x; follow-ups e "como assim?" usam historico.
    """
    if intent == "catalogo_serie":
        series = _build_catalog_series()
        tools_used = list(tools_used) + ["catalogo:serie"]
        return AgentReply(
            text=series[0],
            extra_messages=series[1:],
            keyboard=None,
            tools_used=tools_used,
            provider="offline:catalogo_serie",
        )
    if intent == "dados":
        return AgentReply(
            text=(
                "Recebi seus dados para pre-qualificacao.\n"
                "\n"
                "LGPD (Lei 13.709/2018)\n"
                "- Finalidade: atendimento do 2o Oficio de Notas de Uberlandia/MG\n"
                "- Transito com criptografia (HTTPS/TLS)\n"
                "- CPF/RG ficam com hash no servidor; nao reenviamos em claro\n"
                "- Ato notarial so com validacao humana (HITL)\n"
                "\n"
                "Proximo passo\n"
                "Informe o servico desejado (ex.: autenticacao, procuracao)\n"
                "ou digite /humano para falar com o escrevente.\n"
                "\n"
                "Direitos LGPD: dpo@2notasudi.com.br ou /lgpd"
            ),
            keyboard=None,
            tools_used=list(tools_used) + ["dados:lgpd_ack"],
            provider="offline:dados",
        )
    if intent == "memoria":
        return AgentReply(
            text=(
                "A memoria desta conversa esta ativa.\n"
                "\n"
                "Guardamos o historico recente neste chat (Redis) e o perfil "
                "do seu Telegram (id, username e dados de pre-qualificacao com hash).\n"
                "\n"
                "Pode retomar de onde paramos: diga o servico, peca valores, "
                "agendar, protocolo ou /humano."
            ),
            keyboard=None,
            tools_used=list(tools_used) + ["memoria"],
            provider="offline",
        )
    # Reclamacao de tom
    if _is_tone_complaint(text):
        return AgentReply(
            text=(
                "Desculpa se soou automatico ou seco — nao e a intencao.\n"
                "\n"
                "Estou aqui pra te ajudar de verdade no cartorio.\n"
                "Me conta com suas palavras o que voce precisa "
                "(valor, agendar, protocolo ou falar com escrevente)."
            ),
            keyboard=None,
            tools_used=list(tools_used) + ["tom:desculpa"],
            provider="offline:tom",
        )
    # Small talk curto
    if _is_smalltalk(text):
        return AgentReply(
            text=(
                "Tudo bem sim, obrigado por perguntar.\n\nEm que posso te ajudar no cartorio agora?"
            ),
            keyboard=None,
            tools_used=list(tools_used) + ["smalltalk"],
            provider="offline:smalltalk",
        )
    # Saudacao: CURTA. Nunca despejar o menu completo de novo se ja houve conversa.
    if intent == "saudacao":
        if history and any(h.lower().startswith("bot:") for h in history):
            return AgentReply(
                text="Oi. Em que posso te ajudar agora?",
                keyboard=None,
                tools_used=list(tools_used) + ["saudacao:curta"],
                provider="offline:saudacao",
            )
        return AgentReply(
            text=(
                f"Ola. Sou o Agent AI do {CARTORIO_INFO['nome']}.\n"
                "\n"
                "Pode falar em texto livre — valores, agendamento, protocolo "
                "ou /humano para escrevente.\n"
                "\n"
                "O que voce precisa?"
            ),
            keyboard=None,
            tools_used=list(tools_used) + ["saudacao:welcome"],
            provider="offline:saudacao",
        )
    # Esclarecimento — curto, sem dump de catalogo
    if _is_clarification(text):
        return AgentReply(
            text=(
                "Claro. Em resumo, eu ajudo com:\n"
                "\n"
                "- valor de servicos (ex.: quanto custa autenticacao)\n"
                "- agendar atendimento\n"
                "- consultar protocolo\n"
                "- encaminhar para escrevente (/humano)\n"
                "\n"
                "Me diga o que voce quer fazer, com suas palavras."
            ),
            keyboard=None,
            tools_used=list(tools_used) + ["livre:clarificacao"],
            provider="offline:clarificacao",
        )
    # livre generico com historico: NAO despejar menu/catalogo
    if intent == "livre" and history and any(h.lower().startswith("bot:") for h in history):
        svc = _match_servico(text)
        if svc:
            nome, valor = SERVICOS_CATALOGO[svc]
            return AgentReply(
                text=(
                    f"Sobre {nome}: valor de referencia {valor}.\n"
                    "\n"
                    f"Se quiser agendar, digite: quero agendar {nome.lower()}\n"
                    "Se preferir pessoa: /humano"
                ),
                keyboard=None,
                tools_used=list(tools_used) + [f"livre:servico:{svc}"],
                provider="offline:livre",
            )
        return AgentReply(
            text=(
                "Pode me contar um pouco mais do que voce precisa?\n"
                "\n"
                "Por exemplo: autenticar um documento, reconhecimento de firma, "
                "procuracao, agendar horario ou consultar um protocolo."
            ),
            keyboard=None,
            tools_used=list(tools_used) + ["livre:pergunte"],
            provider="offline:livre",
        )
    svc = _match_servico(text)
    if intent == "preco" and svc:
        nome, valor = SERVICOS_CATALOGO[svc]
        return AgentReply(
            text=(
                f"Sobre {nome}:\n"
                "\n"
                f"Valor de referencia: {valor}\n"
                "(tabela operacional do bot / referencia MG)\n"
                "\n"
                "Para agendar, digite por exemplo:\n"
                f"quero agendar {nome.lower()}"
            ),
            keyboard=None,
            action=None,
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "preco":
        lines = [f"- {n}: {v}" for _, (n, v) in SERVICOS_CATALOGO.items()]
        return AgentReply(
            text=(
                "Valores de referencia que posso informar agora:\n"
                "\n" + "\n".join(lines) + "\n\n"
                "Qual servico te interessa? Digite o nome (nao precisa de menu)."
            ),
            keyboard=None,
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "endereco":
        return AgentReply(
            text=(f"Endereco\n{CARTORIO_INFO['endereco']}\n\nHorario\n{CARTORIO_INFO['horario']}"),
            keyboard=None,
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "horario":
        return AgentReply(
            text=(f"Horario de funcionamento\n\n{CARTORIO_INFO['horario']}"),
            keyboard=None,
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "agendar":
        return AgentReply(
            text=(
                "Posso ajudar a agendar.\n"
                "\n"
                "Qual servico voce precisa?\n"
                "\n"
                "Digite o nome ou escolha um atalho na lista, se preferir."
            ),
            keyboard=_servicos_kb(),
            action="agendar",
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "protocolo":
        return AgentReply(
            text=("Consulta de protocolo\n\nMe informe o numero no formato:\n2026-000123"),
            action="protocolo",
            keyboard=None,
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "humano":
        return AgentReply(
            text=(
                "Vou encaminhar para atendimento humano (escrevente / HITL).\n"
                "\n"
                "Descreva em poucas linhas o que voce precisa.\n"
                "\n"
                "Se for enviar CPF, RG ou documentos para pre-qualificacao, "
                "pode enviar. O tratamento segue a LGPD; o ato oficial "
                "sempre passa por validacao humana."
            ),
            action="humano",
            keyboard=None,
            tools_used=tools_used,
            provider="offline",
        )
    # Fallback final: welcome SO se nao houver historico de bot
    if history and any(h.lower().startswith("bot:") for h in history):
        return AgentReply(
            text=(
                "Pode detalhar o que precisa no cartorio?\n"
                "\n"
                "Exemplos curtos:\n"
                "- quanto custa autenticacao\n"
                "- quero agendar procuracao\n"
                "- protocolo 2026-000123\n"
                "- /humano"
            ),
            keyboard=None,
            tools_used=list(tools_used) + ["fallback:curto"],
            provider="offline:curto",
        )
    return AgentReply(
        text=(
            f"Ola. Sou o assistente do {CARTORIO_INFO['nome']}.\n"
            "\n"
            "Pode falar em texto livre. Exemplos:\n"
            "\n"
            "- quanto custa autenticacao\n"
            "- quero agendar procuracao\n"
            "- protocolo 2026-000123\n"
            "\n"
            "Atalhos: /menu · /humano · /lgpd"
        ),
        keyboard=None,
        tools_used=list(tools_used) + ["fallback:welcome"],
        provider="offline:welcome",
    )


# URLs permitidas no texto de saida do bot (qualquer outra e removida).
_URL_ALLOW = (
    "2notasudi.com.br",
    "t.me/test_cartorio_bot",
    "telegram.me/test_cartorio_bot",
)
_URL_RE = re.compile(r"(https?://[^\s<>\"']+|www\.[^\s<>\"']+)", re.I)
# Domínios/palavras que NUNCA podem sair no chat do cartorio
_TOXIC_HINTS = (
    "pornhub",
    "xvideos",
    "xnxx",
    "xhamster",
    "onlyfans",
    "redtube",
    "youporn",
    "spankbang",
    "chaturbate",
    "stripchat",
    "brazzers",
    "hentai",
    "xxx.",
    "/xxx",
    "nsfw",
    "adult-video",
    "porn",
    "sexcam",
    "camgirl",
)


def _url_allowed(url: str) -> bool:
    low = url.lower()
    return any(a in low for a in _URL_ALLOW)


def sanitize_bot_output(text: str) -> str:
    """Sanitiza saida do agent: zero URL toxica, zero spam, PII scrub, formatacao limpa.

    Se detectar conteudo adulto/spam, descarta o texto inteiro (caller usa offline).
    G9.S3.T10: PII nunca sai raw — scrub obrigatorio no fim.
    """
    if not text:
        return text
    low = text.lower()
    if any(h in low for h in _TOXIC_HINTS):
        logger.error("cartorio_agent BLOCKED toxic content in LLM output")
        return ""

    # Remove URLs nao permitidas (mantem so dominio oficial)
    def _repl(m: re.Match[str]) -> str:
        u = m.group(0)
        return u if _url_allowed(u) else ""

    cleaned = _URL_RE.sub(_repl, text)
    # Se ainda sobrou URL suspeita curta tipo bit.ly generico fora allow — remove
    cleaned = re.sub(r"\b(?:bit\.ly|t\.co|goo\.gl|tinyurl\.com)/\S+", "", cleaned, flags=re.I)
    # Limpa espacos deixados por remocao de URL
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return scrub(cleaned.strip()).text


def _scrub_bad_llm_phrases(text: str) -> str:
    """Remove alucinacoes tipicas de modelo free (stateless / prompt cortado / spam)."""
    if not text:
        return text
    text = sanitize_bot_output(text)
    if not text:
        return ""
    bad = (
        "stateless",
        "nao guardo o historico",
        "não guardo o histórico",
        "nao guardo historico",
        "prompt anterior foi cortado",
        "cole o restante das instrucoes",
        "cole o restante das instruções",
        "para eu assumir a persona",
        "sou um modelo de linguagem",
        "como ia generativa",
        "como uma ia",
    )
    low = text.lower()
    if any(b in low for b in bad):
        return ""
    return text


def _has_personal_data(text: str) -> bool:
    """Detecta CPF/RG/email no texto do cliente (pre-qualificacao cartorio).

    Inclui tokens pos-scrub (`[CPF]`, `[RG]`, marcador DADOS_PESSOAIS_RECEBIDOS)
    porque o webhook mascara PII ANTES de enfileirar no Redis.
    """
    if not text:
        return False
    low = text.lower()
    # Tokens pos-scrub do pii.scrub (ex.: [CPF_REDACTED], [EMAIL_REDACTED])
    if re.search(r"\[(cpf|rg|email|phone_br|cnh)_redacted\]", low):
        return True
    if "dados_pessoais_recebidos" in low:
        return True
    if re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", text):
        return True
    if re.search(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dXx]\b", text):
        return True
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        return True
    if re.search(r"\b(?:cpf|rg|documento|identidade)\b", text, re.I) and (
        re.search(r"\d{5,}", text) or "redacted" in low
    ):
        return True
    return False


async def run_cartorio_agent(
    text: str,
    *,
    history: list[str] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    chat_id: int | str | None = None,
) -> AgentReply:
    """Entrada principal do Agent AI Cartorio.

    FIX 2026-07-12: aceita attachments (foto/doc/video/audio) e chat_id
    para acoes reais (HITL Chatwoot, WebSocket realtime).

    FIX 2026-07-10: history multi-turn obrigatorio; catalogo consolidado
    em 1 mensagem (sem flood).
    """
    raw = (text or "").strip()
    if not raw and not attachments:
        return AgentReply(
            text="Pode me contar o que voce precisa ou enviar uma foto/doc?", keyboard=None
        )

    # Intent em texto RAW (antes do scrub) — CPF/RG devem ser detectados
    intent_raw = _detect_intent(raw)
    scrubbed = scrub(raw).text
    intent = intent_raw if intent_raw == "dados" else _detect_intent(scrubbed)
    tools_ctx, tools_used = _build_tools_context(scrubbed)
    system = AGENT_SYSTEM.format(tools_context=tools_ctx)

    # Hard offline: apenas catalogo extenso em serie quando pedido explicitamente
    hard_offline = ("catalogo_serie",)
    if intent in hard_offline:
        return _offline_reply(scrubbed, intent, tools_used, history=history)

    user_block = scrubbed
    if history:
        hist = "\n".join(f"- {scrub(str(h)).text}" for h in history[-12:])
        user_block = (
            "Historico recente desta conversa (USE isto; voce tem memoria):\n"
            f"{hist}\n\nMensagem atual do cliente: {scrubbed}"
        )
    # FIX 2026-07-12: contexto de midia recebida (foto/doc/video/audio)
    if attachments:
        att_lines = []
        for a in attachments:
            kind = a.get("type", "?")
            name = scrub(str(a.get("file_name") or a.get("file_id", "?"))).text
            mime = a.get("mime_type", "?")
            size = a.get("file_size", "?")
            caption = scrub(str(a.get("caption", ""))).text
            att_lines.append(
                f"- {kind}: {name} | mime={mime} | size={size}"
                + (f" | caption={caption}" if caption else "")
            )
        user_block = (
            (user_block + "\n\n" if user_block else "")
            + "Anexos recebidos nesta mensagem:\n"
            + "\n".join(att_lines)
            + "\n\n(Trate como pre-qualificacao cartorio; confirme recebimento; LGPD)."
        )

    async def _run_llm_with_fallback() -> tuple[str, str, str | None, list[str]]:
        """Run tools and simple fallbacks under one caller-enforced time budget."""
        content, provider, tool_action, tool_used = await _llm_agent_with_tools(system, user_block)
        if content:
            return content, provider, tool_action, tool_used

        fallback_content, fallback_provider = await _llm_minimax(system, user_block)
        return fallback_content, fallback_provider, tool_action, tool_used

    # Agent AI com TOOLS (MiniMax-M3) — precos via tool, nao inventados.
    # Teto global cobre ferramentas E fallback simples: provider travado cai no
    # offline reply em ~LLM_GLOBAL_TIMEOUT_S, sem uma segunda espera completa.
    try:
        content, provider, tool_action, tool_used = await asyncio.wait_for(
            _run_llm_with_fallback(),
            timeout=LLM_GLOBAL_TIMEOUT_S,
        )
    except TimeoutError:
        from app.services.metrics import store

        # E2.02 S3: timeout canonico + degraded counter (alerta via rate()).
        store.inc_llm_calls_total("multi_provider", "chat", "timeout")
        store.inc_llm_degraded_total("timeout")
        logger.warning(
            "cartorio_agent: LLM timeout global (%.0fs) — offline reply",
            LLM_GLOBAL_TIMEOUT_S,
        )
        return _offline_reply(scrubbed, intent, tools_used, history=history, degraded=True)
    tools_used = list(tools_used) + list(tool_used)

    if not content:
        from app.services.metrics import store

        # E2.02 S3: todos os providers falharam — degraded reply observavel.
        store.inc_llm_degraded_total("all_providers_down")
        return _offline_reply(scrubbed, intent, tools_used, history=history, degraded=True)

    clean, action = _parse_action(content)
    if tool_action and not action:
        action = tool_action
    clean = re.sub(
        "[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff]",
        "",
        clean,
    ).strip()
    clean = _scrub_bad_llm_phrases(clean)
    clean = scrub(clean).text
    if not clean:
        return _offline_reply(scrubbed, intent, tools_used, history=history)

    if action is None and intent in ("agendar", "protocolo", "humano"):
        action = intent

    kb = _keyboard_for_action(action, intent)  # FIX 2026-07-12: sempre None (no-buttons)
    if len(clean) > 3200:
        clean = clean[:3200] + "\n\n..."

    return AgentReply(
        text=clean,
        keyboard=kb,
        action=action,
        tools_used=tools_used,
        provider=provider,
    )


__all__ = [
    "AgentReply",
    "run_cartorio_agent",
    "SERVICOS_CATALOGO",
    "sanitize_bot_output",
    "minimax_tts_mp3",
    "AGENT_TOOLS",
]
