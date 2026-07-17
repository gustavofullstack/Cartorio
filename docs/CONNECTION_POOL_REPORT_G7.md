# G7.08.T4 — Connection pool 25 under load (report)

**Task:** G7.08.T4  
**Agent:** cartorio-dev (Wave 25 slot A1)  
**Data (análise local):** 2026-07-17  
**Escopo:** settings + engine create + observabilidade + recomendação `DB_POOL_SIZE=25`.  
**Status:** **HOLD em load test live** — análise de código + plano de teste; **sem** benchmark RPS em produção/staging nesta sessão.

---

## Resultado executivo

| Item | Valor no código (default) | Template `backend/.env.example` | Docs legados / backlog |
|------|---------------------------|----------------------------------|------------------------|
| `DB_POOL_SIZE` | **20** | 20 | alguns docs dizem **25** (v22 / capacity) |
| `DB_MAX_OVERFLOW` | **10** | 10 | — |
| Capacidade total / worker | **30** | 30 | PgBouncer sketch: 25 base |
| `DB_POOL_RECYCLE` | 3600 s | 3600 | OK |
| `DB_POOL_TIMEOUT` | 30 s | 30 | OK |
| `DB_POOL_PRE_PING` | `True` | `true` | OK |
| Load test sob pool 25 | **não executado** | — | **HOLD** |

**Recomendação (código + env prod):** subir default e template para **`DB_POOL_SIZE=25`** com **`DB_MAX_OVERFLOW=10`** (cap **35**/processo) **após** load test controlado; até lá manter 20/10 e monitorar `cartorio_db_pool_utilization_pct`.

---

## 1. Onde o pool é configurado

### 1.1 Settings (`backend/app/config.py`)

```python
# Pool tuning A15 — defaults calibrados pra carga real
db_pool_size: int = 20
db_max_overflow: int = 10
db_pool_recycle: int = 3600
db_pool_timeout: int = 30
db_pool_pre_ping: bool = True
```

Env vars (Pydantic Settings, case-insensitive):

| Env | Campo | Default código |
|-----|-------|----------------|
| `DB_POOL_SIZE` | `db_pool_size` | 20 |
| `DB_MAX_OVERFLOW` | `db_max_overflow` | 10 |
| `DB_POOL_RECYCLE` | `db_pool_recycle` | 3600 |
| `DB_POOL_TIMEOUT` | `db_pool_timeout` | 30 |
| `DB_POOL_PRE_PING` | `db_pool_pre_ping` | True |

### 1.2 Engine (`backend/app/db.py`)

```python
_engine_kwargs = {
    "pool_pre_ping": settings.db_pool_pre_ping,
    "pool_recycle": settings.db_pool_recycle,
}
if not _is_sqlite:
    _engine_kwargs.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_use_lifo=True,  # Postgres only
    )
engine = create_engine(settings.database_url, **_engine_kwargs)
```

| Comportamento | Detalhe |
|---------------|---------|
| SQLite (tests) | **não** aplica `pool_size` / overflow / timeout (pool default SQLAlchemy / StaticPool em conftest) |
| Postgres | QueuePool com LIFO + pre_ping + recycle |
| Stats | `get_pool_stats()` → `pool_size`, `max_overflow`, `checked_out`, `overflow`, `total_capacity`, `utilization_pct` |

### 1.3 Templates e drift

| Arquivo | `DB_POOL_SIZE` | `DB_MAX_OVERFLOW` | Nota |
|---------|----------------|-------------------|------|
| `backend/.env.example` | 20 | 10 | canônico A15 |
| `.env.example` (raiz) | **10** | **5** | **desatualizado** vs backend |
| `docs/INDEX/BACKLOG.md` | 10 → **25** “FEITO v22” | — | **divergência** vs default código 20 |
| `docs/PERFORMANCE_TUNING.md` | exemplo 20; PgBouncer 25 | 10 | misto |
| `docs/PLAN_100_TASKS_2026-07-14.md` | T017: testar 25 | — | task planejada |
| `SUPER_PLANO_100_TASKS_25_SQUADS_v25.md` | E25.S9.T4: 25→50 | — | roadmap futuro |

**Conclusão drift:** o backlog “25 FEITO” **não** se reflete no default de `Settings` (ainda 20). G7.08.T4 documenta o estado real do código.

---

## 2. Observabilidade já existente

| Superfície | Path / métrica |
|------------|----------------|
| HTTP admin | `GET /api/v1/admin/pool` (header API key) |
| Health DB | `/ready` (ou health DB) inclui `pool: get_pool_stats()` |
| Prometheus | `cartorio_db_pool_size`, `_checked_out`, `_overflow`, `_max_overflow`, `_total_capacity`, `_utilization_pct` |
| Alerta | `CartorioDBPoolExhausted`: `cartorio_db_pool_utilization_pct > 85` for 5m (`infra/prometheus/alerts.yml`) |
| Grafana | panel pool em dashboard overview (`infra/grafana/...`) |
| Testes unitários | `tests/test_db_pool_a15.py`, `test_db_pool_stats.py`, `test_admin_pool_a15_endpoint.py` |

```bash
# Prod (sem secrets no output se possível)
curl -sS -H "X-API-Key: $API_KEY" \
  https://api.2notasudi.com.br/api/v1/admin/pool

curl -sS https://api.2notasudi.com.br/api/v1/metrics/prometheus \
  | grep cartorio_db_pool
```

---

## 3. Capacidade teórica (código)

Fórmula por **processo/worker** uvicorn:

```
total_capacity = pool_size + max_overflow
```

| Cenário | pool_size | max_overflow | cap / worker | workers=4 (prod Makefile) |
|---------|-----------|--------------|--------------|---------------------------|
| **Atual default código** | 20 | 10 | 30 | **120** conexões potenciais |
| **Recomendado G7 (25)** | 25 | 10 | 35 | **140** |
| Legado root `.env.example` | 10 | 5 | 15 | 60 |
| Roadmap E25.S9.T4 | 50 | (TBD) | 50+ | 200+ |

**Cuidado com multi-worker:**  
`make -C backend prod` usa 4 workers → conexões no Postgres ≈ `workers × (pool_size + max_overflow)` **se todos saturarem**.  
Postgres `max_connections` (Supabase self-hosted tipicamente 100–200) deve acomodar:

```
API workers × cap + Supavisor/PgBouncer + Studio + N8N + Chatwoot + crons
```

Se o FastAPI fala com Postgres **via Supavisor/PgBouncer** em transaction mode, `pool_size` alto no app ainda compete no pool do proxy — calibrar em conjunto.

---

## 4. Recomendação: pool 25

### 4.1 Por que 25 (não 50 ainda)

1. Documentação operacional e capacity planning já citam **25** como alvo (PgBouncer sketch + backlog v22).
2. Carga esperada (comentário A15): Evolution + N8N + admin + OpenClaw MCP + Chatwoot ≈ **6 fontes**; 20 base foi calibrado A15; 25 dá ~25% headroom no base pool sem dobrar pressão no Postgres.
3. Subir para 50 (E25.S9.T4) exige benchmark 1000 RPS e revisão `max_connections` — fora do escopo G7.08.T4.

### 4.2 Mudança proposta (quando load test passar)

| Arquivo | De | Para |
|---------|----|------|
| `backend/app/config.py` default | 20 | **25** |
| `backend/.env.example` | 20 | **25** |
| `.env.example` raiz | 10 | **25** (alinhar) |
| Prod env (EasyPanel) | verificar live | `DB_POOL_SIZE=25` |
| `tests/test_db_pool_a15.py` asserts | 20 | 25 (ou parametrizar) |

Overflow sugerido permanece **10** (cap 35) salvo evidência de filas `pool_timeout` em prod.

### 4.3 O que **não** fazer sem medição

- Não setar 50+ em multi-worker 4 sem checar `max_connections`.
- Não desligar `pool_pre_ping` (stale connections em LB/pgBouncer).
- Não confundir `DB_POOL_SIZE` do **Supabase/Supavisor (Elixir)** com o da API Python — incidentes 2026-06-30 usavam env do container Supabase (`DB_POOL_SIZE=5` default Elixir).

---

## 5. Plano de load test (não executado — HOLD)

### 5.1 Pré-requisitos

- [ ] Staging ou janela de baixo uso (não prod peak 09–17 BRT sem aprovação).
- [ ] `DB_POOL_SIZE=25` e `DB_MAX_OVERFLOW=10` no env do serviço API.
- [ ] Métricas Prometheus scrapando; alerta pool > 85% ativo.
- [ ] Observar também: latência p95 `/health`, `/api/v1/health/radar`, erros 503, `pg_stat_activity`.

### 5.2 Endpoints de pressão (leve → pesado)

| Nível | Target | Por quê |
|-------|--------|---------|
| L0 | `GET /health` | sem DB (baseline rede) |
| L1 | `GET /ready` ou health DB | 1 checkout rápido |
| L2 | `GET /api/v1/admin/pool` | stats + auth |
| L3 | listagens autenticadas (protocolos/clientes paginados) | hold de conexão mais longo |
| L4 | webhook Telegram/Evolution sintético (idempotente) | path real multi-service |

### 5.3 Apache Bench (sketch)

```bash
# L1 — 100 concurrent, 5k requests (staging)
ab -n 5000 -c 100 -k \
  https://STAGING_HOST/ready

# Com header se necessário:
# ab -n 2000 -c 50 -H "X-API-Key: $API_KEY" \
#   https://STAGING_HOST/api/v1/admin/pool
```

### 5.4 Locust (sketch)

```python
# scripts/load_pool_locust.py  (exemplo — não committed como suite CI)
from locust import HttpUser, task, between

class CartorioPoolUser(HttpUser):
    wait_time = between(0.01, 0.05)

    @task(5)
    def ready(self) -> None:
        self.client.get("/ready")

    @task(1)
    def pool_stats(self) -> None:
        self.client.get(
            "/api/v1/admin/pool",
            headers={"X-API-Key": self.environment.parsed_options.api_key},
        )
```

```bash
# uv run locust -f scripts/load_pool_locust.py --host=https://STAGING \
#   --users 100 --spawn-rate 10 --run-time 5m --headless
```

### 5.5 Script offline de inventário de config

Ver `scripts/pool_config_inventory_g7.py` (sem rede, sem secrets): imprime defaults do código e fórmula de capacidade.

### 5.6 Critérios de aceite do load test (quando rodar)

| Métrica | Pass | Fail |
|---------|------|------|
| `utilization_pct` picos | < 85% sustentado 5 min | ≥ 85% → alerta atual |
| Erros 5xx atribuíveis a pool | 0 | `TimeoutError` / 503 pool |
| p95 `/ready` | < 200 ms (local/staging saudável) | degradação > 3× baseline |
| `pg_stat_activity` | < `max_connections * 0.8` | approaching limit |
| Comparar 20 vs 25 | 25 reduz queue timeout sem subir CPU DB > 70% | 25 piora contenção DB |

### 5.7 Status load test

| Ambiente | Executado? | Resultado |
|----------|------------|-----------|
| Local SQLite pytest | N/A (sem QueuePool real) | unit tests A15 verdes (defaults 20) |
| Staging Postgres | **Não** | **HOLD** |
| Produção | **Não** | **HOLD** |

---

## 6. Testes automatizados existentes (sem load)

| Teste | O que cobre |
|-------|-------------|
| `test_db_pool_a15.py` | defaults 20/10/3600/30/True; mock capacity 30; pre_ping; métricas |
| `test_db_pool_stats.py` | `get_pool_stats` sqlite zero / mock 20+10 |
| `test_admin_pool_a15_endpoint.py` | HTTP `/admin/pool` shape |
| `tests/conftest.py` | força env `DB_POOL_SIZE=20` etc. para isolamento |

**Gap de teste:** não há `test_postgres_pool.py` com 25 conexões reais (T017 no plano 100 tasks). Opcional pós-G7: unit test que só valida `Settings(db_pool_size=25)` + mock `total_capacity == 35`.

---

## 7. Checklist de deploy se adotar 25

1. Atualizar env EasyPanel / Swarm: `DB_POOL_SIZE=25`.
2. Confirmar `max_connections` e pool Supavisor ≥ demanda multi-worker.
3. Rolling restart API (`scale 0→1` se host-mode).
4. `curl .../admin/pool` → `"pool_size": 25`.
5. Observar Grafana 24h (utilization, latency, errors).
6. Só então PR alterando default em `config.py` + asserts de teste.

---

## 8. Status G7.08.T4

| Item | Status |
|------|--------|
| Inventário settings + engine | **DONE** |
| Defaults e templates | **DONE** (drift 20 vs “25 FEITO” documentado) |
| Recomendação pool 25 | **DONE** (condicional a load test) |
| Observabilidade / alertas | **DONE** |
| Sketch ab/locust | **DONE** |
| Load test live sob 25 | **HOLD** |
| Mudança de default no código | **não feita** (HOLD até medição) |

---

Modified by Gustavo Almeida
