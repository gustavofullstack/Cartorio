# A18 Auditoria — tabelas com `updated_at` no DB prod

**Data:** 2026-07-02
**Executor:** cartorio-dev (mvs_6c43838c17714d7aac601681c107b111)
**Método:** psql direto via SSH+Tailscale no container `cartorio_supabase.1`
**Database:** `admin@cartorio_supabase:5432/supabase`

---

## TL;DR

- **8 tabelas** têm coluna `updated_at` no DB.
- **0 triggers** `trg_set_updated_at_*` existem atualmente.
- **0 functions** `fn_set_updated_at` ou `set_updated_at` existem.
- A migration `2026_06_25_0009-trigger-update-at-a18.py` **nunca rodou** nesse DB
  (provavelmente falhou em `webhook_events` que só ganhou `updated_at` na `0015`
  posterior; OR foi revertida antes de chegar a prod; OR o DB foi criado por outro
  path sem alembic).
- **Gap real:** TODAS as 8 tabelas precisam do trigger, não apenas as 10 da
  migration `0009` (que lista `emolumentos`, `lgpd_consents`, `lgpd_audit_anpd`
  — nenhuma dessas tem `updated_at` na DB real).

---

## Query canônica (rodada)

```sql
SELECT table_name FROM information_schema.columns
WHERE column_name = 'updated_at' AND table_schema = 'public'
  AND table_name IN (
    'clientes','protocolos','atendimentos','documentos','conversas',
    'emolumentos','outbox_messages','webhook_events','lgpd_consents',
    'lgpd_audit_anpd','agendamentos'
  )
ORDER BY table_name;
```

## Resultado (8 rows)

| table_name        | data_type                     | is_nullable |
|-------------------|-------------------------------|-------------|
| agendamentos      | timestamp without time zone   | NO          |
| atendimentos      | timestamp without time zone   | NO          |
| clientes          | timestamp without time zone   | NO          |
| conversas         | timestamp without time zone   | NO          |
| documentos        | timestamp without time zone   | NO          |
| outbox_messages   | timestamp with time zone      | NO          |
| protocolos        | timestamp without time zone   | NO          |
| webhook_events    | timestamp without time zone   | NO          |

**Ausentes da migration 0009 mas irrelevantes:**
- `emolumentos` — não tem coluna `updated_at` (tabela legacy sem modelo Python)
- `lgpd_consents` — não existe (legado)
- `lgpd_audit_anpd` — não existe (legado)

## Verificação de trigger/function

```sql
SELECT tgname, tgrelid::regclass FROM pg_trigger
WHERE tgname LIKE 'trg_set_updated_at%';     -- (0 rows)

SELECT proname FROM pg_proc
WHERE proname LIKE '%updated_at%'
   OR proname LIKE '%set_updated%';          -- (0 rows)
```

**Conclusão:** zero infraestrutura de trigger existe no DB prod.

---

## Implicações para a migration `0018`

A migration nova (`0018_a18_complete_update_at_triggers.py`) precisa criar:

1. `fn_set_updated_at()` — função genérica `plpgsql` que setta `NEW.updated_at = NOW()`.
2. **8 triggers** `trg_set_updated_at_<tabela>` BEFORE UPDATE, um por tabela.
3. Idempotência via `DROP TRIGGER IF EXISTS` antes de `CREATE TRIGGER`.
4. `downgrade()` faz drop dos 8 triggers + drop da function.

A migration **NÃO pode** ser aplicada ao DB prod sem GO explícito do Gustavo
(Lesson 110 — push gate). Mas o código fica versionado e testado.

---

## Modified by Gustavo Almeida