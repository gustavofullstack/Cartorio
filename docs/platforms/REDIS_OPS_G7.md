# Redis 8 — Ops & Integração G7 (G7.07.T1)

**Stack:** Redis 8 (EasyPanel / Swarm `cartorio_redis`)  
**Usos no cartório:** idempotência webhooks · rate limit · cache LGPD · redlock DMS · memória multi-turn Telegram  
**Health:** `GET /api/v1/health/radar` → `services.redis` (live 2026-07-16: **online**)

---

## 1. Políticas recomendadas (prod)

| Setting | Valor sugerido | Por quê |
|---------|----------------|---------|
| `maxmemory` | `512mb`–`1gb` (VPS 8GB: 512mb ok) | evita OOM kill do host |
| `maxmemory-policy` | `allkeys-lru` | webhooks/idempotency keys têm TTL; LRU limpa cache frio |
| `appendonly` | `yes` (se persistência desejada) | rate-limit state sobrevive restart |
| `timeout` | `300` | fecha idle clients zombie |

**Fail-open:** `rate_limit.py` / `rate_limit_by_key.py` — se Redis cair, API **não** bloqueia (Lesson: fail-open consciente; log warning).

---

## 2. Key namespaces (convenção)

| Prefixo | TTL | Dono |
|---------|-----|------|
| `idempotency:*` / `webhook:*` | 24h | webhooks Evolution/Telegram/N8N |
| `rl:ip:*` | 60s window | rate limit IP |
| `rl:key:*` | 60s | rate limit API key tiers |
| `lock:dms-loop` | interval-10s | dead man's switch redlock |
| `tg:mem:*` | multi-turn | Telegram conversation memory |
| `cache:lgpd:*` | curto | cache LGPD export |

**Nunca** guardar CPF/RG raw em value — só hash ou already-masked (PII layer).

---

## 3. Integração com os outros serviços

```
Telegram/Evolution webhook
    → Redis SETNX (dedupe 24h)
    → API business logic
    → Postgres audit chain
    → (opcional) OpenClaw / LobeChat
    → Chatwoot handoff
```

- **N8N:** 21/21 webhooks com idempotência (G6.B.T6 injector).
- **API:** `app/services/idempotency_store.py`, `rate_limit*.py`, `dist_lock.py`.
- **DMS:** `acquire_lock("dms-loop")` no lifespan.

---

## 4. Checks operacionais

```bash
# Via API radar
curl -sS https://api.2notasudi.com.br/api/v1/health/radar | jq .services.redis

# Via Swarm (SSH/Tailscale)
docker exec $(docker ps -q -f name=redis) redis-cli INFO memory | head -20
docker exec $(docker ps -q -f name=redis) redis-cli CONFIG GET maxmemory maxmemory-policy
docker exec $(docker ps -q -f name=redis) redis-cli DBSIZE
```

---

## 5. Alertas

- Prometheus: se existir `redis_up == 0` por 5m → Telegram GRUPO PIETRA  
- Radar overall fica `red` se redis offline (crítico — não fail-open para radar)

---

## 6. SOLID/KISS notes

- **S:** um store por concern (`idempotency_store` ≠ `rate_limit`)  
- **KISS:** SETNX + TTL > schemas complexos no Redis  
- **DRY:** helper único de client Redis (`app.core.redis` / ADR-026)

---

**Modified by Gustavo Almeida + cartorio-dev — G7 Wave 15 (G7.07.T1)**
