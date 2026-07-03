# A18 — Trigger `fn_set_updated_at` em todas as tabelas com `updated_at`

**Data:** 2026-07-02
**Sprint:** SQUAD A (API/DB Hardening)
**Branch:** master (local)
**Commit:** `7e61a6621a901707ce00e7206abaa08afccda38b` (NAO pushed — push gate Lesson 110)
**Migration:** `backend/alembic/versions/2026_07_02_0019-a18-complete-update-at-triggers.py`
**Test file:** `backend/tests/test_a18_updated_at.py`

---

## TL;DR

Cria trigger PostgreSQL `BEFORE UPDATE ... FOR EACH ROW` que setta
`NEW.updated_at = NOW()` em **8 tabelas** com coluna `updated_at` no DB prod.
Migration **idempotente** (rodar 2x eh no-op alem de `CREATE OR REPLACE`
na function). Funciona tambem para updates via SQL puro (psql, job batch,
n8n direto) — defesa em profundidade alem do `onupdate=datetime.utcnow`
do TimestampMixin (que soh funciona em updates via ORM).

---

## Tabelas cobertas (auditadas 2026-07-02)

```
agendamentos, atendimentos, clientes, conversas, documentos,
outbox_messages, protocolos, webhook_events
```

(8 tabelas — ver `A18-audit.md` para query SQL exata + resultado.)

**NAO cobertas (intencional):**
- `audit_log` — append-only, hash chain imutavel (LGPD art. 37)
- `outbox_messages` — TEM updated_at (status muda) E TEM trigger
- `emolumentos` — tabela legacy sem coluna `updated_at` no DB

**Gap real pre-existente:**
- Migration `2026_06_25_0009-trigger-update-at-a18.py` lista 10 tabelas,
  mas **nunca rodou com sucesso** no DB prod (referencia `webhook_events`
  antes da `0015` adicionar a coluna `updated_at`). Esta migration `0019`
  substitui a `0009` na pratica.

---

## Design da migration

```sql
CREATE OR REPLACE FUNCTION fn_set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 8x (DROP TRIGGER IF EXISTS + CREATE TRIGGER) idempotente
DROP TRIGGER IF EXISTS trg_set_updated_at_agendamentos ON agendamentos;
CREATE TRIGGER trg_set_updated_at_agendamentos
BEFORE UPDATE ON agendamentos
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
-- ... mesmo para as outras 7 tabelas
```

### Por que `DROP IF EXISTS` + `CREATE` (nao `CREATE OR REPLACE TRIGGER`)

PostgreSQL NAO suporta `CREATE OR REPLACE TRIGGER` (apenas function).
Logo, o pattern canonico eh `DROP IF EXISTS` + `CREATE`. Isso torna a
migration idempotente mesmo se rodarmos `alembic upgrade head` 5x.

### `downgrade()` reversivel

```python
for table in TABLES_WITH_UPDATED_AT:
    op.execute(f"DROP TRIGGER IF EXISTS trg_set_updated_at_{table} ON {table}")
op.execute("DROP FUNCTION IF EXISTS fn_set_updated_at()")
```

---

## Tests (17 cenarios)

`tests/test_a18_updated_at.py` — 13 passam em SQLite + 4 skipif PG:

| # | Tipo | Cenario | Resultado |
|---|------|---------|-----------|
| 1 | schema | `0019` file existe | passa |
| 2 | schema | fn_set_updated_at com CREATE OR REPLACE | passa |
| 3 | schema | 8 tabelas listadas | passa |
| 4 | schema | BEFORE UPDATE FOR EACH ROW | passa |
| 5 | schema | upgrade() idempotente (DROP+CREATE em loop) | passa |
| 6 | schema | downgrade() dropa 8 triggers + function | passa |
| 7 | schema | chain 0019 → down=0018 | passa |
| 8 | PG | UPDATE em tabela COM trigger → updated_at muda | SKIP (sem PG local) |
| 9 | PG | UPDATE em tabela SEM trigger → updated_at NAO muda | SKIP |
| 10 | PG | migration idempotente (rodar upgrade 2x) | SKIP |
| 11 | PG | INSERT NAO dispara trigger BEFORE UPDATE | SKIP |
| 12-15 | mixin | TimestampMixin + SQLAlchemy onupdate | passa |
| 16 | legacy | migration 0009 legada existe para historico | passa |

**Os 4 testes PG-only rodarao automaticamente quando Gustavo aplicar a
migration em prod + rodar CI com `DATABASE_URL=postgresql+psycopg://...`.**

---

## Output do alembic upgrade (esperado, ainda NAO aplicado)

```
$ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade 0018 -> 0019, A18 COMPLETE trigger
INFO  [alembic.runtime.migration] CREATE OR REPLACE FUNCTION fn_set_updated_at()
INFO  [alembic.runtime.migration] CREATE TRIGGER trg_set_updated_at_agendamentos
INFO  [alembic.runtime.migration] CREATE TRIGGER trg_set_updated_at_atendimentos
... (8 triggers total)
```

Validacao pos-upgrade:

```sql
SELECT tgname, tgrelid::regclass FROM pg_trigger
WHERE tgname LIKE 'trg_set_updated_at%' ORDER BY tgrelid::regclass::text;
-- Deve retornar 8 rows

SELECT proname FROM pg_proc WHERE proname = 'fn_set_updated_at';
-- Deve retornar 1 row

UPDATE clientes SET nome = nome WHERE id = 1;
SELECT updated_at FROM clientes WHERE id = 1;
-- Deve ser > valor anterior
```

---

## Decisão de push: NAO pushed

Conforme Lesson 110 + regra Gustavo: **NAO push sem Gustavo GO**.

Codigo commitado localmente em `7e61a6621a901707ce00e7206abaa08afccda38b`.
Migration versionada no master. Aplicacao em prod aguarda Gustavo autorizar.

**Proximos passos** (para Gustavo):
1. Review do diff: `git show 7e61a66`
2. Aprovar merge
3. Push: `git push origin master` (com a migration nao causa downtime — eh
   CREATE OR REPLACE FUNCTION + CREATE TRIGGER, atomico)
4. Deploy: `docker service update --force cartorio_api` (rollback trivial:
   `alembic downgrade -1` dropa os triggers + function)

---

## Cross-ref

- Audit completo: `A18-audit.md` (neste diretorio)
- Memory canon (Lesson 185 Migration DESIGN-FAIL-SILENT): aplicado aqui —
  `0009` original TINHA try/except/pass implicito (DROP sem IF EXISTS nao
  cobria webhook_events quando coluna nao existia). `0019` eh safe-by-
  design: soh faz CREATE TRIGGER em tabelas que JA tem coluna (verificada
  via `information_schema` em 2026-07-02).
- LGPD: trigger garante audit trail exato (LGPD art. 37 — rastreabilidade).
- Master-only rule: respeitada (NAO pushed, NAO rotacionadas chaves).

---

## Modified by Gustavo Almeida