-- G8.19.T4 — audit_log é append-only: retenção nunca pode apagá-lo.
--
-- Migração idempotente para bancos que já receberam o cron legado
-- `retention-daily-03h`. O job é removido e um trigger de banco acrescenta
-- uma defesa em profundidade além das RLS policies da migration Alembic 0022.
--
-- LGPD review obrigatório antes de aplicar em produção.

BEGIN;

DO $$
DECLARE
    retention_job_id bigint;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'cron') THEN
        FOR retention_job_id IN
            SELECT jobid FROM cron.job WHERE jobname = 'retention-daily-03h'
        LOOP
            PERFORM cron.unschedule(retention_job_id);
        END LOOP;
    END IF;
END
$$;

CREATE OR REPLACE FUNCTION public.audit_log_reject_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only; UPDATE and DELETE are forbidden'
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS audit_log_append_only_guard ON public.audit_log;
CREATE TRIGGER audit_log_append_only_guard
BEFORE UPDATE OR DELETE ON public.audit_log
FOR EACH ROW EXECUTE FUNCTION public.audit_log_reject_mutation();

COMMIT;
