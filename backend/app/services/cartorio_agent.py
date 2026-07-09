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

import logging
import os
import re
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.services.pii import scrub

logger = logging.getLogger(__name__)

# Catalogo espelhado do telegram FSM (fonte unica operacional bot)
SERVICOS_CATALOGO: dict[str, tuple[str, str]] = {
    "reconhecimento_firma": ("Reconhecimento de Firma", "R$ 8,50"),
    "autenticacao": ("Autenticacao de Documento", "R$ 6,80"),
    "procuracao": ("Procuracao", "R$ 95,20"),
    "testamento": ("Testamento", "R$ 320,00"),
    "ata_notarial": ("Ata Notarial", "R$ 480,00"),
}

CARTORIO_INFO = {
    "nome": "2o Oficio de Notas de Uberlandia / MG",
    "endereco": "Av. Paulo Gracindo, 150 - Centro, Uberlandia/MG",
    "horario": "Segunda a sexta, 09h as 17h",
    "telefone_humano": "use /humano para falar com escrevente",
}

# LiteLLM MiniMax no coding-vps (alcancavel do container cartorio_api via rede easypanel)
LITELLM_URLS = [
    os.environ.get(
        "CARTORIO_AGENT_LITELLM_URL",
        "http://coding-vps_apenas_para_auxilio_litellm-app:4000",
    ),
    settings.litellm_base_url,
]
LITELLM_MODEL = os.environ.get("CARTORIO_AGENT_MODEL", settings.litellm_model)

AGENT_SYSTEM = """Voce e o Agent AI oficial do Cartorio 2o Oficio de Notas de Uberlandia/MG.

IDENTIDADE
- Assistente virtual do cartorio (nao e tabeliao). Apoia, informa, agenda e pre-qualifica.
- PT-BR, tom cordial mineiro, direto. SEM emojis. SEM enrolacao.
- Max 4 frases curtas por resposta, a menos que o cliente peca detalhe.

REGRAS CRITICAS (NUNCA VIOLAR)
1. NUNCA invente valores de emolumento. Use APENAS o bloco FERRAMENTAS/CATALOGO abaixo.
2. NUNCA de conselho juridico definitivo (testamento, usucapiao, inventário, validade de doc).
   Nessas duvidas: diga que vai acionar um escrevente humano (/humano).
3. NUNCA peca CPF/RG/telefone completo no chat. Se o cliente enviar PII, oriente /humano.
4. Voce NAO emite certidao/escritura sozinho. HITL humano e obrigatorio para atos.
5. Se o cliente quiser agendar: confirme servico e diga que pode usar o botao ou digitar
   "quero agendar [servico] para [data] as [hora]".
6. Se o cliente quiser consultar protocolo: peca o numero no formato AAAA-NNNNNN.

FERRAMENTAS JA EXECUTADAS (use estes fatos; nao chute)
{tools_context}

ACOES ESTRUTURADAS (opcional, 1 linha no FINAL se aplicavel)
Se a intencao for clara, acrescente no FINAL da resposta EXATAMENTE uma linha:
[[ACTION:agendar]] ou [[ACTION:protocolo]] ou [[ACTION:humano]] ou [[ACTION:menu]]
Nao explique a linha ACTION. Se nao houver acao, nao inclua.

BOTOES / TOOLS (estilo MCP)
NAO force menu de botoes. Responda em texto.
So sugira botoes quando for estritamente util (ex: escolher 1 de 5 servicos).
Nunca diga "Falar com Escrevente". Use "atendimento humano" ou "escrevente (HITL)".
"""


@dataclass
class AgentReply:
    text: str
    keyboard: list[list[dict[str, str]]] | None = None
    action: str | None = None  # agendar|protocolo|humano|menu
    tools_used: list[str] = field(default_factory=list)
    provider: str = "none"


def _menu_kb() -> list[list[dict[str, str]]]:
    """Atalhos globais — so quando o usuario pede menu/atalhos explicitamente."""
    return [
        [{"text": "Agendar no cartorio", "callback_data": "cmd:agendar"}],
        [{"text": "Consultar protocolo", "callback_data": "cmd:protocolo"}],
        [{"text": "Atendimento humano (HITL)", "callback_data": "cmd:humano"}],
    ]


def _servicos_kb() -> list[list[dict[str, str]]]:
    """Tool keyboard: so na escolha de servico (necessario)."""
    kb: list[list[dict[str, str]]] = []
    for i, (key, (nome, _)) in enumerate(SERVICOS_CATALOGO.items(), 1):
        kb.append([{"text": f"{i}. {nome}", "callback_data": f"servico:{key}"}])
    kb.append([{"text": "Cancelar", "callback_data": "cmd:menu"}])
    return kb


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


def _detect_intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("humano", "escrevente", "atendente", "pessoa real", "falar com")):
        return "humano"
    if any(w in t for w in ("protocolo", "andamento", "status do", "consulta protocolo")):
        return "protocolo"
    if any(w in t for w in ("agendar", "marcar", "horario", "horário", "visita", "comparecer")):
        return "agendar"
    if any(w in t for w in ("quanto custa", "valor", "preco", "preço", "emolumento", "custa")):
        return "preco"
    if any(w in t for w in ("endereco", "endereço", "onde fica", "localizacao", "localização")):
        return "endereco"
    if any(
        w in t
        for w in ("horario de funcionamento", "funciona", "abre", "fecha", "sabado", "sábado")
    ):
        return "horario"
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


async def _llm_minimax(system: str, user: str) -> tuple[str, str]:
    """Chama MiniMax-M3 via LiteLLM. Retorna (texto, provider_tag)."""
    payload = {
        "model": LITELLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 450,
        "temperature": 0.35,
    }

    litellm_key = settings.litellm_api_key or os.environ.get("LITELLM_API_KEY")
    if not litellm_key:
        logger.warning("cartorio_agent litellm fail: LITELLM_API_KEY nao configurada")
        # Forca cair pro fallback chain
        last_err = "LITELLM_API_KEY nao configurada"
        LITELLM_URLS_TO_TRY = []
    else:
        headers = {
            "Authorization": f"Bearer {litellm_key}",
            "Content-Type": "application/json",
        }
        last_err = ""
        LITELLM_URLS_TO_TRY = LITELLM_URLS

    async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=5.0)) as client:
        for base in LITELLM_URLS_TO_TRY:
            url = f"{base.rstrip('/')}/v1/chat/completions"
            try:
                r = await client.post(url, headers=headers, json=payload)
                if r.status_code != 200:
                    last_err = f"{base} HTTP {r.status_code} {r.text[:120]}"
                    continue
                data = r.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if content:
                    return content, f"litellm:{LITELLM_MODEL}"
                last_err = f"{base} empty content"
            except Exception as exc:
                last_err = f"{base} {type(exc).__name__}: {exc}"
                logger.warning("cartorio_agent litellm fail: %s", last_err)
    # Fallback chain generica do projeto
    try:
        from app.integrations.fallback import chat_with_fallback

        resp = await chat_with_fallback(
            messages=[
                {"role": "system", "content": system[:900]},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            consent_granted=True,
            actor_id="telegram:cartorio_agent",
            db=None,
            session_id=None,
            rate_limit_per_minute=None,
            request_id=None,
            client_ip=None,
        )
        return (resp.content or "").strip(), f"fallback:{getattr(resp, 'provider', '?')}"
    except Exception as exc:
        logger.warning("cartorio_agent fallback fail: %s | litellm=%s", exc, last_err)
        return "", "none"


def _parse_action(text: str) -> tuple[str, str | None]:
    action = None
    m = re.search(r"\[\[ACTION:(agendar|protocolo|humano|menu)\]\]", text, re.I)
    if m:
        action = m.group(1).lower()
        text = re.sub(r"\s*\[\[ACTION:[^\]]+\]\]\s*", "\n", text).strip()
    return text, action


def _keyboard_for_action(action: str | None, intent: str) -> list[list[dict[str, str]]] | None:
    """Teclado so quando e tool util (como MCP tool call), senao None.

    - agendar / preco sem servico claro → lista de servicos
    - menu explicito → atalhos
    - saudacao, endereco, horario, preco com servico, humano, protocolo → SEM botoes
    """
    if action == "menu":
        return _menu_kb()
    if action == "agendar" or intent == "agendar":
        return _servicos_kb()
    if intent == "preco":
        # so teclado se ainda nao identificou servico (precisa escolher)
        return None  # caller decide com match_servico; default sem teclado
    return None


def _offline_reply(text: str, intent: str, tools_used: list[str]) -> AgentReply:
    """Resposta deterministica se LLM cair — ainda e util, nao muda pra FSM cego."""
    svc = _match_servico(text)
    if intent == "preco" and svc:
        nome, valor = SERVICOS_CATALOGO[svc]
        return AgentReply(
            text=(
                f"Pelo catalogo do cartorio, {nome} esta em {valor} "
                f"(tabela operacional bot / referencia MG). "
                f"Se quiser agendar, digite por exemplo: quero agendar {nome.lower()}."
            ),
            keyboard=None,
            action=None,
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "preco":
        lines = [f"- {n}: {v}" for _, (n, v) in SERVICOS_CATALOGO.items()]
        return AgentReply(
            text="Valores de referencia que posso informar agora:\n"
            + "\n".join(lines)
            + "\nQual servico te interessa? Digite o nome (sem precisar de menu).",
            keyboard=None,
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "endereco":
        return AgentReply(
            text=f"Estamos em {CARTORIO_INFO['endereco']}. {CARTORIO_INFO['horario']}.",
            keyboard=None,
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "horario":
        return AgentReply(
            text=f"Funcionamento: {CARTORIO_INFO['horario']}.",
            keyboard=None,
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "agendar":
        return AgentReply(
            text=(
                "Posso ajudar a agendar. Qual servico? "
                "Digite o nome ou escolha na lista se preferir atalho."
            ),
            keyboard=_servicos_kb(),  # tool necessaria: escolha 1 de N
            action="agendar",
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "protocolo":
        return AgentReply(
            text="Me informe o numero do protocolo no formato 2026-000123.",
            action="protocolo",
            keyboard=None,
            tools_used=tools_used,
            provider="offline",
        )
    if intent == "humano":
        return AgentReply(
            text=(
                "Vou encaminhar para atendimento humano (escrevente / HITL). "
                "Descreva em uma frase o que precisa."
            ),
            action="humano",
            keyboard=None,
            tools_used=tools_used,
            provider="offline",
        )
    return AgentReply(
        text=(
            f"Ola! Sou o Agent AI do {CARTORIO_INFO['nome']}. "
            "Pode falar em texto livre "
            "(ex: quanto custa autenticacao, quero agendar procuracao, "
            "protocolo 2026-000123). "
            "Atalhos so se voce digitar /menu."
        ),
        keyboard=None,
        tools_used=tools_used,
        provider="offline",
    )


async def run_cartorio_agent(
    text: str,
    *,
    history: list[str] | None = None,
) -> AgentReply:
    """Entrada principal do Agent AI Cartorio."""
    raw = (text or "").strip()
    if not raw:
        return AgentReply(text="Pode me contar o que voce precisa?", keyboard=None)

    scrubbed = scrub(raw).text
    intent = _detect_intent(scrubbed)
    tools_ctx, tools_used = _build_tools_context(scrubbed)
    system = AGENT_SYSTEM.format(tools_context=tools_ctx)

    user_block = scrubbed
    if history:
        hist = "\n".join(f"- {h}" for h in history[-4:])
        user_block = f"Historico recente:\n{hist}\n\nMensagem atual: {scrubbed}"

    content, provider = await _llm_minimax(system, user_block)
    if not content:
        return _offline_reply(scrubbed, intent, tools_used)

    clean, action = _parse_action(content)
    # strip residual emojis if any
    clean = re.sub(
        "[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff]",
        "",
        clean,
    ).strip()
    if not clean:
        return _offline_reply(scrubbed, intent, tools_used)

    # Se intent forte e LLM nao emitiu ACTION, injeta
    if action is None and intent in ("agendar", "protocolo", "humano"):
        action = intent

    kb = _keyboard_for_action(action, intent)
    # Preco: teclado so se nao identificou servico (precisa "tool" de escolha)
    if intent == "preco" and _match_servico(scrubbed) is None and action != "menu":
        kb = _servicos_kb()
    # Limita tamanho telegram
    if len(clean) > 900:
        clean = clean[:900] + "..."

    return AgentReply(
        text=clean,
        keyboard=kb,
        action=action,
        tools_used=tools_used,
        provider=provider,
    )


__all__ = ["AgentReply", "run_cartorio_agent", "SERVICOS_CATALOGO"]
