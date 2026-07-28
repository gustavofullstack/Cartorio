"""Guard OUTBOUND da Pietra: infra leak + language mixing (P0 2026-07-28).

Evidencia real de prod iMessage (campanha 2026-07-28, 2044 mensagens):
1. LIXO DE INFRA vazava cru ao cliente em ingles:
   "⚡ Interrupting current task", "model provider is rate-limiting",
   "empty response stream", "Sorry, I encountered an unexpected error".
2. LANGUAGE MIXING no meio do PT-BR: russo ("Mas есть uma boa notícia")
   e chines ("então，大概 R$ 22-33").

Esta camada e **independente da causa raiz**: antes de qualquer resposta
sair pelo endpoint /api/v1/pietra/chat/completions, o texto passa por:
a. INFRA GUARD — sentencas contendo vocabulario de sistema/infra sao
   removidas; se nada util restar, resposta vira mensagem humana PT-BR
   (SAFE_FALLBACK). Conteudo util junto e preservado.
b. LANGUAGE GUARD — caracteres nao-latinos (CJK \\u4e00-\\u9fff, cirilico
   \\u0400-\\u04ff) sao removidos e pontuacao full-width (，、。｜) e
   normalizada para equivalentes latinos; resposta quebrada vira fallback.
Toda interceptacao loga WARNING e incrementa metrica (mesmo padrao do
pietra_identity_guard).

Modified by Gustavo Almeida · 2026-07-28
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Final

logger = logging.getLogger(__name__)

# === Mensagem humana de fallback (PT-BR) ===
SAFE_FALLBACK: Final[str] = "Um momento, por favor, que já respondo."

# === Padroes de lixo de infra/sistema (case-insensitive) ===
# Cobre as strings REAIS observadas em prod + variantes plausiveis.
_INFRA_PATTERNS: Final[tuple[str, ...]] = (
    r"interrupting\s+current\s+task",
    r"rate[\s-]?limit(?:ing|ed)?",
    r"empty\s+response(?:\s+stream)?",
    r"unexpected\s+error",
    r"switched\s+to\s+fallback",
    r"usage\s+limit",
    r"home\s+channel",
    r"\bphoton\b",
    r"\bgateway\b",
    r"\btime\s?out\b",
    r"\btimed\s+out\b",
    r"model\s+provider\s+is",
    r"encountered\s+an?\s+error",
    r"sorry,?\s+i\s+encountered",
    r"please\s+try\s+again",
    r"an\s+error\s+occurred",
)

_COMPILED_INFRA: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(p, re.IGNORECASE | re.UNICODE) for p in _INFRA_PATTERNS
)

# === Ranges nao-latinos: CJK (+ext A, compat), cirilico, kana, hangul ===
_NON_LATIN_RE: Final[re.Pattern[str]] = re.compile(
    "[一-鿿㐀-䶿豈-﫿Ѐ-ӿ぀-ヿ가-힯]"
)

# Pontuacao full-width → equivalente latino.
_FULLWIDTH_MAP: Final[dict[str, str]] = {
    "，": ", ",
    "、": ", ",
    "。": ". ",
    "｜": " | ",
    "；": "; ",
    "！": "!",
    "？": "?",
    "（": "(",
    "）": ")",
    "“": '"',
    "”": '"',
}


class OutboundAction(Enum):
    """Acao tomada pelo guard outbound."""

    PASS = "pass"
    SANITIZED = "sanitized"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class OutboundResult:
    """Resultado da sanitizacao outbound."""

    action: OutboundAction
    original_text: str
    sanitized_text: str
    reasons: tuple[str, ...]
    channel: str | None = None


# === Metricas (mesmo padrao do identity guard) ===
_OUTBOUND_INTERCEPTED_TOTAL: int = 0
_OUTBOUND_BY_REASON: dict[str, int] = {
    "infra_leak": 0,
    "language_mixing": 0,
    "fallback": 0,
}


def get_outbound_guard_metrics() -> dict[str, int]:
    """Snapshot das metricas para /metrics endpoint."""
    return {
        "cartorio_pietra_outbound_guard_intercepted_total": _OUTBOUND_INTERCEPTED_TOTAL,
        **_OUTBOUND_BY_REASON,
    }


def reset_outbound_guard_metrics() -> None:
    """Reseta contadores (uso em testes)."""
    global _OUTBOUND_INTERCEPTED_TOTAL  # noqa: PLW0603
    _OUTBOUND_INTERCEPTED_TOTAL = 0
    for k in _OUTBOUND_BY_REASON:
        _OUTBOUND_BY_REASON[k] = 0


def _record_metric(reasons: list[str]) -> None:
    global _OUTBOUND_INTERCEPTED_TOTAL  # noqa: PLW0603
    _OUTBOUND_INTERCEPTED_TOTAL += 1
    for r in reasons:
        _OUTBOUND_BY_REASON[r] = _OUTBOUND_BY_REASON.get(r, 0) + 1


# === Detectores ===


def detect_infra_leak(text: str) -> str | None:
    """Retorna o pattern de infra que casou, ou None se limpo."""
    if not text:
        return None
    for source, compiled in zip(_INFRA_PATTERNS, _COMPILED_INFRA):
        if compiled.search(text):
            return source
    return None


def contains_non_latin_script(text: str) -> bool:
    """True se o texto contem caracteres CJK, cirilico, kana ou hangul."""
    return bool(text) and bool(_NON_LATIN_RE.search(text))


# === Helpers internos ===


def _split_sentences(text: str) -> list[str]:
    """Quebra em sentencas (linhas + pontuacao final), preservando ordem."""
    parts: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip())
    return parts


def _cleanup_spacing(text: str) -> str:
    """Normaliza espacos/pontuacao apos remocao de tokens."""
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,.;:!?])(?=\S)", r"\1 ", text)
    text = re.sub(r"([,.])\s*([,.])", r"\2", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s*([|])\s*", r" \1 ", text)
    return text.strip(" ,;|").strip()


def _alnum_count(text: str) -> int:
    """Conta caracteres alfanumericos latinos (util residual)."""
    return len(re.sub(r"[^0-9A-Za-zÀ-ÿ]", "", text))


# === Guard principal ===


def sanitize_outbound(text: str, *, channel: str = "api") -> OutboundResult:
    """Sanitiza resposta antes de sair ao cliente.

    Fluxo:
    1. INFRA: sentencas com vocabulario de sistema/infra sao removidas.
    2. LANGUAGE: tokens nao-latinos removidos; full-width normalizado.
    3. Se o util residual for insuficiente (<10 alnum) e houve
       interceptacao -> SAFE_FALLBACK.

    Args:
        text: resposta candidata antes do envio.
        channel: canal de saida ("api", "imessage", ...) para metricas/log.

    Returns:
        OutboundResult com action, sanitized_text e reasons.
    """
    if not text:
        return OutboundResult(
            action=OutboundAction.PASS,
            original_text="",
            sanitized_text="",
            reasons=(),
            channel=channel,
        )

    reasons: list[str] = []
    work = text

    # 1. INFRA GUARD: remover sentencas contaminadas.
    sentences = _split_sentences(work)
    contaminated = [s for s in sentences if detect_infra_leak(s)]
    if contaminated:
        kept = [s for s in sentences if not detect_infra_leak(s)]
        reasons.append("infra_leak")
        work = " ".join(kept).strip()

    # 2. LANGUAGE GUARD: remover tokens nao-latinos + normalizar full-width.
    if _NON_LATIN_RE.search(work):
        reasons.append("language_mixing")
        work = _NON_LATIN_RE.sub(" ", work)
    if any(fw in work for fw in _FULLWIDTH_MAP):
        if "language_mixing" not in reasons:
            reasons.append("language_mixing")
        for fw, latin in _FULLWIDTH_MAP.items():
            work = work.replace(fw, latin)
    if "language_mixing" in reasons:
        work = _cleanup_spacing(work)

    # 3. FALLBACK: interceptou mas nao restou conteudo util.
    if reasons and _alnum_count(work) < 10:
        reasons.append("fallback")
        work = SAFE_FALLBACK

    if not reasons:
        return OutboundResult(
            action=OutboundAction.PASS,
            original_text=text,
            sanitized_text=text,
            reasons=(),
            channel=channel,
        )

    action = OutboundAction.FALLBACK if "fallback" in reasons else OutboundAction.SANITIZED
    _record_metric(reasons)
    logger.warning(
        "pietra outbound guard interceptou action=%s reasons=%s channel=%s original=%.120r",
        action.value,
        ",".join(reasons),
        channel,
        text,
    )
    return OutboundResult(
        action=action,
        original_text=text,
        sanitized_text=work,
        reasons=tuple(reasons),
        channel=channel,
    )
