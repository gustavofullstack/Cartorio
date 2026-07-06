# ADR-026: app.core.redis_client — Singleton Async Redis Centralizado

> **Status**: Aceito
> **Data**: 2026-07-06
> **Decisor**: Antigravity (Sonnet 4.6) — sessão 2026-07-06
> **Contexto**: mypy import-not-found em cache_lgpd.py

## Contexto

`app/services/cache_lgpd.py` importava `from app.core.redis_client import get_redis`
but o módulo `app.core` não existia. Isso causava:
- mypy error: `Cannot find implementation or library stub for module named "app.core.redis_client"` [import-not-found]
- Serviços async de cache LGPD não podiam ser usados (ImportError em runtime)

Outros caches do sistema (`emolumento_cache.py`, `agendamento_cache.py`, etc.) usavam
padrão diferente: `_get_redis_client()` local com `redis.Redis.from_url()` **síncrono**.
Cache LGPD precisava de async (serviços LGPD são todos `async def`).

## Decisão

Criar pacote `app.core` com singleton async Redis:
- `app/core/__init__.py` — pacote Python mínimo
- `app/core/redis_client.py` — singleton `get_redis()` + `close_redis()`

Interface:
```python
async def get_redis() -> Any | None:  # None se indisponível
async def close_redis() -> None:      # shutdown limpo
```

Comportamento:
- **Lazy init**: conexão criada na primeira chamada (não no import)
- **Graceful degradation**: retorna `None` se `redis.asyncio` não disponível
- **Singleton global**: `_redis_client` reutilizado entre chamadas
- **decode_responses=True**: respostas já em `str` (evita `.decode()` manual)

## Consequências

### Positivas
- mypy gate restaurado: 0 errors ✅
- Cache LGPD funcionando (`cache_lgpd.py` resolve import)
- Padrão unificado para Redis async em novos serviços
- Graceful degradation: sistema não quebra se Redis ficar offline

### Negativas
- Dois padrões de Redis co-existem: `app.core.redis_client` (async) e `_get_redis_client()` local (sync)
  - Mitigação: documentado como tech debt; migração gradual para `app.core` em sprints futuros
- Singleton pode causar issue se instância Redis for trocada em runtime (raro em prod)

## Alternativas consideradas

### A) Corrigir import em cache_lgpd.py para usar padrão síncrono local
- Pro: zero nova abstração
- Contra: cache LGPD é async, teria que converter para sync OU duplicar padrão inconsistente

### B) Criar `app/services/redis_async.py` (sem pacote core)
- Pro: mantém tudo em `services/`
- Contra: Redis é infra, não serviço de negócio — `core/` é semânticamente correto

### C) Usar `redis.asyncio` direto em cada service (sem singleton)
- Pro: sem estado global
- Contra: múltiplas conexões desnecessárias; não é padrão de performance

## Validação

- mypy: **0 errors** ✅ (era 1 error import-not-found)
- ruff: 0 erros ✅
- pytest: **1796 passed** ✅ (4 novos testes em `test_core_redis_client.py`)
- Coverage: ≥ 90% ✅

## Referências

- Código: `backend/app/core/redis_client.py`
- Código: `backend/app/services/cache_lgpd.py`
- Testes: `backend/tests/test_core_redis_client.py`
- Commit: `16df8f8`

Modified by Gustavo Almeida
