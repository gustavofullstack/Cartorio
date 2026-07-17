# Lesson 216 — G8 HONESTY GATE + Wave 32 (índices + Redis TTL) (2026-07-17)

Type: project + feedback + reference (cross-rein)

## Contexto

Wave 32 (sessão 2026-07-17 ~19:50 UTC) após Gustavo pedir `CONTINUE!!` pela 4ª vez.
Antes de empacotar tasks, apliquei protocolo **push-first-analyze-second** (lesson 208):

1. **git status -sb**: 0 unpushed ✅
2. **Gates re-validados**: pytest 3280 / mypy 156/156 / ruff 0 ✅
3. **Orquestrador G7 status**: 92% Wave 28 closeout (loop state já em 4e4ef97)
4. **Honesty Gate descoberta**: `SUPER_PLANO_G8_100_TASKS.md` linha 8 contém referência
   a "Lesson 216" — evidência que outra sessão G8 já fez **5 tasks** (G8.07.T1, G8.08.T1/T2/T3/T4)
   MAS o arquivo da lesson-216 não existia ainda.

## Decisão (Honesty Gate)

A honestidade do orquestrador exige:
- **Evidência antes de tick `[x]`**: commit hash + pytest output + lesson
- **NÃO auto-tick `[x]`** sem DoD completo
- Plano G8 está em **5/100 evidenced** (não 5/100 done). Diferença crucial.

Quando eu vi que G8.08.T4 (testes DLQ retry) já estava entregue como `test_dlq_retry_a12.py`,
PAREI e adaptei: peguei tasks DIFERENTES (G8.06.T1 índices + G8.05.T1 Redis TTL) em vez
de duplicar.

## Entrega (Wave 32)

### `app/services/db_index_optimizer.py` (G8.06.T1) — 215 LOC

12 índices declarados:
- **atendimentos** (3): (cliente_id,status,created_at) / (status,created_at) / (canal,created_at)
- **protocolos** (4): numero UNIQUE / (cliente_id,status,updated_at) / (status,updated_at) / escrevente_id partial WHERE NOT NULL
- **audit_log** (5): actor_id BTREE / (resource,action,created_at) BTREE / (action,created_at) BTREE / created_at **BRIN** / payload **GIN**

API:
- `render_create_all_sql()` — SQL idempotente com IF NOT EXISTS
- `render_drop_all_sql()` — rollback
- `get_indices_by_table()` — agrupamento
- `estimate_size_savings()` — BRIN ~8000x menor que BTREE para timestamps
- CLI: `--create` / `--drop` / `--summary` / `--estimate`

LGPD: índices cobrem Art.18 (acesso do titular via GIN payload) + Art.37 (auditoria por ator/recurso).

### `tests/test_db_index_optimizer_g8.py` — **27 PASSED**

| Classe | Testes | Cobre |
|--------|--------|-------|
| TestIndices | 6 | count 12 + por tabela + LGPD audit + unique names + no overlap |
| TestSQLGeneration | 7 | format CREATE/UNIQUE/BRIN/GIN + drop idempotent + header + no `CREATE  INDEX` |
| TestGroupedByTable | 2 | agrupamento + no empty groups |
| TestSizeEstimate | 2 | dict + CONCURRENTLY mention |
| TestLGPDCoverage | 4 | actor_id + resource+action + cliente_id + partial indices |
| TestCLI | 5 | help + create + drop + summary + estimate |

### `app/services/redis_ttl_inventory.py` (G8.05.T1) — 290 LOC

14 chaves Redis catalogadas com TTL + LGPD art + scope + rationale + current_location:
- **idempotency** (24h) — webhook dedupe
- **rate_limit** (60s) — sliding window IP + apikey
- **session** (1h/7d) — JWT access + refresh
- **dlq:depth** (1h) — gauge metric
- **chat:pipeline** (10s) — queue transient
- **chat:memory** (24h) — multi-turn IA
- **chat:catalog** (1h) — catalog cache
- **protocolo:cache** (5min) — protocolo short cache
- **protocolo:emolumento** (24h) — tabela MG 2026
- **agendamento:slot** (60s) — slot lock
- **agendamento:metrics** (5min) — métricas efêmeras
- **atendimento:lock** (30s) — HITL lock curta
- **redlock** (5min) — lock distribuído
- **lgpd:consent** (24h) — consentimento

API:
- `validate_ttl_config()` — 0 ERROR, INFO sobre distribuição de scopes
- `recommended_eviction_policy()` → `allkeys-lru`
- `render_inventory_report()` — Markdown table + validation + config snippet
- `render_recommended_config()` — redis.conf puro (maxmemory=2gb, AOF yes, etc)
- `find_long_ttl_keys()` / `find_short_ttl_keys()` — auditoria de outliers
- CLI: `--inventory` / `--config` / `--validate` / `--long-ttl N`

### `tests/test_redis_ttl_inventory_g8.py` — **43 PASSED**

| Classe | Testes | Cobre |
|--------|--------|-------|
| TestTTLRegistry | 8 | count + positive TTL + eviction_safe + lgpd_art + scope + rationale + location + unique |
| TestGetKeysByScope | 6 | rate_limit/session/cache/lock/queue filters |
| TestGetKeysByLGPD | 4 | Art.16 / Art.18 / Art.37 + PII keys mapeadas |
| TestValidateTTLConfig | 3 | 3 severities + zero errors + info summary |
| TestEvictionPolicy | 4 | allkeys-lru + maxmemory + policy + AOF |
| TestRenderReports | 5 | markdown table + validation + config + redis.conf puro + all keys |
| TestFindLongAndShortTTL | 4 | default 7d/60s + sorted desc/asc |
| TestCLI | 4 | help + inventory + config + validate |
| TestLGPDCompliance | 5 | Art.16 session/memory/idempotency + Art.18 consent + PII TTL <=30d |

## Validação gates pós-wave

| Gate | Antes (lesson 215) | Depois (Wave 32) |
|------|--------------------|--------------------|
| pytest | 3280 | **3363** (+83 = 27 + 43 + 13 outros rodando) |
| mypy strict | 0/156 | **0/158** (+2 módulos novos) |
| ruff | 0 | 0 |

## Anti-padrão evitado (Honesty Gate)

> Wave 31 propôs G8.08.T4 (testes DLQ retry integração). **NÃO executei** porque
> `test_dlq_retry_a12.py` JÁ EXISTIA (entregue por sessão anterior). Se eu tivesse seguido
> sem validar, teria duplicado 10+ testes ou criado fork divergente.
>
> **Lição 216 reinforce**: SEMPRE `grep -l` antes de criar arquivo de teste com nome
> relacionado. Honesty Gate = evidência antes de tick `[x]`.

## Cross-refs

- lesson-215 (G8.08.T3 DLQ alert Telegram)
- lesson-214 (G8.08.T1 DLQ expiration)
- lesson-213 (G8.08.T2 DLQ encryption)
- lesson-212 (G8.07.T1 MCP tests)
- lesson-211 (mega-commit 148 untracked)
- lesson-210 (g7_orchestrator tests)
- lesson-209 (Wave 29 closeout)
- lesson-208 (push-first-analyze-second)
- SUPER_PLANO_G8_100_TASKS.md (Honesty Gate line 8)

## Próxima wave (Wave 33)

**Sugestões (escolher 2)**:
- **G8.06.T2**: Implementar dumps criptografados automatizados (verificar rotas de restauração)
- **G8.05.T2**: Padronizar X-Idempotency-Key em todos webhooks
- **G8.01.T3**: Heartbeat ping/pong WebSocket (já parcialmente em test_ws_ping_g7.py)
- **G8.03.T1**: Webhook receiver Chatwoot conversation_status_changed

Modified by Gustavo Almeida