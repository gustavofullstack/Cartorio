# G8.06.T3 — RLS Inventory (cliente PII tables)

**Task:** G8.06.T3  
**Module:** `backend/app/services/rls_inventory.py`  
**SQL ref:** `infra/supabase/rls_g8.sql`  
**Canonical migration:** `backend/alembic/versions/2026_06_25_0004-supabase-rls-policies-and-audit-chain-fn.py`  
**Related:** `docs/RLS_AUDIT_SAMPLE_G7.md` (G7 sample audit)

## Scope

Tables with cliente PII in scope of this validator:

| Table | `authenticated_read_own` join col |
|-------|-----------------------------------|
| `clientes` | `id` |
| `conversas` | `cliente_id` |
| `protocolos` | `cliente_id` |
| `atendimentos` | `cliente_id` |

## Expected policies (3 × 4 = 12)

| Policy | CMD | Roles |
|--------|-----|-------|
| `service_role_full_access` | ALL | `service_role` |
| `dpo_read_access` | SELECT | `dpo` |
| `authenticated_read_own` | SELECT | `authenticated` |

`anon` has **no** policy on these tables (deny-by-default when RLS is ENABLE).

## Python API

```python
from app.services.rls_inventory import (
    EXPECTED_RLS_POLICIES,
    list_expected_policies,
    validate_rls_inventory,
    render_pg_policies_query,
)

# rows = result of pg_policies query (list[dict])
report = validate_rls_inventory(rows)
assert report["ok"], report["summary"]
# report keys: missing, extra, matched, red_flags, out_of_scope
```

CLI (from `backend/`):

```bash
unset PYTHONPATH
.venv312/bin/python -m app.services.rls_inventory --inventory
.venv312/bin/python -m app.services.rls_inventory --sql
.venv312/bin/python -m app.services.rls_inventory --query
.venv312/bin/python -m app.services.rls_inventory --validate-self
```

## Live SQL

```sql
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual AS using_expr,
  with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('clientes', 'conversas', 'protocolos', 'atendimentos')
ORDER BY tablename, policyname;
```

## Red flags (must not appear if 0004 is canonical)

| Pattern | Why |
|---------|-----|
| `anon_*` | Breaks “anon SEM acesso” design |
| `auth_all_*` | FOR ALL USING true **OR**s with own-filter and nullifies it |
| `service_all_*` | Legacy naming from `schema.sql` dump |

## Known gaps (from G7 audit)

1. `OR col IS NULL` in `authenticated_read_own` is a placeholder (review before exposing PostgREST with `authenticated`).
2. FastAPI with table-owner / superuser role **bypasses** RLS; RLS protects limited roles (PostgREST).
3. Full PII set in 0004 also includes `documentos`, `emolumentos` — out of G8.06.T3 narrow scope but same pattern.

## Status

| Item | Status |
|------|--------|
| Static inventory (Python) | DONE |
| SQL reference (`rls_g8.sql`) | DONE |
| Unit tests `test_rls_inventory_g8.py` | DONE |
| Live `pg_policies` on prod | HOLD (ops) |

Modified by Gustavo Almeida — G8.06.T3.
