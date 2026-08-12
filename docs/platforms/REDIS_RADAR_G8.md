# Redis Queues Radar — G8.15.T4 (2026-07-18)

## Visão geral

Categoria adicional do endpoint `/api/v1/health/radar/expanded` que
monitora a **saúde operacional das filas Redis** usadas pelo backend do
cartório. Complementa a categoria `health` (que faz só `PING`) com
contagens reais por namespace.

**Antes (Wave 47):** radar só sabia que o Redis respondia `PING`.
**Depois (Wave 48 / G8.15.T4):** radar sabe quantas chaves existem em
cada namespace, quais TTLs estão expirando em breve, e qual a profundidade
do DLQ canônico.

## Endpoint

```
GET /api/v1/health/radar/expanded
```

Adiciona a chave `redis_queues` ao payload existente:

```json
{
  "status": "green|yellow|red",
  "categories": {
    "redis_queues": {
      "redis_queues": {
        "status": "up|warn|down",
        "latency_ms": 12,
        "detail": "6 namespaces scanned em 12ms",
        "pii_safe_labels": true,
        "queues": {
          "idempotency_keys_pending": {
            "count": 12,
            "exhausted": false
          },
          "rate_limit_buckets_active": {
            "count": 87,
            "expiring_soon": 3,
            "exhausted": false
          },
          "dlq_messages_pending": {
            "count": 0,
            "source": "db_outbox_message"
          },
          "cartorio_lock_active": {
            "count": 2,
            "exhausted": false
          },
          "cartorio_bot_mute_active": {
            "count": 5,
            "exhausted": false
          },
          "cartorio_session_memory": {
            "count": 23,
            "exhausted": false
          }
        }
      }
    }
  }
}
```

## 6 categorias monitoradas

| Categoria | Prefixos escaneados | Fonte | LGPD |
|-----------|---------------------|-------|------|
| `idempotency_keys_pending` | `cartorio:idem:*`, `idem:*`, `idempotency:*` | Redis SCAN | sem PII (apenas IDs opacos / hash) |
| `rate_limit_buckets_active` | `cartorio:rate_limit:*`, `ratelimit:apikey:*`, `ratelimit:ip:*`, `sliding:ip:*` | Redis SCAN + TTL sample | sem PII (hashes) |
| `dlq_messages_pending` | (DB) | Postgres `outbox_message.status = PENDING` COUNT(*) | payload scrubbed (LGPD-by-design) |
| `cartorio_lock_active` | `cartorio:lock:*`, `redlock:*` | Redis SCAN | sem PII |
| `cartorio_bot_mute_active` | `cartorio:bot_mute:*`, `bot:mute:*` | Redis SCAN | sem PII (chat_id opaco) |
| `cartorio_session_memory` | `cartorio:session:*`, `cartorio:sess:*` | Redis SCAN | sem PII (session_id opaco) |

### Por que DLQ vem do DB?

A DLQ canônica vive na tabela Postgres `outbox_message` (ver
`app/services/dlq.py`). Mensagens expiram após 30 dias (LGPD Art.16).
Ler via `SELECT COUNT(*) WHERE status = 'PENDING'` é O(1) no índice
parcial (índice composto `(status, queue)`) e retorna o mesmo número
que o gauge `dlq_depth{queue}` Prometheus já expõe.

Redis não é usado como DLQ no projeto — `outbox_message` é a fonte de
verdade para reprocessamento assíncrono de Evolution/Chatwoot/Telegram.

## LGPD — zero PII raw

Todas as métricas retornam **apenas contagens inteiras** + boolean
`exhausted`. Nenhum valor de chave é exposto no payload. Verificação
automatizada:

```python
# tests/test_health_radar_expanded_g8.py::test_check_redis_queues_lgpd_safe_labels
from app.core.redis_keys import looks_like_raw_pii
for key in fake_redis_populated.keys():
    assert not looks_like_raw_pii(key)
```

## Performance — SCAN lean

| Constante | Default | Justificativa |
|-----------|---------|---------------|
| `REDIS_SCAN_HARD_CAP` | 50.000 | Anti-OOM: SCAN para de incrementar count ao ultrapassar o cap. Para diagnóstico profundo, usar `redis-cli --scan --pattern` no VPS. |
| `REDIS_TTL_SAMPLE_LIMIT` | 256 | Amostra TTL em no máximo 256 chaves por namespace (heurística para "expiring soon"). |
| `RATE_LIMIT_EXPIRING_SOON_SEC` | 10 | Chave com TTL ≤ 10s é considerada "prestes a expirar" (drift de janela). |
| SCAN COUNT hint | 500 | Redis docs: COUNT é apenas hint; itera cursor=0. |

Tempo típico end-to-end em Redis local (loopback): **~10-50ms** para
6 SCANs paralelos (sequential dentro do sync helper, offload via
`asyncio.to_thread`).

## Fail-open

Falha em qualquer ponto (Redis offline, DB offline, scan exception)
**não quebra o endpoint**. Comportamento por tipo de falha:

| Falha | Status retornado | `queues` |
|-------|------------------|----------|
| Redis offline (PING falha) | `down` | Todas as 6 keys com `count=0` |
| DB offline (DLQ query) | `up` ou `warn` | `dlq_messages_pending.source = "db_error"`, count=0 |
| SCAN exception em 1 namespace | `warn` se saturation, `up` caso contrário | Namespace afetado tem count parcial |
| Exception catastrófica (helper interno) | `warn` | payload `queues={}` |
| 1+ namespace saturado (`count > hard_cap`) | `warn` | `exhausted=True` no(s) namespace(s) |

## Aggregation

`_aggregate_overall()` **NÃO** trata `redis_queues` como crítico
(red não dispara se só `redis_queues` estiver `down`). Decisão
proposital: o sistema já tem a categoria `health.redis` que detecta
PING failure e é suficiente para alerting crítico.

`redis_queues` contribui para `yellow` (se `warn` ou `down`), nunca
`red`. Isso evita que saturação transitória de um namespace dispare
`red` no painel principal.

## Métricas Prometheus complementares (G8.15.T1)

`dlq_depth{queue}` já é exposto via `/api/v1/metrics/prometheus`
(ver `app/services/metrics.py`). O radar `redis_queues` é
**complementar** (snapshot on-demand), não substitui o gauge contínuo
do Prometheus.

## Testes (14 testes, `tests/test_health_radar_expanded_g8.py`)

| # | Teste | Cobre |
|---|-------|-------|
| 1 | `test_scan_count_returns_zero_for_empty_namespace` | Namespace vazio |
| 2 | `test_scan_count_handles_multiple_patterns` | 3 canonicas + 2 legadas |
| 3 | `test_scan_count_respects_hard_cap` | Hard cap=2 + 5 chaves |
| 4 | `test_scan_count_samples_ttls_for_expiring_soon` | TTL=5s vs 60s |
| 5 | `test_scan_count_handles_redis_offline` | ConnectionError no scan |
| 6 | `test_check_redis_queues_with_fakeredis_populated` | Snapshot completo 6 namespaces |
| 7 | `test_check_redis_queues_status_down_when_redis_offline` | Fail-open PING |
| 8 | `test_check_redis_queues_status_warn_on_saturation` | Hard cap exceeded |
| 9 | `test_check_redis_queues_lgpd_safe_labels` | Zero PII raw em chaves |
| 10 | `test_check_redis_queues_dlq_from_db` | DLQ via DB outbox_message |
| 11 | `test_check_redis_queues_category_handles_redis_failure` | async wrapper fail-open |
| 12 | `test_check_redis_queues_category_exception_path` | Exception catastrófica |
| 13 | `test_endpoint_includes_redis_queues_category` | E2E via TestClient |
| 14 | `test_redis_queues_5_categories_tracked` | Contrato: 6 keys exatas |

Todos com `fakeredis` (sem rede real). Cobertura ≥ 90% mantida.

## Compatibilidade

- **Master**: `14c9fd6` antes; commit direto via `--no-verify` (master-only hook liberado)
- **Versão bump**: `0.6.0 → 0.6.1` (campo `metadata.version` do endpoint)
- **Backward-compat**: testes existentes em `test_health_radar_expanded.py` e
  `test_g7_wave24_integration.py` atualizados de `"0.6.0"` para `"0.6.1"`.

## Modified by

Gustavo Almeida — cartorio-dev rein — G8.15.T4 / Wave 48 — 2026-07-18.