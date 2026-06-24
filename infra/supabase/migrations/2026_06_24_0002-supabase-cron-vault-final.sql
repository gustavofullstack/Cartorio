-- ============================================
-- 2026-06-24 Supabase Cron + Vault (FINAL)
-- Applied via supabase_admin (DB owner) on VPS
-- ============================================
--
-- CONTEXTO:
--   DB `cartorio` e OWNED por `supabase_admin` (nao `postgres`).
--   pg_cron worker le jobs APENAS do DB configurado em
--   `cron.database_name` = 'postgres' (nao pode ser mudado em runtime
--   sem restart do container, que foi evitado para nao derrubar
--   OpenClaw em reinicializacao).
--
-- SOLUCAO:
--   - pg_cron: jobs criados no DB `postgres`, usando dblink
--     para executar SQL no DB `cartorio` (supabase_admin).
--   - supabase_vault + pg_net: criados diretamente no DB `cartorio`
--     (extensoes funcionam normalmente, owner e supabase_admin).
--
-- APLICADO EM:
--   ssh root@100.99.172.84
--   docker exec -i cartorio_supabase-db-1 psql -U supabase_admin -d <db>
--
-- ============================================
-- BLOCO 1: EXTENSIONS (DB cartorio)
-- ============================================
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;
CREATE SCHEMA IF NOT EXISTS vault;
CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;
-- pg_cron: NAO criar em cartorio (hard-blocked pelo worker).
--          Configurar cron.database_name='cartorio' exigiria restart
--          do container, o que foi evitado.

-- ============================================
-- BLOCO 2: VAULT SECRETS (DB cartorio)
-- 8 secrets: 7 chaves + 1 URL
-- ============================================
SELECT vault.create_secret('https://evo.odc.com.br',     'evolution_api_url',           'Evolution API base URL');
SELECT vault.create_secret('PLACEHOLDER_REPLACE_ME',     'evolution_api_key',           'Evolution API authentication key');
SELECT vault.create_secret('PLACEHOLDER_REPLACE_ME',     'chatwoot_api_key',            'Chatwoot API token');
SELECT vault.create_secret('PLACEHOLDER_REPLACE_ME',     'n8n_api_key',                 'n8n API token');
SELECT vault.create_secret('PLACEHOLDER_REPLACE_ME',     'opencode_go_api_key',         'OpenCode Go API key');
SELECT vault.create_secret('PLACEHOLDER_REPLACE_ME',     'openclaw_api_key',            'OpenClaw API key');
SELECT vault.create_secret('PLACEHOLDER_REPLACE_ME',     'telegram_webhook_secret',     'Telegram webhook HMAC secret');
SELECT vault.create_secret('PLACEHOLDER_REPLACE_ME',     'cartorio_api_key_placeholder','Cartorio internal API key placeholder');

-- ============================================
-- BLOCO 3: CRON JOBS (DB postgres, target=cartorio via dblink)
-- Worker pg_cron roda APENAS em postgres (cron.database_name).
-- Cada job usa dblink para executar SQL no DB cartorio.
-- ============================================

-- Job 1: cleanup-sessions-24h -- apaga sessoes inativas > 24h
SELECT cron.schedule(
  'cleanup-sessions-24h',
  '0 3 * * *',
  $J$SELECT dblink_exec('dbname=cartorio user=supabase_admin',
    'DELETE FROM public.chat_hub_sessions WHERE "lastMessageAt" < NOW() - INTERVAL ''24 hours'' AND type=''production''')$J$
);

-- Job 2: audit-chain-verify-6h -- conta audit_log entries sem HMAC
SELECT cron.schedule(
  'audit-chain-verify-6h',
  '0 */6 * * *',
  $J$SELECT dblink_exec('dbname=cartorio user=supabase_admin',
    'SELECT COUNT(*) FROM public.audit_log WHERE hmac_signature IS NULL')$J$
);

-- Job 3: retention-daily-03h -- remove audit_log > 365 dias
SELECT cron.schedule(
  'retention-daily-03h',
  '0 3 * * *',
  $J$SELECT dblink_exec('dbname=cartorio user=supabase_admin',
    'DELETE FROM public.audit_log WHERE timestamp < NOW() - INTERVAL ''365 days''')$J$
);

-- Job 4: stale-detector-5min -- incrementa attempts em DLQ items
SELECT cron.schedule(
  'stale-detector-5min',
  '*/5 * * * *',
  $J$SELECT dblink_exec('dbname=cartorio user=supabase_admin',
    'UPDATE public.webhook_event_dlq SET attempts = attempts + 1 WHERE attempts < 5')$J$
);

-- Job 5: dlq-refresh-10min -- sanity count do DLQ
SELECT cron.schedule(
  'dlq-refresh-10min',
  '*/10 * * * *',
  $J$SELECT dblink_exec('dbname=cartorio user=supabase_admin',
    'SELECT COUNT(*) FROM public.webhook_event_dlq')$J$
);

-- ============================================
-- VERIFICACAO POS-APLICACAO
-- ============================================
-- postgres DB:
--   SELECT jobid, jobname, schedule, active FROM cron.job ORDER BY jobid;
--   => 5 rows: cleanup-sessions-24h, audit-chain-verify-6h,
--              retention-daily-03h, stale-detector-5min, dlq-refresh-10min
--
-- cartorio DB:
--   SELECT name FROM vault.secrets ORDER BY name;
--   => 8 rows: cartorio_api_key_placeholder, chatwoot_api_key,
--              evolution_api_key, evolution_api_url, n8n_api_key,
--              openclaw_api_key, opencode_go_api_key, telegram_webhook_secret
-- ============================================
