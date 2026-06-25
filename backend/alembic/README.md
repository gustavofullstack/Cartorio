# Alembic Migrations — Cartório 2º Notas Uberlândia

Sistema de migrations para o banco Postgres central (Supabase self-hosted).

## Quick Start

```bash
cd backend
uv run alembic upgrade head     # Aplica TODAS as migrations
uv run alembic downgrade -1     # Reverte 1 migration
uv run alembic current          # Mostra rev atual
uv run alembic history          # Lista todas as revs
```

## Estrutura de arquivos

```
backend/alembic/
├── env.py                          # Config Alembic
├── script.py.mako                  # Template para novas migrations
└── versions/
    ├── 2026_06_23_0001-...py       # Sprint 0.5 hardening
    ├── 2026_06_24_0000-...py       # Sprint 1 - base core tables
    ├── 2026_06_24_0001-...py       # Sprint 1 - audit_log IP truncated
    ├── 2026_06_24_0002-...py       # Sprint 1 - outbox messages DLQ
    ├── 2026_06_24_0003-...py       # Sprint 1 - merge head
    ├── 2026_06_25_0001-...py       # Sprint 4 A16 - mv_protocolo_stats
    ├── 2026_06_25_0002-...py       # Sprint 4 A17 - soft delete
    ├── 2026_06_25_0003-...py       # Sprint 4 A24 - pg_notify outbox
    ├── 2026_06_25_0004-...py       # Sprint 4 S0 - RLS + audit_chain_fn + auto_audit
    ├── 2026_06_25_0005-...py       # Sprint 4 S0 - pg_cron jobs (4 jobs)
    ├── 2026_06_25_0006-...py       # Sprint 4 S0 - database webhooks (outbox -> API)
    └── 2026_06_25_0007-...py       # Sprint 4 S0 - GraphQL+Storage+Realtime
```

## Convenções

1. **ID sempre com prefixo de data**: `YYYY_MM_DD_NNNN-nome-descritivo.py`
2. **Revision ID e down_revision** declarados explicitamente
3. **Idempotente**: usar `IF NOT EXISTS` / `IF EXISTS` / `DROP IF EXISTS` em DDL
4. **LGPD-by-design**: nunca colocar PII ou secrets em migrations versionadas
5. **Sem `op.drop_table` em downgrades** a menos que seja tabela criada NA migration
6. **Comentar cabeçalho**: o que a migration faz, squad, PR, dependencias
7. **1 squad = 1 tema**: A1x (SQUAD A obs/perf/data), S0x (SQUAD S0 Supabase), etc

## Criar nova migration

```bash
cd backend
uv run alembic revision -m "add coluna X na tabela Y"
# Edita o arquivo gerado em versions/
# Testa local:
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
# Valida gates
uv run mypy app/ && uv run ruff check app/ && uv run pytest tests/ -q --no-cov
# Commit
git add backend/alembic/versions/...
git commit -m "feat(db): descricao"
```

## Em produção (container cartorio_api)

```bash
docker exec cartorio_api.1.<id> alembic upgrade head
```

Semiautomatico via script `infra/scripts/post-deploy-alembic.sh` (criado em 2026-06-25).

## SQUAD S0 — Supabase Foundation (P0, BLOQUEIA 70% do sistema)

| Migration | Tema | Status |
|---|---|---|
| 0004 | RLS policies (anon/authenticated/service_role/dpo) + fn_audit_chain_verify + fn_auto_audit trigger | ✅ done 2026-06-25 |
| 0005 | pg_cron jobs (audit_verify 03:00 + dlq_retry 5min + cache_warm 06:00 + snapshot 23:55) | ✅ done 2026-06-25 |
| 0006 | Database webhooks (outbox INSERT -> API /integrations/outbox/process) | ✅ done 2026-06-25 |
| 0007 | pg_graphql + 3 storage buckets + publication supabase_realtime | ✅ done 2026-06-25 |
| 0008 | pgsodium + vault + vault_get_or_create helper | ✅ done 2026-06-25 (S08) |

## S0 — Operador (rodar após migration 0008)

```bash
# 1. Aplicar 0008
docker exec cartorio_api.1.<id> alembic upgrade head

# 2. Popular vault com 11 secrets
cd backend
uv run python scripts/seed_vault_secrets.py        # aplica
uv run python scripts/seed_vault_secrets.py --dry-run   # preview
```

## Triggers ativos após S0

- `fn_auto_audit()` em 6 tabelas PII (clientes, protocolos, atendimentos, documentos, conversas, emolumentos) — INSERT/UPDATE/DELETE gravam em audit_log automaticamente
- `notify_outbox_new()` em outbox_messages — INSERT faz pg_notify('outbox_new') (A24)
- `pg_cron` agenda 4 jobs (0005)

## Gotchas

- **pg_cron em UTC**: BRT = UTC-3. Schedule `0 6 * * *` = 03:00 BRT
- **psql em produção**: `docker exec cartorio_supabase-db-1 psql -U supabase_admin -h 127.0.0.1`
- **Vault sem secret**: `vault_get_or_create()` retorna 'AWAITING_OPERATOR' + WARNING (fail-loud)
- **Downgrade conservador**: nunca dropa extensão (outros sistemas podem depender)

## Validação obrigatória

Toda migration DEVE passar:

```bash
cd backend
uv run mypy app/                                 # 0 errors
uv run ruff check app/ alembic/                  # 0 errors
uv run pytest tests/ -q --no-cov                 # 920+ passed
alembic upgrade head                             # OK
alembic downgrade -1                             # OK
alembic upgrade head                             # re-aplica OK
```

---

**Maintained by**: Cartorio Dev Squad (Pietra orchestrator)
**Sprint**: 4-7 (2026-06-25 em diante)
**Last update**: 2026-06-25 (S0 S02-S08)
