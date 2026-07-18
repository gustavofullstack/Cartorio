# Lesson 228 — G8.12.T3 — Padronizar chaves Redis via RedisKey helper (DRY)

- **Date**: 2026-07-18 (Wave 47)
- **Rein**: `cartorio-dev`
- **Task ID**: G8.12.T3 (Squad 6 DRY — Redis key pattern unification)
- **Branch**: `feat/g8-12-t3-redis-key-pattern`
- **Commit SHA**: `8df43df`

## Resumo

Antes desta task, o backend do cartorio tinha **N variacoes independentes**
de nomenclatura de chaves Redis, espalhadas em ~10 arquivos. O inventario
abaixo foi levantado via:

```bash
grep -rnE '(f"idem:|f"chat:|f"redlock:|"cartorio:|"bot:mute:|"emolumento:|"ratelimit:|prefix = |MUTE_KEY_PREFIX)' \
  backend/app/ 2>&1 | head -60
```

### Inventario pre-refactor (N variacoes)

| Pattern                          | Arquivos                                    |
| -------------------------------- | ------------------------------------------- |
| `bot:mute:<channel>:<conv>`     | `app/services/bot_mute.py`                  |
| `emolumento:<tipo>:<valor>`     | `app/services/emolumento_cache.py`          |
| `redlock:<name>`                | `app/services/redlock.py`                   |
| `ratelimit:session:<hash>`      | `app/services/rate_limit.py`                |
| `ratelimit:ip:<hash>`           | `app/services/rate_limit.py`                |
| `ratelimit:apikey:<hash>:<b>`   | `app/services/rate_limit_by_key.py`          |
| `sliding:ip:<hash>`             | `app/services/rate_limit_by_key.py`          |
| `idem:<channel>:<update_id>`    | `app/services/chat_pipeline.py`             |
| `idempotency:<sha256>`          | `app/middleware/idempotency.py`             |
| `chat:mute:<channel>:<conv>`    | `app/services/bot_mute.py` (alias)          |
| `lock:dist:<name>`              | `app/services/dist_lock.py`                 |
| `cartorio:atendimentos` etc.    | `app/services/redis_bus.py` (pub/sub — ja canonico) |
| `cartorio:slow_queries`         | `app/services/slow_queries.py` (ja canonico) |
| `cache:lookup:<kind>:<hash>`    | `app/services/redis_doc_keys.py` (ja canonico) |

**Total: 13+ variantes** de prefixo/estrutura.

### Decisao de padrao

**Pattern canonico**: `cartorio:<namespace>:<scope>:<id>`

Exemplos validos:

```
cartorio:session:telegram:user_123
cartorio:idem:webhook:abc-def-123
cartorio:rate_limit:api_key:n8n_main_2999
cartorio:cache:emolumento:escritura_5000
cartorio:bot_mute:telegram:42
cartorio:lock:redlock:alembic_migration
```

**Regex canonico** (validado em todos os testes):

```regex
^cartorio:[a-z][a-z0-9_]{1,63}:[a-z][a-z0-9_]{1,63}:[A-Za-z0-9_.\-]{1,128}$
```

## Implementacao

### Helper central: `backend/app/core/redis_keys.py`

- Constante `PREFIX = "cartorio"` (UNICA fonte da verdade no codigo)
- Classe `RedisKey` com metodos estaticos:
  - `session(scope, scope_id)` → `cartorio:session:<scope>:<id>`
  - `idempotency(scope, key)` → `cartorio:idem:<scope>:<key>`
  - `rate_limit(scope, scope_id, bucket=None)` → `cartorio:rate_limit:<scope>:<id>[_<bucket>]`
  - `cache(entity, entity_id)` → `cartorio:cache:<entity>:<id>`
  - `bot_mute(channel, conv_key)` → `cartorio:bot_mute:<channel>:<conv>`
  - `lock(name)` → `cartorio:lock:redlock:<name>`
- `@lru_cache(maxsize=512)` em `_build()` para evitar realocacao em hot path (rate limit por request)
- `normalize_legacy(key)` aceita 13+ formatos legados e mapeia para canonico
- `looks_like_raw_pii(key)` — detector de raw-CPF/CNPJ para auditoria
- Validacao estrita via regex em cada factory

### Callers refatorados (5 arquivos)

| Caller                                | Antes                            | Depois |
| ------------------------------------- | -------------------------------- | ------ |
| `app/services/bot_mute.py`            | `bot:mute:<ch>:<conv>`           | `cartorio:bot_mute:<ch>:<conv>` |
| `app/services/emolumento_cache.py`    | `emolumento:<tipo>:<valor>`      | `cartorio:cache:emolumento:<tipo>_<valor>` |
| `app/services/redlock.py`             | `redlock:<name>`                 | `cartorio:lock:redlock:<name_sanitized>` |
| `app/middleware/idempotency.py`       | `idempotency:<sha>`              | `cartorio:idem:default_post:<sha>` |
| `app/services/chat_pipeline.py`       | `idem:<ch>:<id>` + `rl:<ch>:<k>` | `cartorio:idem:chat_pipeline:<ch>_<id>` + `cartorio:rate_limit:chat:<ch>_<k>` |

### Tests adicionados: 19 (G8.12.T3 - test_redis_key_helper.py)

Cobertura:
- Formato basico (5 factories)
- Validacao regex canonico
- Validacao de input (empty raises, special chars sanitization)
- Compatibilidade legacy (10+ mappings)
- LGPD anti-regression (looks_like_raw_pii)
- Determinismo / hot-path cache

### Tests existentes migrados (3 arquivos)

- `tests/test_bot_mute_g8.py` (3 assertions atualizadas)
- `tests/test_redlock.py` (5 assertions atualizadas)
- `tests/test_redlock_a20_v2.py` (`test_key_formato_canonico`)

## Honesty gate (verificado)

```bash
cd backend && uv run pytest tests/test_redis_key_helper.py --no-cov -v
# → 19 passed

uv run pytest --no-cov -q -k "redis or idempotency or rate_limit or cache or emolumento or redlock or bot_mute"
# → 386 passed (somando helpers + callers refatorados)

uv run ruff check app/core/redis_keys.py app/middleware/idempotency.py \
  app/services/bot_mute.py app/services/chat_pipeline.py \
  app/services/emolumento_cache.py app/services/redlock.py
# → All checks passed!

uv run mypy app/core/redis_keys.py app/middleware/idempotency.py \
  app/services/bot_mute.py app/services/chat_pipeline.py \
  app/services/emolumento_cache.py app/services/redlock.py
# → Success: no issues found in 6 source files
```

## Follow-up waves (callers ainda NAO refatorados)

Identificados mas fora do escopo desta task:

| Caller                       | Path                                       | Prioridade |
| ---------------------------- | ------------------------------------------ | ---------- |
| `app/services/rate_limit.py`     | 2 chaves (`ratelimit:session`, `ratelimit:ip`) | P1 (security — DDoS shield) |
| `app/services/rate_limit_by_key.py` | 3 chaves (`ratelimit:apikey`, `sliding:ip`, `ratelimit:ip`) | P1 |
| `app/services/sliding_window.py`    | key passada como arg, NAO eh construida     | P2 |
| `app/services/cache_lgpd.py`        | NAO cria chaves — usa apenas cache.get/set  | n/a |
| `app/services/dist_lock.py`         | `LOCK_PREFIX = "cartorio:lock:"` — ja perto | P3 |
| `app/services/dialog_history.py`    | chave ainda nao inventariada               | P3 |
| `app/services/sessions.py`          | nao existe — eh `cache_lgpd`               | n/a |
| `app/services/stream_buffer.py`     | nao inventariado                            | P3 |
| `app/services/encrypted_dump.py`    | nao inventariado                            | P3 |
| `app/services/telegram_error_handler.py` | nao inventariado                       | P3 |
| `app/services/chat_pipeline.py`     | Some pub/sub ja canonicas, mas ha outras   | P2 |
| Pubs/subs                        | ja canonicos (cartorio:atendimentos, cartorio:protocolos) | done |

### Wave 47.5 (proposto) — backend services high-traffic
1. `app/services/rate_limit.py`
2. `app/services/rate_limit_by_key.py`
3. `app/services/sliding_window.py`

### Wave 48 — cleanup margin
4. `app/services/redis_ttl_inventory.py` (atualizar TTL_REGISTRY com chaves canonicas)
5. `app/services/redis_doc_keys.py` (migrar prefixo `cache:lookup:...` para `cartorio:cache:lookup:...`)
6. `app/services/redis_bus.py` channels (ja canonicos, talvez uniformizar docs)

## Lições reaproveitaveis (cross-rein)

1. **Pattern unificado > no pattern** — 13 variantes de prefixo eh divida
   tecnica que volta com juros em monitoramento e auditoria. O fix eh
   1 helper central + 1 regex de validacao + migration incremental.

2. **`@lru_cache` em factories puras** — `_build()` eh chamada em loop
   (rate limit por request). Sem cache, gera lixo de short-lived strings
   que pressionam o GC. Com `lru_cache(maxsize=512)` (cobre qualquer
   combinacao real), o output eh um singleton por combinacao (ns, scope, id).

3. **Legacy normalizer primeiro** — antes de forcar todos os callers a
   migrar, escreva `normalize_legacy()` que aceita as variacoes antigas
   E produz o formato canonico. Isso desacopla o helper de qualquer
   breaking change — leituristas e migradores convivem pacificamente.

4. **`is_valid()` como contract test** — toda chave canonica DEVE casar o
   regex. Os 19 testes em `test_redis_key_helper.py` fixam esse contrato
   e falham imediatamente se alguem quebrar o pattern (e.g., esquecer o
   prefixo, introduzir caractere proibido).

5. **LGPD via `looks_like_raw_pii()`** — detector de 11/14 digitos
   contiguos ja existia em `app.services.redis_doc_keys`. Reaproveitar
   a mesma heuristica no helper central evita drift entre deteccoes e
   mantem a fronteira PII unica.

Modified by Gustavo Almeida — Wave 47 / Squad 6 DRY.
