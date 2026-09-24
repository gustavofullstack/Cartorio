"""Fail-closed guard for customer-facing Hermes/Feishu replies.

Hermes' native Feishu adapter does not pass through the FastAPI Pietra
sanitizer.  This dependency-free module is mounted into the Hermes container
and applied by Hermes' official ``transform_llm_output`` plugin hook.

The guard deliberately operates on the public copy only.  Tool calls, private
reasoning and the persisted transcript remain available to the agent, while
the customer receives only a normal cartorio response with PII masked and HITL
preserved.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Final

SAFE_FALLBACK: Final[str] = (
    "Sou a Pietra, a agente do 2º Cartório de Notas de Uberlândia. "
    "Posso orientar sobre serviços notariais, documentos, agendamentos e emolumentos."
)
HUMAN_REVIEW_NOTICE: Final[str] = (
    "Essa providência depende da validação de um escrevente antes de qualquer andamento."
)

_PRIVATE_BLOCK_RE: Final[re.Pattern[str]] = re.compile(
    r"<(?:think|thinking|reasoning|analysis)\b[^>]*>[\s\S]*?"
    r"(?:</(?:think|thinking|reasoning|analysis)>|$)"
    r"|<(?:tool_call|function_calls?|invoke)\b[^>]*>[\s\S]*?"
    r"(?:</(?:tool_call|function_calls?|invoke)>|$)"
    r"|\[/?(?:tool_call|reasoning|thinking)\][\s\S]*?(?=\n\n|$)",
    re.IGNORECASE,
)
_UNBALANCED_PRIVATE_TAG_RE: Final[re.Pattern[str]] = re.compile(
    r"</?(?:think|thinking|reasoning|analysis|tool_call|function_calls?|invoke)\b[^>]*>",
    re.IGNORECASE,
)
_CONTROL_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:redirected\s+current\s+run|interrupting\s+current\s+task"
    r"|current\s+run\s*\(.*iteration\s+\d+/\d+"
    r"|self-improvement\s+review|first-time\s+tip"
    r"|(?:send|type)\s+/busy\b|/busy\s+(?:queue|steer|status)"
    r"|approve\s+once|always\s+approve|tool\s*(?:call|result|output|trace)"
    r"|calling\s+(?:a\s+)?tool|^assistant\s+to=|^analysis\s*:|^reasoning\s*:|^thought\s*:)",
    re.IGNORECASE,
)
_INTERNAL_CAPABILITY_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:posso\s+te\s+ajudar\s+com\s+bastante\s+coisa"
    r"|aqui\s+vai\s+um\s+resumo\s+do\s+que\s+fa[cç]o\s+bem"
    r"|por\s+onde\s+voc[eê]\s+quer\s+come[cç]ar"
    r"|produtividade\s+e\s+pesquisa|c[oó]digo\s*(?:&|e)\s*tecnologia"
    r"|m[ií]dia\s*(?:&|e)\s*cria[cç][aã]o|automa[cç][oõ]es\s*(?:&|e)\s*agentes"
    r"|vida\s+pr[aá]tica"
    r"|buscar\s+e\s+resumir\s+informa[cç][oõ]es\s*\(web"
    r"|criar/editar\s+documentos\s+(?:word|excel|powerpoint)"
    r"|gerenciar\s+notas\s+no\s+(?:obsidian|notion|google\s+workspace)"
    r"|ler\s+e\s+responder\s+e-?mails"
    r"|escrever,?\s+revisar,?\s+debugar\s+c[oó]digo"
    r"|trabalhar\s+com\s+git(?:hub)?|rodar\s+testes,?\s+executar\s+scripts"
    r"|gerar\s+imagens,?\s+v[ií]deos\s+e\s+[aá]udio"
    r"|transcrever\s+v[ií]deos\s+do\s+youtube|fazer\s+m[uú]sica\s+com"
    r"|criar\s+tarefas\s+agendadas\s*\(cron|delegar\s+trabalho\s+para\s+sub-?agentes"
    r"|controlar\s+luzes\s+philips\s+hue|buscar\s+mercados\s+no\s+polymarket"
    r"|consultar\s+pre[cç]o\s+de\s+a[cç][oõ]es|postar\s+no\s+x/twitter"
    r"|\b(?:hermes|mini?max|mcp|agent\s+zero|openclaw|chatwoot)\b"
    r"|\b(?:sub-?agents?|cron\s+jobs?|github)\b)",
    re.IGNORECASE,
)
_LEGAL_AUTONOMY_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:eu\s+)?(?:aprovei|autorizei|validei|emiti|lavrei|conclu[ií]|processei|isentei)\b"
    r"|\b(?:protocolo|certid[aã]o|escritura|procura[cç][aã]o|testamento|isen[cç][aã]o"
    r"|urg[eê]ncia)\s+(?:foi|est[aá])\s+(?:aprovad[ao]|emitid[ao]|lavrad[ao]|conclu[ií]d[ao])\b",
    re.IGNORECASE,
)
_HUMAN_REVIEW_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:escrevente|equipe\s+do\s+cart[oó]rio|atendimento\s+humano"
    r"|valida[cç][aã]o\s+humana|an[aá]lise\s+humana)\b",
    re.IGNORECASE,
)
_CPF_RE: Final[re.Pattern[str]] = re.compile(r"\b(\d{3})\.?\d{3}\.?\d{3}-?(\d{2})\b")
_EMAIL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b"
)
_PHONE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:\+?55[\s.-]*)?\(?\d{2}\)?[\s.-]*9\d{4}[\s.-]?\d{4}"
)
_FEISHU_INBOUND_LOG: Final[str] = "[Feishu] Inbound %s message received:"
_GATEWAY_INBOUND_LOG: Final[str] = "inbound message: platform=%s user=%s"
_TURN_LOG: Final[str] = "conversation turn: session=%s model=%s"


class SensitiveMessageLogFilter(logging.Filter):
    """Replace known Hermes message previews with non-identifying metadata."""

    def filter(self, record: logging.LogRecord) -> bool:
        template = str(record.msg)
        args = record.args if isinstance(record.args, tuple) else ()

        if template.startswith(_FEISHU_INBOUND_LOG) and len(args) >= 8:
            record.msg = (
                "[Feishu] Inbound %s message received: type=%s text_chars=%d media=%d"
            )
            record.args = (args[0], args[2], len(str(args[6] or "")), args[7])
        elif template.startswith(_GATEWAY_INBOUND_LOG) and len(args) >= 6:
            record.msg = "inbound message: platform=%s text_chars=%d reply_chars=%d"
            record.args = (
                args[0],
                len(str(args[3] or "")),
                len(str(args[5] or "")),
            )
        elif template.startswith(_TURN_LOG) and len(args) >= 6:
            record.msg = (
                "conversation turn: provider=%s platform=%s history=%d text_chars=%d"
            )
            record.args = (
                args[2],
                args[3],
                args[4],
                len(str(args[5] or "")),
            )
        return True


def install_sensitive_log_filter() -> None:
    """Install the Cartório PII filter once on Hermes' message loggers."""
    for logger_name in (
        "hermes_plugins.feishu_platform.adapter",
        "gateway.run",
        "agent.turn_context",
    ):
        logger = logging.getLogger(logger_name)
        if not any(
            isinstance(item, SensitiveMessageLogFilter) for item in logger.filters
        ):
            logger.addFilter(SensitiveMessageLogFilter())


@dataclass(frozen=True)
class PublicOutput:
    """Sanitized customer-facing copy plus machine-readable audit reasons."""

    text: str
    reasons: tuple[str, ...]


def _mask_pii(text: str) -> str:
    text = _CPF_RE.sub(r"\1.***.***-\2", text)
    text = _EMAIL_RE.sub(r"\1***@\2", text)
    return _PHONE_RE.sub("[telefone mascarado]", text)


def _clean_spacing(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(" \n,;:-")


def sanitize_public_reply(text: str) -> PublicOutput:
    """Return a normal public reply or a deterministic safe fallback."""
    original = str(text or "")
    work = original
    reasons: list[str] = []

    stripped_private = _PRIVATE_BLOCK_RE.sub("", work)
    stripped_private = _UNBALANCED_PRIVATE_TAG_RE.sub("", stripped_private)
    if stripped_private != work:
        reasons.append("private_trace")
        work = stripped_private

    kept_lines: list[str] = []
    legal_claim_removed = False
    for line in work.splitlines():
        units = re.split(r"(?<=[.!?])\s+", line)
        kept_units: list[str] = []
        for unit in units:
            if _CONTROL_LINE_RE.search(unit):
                if "internal_control" not in reasons:
                    reasons.append("internal_control")
                continue
            if _INTERNAL_CAPABILITY_RE.search(unit):
                if "internal_capability" not in reasons:
                    reasons.append("internal_capability")
                continue
            if _LEGAL_AUTONOMY_RE.search(unit) and not _HUMAN_REVIEW_RE.search(unit):
                legal_claim_removed = True
                if "hitl" not in reasons:
                    reasons.append("hitl")
                continue
            kept_units.append(unit)
        if kept_units:
            kept_lines.append(" ".join(kept_units))

    work = _clean_spacing("\n".join(kept_lines))
    if legal_claim_removed and HUMAN_REVIEW_NOTICE not in work:
        work = _clean_spacing(f"{work}\n\n{HUMAN_REVIEW_NOTICE}")

    masked = _mask_pii(work)
    if masked != work:
        reasons.append("pii")
        work = masked

    if len(re.sub(r"[^0-9A-Za-zÀ-ÿ]", "", work)) < 10:
        if original.strip() and "fallback" not in reasons:
            reasons.append("fallback")
        work = SAFE_FALLBACK

    return PublicOutput(text=work, reasons=tuple(reasons))
