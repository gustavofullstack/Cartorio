"""G8.02.T3 — Pure helpers for Telegram debounce + update_id dedupe.

Extrai a lógica de decisão do debounce (janela 1.2s) de
`chat_pipeline.enqueue_message` / `resume_burst` e de
`telegram._process_telegram_debounce` para funções puras, testáveis
sem Redis/asyncio.

Workflow (ver docs/TELEGRAM_DEBOUNCE_G8.md):
  1. Webhook chega com update_id
  2. is_duplicate_update(seen, update_id) → drop se replay na janela
  3. enqueue → should_start_debounce(queue_len) → só o 1º dispara sleep 1.2s
  4. Após a janela: merge_burst_texts(textos) → 1 prompt consolidado

Constantes alinhadas com chat_pipeline.DEBOUNCE_WINDOW_SEC e
telegram.DEBOUNCE_WINDOW (= 1.2).

Modified by Gustavo Almeida — G8.02.T3.
"""

from __future__ import annotations

from collections.abc import MutableSet, Sequence
from typing import Any

# Alinhado com chat_pipeline.DEBOUNCE_WINDOW_SEC e telegram.DEBOUNCE_WINDOW
DEBOUNCE_WINDOW_SEC: float = 1.2

# A partir de quantas msgs na janela o merge resume (espelha resume_burst)
BURST_RESUME_THRESHOLD: int = 2

# Cap de caracteres no texto consolidado (espelha resume_burst[:600])
BURST_JOIN_MAX_CHARS: int = 600


def should_start_debounce(queue_len: int) -> bool:
    """Decide se este enqueue deve disparar a task de debounce.

    Regra canônica (chat_pipeline.enqueue_message):
      return llen == 1  # primeiro → dispara debounce

    - queue_len == 1 → True  (primeira msg da janela; agenda sleep 1.2s)
    - queue_len > 1  → False (já há debounce em curso; só enfileira)
    - queue_len <= 0 → False (fila vazia / estado inválido; não agenda)

    Args:
        queue_len: Tamanho da fila **após** o push da mensagem atual.

    Returns:
        True se deve iniciar a janela de debounce.
    """
    try:
        n = int(queue_len)
    except (TypeError, ValueError):
        return False
    return n == 1


def merge_burst_texts(texts: Sequence[str] | None) -> str:
    """Consolida textos coletados na janela de debounce em um único prompt.

    Espelha `chat_pipeline.resume_burst` + dedupe leve de strings vazias:

    - vazio / só whitespace → \"\"
    - 1 ou 2 textos não-vazios → último texto (comportamento v2.0 anti-spam)
    - 3+ textos → \"[N mensagens] t1 | t2 | ...\" truncado a BURST_JOIN_MAX_CHARS

    Não chama LLM; é pure merge para o agent path.

    Args:
        texts: Lista de textos brutos da fila (ordem cronológica).

    Returns:
        String única pronta para o agent / rate-limit path.
    """
    if not texts:
        return ""

    cleaned: list[str] = []
    for t in texts:
        if t is None:
            continue
        s = str(t).strip()
        if s:
            cleaned.append(s)

    if not cleaned:
        return ""

    if len(cleaned) <= BURST_RESUME_THRESHOLD:
        return cleaned[-1]

    joined = " | ".join(cleaned)
    body = joined[:BURST_JOIN_MAX_CHARS]
    return f"[{len(cleaned)} mensagens] {body}"


def is_duplicate_update(
    seen_set: MutableSet[Any],
    update_id: Any,
) -> bool:
    """Dedupe de update_id dentro da janela de debounce (in-memory set).

    Uso típico no webhook (antes do enqueue):

        seen: set[int] = set()  # ou por chat, com TTL externo
        if is_duplicate_update(seen, update_id):
            return {\"status\": \"duplicate\"}

    Comportamento:
      - update_id falsy (None, 0, \"\") → False (não dá pra dedupe; deixa passar)
      - update_id já em seen_set → True  (replay; caller deve drop)
      - update_id novo → adiciona em seen_set e retorna False

    Nota: a idempotência de longo prazo continua em Redis
    (`tg:idem:{update_id}` / `idem:{channel}:{update_id}` TTL 600s).
    Este helper cobre a janela curta / burst / redelivery na mesma request path.

    Args:
        seen_set: Set mutável de update_ids já vistos nesta janela/processo.
        update_id: ID do update Telegram (int) ou message_id genérico.

    Returns:
        True se for duplicata e deve ser ignorada.
    """
    if update_id is None or update_id == "" or update_id == 0:
        return False

    if update_id in seen_set:
        return True

    seen_set.add(update_id)
    return False
