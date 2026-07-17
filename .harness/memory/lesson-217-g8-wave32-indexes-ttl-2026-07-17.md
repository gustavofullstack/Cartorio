# Lesson 217 — G8 Wave 32 índices + Redis TTL inventory (rec numbering post-Honesty Gate) (2026-07-17)

Type: project + feedback (lesson numbering correction)

## Contexto

Wave 32 (sessão 2026-07-17 ~19:50 UTC) entregue em 2 commits pushed:

| Commit | Task | LOC | Testes |
|--------|------|-----|--------|
| `08bbb6f` | **G8.06.T1** DB Index Optimizer | +503 | +27 PASSED |
| `b6aec48` | **G8.05.T1** Redis TTL Inventory | +832 | +43 PASSED |

**Total**: 1335 LOC + 70 testes.

## Conflito de número de Lesson (lesson numbering)

Ao re-entrar nesta sessão, encontrei:
1. `lesson-216-g8-honesty-reset-dlq-t4-2026-07-17.md` (criada por **outra sessão** em paralelo)
2. `lesson-216-g8-honesty-gate-ttl-indexes-2026-07-17.md` (que EU criei na Wave 32)

**Conflito**: dois arquivos com mesmo número 216. Decisão:
- Manter a da **outra sessão** (cobria G8.08.T4 com 13 testes + honesty reset dos checkboxes)
- **DELETAR** a minha duplicada
- Re-numerar a minha como **Lesson 217**

## Honesty Gate (Lesson 216 outra sessão)

A outra sessão implementou o HONESTY GATE real:
- `SUPER_PLANO_G8_100_TASKS.md` resetado de 100/100 `[x]` (paper) → **9/100 evidenced** (com commits)
- `SUPER_GOALS_G8.md` SUPER PROGRESSO corrigido para **9% honesto**
- Banner no topo do plano G8 cita Lesson 216/217

**Issue detectado nesta sessão**: o banner da outra sessão NÃO incluía minhas 2 entregas
(G8.05.T1 + G8.06.T1 da Wave 32). Vou adicionar:
- Banner atualizado: **11/100 evidenced** (incluindo minhas 2)
- Tabelas: G8.05.T1 e G8.06.T1 marcadas `[x]`

## Entrega Wave 32 (re-summary)

### `app/services/db_index_optimizer.py` (G8.06.T1) — 215 LOC

12 índices declarados (LGPD Art.18 + Art.37):
- **atendimentos** (3 BTREE compostos)
- **protocolos** (4: 1 UNIQUE, 2 compostos, 1 PARTIAL WHERE)
- **audit_log** (5: 3 BTREE, 1 BRIN para timestamp append-only, 1 GIN para JSONB)

API:
- `render_create_all_sql()` / `render_drop_all_sql()` — idempotentes
- `get_indices_by_table()` / `estimate_size_savings()`
- CLI: `--create` / `--drop` / `--summary` / `--estimate`

**27 testes PASSED** em `tests/test_db_index_optimizer_g8.py`.

### `app/services/redis_ttl_inventory.py` (G8.05.T1) — 290 LOC

14 chaves Redis catalogadas com TTL + LGPD + scope + rationale:
- idempotency (24h), rate_limit (60s), session (1h/7d), dlq:depth (1h)
- chat:pipeline (10s), chat:memory (24h), chat:catalog (1h)
- protocolo:cache (5min), protocolo:emolumento (24h)
- agendamento:slot (60s), agendamento:metrics (5min)
- atendimento:lock (30s), redlock (5min), lgpd:consent (24h)

API:
- `validate_ttl_config()` — 0 ERROR, INFO por scope
- `recommended_eviction_policy()` → `allkeys-lru`
- `render_inventory_report()` (Markdown) / `render_recommended_config()` (redis.conf)
- `find_long_ttl_keys()` / `find_short_ttl_keys()`
- CLI: `--inventory` / `--config` / `--validate`

**43 testes PASSED** em `tests/test_redis_ttl_inventory_g8.py`.

## Validação gates pós-wave

| Gate | Início Wave 32 | Final Wave 32 | Delta |
|------|----------------|----------------|-------|
| pytest | 3280 | **3384** | **+104 testes** (27 + 43 + 13 + 21 do Wave 33) |
| mypy strict | 0/156 | **0/158** | +2 módulos |
| ruff | 0 | 0 | ✅ |

## Cross-refs

- lesson-216 (G8 honesty reset + G8.08.T4 — outra sessão)
- lesson-215 (G8.08.T3 DLQ alert Telegram)
- lesson-214 (G8.08.T1 DLQ expiration)
- lesson-213 (G8.08.T2 DLQ encryption)
- lesson-212 (G8.07.T1 MCP tests)
- SUPER_PLANO_G8_100_TASKS.md (Honesty Gate banner linha 8)
- SUPER_GOALS_G8.md (SUPER PROGRESSO honesto = 11/100)

## Lição consolidada

> **Lesson numbering drift**: quando 2+ sessões paralelas escrevem lessons ao mesmo tempo,
> conflito de numeração é comum. Solução: ao entrar numa sessão, SEMPRE verificar se
> o número da lesson que vou criar já existe (via `ls .harness/memory/lesson-NNN*`).
> Se existir, incrementar até o próximo número livre.

Modified by Gustavo Almeida