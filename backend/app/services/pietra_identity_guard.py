"""Defesa-em-profundidade contra IDENTITY_HERMES_LEAK (Lesson 280 + paste #2 §3.3).

Problema: o cache do sidecar Photon Spectrum (Node.js :8793) injeta respostas
contendo "Sou o Hermes" mesmo após o snapshot + sessions terem sido purgados.
A causa raiz (Camada 3 do cache) está em código fechado
(`nousresearch/hermes-agent`, digest fixado 2026-07-26) e ainda em investigação.

Esta camada é **independente da causa raiz**: antes de qualquer resposta
chegar ao iMessage, escaneia o texto por padrões de identidade Hermes
e intercepta/substitui/regenera a resposta. Também expõe um contador Prometheus
para visibilidade contínua.

3 estrategias de mitigacao (em ordem de severidade crescente):
1. SUBSTITUIR por abertura canonica da Pietra ("Sou a Pietra...")
2. REGENERAR via response_planner como fallback
3. HARD-STOP: nao enviar a resposta, enviar mensagem generica "instabilidade"

Modified by Gustavo Almeida · 2026-07-27 (Lição 282)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Final


# === Padroes de identidade Hermes (regex compilados) ===
# Cobre variantes observadas: "Sou o Hermes", "Hermes-2", "assistente Hermes",
# "agente Hermes", "meu nome e Hermes", "chamo Hermes", etc.
# Case-insensitive e tolerante a acento.
_HERMES_IDENTITY_PATTERNS: Final[tuple[str, ...]] = (
    # Padroes de identificacao direta (vazamento de persona)
    r"(?:^|\W)sou\s+(?:o|a)\s+hermes(?:\W|$)",
    r"(?:^|\W)sou\s+(?:o|a)\s+hermes\s*-?\s*2(?:\W|$)",
    r"(?:^|\W)(?:me\s+)?nome\s+(?:e|é)\s+hermes(?:\W|$)",
    r"(?:^|\W)(?:me\s+)?chamo\s+hermes(?:\W|$)",
    r"(?:^|\W)sou\s+(?:o|a)\s+assistente\s+hermes(?:\W|$)",
    r"(?:^|\W)(?:como|seja)\s+hermes(?:\W|$)",
    r"(?:^|\W)agente\s+hermes(?:\W|$)",
    r"(?:^|\W)atendente\s+hermes(?:\W|$)",
    r"(?:^|\W)hermes\s*-?\s*2\s+(?:aqui|falando|respondendo)(?:\W|$)",
    r"(?:^|\W)hermes\s+agent(?:\W|$)",
    r"(?:^|\W)hermes-agent(?:\W|$)",
    # Variante standalone: "Hermes continua online" / "Hermes responde" /
    # "Hermes te ajuda" — sem verbo de identificacao, mas presente como sujeito
    # de acao, sinal claro de identity leak quando contexto e bot/cartorio.
    r"(?:^|\W)hermes\s+(?:continua|responde|te\s+ajuda|esta\s+aqui|iniciou|finalizou|encerrou)(?:\W|$)",
    r"(?:^|\W)hermes\s+tambem(?:\W|$)",
    # Padroes standalone sem verbo posposto (cobrem "Hermes respondendo",
    # "HERMES aqui", etc.)
    r"(?:^|\W)hermes\s+respondendo(?:\W|$)",
    r"(?:^|\W)hermes\s+aqui(?:\W|$)",
)

_COMPILED_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(p, re.IGNORECASE | re.UNICODE) for p in _HERMES_IDENTITY_PATTERNS
)


# === Aberturas canonicas da Pietra (para substituicao) ===
PIETRA_CANONICAL_OPENINGS: Final[tuple[str, ...]] = (
    "Sou a Pietra, agente virtual do 2o Tabelionato de Notas de Uberlandia.",
    "Sou a Pietra, a agente do 2o Cartorio de Notas de Uberlandia.",
    "Aqui e a Pietra, do 2o Tabelionato de Notas de Uberlandia.",
)


class InterceptAction(Enum):
    """Acao tomada quando o guard detecta identity leak."""

    PASS = "pass"
    SUBSTITUTE = "substitute"
    REGENERATE = "regenerate"
    HARD_STOP = "hard_stop"


@dataclass(frozen=True)
class InterceptResult:
    """Resultado da interceptacao."""

    action: InterceptAction
    original_text: str
    sanitized_text: str
    matched_pattern: str | None
    channel: str | None = None


# === Metricas Prometheus (instrumentadas) ===
# Incrementado toda vez que o guard intercepta algo. Thread-safe via GIL.
_IDENTITY_LEAK_INTERCEPTED_TOTAL: int = 0
_IDENTITY_LEAK_BY_ACTION: dict[str, int] = {
    "pass": 0,
    "substitute": 0,
    "regenerate": 0,
    "hard_stop": 0,
}


def get_identity_leak_metrics() -> dict[str, int]:
    """Snapshot das metricas Prometheus para /metrics endpoint."""
    return {
        "cartorio_pietra_identity_leak_intercepted_total": _IDENTITY_LEAK_INTERCEPTED_TOTAL,
        **_IDENTITY_LEAK_BY_ACTION,
    }


def _record_metric(action: InterceptAction) -> None:
    """Incrementa contadores internos (substitui prometheus_client quando indisponivel)."""
    global _IDENTITY_LEAK_INTERCEPTED_TOTAL  # noqa: PLW0603
    _IDENTITY_LEAK_INTERCEPTED_TOTAL += 1
    _IDENTITY_LEAK_BY_ACTION[action.value] = (
        _IDENTITY_LEAK_BY_ACTION.get(action.value, 0) + 1
    )


def reset_identity_leak_metrics() -> None:
    """Reseta contadores (uso em testes)."""
    global _IDENTITY_LEAK_INTERCEPTED_TOTAL  # noqa: PLW0603
    _IDENTITY_LEAK_INTERCEPTED_TOTAL = 0
    for k in _IDENTITY_LEAK_BY_ACTION:
        _IDENTITY_LEAK_BY_ACTION[k] = 0


# === Detector ===

def detect_hermes_identity_leak(text: str) -> str | None:
    """Retorna o pattern regex que vazou, ou None se limpo.

    Case-insensitive, tolerante a acento via NFD decompose + strip combining.
    Python re usa \\w ASCII-only — bypass por acento como "Hérmes" exige
    normalizacao previa.
    """
    if not text:
        return None
    import unicodedata

    # NFD decompõe acentos em letra + combining mark (e.g., "é" -> "e" + U+0301).
    # Strip combining marks (categoria Mn) para bypass tolerante.
    nfd = unicodedata.normalize("NFD", text)
    accent_free = "".join(
        ch for ch in nfd if unicodedata.category(ch) != "Mn"
    )
    for source, compiled in zip(_HERMES_IDENTITY_PATTERNS, _COMPILED_PATTERNS):
        m = compiled.search(accent_free)
        if m:
            return source
    return None


# === Guard principal ===

def guard_identity(
    text: str,
    *,
    channel: str = "imessage",
    substitute_opening: str | None = None,
) -> InterceptResult:
    """Aplica o guard de identidade antes do envio ao cliente.

    Fluxo:
    1. Detectar padrao Hermes no texto.
    2. Se nao vazou -> PASS (sem modificacao).
    3. Se vazou -> SUBSTITUTE (prefixar com abertura canonica Pietra).
    4. Caller decide se vai REGENERATE ou HARD_STOP baseado no contexto.

    Args:
        text: resposta candidata antes do envio.
        channel: "imessage", "whatsapp", "telegram", "web" — para metricas.
        substitute_opening: abertura canonica custom (testabilidade).

    Returns:
        InterceptResult com action, original_text, sanitized_text, matched_pattern.
    """
    if not text:
        return InterceptResult(
            action=InterceptAction.PASS,
            original_text="",
            sanitized_text="",
            matched_pattern=None,
            channel=channel,
        )

    bad = detect_hermes_identity_leak(text)
    if bad is None:
        return InterceptResult(
            action=InterceptAction.PASS,
            original_text=text,
            sanitized_text=text,
            matched_pattern=None,
            channel=channel,
        )

    # Identity leak detectado -> SUBSTITUTE
    opening = substitute_opening or PIETRA_CANONICAL_OPENINGS[1]
    sanitized = f"{opening}\n\n{text}"

    _record_metric(InterceptAction.SUBSTITUTE)
    return InterceptResult(
        action=InterceptAction.SUBSTITUTE,
        original_text=text,
        sanitized_text=sanitized,
        matched_pattern=bad,
        channel=channel,
    )


def guard_identity_hard_stop(
    text: str,
    *,
    channel: str = "imessage",
) -> InterceptResult:
    """Versao HARD-STOP: quando detectar leak, retorna string generica.

    Use esta variante para canais customer-facing criticos (iMessage publico)
    onde QUALQUER leak de identidade e inaceitavel. Caller substitui a resposta
    por uma mensagem de instabilidade temporaria.
    """
    if not text:
        return InterceptResult(
            action=InterceptAction.PASS,
            original_text="",
            sanitized_text="",
            matched_pattern=None,
            channel=channel,
        )

    bad = detect_hermes_identity_leak(text)
    if bad is None:
        return InterceptResult(
            action=InterceptAction.PASS,
            original_text=text,
            sanitized_text=text,
            matched_pattern=None,
            channel=channel,
        )

    # HARD STOP: nao envia resposta vazada; usa mensagem generica
    sanitized = (
        "Estou com uma instabilidade momentanea. "
        "Posso te ajudar com emolumentos, protocolos ou informacoes institucionais. "
        "Para atendimento humano: (34) 3216-0252."
    )

    _record_metric(InterceptAction.HARD_STOP)
    return InterceptResult(
        action=InterceptAction.HARD_STOP,
        original_text=text,
        sanitized_text=sanitized,
        matched_pattern=bad,
        channel=channel,
    )