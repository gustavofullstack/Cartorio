# Redis 7.x - Quick Reference

> **20 comandos mais usados (String, Hash, List, Set, Stream, Pub/Sub).**
> Versao: 7.x (2026-06-24)
> Endereco prod: `redis://187.77.236.77:1001` (porta host)
> Endereco interno: `redis://default:<senha>@cartorio_redis:6379/0`
> Doc oficial: https://redis.io/docs/commands/

## Visao geral

Redis e' um **in-memory data store** usado como cache, message broker e rate limiter. Suporta varios tipos de dados: String, Hash, List, Set, Sorted Set, Stream, Pub/Sub.

**Por que usamos**: baixa latencia (<1ms), TTL automatico, atomic operations (INCR, EXPIRE), rate limit via INCR+EXPIRE, pub/sub para webhook bus.

## Conectar

```bash
# Local (dev)
redis-cli -h localhost -p 6379

# Prod (via firewall, porta host 1001)
redis-cli -h 187.77.236.77 -p 1001 -a <senha>

# Docker (interno)
docker exec -it cartorio_redis redis-cli -a <senha>
```

## 20 Comandos prioritarios (Cartorio usa esses)

### String (chave-valor simples)

#### 1. SET
```bash
SET chave valor [EX 60] [NX|XX]
# EX 60 = TTL 60s
# NX = so cria se nao existir
# XX = so atualiza se ja existir
SET ratelimit:apikey:abc:123 1 EX 60 NX
```

#### 2. GET
```bash
GET chave
GET ratelimit:apikey:abc:123
# "1"
```

#### 3. DEL
```bash
DEL chave1 chave2 chave3
# retorna numero deletado
```

#### 4. EXISTS
```bash
EXISTS chave
# 1 = existe, 0 = nao
```

#### 5. INCR (atomic counter)
```bash
INCR chave
INCR ratelimit:apikey:abc:123
# retorna novo valor (1, 2, 3, ...)
```

#### 6. EXPIRE
```bash
EXPIRE chave 60
# TTL 60s (atomic com INCR no rate limiter)
```

#### 7. TTL
```bash
TTL chave
# -1 = sem TTL, -2 = nao existe, N = segundos restantes
```

#### 8. APPEND
```bash
APPEND chave valor
APPEND log:2026-06-24 "linha 1\n"
```

### Hash (campo-valor dentro de uma chave)

#### 9. HSET
```bash
HSET user:42 nome "Joao" email "joao@cartorio.com" role "escrevente"
# cria hash com 3 campos
```

#### 10. HGET
```bash
HGET user:42 nome
# "Joao"
```

#### 11. HGETALL
```bash
HGETALL user:42
# {nome: "Joao", email: "joao@cartorio.com", role: "escrevente"}
```

#### 12. HINCRBY
```bash
HINCRBY user:42 contador_atendimentos 1
# atomic increment em hash field
```

### List (lista FIFO/LIFO)

#### 13. LPUSH / RPUSH
```bash
LPUSH fila:emails "msg1" "msg2"
RPUSH fila:emails "msg3"  # append right
```

#### 14. LPOP / RPOP
```bash
LPOP fila:emails  # remove e retorna primeiro
# BLPOP fila:emails 30  # blocking, espera 30s
```

#### 15. LRANGE
```bash
LRANGE fila:emails 0 9  # primeiros 10
```

### Set (colecao unica, sem ordem)

#### 16. SADD / SMEMBERS
```bash
SADD tags:protocolo:123 "urgente" "v2" "minimax"
SMEMBERS tags:protocolo:123
# {urgente, v2, minimax}
```

#### 17. SISMEMBER
```bash
SISMEMBER tags:protocolo:123 "urgente"
# 1 = sim, 0 = nao
```

### Pub/Sub (message broker leve)

#### 18. PUBLISH
```bash
PUBLISH canal:eventos '{"tipo":"pii_detected","protocolo":123}'
```

#### 19. SUBSCRIBE
```bash
SUBSCRIBE canal:eventos
# bloqueia, recebe todas mensagens publicadas
```

### Stream (log append-only, tipo Kafka leve)

#### 20. XADD / XREAD
```bash
# Adiciona evento ao stream
XADD audit:stream * tipo "conversa" protocolo 123 correlation_id "abc"

# Le eventos apos ID 0
XREAD COUNT 5 STREAMS audit:stream 0
```

## Cenarios de uso no Cartorio

### Rate limit (String + INCR/EXPIRE)

```python
# backend/app/services/rate_limit_by_key.py
pipe = redis.pipeline()
pipe.incr(redis_key)        # contador
pipe.expire(redis_key, 60)  # TTL 60s (atomic)
current, _ = await pipe.execute()

if current > limit:
    raise HTTPException(429, "rate limit exceeded")
```

### Session cache (Hash)

```python
# session:abc -> {user_id, ip, login_at, last_seen}
redis.hset("session:abc", mapping={
    "user_id": 42,
    "ip": "187.77.236.77",
    "login_at": "2026-06-24T10:00:00Z"
})
redis.expire("session:abc", 86400)  # 24h
```

### Webhook bus (Pub/Sub)

```python
# Publica
redis.publish("webhook:chatwoot", json.dumps({
    "event": "message_created",
    "conversation_id": 123,
    "content": "..."
}))

# Worker subscreve
pubsub = redis.pubsub()
pubsub.subscribe("webhook:chatwoot")
for message in pubsub.listen():
    process(message)
```

### Audit log (Stream)

```python
# Append-only log de eventos
redis.xadd("audit:stream", {
    "tipo": "pii_blocked",
    "cliente_id": 42,
    "correlation_id": "abc"
})

# Query eventos recentes
events = redis.xread({"audit:stream": "0"}, count=100, block=5000)
```

## TTL Strategies (cartorio)

| Tipo | TTL | Uso |
|---|---|---|
| Rate limit | 60s | req/min counter |
| Session | 24h | user login |
| Idempotency key | 5min | webhook dedup |
| Webhook dedup | 24h | message_id visto |
| API key cache | 5min | X-API-Key -> tier |
| Temp result | 1min | emolumento calculation cache |

## Performance Tips

- **Use pipelining**: agrupar varios comandos em 1 round-trip (10x speedup)
- **Use Lua scripts**: para operacoes atomicas complexas (server-side)
- **Pipeline + Lua**: `EVAL "..." KEYS ARGV` em 1 round-trip
- **Connection pool**: nunca criar 1 connection por request

## Troubleshooting

| Problema | Solucao |
|---|---|
| `Error 8 connecting to cartorio_redis` | DNS nao resolve - usar IP ou verificar Swarm network |
| `LOADING Redis is loading` | Redis iniciando - aguardar ~1s e retry |
| `OOM command not allowed` | `maxmemory` excedido - aumentar ou usar `maxmemory-policy allkeys-lru` |
| `WRONGTYPE` | chave existe com tipo diferente (String vs Hash) - DEL e recriar |
| `NOAUTH Authentication required` | senha faltando - usar `-a` no redis-cli ou `password=` na URL |
| `READONLY` | replica em read-only - escrever no master |

## Comandos perigosos (cuidado!)

```bash
FLUSHDB        # apaga TODAS chaves do DB atual
FLUSHALL       # apaga TODAS chaves de TODOS os DBs
KEYS *         # O(N) - bloquear Redis em prod
DEBUG SLEEP 5  # bloqueia Redis por 5s
```

**NUNCA** rodar em prod sem `--scan` ou `SCAN` (cursor incremental).

## Referencias

- Doc oficial: https://redis.io/docs/
- Comandos: https://redis.io/commands/
- Redis 7 release notes: https://redis.io/docs/about/releases/
- Cliente Python: https://redis-py.readthedocs.io/
- HTML oficial: `docs/platforms/REDIS_OFFICIAL_DOCS.html`
- Integração: `backend/app/services/rate_limit.py`, `rate_limit_by_key.py`, `redis_bus.py`

Modified by ZCode/Mavis - 2026-06-24
