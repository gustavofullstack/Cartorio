# G8.02.T3 — Telegram debounce + dedupe de updates

Design da janela de consolidação (1.2s) e anti-replay de `update_id`
para o bot Telegram (e espelho no `chat_pipeline` multi-canal).

## Objetivo

Cliente manda 3–10 mensagens em sequência (ou Telegram reentrega o
mesmo `update_id`). O bot deve:

1. **Não** processar o mesmo `update_id` duas vezes na janela.
2. **Não** agendar N tasks de debounce (uma por mensagem).
3. Após 1.2s, **consolidar** os textos em **um** prompt e responder 1x.

## Constantes

| Nome | Valor | Onde |
|------|-------|------|
| `DEBOUNCE_WINDOW` / `DEBOUNCE_WINDOW_SEC` | **1.2 s** | `telegram.py`, `chat_pipeline.py`, `message_debounce.py` |
| Idempotência longa | Redis SETNX TTL **600 s** | `tg:idem:{update_id}` / `idem:{channel}:{update_id}` |
| Fila curta | Redis `tg:queue:{key}` TTL ~10 s | `telegram._enqueue_message` |
| Lock debounce | Redis `tg:lock:{key}` TTL 5 s | evita double-schedule |

## Workflow

```
Webhook POST /telegram
        │
        ▼
[A] is_duplicate_update(seen, update_id)     ← pure (janela in-memory)
        │  True → status=duplicate (drop)
        ▼
[B] Redis SETNX tg:idem:{update_id} TTL 600s ← idempotência longa
        │  já existe → drop
        ▼
[C] scrub PII + route (comando/state/free-text)
        │  free-text:
        ▼
[D] enqueue → queue_len
        │
        ▼
[E] should_start_debounce(queue_len)
        │  True (len==1) → set lock + schedule _process_telegram_debounce
        │  False         → só append na fila
        ▼
[F] sleep(1.2s)  → GET+DEL fila → textos[]
        │
        ▼
[G] merge_burst_texts(textos)  ← pure (1 prompt)
        │
        ▼
[H] rate limit → agent → send 1 resposta
```

## Helpers puros (`app/services/message_debounce.py`)

| Função | Contrato |
|--------|----------|
| `should_start_debounce(queue_len) -> bool` | `True` **somente** se `queue_len == 1` (primeiro push da janela). |
| `merge_burst_texts(texts) -> str` | ≤2 textos → último; ≥3 → `"[N mensagens] t1 \| t2 \| …"` (cap 600). |
| `is_duplicate_update(seen_set, update_id) -> bool` | `True` se `update_id` já em `seen_set`; senão adiciona e retorna `False`. Ids falsy (0/None/"") não deduplicam. |

Espelham:

- `chat_pipeline.enqueue_message` → `llen == 1`
- `chat_pipeline.resume_burst`
- Camada curta antes de Redis idempotency

## Por que duas camadas de dedupe?

| Camada | Escopo | Persistência |
|--------|--------|--------------|
| `is_duplicate_update` | Burst / redelivery na mesma request path ou worker | Set em memória (teste / futuro middleware) |
| Redis `tg:idem:*` | Replay de webhook entre processos/workers | SETNX 10 min |

A janela de **debounce** (1.2s) **não substitui** idempotência: ela só
agrupa free-text. Duplicatas de `update_id` devem ser cortadas **antes**
do enqueue.

## Integração atual (produção)

- Path legado: `app/api/v1/telegram.py` → `_enqueue_message` + lock +
  `_process_telegram_debounce` + `_resumir_mensagens` (resumo semântico
  quando `len > 2`).
- Path unificado: `app/services/chat_pipeline.py` → `enqueue_message` +
  `process_debounced` + `resume_burst`.

Os helpers de `message_debounce.py` são a **fonte testável** das
regras de decisão; wiring completo nos callers pode migrar
gradualmente (DRY) sem mudar comportamento.

## Testes

```bash
cd backend
env -u PYTHONPATH .venv312/bin/pytest tests/test_message_debounce_g8.py -q
```

## LGPD

- Fila e seen-set usam `update_id` / `chat_id` opacos — sem PII nas chaves.
- Texto enfileirado deve já ter passado por `scrub()` (camada input)
  antes do merge.
