-- ============================================
-- 2026-06-24 Supabase Realtime + Webhooks (FINAL)
-- ============================================
-- CONTEXTO: webhooks sao criados via trigger no DB cartorio
-- que chama supabase_functions.http_request() (instalado no DB
-- postgres onde supabase_functions extension vive).
-- API key lida de vault.secrets (placeholder por enquanto).
-- ============================================

-- 1) REALTIME: garantir publication existe com 5 tabelas
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
    CREATE PUBLICATION supabase_realtime FOR TABLE
      atendimentos, conversas, lgpd_consent_log, outbox_messages, protocolos;
  ELSE
    -- Idempotente: adiciona tabelas que faltarem
    BEGIN ALTER PUBLICATION supabase_realtime ADD TABLE atendimentos; EXCEPTION WHEN duplicate_object THEN NULL; END;
    BEGIN ALTER PUBLICATION supabase_realtime ADD TABLE conversas; EXCEPTION WHEN duplicate_object THEN NULL; END;
    BEGIN ALTER PUBLICATION supabase_realtime ADD TABLE lgpd_consent_log; EXCEPTION WHEN duplicate_object THEN NULL; END;
    BEGIN ALTER PUBLICATION supabase_realtime ADD TABLE outbox_messages; EXCEPTION WHEN duplicate_object THEN NULL; END;
    BEGIN ALTER PUBLICATION supabase_realtime ADD TABLE protocolos; EXCEPTION WHEN duplicate_object THEN NULL; END;
  END IF;
END $$;

-- 2) WEBHOOK 1: outbox_messages INSERT -> API dispatch
CREATE OR REPLACE FUNCTION public.outbox_webhook() RETURNS trigger AS $F$
DECLARE
  api_key text;
BEGIN
  SELECT secret::text INTO api_key FROM vault.secrets
    WHERE name = 'cartorio_api_key_placeholder' LIMIT 1;
  IF api_key IS NULL OR api_key = 'PLACEHOLDER_REPLACE_ME' THEN
    api_key := 'PLACEHOLDER_REPLACE_ME';
  END IF;
  PERFORM supabase_functions.http_request(
    'https://api.2notasudi.com.br/api/v1/integrations/outbox/dispatch'::text,
    'POST'::text,
    jsonb_build_object('Content-Type','application/json','X-API-Key', api_key),
    jsonb_build_object('event','INSERT','table','outbox_messages','record', row_to_json(NEW)::jsonb),
    '5000'::text
  );
  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'outbox_webhook failed: %', SQLERRM;
  RETURN NEW;
END;
$F$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_outbox_webhook ON public.outbox_messages;
CREATE TRIGGER trg_outbox_webhook
  AFTER INSERT ON public.outbox_messages
  FOR EACH ROW EXECUTE FUNCTION public.outbox_webhook();

-- 3) WEBHOOK 2: protocolos UPDATE de status -> N8N flow
CREATE OR REPLACE FUNCTION public.protocolo_status_webhook() RETURNS trigger AS $F$
BEGIN
  IF (TG_OP = 'UPDATE') AND (
    NEW.status IS DISTINCT FROM OLD.status
    OR NEW.updated_at IS DISTINCT FROM OLD.updated_at
  ) THEN
    PERFORM supabase_functions.http_request(
      'https://flow.2notasudi.com.br/webhook/protocolo-status'::text,
      'POST'::text,
      '{"Content-Type":"application/json"}'::jsonb,
      jsonb_build_object(
        'event','UPDATE','table','protocolos',
        'old', row_to_json(OLD)::jsonb,
        'new', row_to_json(NEW)::jsonb
      ),
      '5000'::text
    );
  END IF;
  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'protocolo_status_webhook failed: %', SQLERRM;
  RETURN NEW;
END;
$F$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_protocolo_status_webhook ON public.protocolos;
CREATE TRIGGER trg_protocolo_status_webhook
  AFTER UPDATE ON public.protocolos
  FOR EACH ROW EXECUTE FUNCTION public.protocolo_status_webhook();

-- 4) WEBHOOK 3: lgpd_consent_log INSERT -> N8N flow
CREATE OR REPLACE FUNCTION public.lgpd_consent_webhook() RETURNS trigger AS $F$
BEGIN
  PERFORM supabase_functions.http_request(
    'https://flow.2notasudi.com.br/webhook/lgpd-consent'::text,
    'POST'::text,
    '{"Content-Type":"application/json"}'::jsonb,
    jsonb_build_object('event','INSERT','table','lgpd_consent_log','record', row_to_json(NEW)::jsonb),
    '5000'::text
  );
  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'lgpd_consent_webhook failed: %', SQLERRM;
  RETURN NEW;
END;
$F$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_lgpd_consent_webhook ON public.lgpd_consent_log;
CREATE TRIGGER trg_lgpd_consent_webhook
  AFTER INSERT ON public.lgpd_consent_log
  FOR EACH ROW EXECUTE FUNCTION public.lgpd_consent_webhook();

-- ============================================
-- VERIFICACAO
-- ============================================
-- SELECT schemaname, tablename FROM pg_publication_tables WHERE pubname='supabase_realtime';
-- SELECT tgname, tgrelid::regclass FROM pg_trigger WHERE tgname LIKE '%webhook%';

-- ============================================
-- BLOCO 4: pg_graphql (DB cartorio)
-- Habilitado para suportar queries GraphQL sobre schema public.
-- Validado: atendimentosCollection retorna dados via graphql.resolve().
-- Schema version: 4
-- ============================================
CREATE EXTENSION IF NOT EXISTS pg_graphql;

-- ============================================
-- VERIFICACAO POS-APLICACAO
-- ============================================
-- Realtime:
--   SELECT schemaname, tablename FROM pg_publication_tables
--     WHERE pubname='supabase_realtime' ORDER BY tablename;
--   => 5 rows: atendimentos, conversas, lgpd_consent_log,
--              outbox_messages, protocolos
--
-- Webhooks (triggers):
--   SELECT tgname, tgrelid::regclass FROM pg_trigger
--     WHERE tgname LIKE '%webhook%';
--   => 3 rows: trg_outbox_webhook, trg_protocolo_status_webhook,
--              trg_lgpd_consent_webhook
--
-- pg_graphql:
--   SELECT graphql.resolve('{ atendimentosCollection(first:1){ edges { node { id } } } }');
--   => {"data":{"atendimentosCollection":{"edges":[{"node":{"id":1}}]}}}
--
-- NOTA SOBRE API KEY:
--   O secret 'cartorio_api_key_placeholder' em vault esta como
--   'PLACEHOLDER_REPLACE_ME'. Webhook 1 (outbox) le vault no
--   runtime; trocar o valor UPDATE no vault.secrets.secret e
--   webhooks passam a usar a chave real sem novo deploy.
-- ============================================
