-- =============================================================================
-- G8.06.T4 — pg_notify triggers for critical metadata changes → n8n
-- =============================================================================
-- Canal: cartorio_meta
-- Tabelas: public.protocolos, public.atendimentos
-- Eventos: AFTER INSERT; AFTER UPDATE OF status (somente se status mudou)
--
-- Payload JSON (text, LGPD-safe — sem PII raw):
--   {
--     "channel": "cartorio_meta",
--     "table": "protocolos" | "atendimentos",
--     "op": "INSERT" | "UPDATE",
--     "id": <int>,
--     "status": "<new status>",
--     "old_status": null | "<old status>",
--     "protocolo_id": null | <int>,   -- só atendimentos (quando existir)
--     "numero": null | "<str>",       -- só protocolos (quando existir)
--     "ts": "<ISO UTC>"
--   }
--
-- n8n consumer: Postgres LISTEN cartorio_meta (ou bridge HTTP que reenvia).
-- Ver: docs/N8N_META_TRIGGERS_G8.md
--
-- Idempotente: CREATE OR REPLACE FUNCTION + DROP TRIGGER IF EXISTS.
-- Sem live DB required neste arquivo (aplica-se via psql/migration).
-- =============================================================================

CREATE OR REPLACE FUNCTION public.notify_cartorio_meta()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $fn$
DECLARE
  payload jsonb;
  row_new jsonb;
  old_status text;
  new_status text;
  numero_val text;
  protocolo_id_text text;
  protocolo_id_val bigint;
BEGIN
  -- Só dispara em INSERT, ou UPDATE quando status mudou
  IF TG_OP = 'UPDATE' THEN
    IF NEW.status IS NOT DISTINCT FROM OLD.status THEN
      RETURN NEW;
    END IF;
    old_status := OLD.status;
  ELSE
    old_status := NULL;
  END IF;

  new_status := NEW.status;
  row_new := to_jsonb(NEW);

  -- Campos opcionais via jsonb (funciona nas duas tabelas sem undefined_column)
  numero_val := row_new ->> 'numero';
  protocolo_id_text := row_new ->> 'protocolo_id';
  IF protocolo_id_text IS NULL OR protocolo_id_text = '' THEN
    protocolo_id_val := NULL;
  ELSE
    protocolo_id_val := protocolo_id_text::bigint;
  END IF;

  payload := jsonb_build_object(
    'channel', 'cartorio_meta',
    'table', TG_TABLE_NAME,
    'op', TG_OP,
    'id', NEW.id,
    'status', new_status,
    'old_status', old_status,
    'protocolo_id', protocolo_id_val,
    'numero', numero_val,
    'ts', to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')
  );

  -- pg_notify payload max ~8KB; nosso JSON é pequeno e sem PII
  PERFORM pg_notify('cartorio_meta', payload::text);

  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  -- Nunca quebra o DML de negócio por falha de notify
  RAISE WARNING 'notify_cartorio_meta failed on %.%: %', TG_TABLE_SCHEMA, TG_TABLE_NAME, SQLERRM;
  RETURN NEW;
END;
$fn$;

COMMENT ON FUNCTION public.notify_cartorio_meta() IS
  'G8.06.T4: pg_notify(cartorio_meta) on critical status changes (protocolos/atendimentos).';

-- -----------------------------------------------------------------------------
-- Triggers: protocolos
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_cartorio_meta_protocolos ON public.protocolos;
CREATE TRIGGER trg_cartorio_meta_protocolos
  AFTER INSERT OR UPDATE OF status
  ON public.protocolos
  FOR EACH ROW
  EXECUTE FUNCTION public.notify_cartorio_meta();

-- -----------------------------------------------------------------------------
-- Triggers: atendimentos
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_cartorio_meta_atendimentos ON public.atendimentos;
CREATE TRIGGER trg_cartorio_meta_atendimentos
  AFTER INSERT OR UPDATE OF status
  ON public.atendimentos
  FOR EACH ROW
  EXECUTE FUNCTION public.notify_cartorio_meta();

-- =============================================================================
-- Verificação (manual):
--   SELECT tgname, tgrelid::regclass
--     FROM pg_trigger
--    WHERE tgname LIKE 'trg_cartorio_meta%';
--   LISTEN cartorio_meta;
--   UPDATE protocolos SET status = status;  -- não deve notificar
--   UPDATE protocolos SET status = 'em_andamento' WHERE id = 1;
-- =============================================================================
