# Performance Tuning — Cartório Chatbot

> Guia de otimização de performance para API, banco, cache e integrações.
> Última atualização: 2026-06-26.

## TL;DR

**SLO Targets**:
- API: p95 < 500ms, p99 < 1s
- N8N: p95 < 5s, p99 < 30s
- OpenClaw: p95 < 5s (thinking ON)
- DB query: p95 < 200ms
- Cache hit rate: > 80%

**Ferramentas**:
- `pytest --durations=10` - testes mais lentos
- `/admin/slow-queries` - queries lentas em prod
- Prometheus + Grafana - métricas
- `EXPLAIN ANALYZE` - plano de execução

---

## Índice

1. [API Performance](#1-api-performance)
2. [Database Performance](#2-database-performance)
3. [Cache Strategy](#3-cache-strategy)
4. [N8N Performance](#4-n8n-performance)
5. [OpenClaw Performance](#5-openclaw-performance)
6. [Network & HTTP](#6-network--http)
7. [Profiling e Debugging](#7-profiling-e-debugging)
8. [Capacity Planning](#8-capacity-planning)

---

## 1. API Performance

### 1.1 Async/Await Everywhere

```python
# ✅ Async para I/O
async def get_cliente(id: UUID) -> Cliente:
    async with get_db() as session:
        result = await session.execute(
            select(Cliente).where(Cliente.id == id)
        )
        return result.scalar_one_or_none()

# ❌ Sync bloqueia event loop
def get_cliente_sync(id: UUID) -> Cliente:
    with get_db() as session:
        return session.query(Cliente).filter_by(id=id).first()
```

### 1.2 Eager Loading (Evitar N+1)

```python
# ❌ N+1 problem (1 + N queries)
clientes = await session.execute(select(Cliente))
for c in clientes:
    protocolos = await session.execute(
        select(Protocolo).where(Protocolo.cliente_id == c.id)
    )

# ✅ Eager loading (1 query)
from sqlalchemy.orm import selectinload
clientes = await session.execute(
    select(Cliente).options(selectinload(Cliente.protocolos))
)
```

### 1.3 Pagination

```python
# ✅ Sempre paginar
@router.get("/clientes", response_model=list[ClienteResponse])
async def listar(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service: ClienteService = Depends(),
):
    return await service.listar(skip=skip, limit=limit)

# ❌ Nunca retornar tudo
@router.get("/clientes/all")  # NUNCA!
async def listar_tudos():
    return await service.listar()  # pode retornar 1M rows
```

### 1.4 Connection Pool

```python
# backend/app/db.py
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

engine = create_async_engine(
    settings.database_url,
    pool_size=20,           # conexões permanentes
    max_overflow=10,        # extras em pico
    pool_timeout=30,        # timeout para obter conexão
    pool_recycle=3600,      # reciclar a cada 1h
    pool_pre_ping=True,     # validar antes de usar
    echo=False,             # SQL log (dev only)
)
```

### 1.5 Compressão HTTP

```python
# backend/app/main.py
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
# Comprime responses > 1KB (JSON, HTML)
```

### 1.6 HTTP/2

```bash
# Traefik já suporta HTTP/2 por padrão
# Verificar:
curl -I --http2 https://api.2notasudi.com.br/health
# Esperado: HTTP/2 200
```

---

## 2. Database Performance

### 2.1 Índices Estratégicos

```sql
-- Single column
CREATE INDEX CONCURRENTLY ix_clientes_cpf_hash ON clientes (cpf_hash);

-- Composto (ordem importa!)
CREATE INDEX CONCURRENTLY ix_protocolos_cliente_status 
  ON protocolos (cliente_id, status);

-- Parcial
CREATE INDEX CONCURRENTLY ix_protocolos_abertos 
  ON protocolos (cliente_id) 
  WHERE status = 'aberto';

-- GIN (JSONB / full-text)
CREATE INDEX CONCURRENTLY ix_protocolos_dados_gin 
  ON protocolos USING GIN (dados);

-- BRIN (tabelas grandes com ordem natural)
CREATE INDEX CONCURRENTLY ix_audit_log_created_brin 
  ON audit_log USING BRIN (created_at);
```

### 2.2 Query Optimization

```sql
-- ❌ Subquery correlacionada (lenta)
SELECT c.nome, 
       (SELECT count(*) FROM protocolos p WHERE p.cliente_id = c.id) as total
FROM clientes c;

-- ✅ JOIN com agregação (1 query)
SELECT c.nome, count(p.id) as total
FROM clientes c
LEFT JOIN protocolos p ON p.cliente_id = c.id
GROUP BY c.id, c.nome;

-- ❌ SELECT *
SELECT * FROM clientes;

-- ✅ Apenas colunas necessárias
SELECT id, nome, telefone FROM clientes;

-- ❌ LIKE '%text%' (não usa índice)
SELECT * FROM clientes WHERE nome LIKE '%silva%';

-- ✅ Full-text search (usa índice GIN)
SELECT * FROM clientes WHERE to_tsvector('portuguese', nome) @@ to_tsquery('silva');
```

### 2.3 EXPLAIN ANALYZE

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE) 
SELECT * FROM clientes WHERE cpf_hash = 'abc123';

-- Sinais de problema:
-- Seq Scan em tabela grande → falta índice
-- rows=N muito diferente → estatísticas desatualizadas
-- Sort em memória → falta índice
```

### 2.4 Vacuum e Analyze

```sql
-- Atualizar estatísticas (diário via pg_cron)
ANALYZE;

-- Liberar tuplas mortas
VACUUM clientes;

-- Liberar espaço em disco (locka tabela!)
-- APENAS em horário de baixo uso
VACUUM FULL clientes;
```

### 2.5 Connection Pooling (PgBouncer)

```yaml
# PgBouncer config (futuro)
[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 5
```

---

## 3. Cache Strategy

### 3.1 O que Cachear

```
✅ Tabelas de consulta (emolumentos, tabelas de referência)
✅ Respostas de APIs externas (Evolution, Chatwoot, OpenClaw)
✅ Sessões de usuário (TTL 30min)
✅ Cálculos pesados (emolumento cálculo, métricas)
✅ Health check results (TTL 10s)

❌ NÃO cachear:
- Dados pessoais de clientes (LGPD)
- Audit log (compliance)
- Tokens/secrets
- Transações em andamento
```

### 3.2 Cache Redis (E8.A21)

```python
# backend/app/services/emolumento_cache.py
import json
from redis.asyncio import Redis

redis = Redis.from_url(settings.redis_url)

async def get_emolumento(tipo: str) -> dict | None:
    """Cache 24h com pub/sub invalidation."""
    key = f"emolumento:{tipo}"
    
    # Try cache
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    
    # Cache miss: query DB
    result = await db.execute(
        select(Emolumento).where(Emolumento.tipo == tipo)
    )
    emolumento = result.scalar_one_or_none()
    
    if emolumento:
        data = {
            "tipo": emolumento.tipo,
            "valor": float(emolumento.valor),
            "prazo_dias": emolumento.prazo_dias,
        }
        # Cache por 24h
        await redis.setex(key, 86400, json.dumps(data))
        
        # Subscribe para invalidation
        # (pub/sub configurado em services)
        
        return data
    return None

async def invalidate_emolumento(tipo: str | None = None):
    """Invalida cache por tipo ou full."""
    if tipo:
        await redis.delete(f"emolumento:{tipo}")
    else:
        # Full invalidation
        async for key in redis.scan_iter("emolumento:*"):
            await redis.delete(key)
```

### 3.3 Cache Hit Rate

```bash
# Ver hit rate
ssh vps-cartorio "redis-cli -p 6379 -a \$REDIS_AUTH INFO stats | grep keyspace_hits"
ssh vps-cartorio "redis-cli -p 6379 -a \$REDIS_AUTH INFO stats | grep keyspace_misses"

# Calcular
hits=100000
misses=20000
echo "scale=2; $hits / ($hits + $misses) * 100" | bc
# Esperado: > 80%
```

### 3.4 Cache Warming (E8.A22)

```python
# backend/app/services/cache_warming.py
# Roda às 06:00 (antes do expediente)
async def warm_cache():
    """Pre-aquece cache antes do pico de uso."""
    tipos = [
        "reconhecimento_firma",
        "autenticacao",
        "procuracao",
        "escritura_compra_venda",
        # ... 50+ tipos
    ]
    
    for tipo in tipos:
        await get_emolumento(tipo)  # popula cache
    
    logger.info("cache_warming_completed", extra={"tipos": len(tipos)})
```

### 3.5 Multi-Layer Cache

```
L1: In-process (Python dict) - 1ms
L2: Redis (compartilhado) - 5ms
L3: DB - 50-200ms

Padrão: L1 → L2 → L3
```

```python
# L1: in-process (LruCache)
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_emolumento_l1(tipo: str) -> dict:
    # Try L2 (Redis)
    cached = redis.get(f"emolumento:{tipo}")
    if cached:
        return json.loads(cached)
    
    # Try L3 (DB)
    return query_db(tipo)
```

---

## 4. N8N Performance

### 4.1 Padrões Aplicados (B07-B10)

| Padrão | Aplicado | Métrica |
|--------|---------|---------|
| **B07 Retry 3x exp** | 63/63 HTTP nodes | 1s→5s→15s |
| **B08 Timeout 5s/10s** | 130/130 nodes | Default 5s |
| **B09 Logs JSON** | Todos WFs | X-Correlation-ID |
| **B10 Métricas Prometheus** | Todos WFs | count, latency, error rate |

### 4.2 Otimizar Workflows

```javascript
// Code node: usar Set ao invés de Array.includes
// ❌ Lento (O(n))
const filtered = items.filter(i => i.status === 'active');

// ✅ Rápido (O(1))
const activeIds = new Set(activeItems.map(i => i.id));
const filtered = items.filter(i => activeIds.has(i.id));

// Evitar console.log em loop
// ❌ Spam de logs
for (const item of items) {
  console.log(item);
}

// ✅ Uma linha
console.log(JSON.stringify(items));
```

### 4.3 Batch Processing

```javascript
// ❌ 1 request por item
for (const cliente of clientes) {
  await fetch(`/api/v1/clientes/${cliente.id}`);
}

// ✅ Batch endpoint
await fetch('/api/v1/clientes/batch', {
  method: 'POST',
  body: JSON.stringify({ ids: clientes.map(c => c.id) })
});
```

### 4.4 Code Node Limits

```yaml
# N8N runner
N8N_RUNNERS_MAX_CONCURRENCY=5
N8N_RUNNERS_TASK_TIMEOUT=300
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=168  # 7 dias
```

---

## 5. OpenClaw Performance

### 5.1 Thinking ON (Adaptive)

```json
// agent.json
{
  "thinking": {
    "enabled": true,
    "mode": "adaptive",  // só pensa quando necessário
    "budget_tokens": 10000
  }
}
```

**Benefício**: Reduz latência em perguntas simples (sem thinking) e mantém qualidade em perguntas complexas (com thinking).

### 5.2 Contexto 1M Tokens

```json
// models.json
{
  "providers": {
    "opencode_go": {
      "models": [{
        "id": "deepseek-v4-flash",
        "contextWindow": 1048576  // 1M (corrigido v4.0.0)
      }]
    }
  }
}
```

**Benefício**: Contexto maior = mais informações por conversa = menos trocas de contexto.

### 5.3 Tools Otimizadas

```python
# ✅ Tool: resposta compacta
@tool
async def consultar_cliente(cpf_hash: str) -> dict:
    """Retorna apenas dados essenciais."""
    return {
        "id": cliente.id,
        "nome": cliente.nome[:3] + "***",  # mascarado
        "criado_em": cliente.created_at.date()
    }

# ❌ Tool: retorna tudo (lento)
@tool
async def consultar_cliente_full(cpf: str) -> dict:
    """Retorna TUDO do cliente (incluindo PII)."""
    return cliente.to_dict()  # lento + PII
```

### 5.4 WebSocket vs HTTP

```
✅ WebSocket /v1/chat (usar sempre)
- Conexão persistente
- Menor latência (sem handshake)
- Bidirecional

❌ HTTP /v1/chat (404 - não funciona)
- Cada request é handshake completo
- Maior latência
- Unidirecional
```

---

## 6. Network & HTTP

### 6.1 Keep-Alive

```python
# httpx com keep-alive
import httpx

client = httpx.AsyncClient(
    timeout=10.0,
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=50,
        keepalive_expiry=30
    )
)
```

### 6.2 HTTP/2 Multiplexing

```bash
# Traefik já usa HTTP/2
# Verificar:
curl -I --http2 https://api.2notasudi.com.br/health | head -1
# HTTP/2 200

# Benefício: múltiplas requests em 1 conexão TCP
```

### 6.3 CDN (Cloudflare)

```
✅ Assets estáticos (CSS, JS, imagens) - cache 1 ano
✅ Documentação - cache 1 dia
✅ API responses - NÃO cachear (dinâmico)
```

### 6.4 Latência VPS ↔ Serviços

| Origem | Destino | Latência Esperada |
|--------|---------|-------------------|
| API → Supabase | localhost (mesma VPS) | < 10ms |
| API → Redis | localhost | < 5ms |
| API → OpenClaw | localhost | < 20ms |
| API → N8N | localhost | < 30ms |
| N8N → Evolution | localhost | < 30ms |
| Cliente → VPS (BR) | WAN | 30-100ms |
| Cliente → VPS (US/EU) | WAN | 100-300ms |

---

## 7. Profiling e Debugging

### 7.1 cProfile (Python)

```python
import cProfile
import pstats

def slow_function():
    # código a ser perfilado
    pass

profiler = cProfile.Profile()
profiler.enable()
slow_function()
profiler.disable()

stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # top 20
```

### 7.2 py-spy (Sampling Profiler)

```bash
# Attach ao processo
py-spy dump --pid <PID>
py-spy top --pid <PID>
py-spy record -o profile.svg --pid <PID> --duration 30
```

### 7.3 Memory Profiling

```bash
# memory_profiler
pip install memory_profiler

@profile
def my_func():
    a = [1] * (10 ** 6)
    del a
    b = [2] * (2 * 10 ** 7)
    return b

# Rodar
python -m memory_profiler script.py
```

### 7.4 SQLAlchemy Echo

```python
# Dev only: ver TODAS queries SQL
engine = create_async_engine(url, echo=True)

# Log com timing
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### 7.5 N+1 Detection

```python
# Instalar
pip install nplusone

# Configurar
from nplusone.ext.sqlalchemy import NPlusOneCallback
NPlusOneCallback()

# Rodar testes
pytest -W error::nplusone.exc.NPlusOneError
```

---

## 8. Capacity Planning

### 8.1 Métricas-Chave (Junho 2026)

```
Requisições/dia: ~5.000 (estimativa)
Requisições/pico: ~100/min (10h-16h)
Clientes ativos/mês: ~500
Mensagens WhatsApp/mês: ~2.000
Storage: ~10GB (DB) + ~5GB (backups)
```

### 8.2 Limites Atuais

```
API FastAPI:
- 1 container, 1 CPU, 2GB RAM
- Throughput: ~200 req/s (benchmark)
- Conexões DB pool: 20 + 10 overflow

N8N:
- 1 main + 1 runner
- Execuções concorrentes: 5 (runner)
- 34 WFs ativos

Supabase:
- Postgres: 1 CPU, 2GB RAM
- Conexões max: 100 (pg_settings)
- Storage: 50GB (volume Docker)

Redis:
- 256MB maxmemory
- LRU eviction policy
- ~10k chaves ativas

OpenClaw:
- 1 container, 1 CPU, 1GB RAM
- Context: 1M tokens
- Throughput: depende do provider LLM
```

### 8.3 Projeção 12 meses

```
Requisições/dia: 5k → 20k
Clientes: 500 → 5.000
Mensagens: 2k → 15k
Storage: 10GB → 50GB

Necessário:
✅ 2 replicas API (1 → 2)
✅ 2 replicas N8N runner (1 → 2)
✅ 2 replicas OpenClaw (1 → 2)
✅ Aumentar Supabase para 4GB RAM
✅ Aumentar Redis para 512MB
✅ Adicionar read replica do Postgres
```

### 8.4 Alertas de Capacidade

```yaml
# Prometheus
- alert: APIHighCPU
  expr: rate(container_cpu_usage_seconds_total{name="cartorio_api"}[5m]) > 0.8
  for: 10m
  labels: {severity: warning}
  annotations: {summary: "API CPU > 80% - considerar scale up"}

- alert: APIHighMemory
  expr: container_memory_usage_bytes{name="cartorio_api"} / container_spec_memory_limit_bytes{name="cartorio_api"} > 0.85
  for: 5m
  labels: {severity: warning}
  annotations: {summary: "API memory > 85%"}

- alert: RedisNearMaxMemory
  expr: redis_memory_used_bytes / redis_max_memory_bytes > 0.8
  for: 10m
  labels: {severity: warning}
  annotations: {summary: "Redis memory > 80% - considerar aumentar maxmemory"}

- alert: DiskSpaceHigh
  expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) < 0.2
  for: 30m
  labels: {severity: warning}
  annotations: {summary: "Disco com < 20% livre"}
```

---

## 9. Load Testing

### 9.1 Apache Bench (ab)

```bash
# 1000 requests, 10 concurrent
ab -n 1000 -c 10 https://api.2notasudi.com.br/api/v1/emolumentos?tipo=reconhecimento_firma

# Output:
# Requests per second:    234.56 [#/sec] (mean)
# Time per request:       42.63 [ms] (mean)
# Time per request:       4.26 [ms] (mean, across all concurrent requests)
# Percentage of the requests served within a certain time (ms)
#   50%     42
#   95%    123
#   99%    187
#  100%    234 (longest request)
```

### 9.2 Locust (Python)

```python
# locustfile.py
from locust import HttpUser, task, between

class CartorioUser(HttpUser):
    wait_time = between(1, 5)
    
    @task(3)
    def consultar_emolumento(self):
        self.client.get("/api/v1/emolumentos?tipo=reconhecimento_firma")
    
    @task(1)
    def criar_protocolo(self):
        self.client.post("/api/v1/protocolos", json={
            "cliente_id": "...",
            "tipo": "emolumento"
        })

# Rodar
locust -f locustfile.py --host=https://api.2notasudi.com.br
# UI: http://localhost:8089
```

### 9.3 k6 (JavaScript)

```javascript
// load-test.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },   // ramp-up
    { duration: '1m', target: 50 },    // steady
    { duration: '30s', target: 100 },  // peak
    { duration: '30s', target: 0 },    // ramp-down
  ],
};

export default function () {
  const res = http.get('https://api.2notasudi.com.br/api/v1/emolumentos');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'latency < 500ms': (r) => r.timings.duration < 500,
  });
}

// Rodar
// k6 run load-test.js
```

---

## 10. Checklist de Performance

### 10.1 API

- [x] Async/await em todo I/O
- [x] Eager loading (evitar N+1)
- [x] Pagination em todos endpoints
- [x] Connection pool configurado
- [x] GZip middleware ativo
- [x] HTTP/2 via Traefik

### 10.2 Database

- [x] Índices em colunas consultadas
- [x] VACUUM ANALYZE diário
- [x] Connection pool (20 + 10)
- [x] Slow query log (>200ms)
- [x] Query plan revisado
- [ ] Read replica (futuro)

### 10.3 Cache

- [x] Redis para emolumento (24h TTL)
- [x] Cache warming às 06:00
- [x] Pub/sub invalidation
- [x] Hit rate > 80%
- [ ] Multi-layer cache (L1 in-process)

### 10.4 N8N

- [x] Retry policy (3x exp backoff)
- [x] Timeout (5s/10s)
- [x] Logs JSON estruturados
- [x] Métricas Prometheus
- [x] Batch endpoints quando possível

### 10.5 OpenClaw

- [x] Contexto 1M tokens
- [x] Thinking adaptive ON
- [x] Tools otimizadas
- [x] WebSocket (não HTTP)
- [ ] MCP server tools caching (futuro)

### 10.6 Network

- [x] Cloudflare CDN
- [x] HTTP/2
- [x] Keep-Alive
- [x] Traefik SSL termination
- [x] Localhost para serviços internos

---

## Recursos

- **Database**: `/docs/DATABASE_OPERATIONS.md`
- **Monitoring**: `/docs/MONITORING_GUIDE.md`
- **Caching**: `/docs/CACHING_STRATEGY.md`
- **Capacity**: `/docs/CAPACITY_PLANNING.md`
- **Troubleshooting**: `/docs/TROUBLESHOOTING.md`

---

**Mantido por**: Pietra (orquestrador)
**Próxima revisão**: 2026-07-02
**Versão**: 1.0.0
