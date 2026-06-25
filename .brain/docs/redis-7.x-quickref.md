# Redis 7.x — Quick Reference

**Source**: https://redis.io/docs/
**Versao em uso**: 7.x (port 6379, interno cartorio_redis:6379)
**Atualizado**: 2026-06-25

## 1. Conexao

```bash
# Via container
docker exec cartorio_redis-1 redis-cli -a cartorio-redis-secret-v1

# Via URL do backend
REDIS_URL="redis://:cartorio-redis-secret-v1@cartorio_redis:6379/0"
```

## 2. Comandos Essenciais

```bash
# Set/Get
SET key value EX 3600           # set com TTL 1h
GET key
DEL key
EXISTS key
TTL key
EXPIRE key 60                    # set TTL em key existente

# Hash
HSET user:123 nome "Joao" idade 30
HGET user:123 nome
HGETALL user:123

# List
LPUSH queue:items "a"
RPUSH queue:items "b"
LRANGE queue:items 0 -1

# Set
SADD tags:user:123 "vip" "pf"
SMEMBERS tags:user:123

# Sorted Set
ZADD ranking 100 "user:1" 200 "user:2"
ZREVRANGE ranking 0 9 WITHSCORES

# Streams
XADD events * type "msg" payload "..."
XREAD BLOCK 0 STREAMS events $

# Pub/Sub
PUBLISH channel:updates "hello"
SUBSCRIBE channel:updates
```

## 3. Uso no Cartorio

### 3.1 Cache de emolumento (A21 - 24h)

```bash
# Key: emol:tabela:{tipo}:{folhas}:{urgencia}
SET "emol:tabela:reconhecimento:1:normal" '{"valor_centavos":1500}' EX 86400
GET "emol:tabela:reconhecimento:1:normal"
```

### 3.2 Idempotencia (A6 - 24h)

```bash
# Key: idempotency:{chave_cliente}
SETNX "idempotency:abc123" "request-payload" EX 86400
EXISTS "idempotency:abc123"
```

### 3.3 Rate Limit (A7 - 60s)

```bash
# Sliding window
INCR rate_limit:user:123
EXPIRE rate_limit:user:123 60
```

### 3.4 Redlock distribuido (A20)

```bash
SET "lock:redlock:migration-001" "owner-uuid" NX EX 30
# Owner: executar trabalho
DEL "lock:redlock:migration-001"
```

### 3.5 Sessions OpenClaw

```bash
SET "session:openclaw:{session_id}" "context" EX 3600
GETDEL "session:openclaw:{session_id}"  # atomico
```

## 4. Persistence

Cartorio Redis esta configurado com:
- `appendonly yes` (AOF)
- `appendfsync everysec`
- RDB snapshots a cada 60s se 100+ chaves modificadas

## 5. Memory Optimization

```bash
# Verificar uso
INFO memory

# Config: maxmemory 256mb, maxmemory-policy allkeys-lru
```

## 6. Monitoramento

```bash
# Comandos
INFO all
INFO clients
INFO stats
SLOWLOG GET 10

# Pub/Sub monitor (NAO em prod)
MONITOR
```

## 7. Failover / HA

Cartorio usa 1 instancia (sem HA). Para HA, configurar:
- Redis Sentinel (3 sentinels min)
- Redis Cluster (6 nodes min)
- Ou Redis Cloud gerenciado

## 8. Gotchas

- TTL em segundos (nao ms)
- KEYS * NAO usar em prod (usa SCAN)
- Lua scripts atomicos (EVAL)
- Pipelining para batch
- Cluster: 16.384 hash slots, key com {} tem hashtag
- Streams consomem memoria linearmente (XADD sem MAXLEN = cresce infinito)

## 9. Backup

```bash
# Snapshot
docker exec cartorio_redis-1 redis-cli -a cartorio-redis-secret-v1 BGSAVE
docker exec cartorio_redis-1 cat /data/dump.rdb > /var/backups/redis/$(date +%Y%m%d).rdb
```

Modified by Pietra + Gustavo Almeida 2026-06-25
