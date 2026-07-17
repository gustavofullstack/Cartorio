"""G8.02.T1 — Histórico multi-turn com budget dinâmico de tokens.

Extrai e endurece a lógica de HIST_MAX fixo do telegram.py:
mantém as mensagens mais recentes sob um teto de tokens estimado
(heurística chars//4, documentada — não é tokenizer real).

LGPD: caller deve passar texto já scrubado.

Modified by Gustavo Almeida — Wave 35.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DialogHistoryConfig:
    max_entries: int = 40
    max_tokens: int = 2000
    ttl_sec: int = 7200
    snippet_chars: int = 400
    min_keep: int = 2


def estimate_tokens(text: str) -> int:
    """Heurística barata: ~4 chars por token (inglês/PT-BR misto).

    Não substitui tiktoken; serve só para podar histórico Redis.
    """
    if not text:
        return 0
    return max(1, len(text) // 4) if text.strip() else 0


def trim_history_to_token_budget(
    history: list[str],
    max_tokens: int,
    *,
    min_keep: int = 2,
) -> list[str]:
    """Mantém o sufixo (mais recente) sob o budget de tokens.

    Se max_tokens for muito baixo, ainda preserva min_keep entradas
    (quando disponíveis).
    """
    if not history:
        return []
    if max_tokens <= 0:
        return list(history[-max(min_keep, 0) :]) if min_keep > 0 else []

    # Se já cabe, corta só por tamanho de lista não é responsabilidade aqui
    total = estimate_tokens('\n'.join(history))
    if total <= max_tokens and len(history) <= 10_000:
        # still return copy
        out = list(history)
    else:
        out = list(history)

    # Drop oldest until under budget
    while len(out) > min_keep and estimate_tokens('\n'.join(out)) > max_tokens:
        out.pop(0)

    # Se ainda acima do budget mas só min_keep restam, keep them
    return out


def apply_entry_cap(history: list[str], max_entries: int) -> list[str]:
    if max_entries <= 0:
        return []
    if len(history) <= max_entries:
        return list(history)
    return list(history[-max_entries:])


def prepare_history_for_store(
    history: list[str],
    *,
    config: DialogHistoryConfig | None = None,
) -> list[str]:
    """Aplica cap de entradas + budget de tokens (ordem: cap depois budget)."""
    cfg = config or DialogHistoryConfig()
    capped = apply_entry_cap(history, cfg.max_entries)
    return trim_history_to_token_budget(
        capped,
        cfg.max_tokens,
        min_keep=cfg.min_keep,
    )


def apply_history_limits(
    history: list[str],
    config: DialogHistoryConfig | None = None,
    *,
    min_keep: int = 2,
) -> list[str]:
    """Alias G8.02.T1 usado pelo telegram.py (compat)."""
    cfg = config or DialogHistoryConfig(min_keep=min_keep)
    return prepare_history_for_store(history, config=cfg)


async def hist_get(bus: Any, key: int | str, *, prefix: str = 'tg:hist:') -> list[str]:
    """Lê histórico multi-turn do Redis (lista de strings role:text)."""
    if not bus:
        return []
    try:
        client = getattr(bus, 'client', bus)
        raw = await client.get(f'{prefix}{key}')
        if not raw:
            return []
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8', errors='replace')
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


async def hist_append(
    bus: Any,
    key: int | str,
    role: str,
    text: str,
    *,
    config: DialogHistoryConfig | None = None,
    prefix: str = 'tg:hist:',
) -> list[str]:
    """Append + trim + SET com TTL. Retorna histórico final."""
    cfg = config or DialogHistoryConfig()
    if not bus or not text:
        return []
    try:
        hist = await hist_get(bus, key, prefix=prefix)
        snippet = text[: cfg.snippet_chars]
        hist.append(f'{role}: {snippet}')
        hist = prepare_history_for_store(hist, config=cfg)
        client = getattr(bus, 'client', bus)
        await client.set(
            f'{prefix}{key}',
            json.dumps(hist, ensure_ascii=False),
            ex=cfg.ttl_sec,
        )
        return hist
    except Exception:
        return []


__all__ = [
    'DialogHistoryConfig',
    'apply_entry_cap',
    'apply_history_limits',
    'estimate_tokens',
    'hist_append',
    'hist_get',
    'prepare_history_for_store',
    'trim_history_to_token_budget',
]
