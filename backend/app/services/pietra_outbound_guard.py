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

# === LANGUAGE GUARD LATINO (round 2, 2026-07-28) ===
# O guard round 1 so cobre ranges NAO-latinos; ingles e PT-PT sao latim
# puro e passavam. Evidencia real (personas P7-P10): "sensibility",
# "sounds like", "indeed", "explains that situation", "es velho".
# Lexico curado, case-insensitive, word boundary — auditavel.

_LATIN_MIX_EN_PATTERNS: Final[tuple[str, ...]] = (
    r"\bsounds\s+like\b",
    r"\bsensibility\b",
    r"\bindeed\b",
    r"\broughly\b",
    r"\bdepending\s+on\b",
    r"\bexplains\s+that\b",
    r"\bactually\b",
    r"\bbasically\b",
    r"\bhowever\b",
)

_LATIN_MIX_PTPT_PATTERNS: Final[tuple[str, ...]] = (
    r"\b[ée]s\s+velho\b",
    r"\best[aá]s\b",
    r"\bt[aá]s\b",
    r"\bcasa\s+de\s+banho\b",
    r"\bautocarro\b",
    r"\btelem[oó]vel\b",
    r"\bfixe\b",
)

# Whitelist: termos estrangeiros ja incorporados ao PT-BR do negocio.
# Mascarados ANTES do scan para nunca disparar deteccao.
LATIN_MIX_WHITELIST: Final[tuple[str, ...]] = (
    "WhatsApp",
    "iMessage",
    "e-mail",
    "email",
    "link",
    "online",
    "app",
    "e-Notariado",
    "selfie",
)

_WHITELIST_RE: Final[re.Pattern[str]] = re.compile(
    "|".join(re.escape(w) for w in LATIN_MIX_WHITELIST), re.IGNORECASE
)

_COMPILED_LATIN_MIX: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(p, re.IGNORECASE | re.UNICODE)
    for p in (*_LATIN_MIX_EN_PATTERNS, *_LATIN_MIX_PTPT_PATTERNS)
)

# === VALIDADOR ANTI-GLITCH (round 2, 2026-07-28) ===
# Tokens fora do vocabulario PT-BR plausivel gerados pelo modelo rapido.
# Evidencia real: "prosetão" (P8), "Carta minecraft:" (P9 id 4272),
# "quandoolhar" (P7 id 4254), "ISSA" (P6). Abordagem leve e auditavel:
# constante de padroes suspeitos + heuristicas de tamanho/capitalizacao.
# SEM dependencia pesada (wordfreq/hunspell).

_GLITCH_PATTERNS: Final[tuple[str, ...]] = (
    r"\bcarta\s+minecraft\b",  # bigrama impossivel (P9)
    r"\bminecraft\b",
    r"\bproset[aã]o\b",
    r"\bquandoolhar\b",
)

_COMPILED_GLITCH: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(p, re.IGNORECASE | re.UNICODE) for p in _GLITCH_PATTERNS
)

# Heuristica 1: token alfabetico com 16+ chars sem hifen — fora do PT-BR
# plausivel (maior palavra notarial comum: "reconhecimento", 14 chars).
_GLITCH_LONG_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![\wÀ-ÿ-])[A-Za-zÀ-ÿ]{16,}(?![\wÀ-ÿ-])", re.UNICODE
)

# Heuristica 2: token ALLCAPS 3+ fora da whitelist de siglas do dominio.
_GLITCH_CAPS_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{3,}\b"
)

_GLITCH_CAPS_WHITELIST: Final[frozenset[str]] = frozenset(
    {
        "CPF",
        "CNPJ",
        "CNH",
        "CRM",
        "OAB",
        "CREA",
        "RNE",
        "IPTU",
        "ITBI",
        "LGPD",
        "TFJ",
        "TJMG",
        "CNS",
        "CNJ",
    }
)


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
    "language_mixing_latin": 0,
    "token_glitch": 0,
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


def detect_latin_language_mix(text: str) -> str | None:
    """Detecta anglicismo/PT-PT em texto PT-BR (round 2).

    Mascara a whitelist (WhatsApp, iMessage, e-mail, ...) antes do scan e
    retorna o pattern que casou, ou None se limpo.
    """
    if not text:
        return None
    masked = _WHITELIST_RE.sub(" ", text)
    for source, compiled in zip(
        (*_LATIN_MIX_EN_PATTERNS, *_LATIN_MIX_PTPT_PATTERNS), _COMPILED_LATIN_MIX
    ):
        if compiled.search(masked):
            return source
    return None


def strip_latin_mix_sentences(text: str) -> tuple[str, bool]:
    """Remove sentencas contaminadas por anglicismo/PT-PT.

    Retorna (texto_limpo, agiu). Sentencas limpas sao preservadas.
    """
    sentences = _split_sentences(text)
    contaminated = [s for s in sentences if detect_latin_language_mix(s)]
    if not contaminated:
        return text, False
    kept = [s for s in sentences if not detect_latin_language_mix(s)]
    return _cleanup_spacing(" ".join(kept)), True


def detect_glitch_tokens(text: str) -> str | None:
    """Detecta token fora do vocabulario PT-BR plausivel (anti-glitch).

    Retorna o token/pattern que casou, ou None se limpo. Camadas:
    1. Constante de padroes suspeitos (bigramas impossiveis, palavras
       inventadas observadas em prod).
    2. Token alfabetico 16+ chars sem hifen.
    3. Token ALLCAPS 3+ fora da whitelist de siglas do dominio.
    """
    if not text:
        return None
    for source, compiled in zip(_GLITCH_PATTERNS, _COMPILED_GLITCH):
        if compiled.search(text):
            return source
    long_token = _GLITCH_LONG_TOKEN_RE.search(text)
    if long_token:
        return long_token.group(0)
    for caps in _GLITCH_CAPS_TOKEN_RE.finditer(text):
        if caps.group(0) not in _GLITCH_CAPS_WHITELIST:
            return caps.group(0)
    return None


def strip_glitch_sentences(text: str) -> tuple[str, bool]:
    """Remove sentencas contendo glitch de token. Retorna (texto, agiu)."""
    sentences = _split_sentences(text)
    contaminated = [s for s in sentences if detect_glitch_tokens(s)]
    if not contaminated:
        return text, False
    kept = [s for s in sentences if not detect_glitch_tokens(s)]
    return _cleanup_spacing(" ".join(kept)), True


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

    # 2b. LANGUAGE GUARD LATINO (round 2): sentencas com anglicismo/PT-PT
    # sao removidas; conteudo util adjacente e preservado.
    work_latin, latin_stripped = strip_latin_mix_sentences(work)
    if latin_stripped:
        reasons.append("language_mixing_latin")
        work = work_latin

    # 2c. ANTI-GLITCH (round 2): sentencas com token fora do vocabulario
    # PT-BR plausivel ("prosetão", "Carta minecraft", "ISSA") removidas.
    work_glitch, glitch_stripped = strip_glitch_sentences(work)
    if glitch_stripped:
        reasons.append("token_glitch")
        work = work_glitch

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
