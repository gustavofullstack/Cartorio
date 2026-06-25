# Redis — Documentação Consolidada

> **Fonte**: redis.io/docs + nossa experiência operacional
> **Versão**: Redis 8.8
> **Porta interna**: 6379
> **Porta host**: 1001
> **Auth**: @Techno832466
> **Health**: redis-cli PING → PONG

---

## 🔌 Conexão

```python
# Via Tailscale (preferido)
redis://default:@Techno832466@100.99.172.84:1001/0

# DBs lógicos (separação lógica):
# DB 0 → Sessões de usuário
# DB 1 → Cache de emolumentos
# DB 2 → Cache geral
# DB 3 → Rate limiting
```

---

## 🎯 Usos no Cartório

| Uso | TTL | DB |
|-----|-----|-----|
| **Sessões de usuário** | 30min | 0 |
| **Cache emolumentos** | 1h | 1 |
| **Cache de dados frequentes** | variável | 2 |
| **Pub/Sub eventos tempo real** | — | 0 |
| **Rate limiting (Evolution)** | 1min | 3 |
| **Fila notificações** | persistente | 0 |
| **Cache agent OpenClaw** | sessão | 0 |
| **Cache protocolos recentes** | 5min | 2 |

---

## 📚 Comandos Mais Usados

### Conexão e PING
```bash
redis-cli -h 100.99.172.84 -p 1001 -a @Techno832466 PING
# Resposta: PONG

redis-cli -h 100.99.172.84 -p 1001 -a @Techno832466 --stat
# Estatísticas em tempo real
```

### Keys
```bash
SET key value                  # Setar string
SET key value EX 60            # Com TTL 60s
GET key                        # Obter valor
DEL key                        # Deletar
EXISTS key                     # Verificar existência
EXPIRE key 60                  # Setar TTL
TTL key                        # Ver TTL restante
KEYS pattern                   # Listar (NÃO use em produção)
SCAN 0 MATCH pattern COUNT 100 # Iterar (use em produção)
```

### Hashes
```bash
HSET user:1 name "Gustavo" age 30
HGET user:1 name
HGETALL user:1
HDEL user:1 age
```

### Lists (Filas)
```bash
LPUSH queue:emails "msg1"
RPUSH queue:emails "msg2"
LPOP queue:emails
BRPOP queue:emails 5  # Blocking com timeout 5s
LLEN queue:emails
LRANGE queue:emails 0 -1
```

### Sorted Sets (Leaderboards)
```bash
ZADD ranking 100 "user1" 200 "user2"
ZRANGE ranking 0 -1 WITHSCORES
ZREVRANK ranking "user1"
```

### Pub/Sub
```bash
# Subscribe
SUBSCRIBE cartorio:events

# Publish
PUBLISH cartorio:events "novo_cliente"
```

### Streams (Event Sourcing)
```bash
XADD events * type "novo_cliente" id 123
XLEN events
XRANGE events - + COUNT 10
XREAD COUNT 10 STREAMS events 0
```

---

## 🔒 Segurança

| Item | Status |
|------|--------|
| **Auth (requirepass)** | ✅ `@Techno832466` |
| **bind** | 0.0.0.0 (com password) |
| **protected-mode** | yes |
| **rename-command** | desabilitado (admin via SSH) |
| **SSL/TLS** | ⚠️ interno (não exposto) |

---

## 🛠️ Padrões de Uso

### Cache-Aside (Lazy Loading)
```python
def get_cliente(cliente_id):
    # 1. Tentar cache
    cached = redis.get(f"cliente:{cliente_id}")
    if cached:
        return json.loads(cached)
    
    # 2. Cache miss → query DB
    cliente = db.query(Cliente).get(cliente_id)
    
    # 3. Setar cache com TTL
    redis.setex(f"cliente:{cliente_id}", 300, json.dumps(cliente.to_dict()))
    return cliente
```

### Write-Through
```python
def update_cliente(cliente_id, data):
    # 1. Update DB
    db.update(cliente_id, data)
    
    # 2. Invalidate cache
    redis.delete(f"cliente:{cliente_id}")
```

### Distributed Lock (Redlock pattern)
```python
# Lock distribuído para evitar race conditions
import redis_lock

lock = redis_lock.Lock(redis, "lock:protocolo:123", timeout=30)
if lock.acquire(blocking=True):
    try:
        # Critical section
        process_protocol(123)
    finally:
        lock.release()
```

---

## 📊 Métricas Importantes

```bash
# Memória
INFO memory

# Estatísticas
INFO stats

# Clients conectados
INFO clients

# Slowlog (queries lentas)
SLOWLOG GET 10

# Latência
LATENCY HISTORY
```

---

## 🚨 Comandos Perigosos (NUNCA em produção)

| Comando | Por que NÃO |
|---------|-------------|
| `FLUSHALL` | Apaga TODOS os dados de TODOS os DBs |
| `FLUSHDB` | Apaga dados do DB atual |
| `KEYS *` | Bloqueia Redis em prod (use SCAN) |
| `DEBUG SLEEP 60` | Bloqueia Redis por 60s |
| `CONFIG SET maxmemory 0` | Pode OOM Redis |

---

## 🔧 UI Web (Debug)

| Ferramenta | URL | Auth |
|-----------|-----|------|
| **Redis Commander** | http://VPS:8081 | admin/admin |
| **DBGate** | http://VPS:3001 | admin/admin |

---

## 🔗 Links Úteis

| Recurso | URL |
|---------|-----|
| Docs oficial | https://redis.io/docs/ |
| Commands | https://redis.io/commands/ |
| Data types | https://redis.io/docs/data-types/ |
| Patterns | https://redis.io/docs/manual/patterns/ |
| Persistence | https://redis.io/docs/management/persistence/ |
| Replication | https://redis.io/docs/management/replication/ |
| Clustering | https://redis.io/docs/management/scaling/ |
| Security | https://redis.io/docs/management/security/ |
| Python client | https://redis-py.readthedocs.io/ |
| Async Python | https://redis-py.readthedocs.io/en/stable/commands.html |

---

## 🎯 Nossa Stack com Redis

```python
# Python: redis-py + redis.asyncio
import redis.asyncio as redis

# Sessão de usuário
await redis.setex(f"sess:{user_id}", 1800, session_data)

# Cache de emolumento
await redis.setex(f"emolumento:{tipo_doc}", 3600, valor)

# Rate limit (sliding window)
ZADD rate:user:{user_id} {now_ms} {now_ms}
ZREMRANGEBYSCORE rate:user:{user_id} 0 {window_start}
ZCARD rate:user:{user_id}
```

---

## ✅ Status Atual (2026-06-25)

- ✅ Redis 8.8 UP
- ✅ PONG respondendo
- ✅ Auth @Techno832466 configurado
- ✅ 44h+ uptime
- ✅ 4 DBs lógicos separados
- ✅ Redis Commander + DBGate acessíveis (interno)