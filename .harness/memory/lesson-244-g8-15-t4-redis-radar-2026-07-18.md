# Lesson 244 — G8.15.T4 Redis queue radar (2026-07-18)

## Task

Integrar status das filas Redis (idempotency / rate_limit / dlq / lock /
bot_mute / session) no endpoint `/api/v1/health/radar/expanded`.

## Implementação

### O que mudou em `health_radar_expanded.py`

1. **Constantes de scan** (anti-OOM):
   - `REDIS_SCAN_HARD_CAP = 50_000` — para incremento de count quando passa.
   - `REDIS_TTL_SAMPLE_LIMIT = 256` — amostra TTL em até N chaves por prefixo.
   - `RATE_LIMIT_EXPIRING_SOON_SEC = 10` — bucket com TTL ≤ 10s = "expiring soon".

2. **Função pura `_scan_count(redis_client, pattern, hard_cap, sample_ttls, expiring_soon_sec)`**:
   - SCAN com `count=500` hint; cursor loop; respects hard cap.
   - Sampling TTL opcional (até `sample_ttls` chaves) para detectar drift
     em buckets rate-limit / lock-presence.
   - Fail-open: exception no SCAN retorna `(count_parcial, 0)` com warning log.

3. **Função sync `_check_redis_queues_sync(redis_url, ...)`** (offload via `asyncio.to_thread`):
   - 1 PING (saude geral)
   - 6 SCANs sequenciais por namespace (idempotency / rate_limit / lock /
     bot_mute / session + DB query para DLQ)
   - DLQ depth vem de `SELECT COUNT(*) FROM outbox_message WHERE status='PENDING'`
     (DLQ canonica eh Postgres, NAO Redis LIST)
   - Cada prefixo tem aliases legados alem do canonico G8.12.T3 (backward-compat).
   - Status logico: `up` (tudo dentro do cap) / `warn` (1+ namespace saturado)
     / `down` (Redis offline).

4. **Async wrapper `_check_redis_queues_category()`**:
   - Chama `_check_redis_queues_sync` via `asyncio.to_thread` (nao bloqueia event loop).
   - Try/except total: exception no helper interno -> status="warn".

5. **Endpoint**: adiciona `redis_queues_coro` ao `asyncio.gather`. Metadata
   bumped de 0.6.0 para 0.6.1 + 3 campos novos (`redis_scan_hard_cap`,
   `redis_ttl_sample_limit`, `rate_limit_expiring_soon_sec`).

6. **Aggregation**: `_aggregate_overall` NAO trata `redis_queues` como
   critico (NAO dispara red). Decisao proposital: categoria `health.redis`
   ja cobre critical-down. `redis_queues` sobe para `yellow` quando
   `warn`/`down`.

### Por que DLQ vem do DB (nao de Redis LIST)

`app/services/dlq.py` define que a DLQ canonica vive em
`outbox_message` (Postgres). Redis nao eh usado como DLQ no projeto.
O gauge `dlq_depth{queue}` ja eh exposto via Prometheus
(`/api/v1/metrics/prometheus`); o radar `redis_queues` eh
**complementar** (snapshot on-demand).

### LGPD-by-design

- Retorna apenas contagens inteiras + boolean `exhausted`.
- Zero PII raw em qualquer chave.
- Verificacao automatica via `app.core.redis_keys.looks_like_raw_pii`.
- Assertion explicita `pii_safe_labels=True` em todos os tests.

## Testes (14 adicionados em `test_health_radar_expanded_g8.py`)

Padrao: `fakeredis.FakeRedis(decode_responses=True)` (sync) com chaves
criadas via `RedisKey` helper canonico G8.12.T3. Cada teste exercita
1 cenario canonico:

1. `_scan_count` com namespace vazio
2. `_scan_count` com 3 canonicas + 2 legadas
3. `_scan_count` respeita hard cap
4. `_scan_count` amostra TTLs (expiring soon)
5. `_scan_count` trata Redis offline (ConnectionError)
6. `_check_redis_queues_sync` populado completo (fakeredis)
7. `_check_redis_queues_sync` Redis offline -> status="down" + queues 0
8. `_check_redis_queues_sync` saturation -> status="warn"
9. LGPD: zero PII raw em chaves (validacao automatica)
10. DLQ vem do DB outbox_message
11. Async wrapper fail-open (Redis offline)
12. Async wrapper fail-open (exception catastrófica)
13. E2E via TestClient inclui categoria redis_queues
14. Contrato: 6 keys exatas (idempotency/rate_limit/dlq/lock/bot_mute/session)

## Pitfalls encontrados

### 1. `fakeredis.FakeRedis(decode_responses=True)` + `patch.object(client, "ping", ...)`

NÃO funciona para simular Redis offline: o `patch.object` é um context
manager que aplica o patch no momento do `with`, mas o retorno do
`from_url` ja foi avaliado — o `r.ping()` chamado depois pelo
`_check_redis_queues_sync` nao enxerga o patch.

**Solução**: usar `MagicMock()` direto como retorno de `from_url`:

```python
broken = MagicMock()
broken.ping.side_effect = ConnectionError("offline")
monkeypatch.setattr(redis_sync, "from_url", lambda *a, **kw: broken)
```

### 2. `RedisKey.lock(name)` aceita 1 argumento, NAO 2

A factory G8.12.T3 do lock toma so o `name` (o escopo `redlock` ja eh
hardcoded internamente). Errar e chamar `RedisKey.lock("redlock", "x")`
gera `TypeError: takes 1 positional argument but 2 were given`.

```python
# CERTO:
RedisKey.lock("emitir_protocolo:42")           # canonico
RedisKey.lock("redlock_legacy_lock")           # evita 2-args

# ERRADO:
RedisKey.lock("redlock", "emitir_protocolo:42") # TypeError
```

### 3. Scope com 1 caractere falha o pattern canonico

`RedisKey.idempotency("w", "a")` -> `cartorio:idem:w:a` -> fail
(pattern exige `[a-z][a-z0-9_]{1,63}` = no minimo 2 chars no escopo).

**Solução**: sempre usar 2+ chars (`"webhook"`, `"post"`, `"wp"`, `"tg"`).

### 4. DLQ depth NAO esta em Redis LIST

A DLQ canonica eh Postgres. Ler de Redis LIST daria 0 sempre. Ver
`app/services/dlq.py::depth()` — fonte de verdade eh `outbox_message`.

### 5. `metadata.version` bump quebra testes que hardcodam

Tests em `test_health_radar_expanded.py::test_radar_endpoint_metadata_includes_version`
e `test_g7_wave24_integration.py::test_health_radar_expanded_coerce_non_dict_fallback`
fazem `assert meta["version"] == "0.6.0"`. Bumped para `0.6.1` requer
atualizar esses 2 tests.

## Métricas

- Radar suite (pytest -k radar): **88 passed, 1 skipped** (antes: 74)
- Full pytest: **4170 passed, 23 skipped** (antes: 4085 — diff inclui +14 novos + alguns baseline)
- ruff: clean
- mypy app/: clean (195 files, 0 errors)

## Modified by

cartorio-dev (Gustavo Almeida) — Wave 48 G8.15.T4 — 2026-07-18.