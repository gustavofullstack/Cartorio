-- G8.06.T3 — RLS inventory reference for cliente PII tables
-- Source of truth: Alembic 2026_06_25_0004 (S02) + backend/app/services/rls_inventory.py
--
-- Pattern: DROP POLICY IF EXISTS + CREATE POLICY (Postgres has no CREATE POLICY IF NOT EXISTS
-- on all versions; this is the idempotent apply style used in the migration).
--
-- Roles:
--   anon          — no policies here (deny-by-default with RLS ENABLE)
--   authenticated — SELECT own row (cliente_id or id)
--   service_role  — FOR ALL (backend / bypass operacional)
--   dpo           — SELECT (LGPD / ANPD reports)
--
-- Scope tables: clientes, conversas, protocolos, atendimentos
--
-- Apply only after reviewing drift vs live pg_policies.
-- Do NOT re-introduce anon_* or auth_all_* (see docs/RLS_INVENTORY_G8.md).

-- ---------------------------------------------------------------------------
-- Live inventory query
-- ---------------------------------------------------------------------------
-- SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
-- FROM pg_policies
-- WHERE schemaname = 'public'
--   AND tablename IN ('clientes', 'conversas', 'protocolos', 'atendimentos')
-- ORDER BY tablename, policyname;

-- ---------------------------------------------------------------------------
-- Ensure roles exist (migration-style)
-- ---------------------------------------------------------------------------
-- DO $$ BEGIN
--   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
--     CREATE ROLE service_role WITH NOLOGIN;
--   END IF;
--   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dpo') THEN
--     CREATE ROLE dpo WITH NOLOGIN;
--   END IF;
--   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
--     CREATE ROLE authenticated WITH NOLOGIN;
--   END IF;
--   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
--     CREATE ROLE anon WITH NOLOGIN;
--   END IF;
-- END $$;

-- CREATE SCHEMA IF NOT EXISTS auth;
-- CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql AS 'SELECT NULL::uuid';

-- === clientes ===
ALTER TABLE public.clientes ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.clientes FORCE ROW LEVEL SECURITY;  -- recommended in prod

DROP POLICY IF EXISTS service_role_full_access ON public.clientes;
CREATE POLICY service_role_full_access ON public.clientes
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS dpo_read_access ON public.clientes;
CREATE POLICY dpo_read_access ON public.clientes
  FOR SELECT TO dpo
  USING (true);

DROP POLICY IF EXISTS authenticated_read_own ON public.clientes;
CREATE POLICY authenticated_read_own ON public.clientes
  FOR SELECT TO authenticated
  USING (id::text = auth.uid()::text OR id IS NULL);

-- === conversas ===
ALTER TABLE public.conversas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_full_access ON public.conversas;
CREATE POLICY service_role_full_access ON public.conversas
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS dpo_read_access ON public.conversas;
CREATE POLICY dpo_read_access ON public.conversas
  FOR SELECT TO dpo
  USING (true);

DROP POLICY IF EXISTS authenticated_read_own ON public.conversas;
CREATE POLICY authenticated_read_own ON public.conversas
  FOR SELECT TO authenticated
  USING (cliente_id::text = auth.uid()::text OR cliente_id IS NULL);

-- === protocolos ===
ALTER TABLE public.protocolos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_full_access ON public.protocolos;
CREATE POLICY service_role_full_access ON public.protocolos
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS dpo_read_access ON public.protocolos;
CREATE POLICY dpo_read_access ON public.protocolos
  FOR SELECT TO dpo
  USING (true);

DROP POLICY IF EXISTS authenticated_read_own ON public.protocolos;
CREATE POLICY authenticated_read_own ON public.protocolos
  FOR SELECT TO authenticated
  USING (cliente_id::text = auth.uid()::text OR cliente_id IS NULL);

-- === atendimentos ===
ALTER TABLE public.atendimentos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_full_access ON public.atendimentos;
CREATE POLICY service_role_full_access ON public.atendimentos
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS dpo_read_access ON public.atendimentos;
CREATE POLICY dpo_read_access ON public.atendimentos
  FOR SELECT TO dpo
  USING (true);

DROP POLICY IF EXISTS authenticated_read_own ON public.atendimentos;
CREATE POLICY authenticated_read_own ON public.atendimentos
  FOR SELECT TO authenticated
  USING (cliente_id::text = auth.uid()::text OR cliente_id IS NULL);

-- ---------------------------------------------------------------------------
-- Red-flag cleanup (drift from historical schema.sql dump)
-- Uncomment only after confirming 0004 is canonical in the target DB.
-- ---------------------------------------------------------------------------
-- DROP POLICY IF EXISTS anon_select_own_clientes ON public.clientes;
-- DROP POLICY IF EXISTS anon_insert_own_clientes ON public.clientes;
-- DROP POLICY IF EXISTS auth_all_atendimentos ON public.atendimentos;
-- DROP POLICY IF EXISTS auth_all_conversas ON public.conversas;
-- DROP POLICY IF EXISTS service_all_all_tables ON public.clientes;
