"""Fix fn_auto_audit: preencher hash + hmac_signature (NOT NULL).

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-09

P0 Telegram HITL (2026-07-09):
POST /api/v1/atendimento falhava com IntegrityError porque o trigger
`trg_auto_audit_atendimentos` → `fn_auto_audit()` inseria em audit_log
SEM as colunas obrigatorias `hash` e `hmac_signature`.

Impacto: bot Telegram /humano e criacao de ticket HITL retornavam 500
(transacao rollback). Comandos /start /menu /agendar (sem INSERT
atendimentos) continuavam OK — da percepcao "bot funciona mas humano nao".

Fix: recria `fn_auto_audit()` com:
- prev_hash da ultima linha de audit_log (ou 64 zeros)
- hash = sha256(canonical block) via pgcrypto digest
- hmac_signature = hmac(sha256) via pgcrypto, chave em GUC
  `app.audit_hmac_key` (setada no DB via ALTER DATABASE a partir de
  AUDIT_HMAC_KEY do container) com fallback 'auto_audit_local_key'

Idempotente: CREATE OR REPLACE FUNCTION.
Downgrade: restaura versao legada SEM hash (somente para rollback
controlado — NAO usar em prod).

Modified by Gustavo Almeida
"""

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


UPGRADE_SQL = r"""
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION public.fn_auto_audit() RETURNS trigger
LANGUAGE plpgsql
AS $function$
DECLARE
    v_action TEXT;
    v_resource TEXT;
    v_actor_id TEXT;
    v_payload JSONB;
    v_prev_hash TEXT;
    v_ts TEXT;
    v_canonical TEXT;
    v_hash TEXT;
    v_hmac TEXT;
    v_key TEXT;
    v_request_id TEXT;
    v_canal TEXT;
    v_ip TEXT;
    v_ua TEXT;
BEGIN
    v_resource := TG_TABLE_NAME;

    IF TG_OP = 'INSERT' THEN
        v_action := 'create';
        v_payload := to_jsonb(NEW);
    ELSIF TG_OP = 'UPDATE' THEN
        v_action := 'update';
        v_payload := jsonb_build_object('old', to_jsonb(OLD), 'new', to_jsonb(NEW));
    ELSIF TG_OP = 'DELETE' THEN
        v_action := 'delete';
        v_payload := to_jsonb(OLD);
    END IF;

    BEGIN
        v_actor_id := current_setting('app.current_actor_id', true);
    EXCEPTION WHEN OTHERS THEN
        v_actor_id := 'auto_audit';
    END;
    IF v_actor_id IS NULL OR v_actor_id = '' THEN
        v_actor_id := 'auto_audit';
    END IF;

    v_request_id := COALESCE(NULLIF(current_setting('app.request_id', true), ''), 'auto');
    v_canal := COALESCE(NULLIF(current_setting('app.canal', true), ''), 'system');
    v_ip := COALESCE(NULLIF(current_setting('app.ip', true), ''), '0.0.0.0');
    v_ua := COALESCE(NULLIF(current_setting('app.user_agent', true), ''), 'auto_audit_trigger');

    SELECT al.hash INTO v_prev_hash
    FROM audit_log al
    ORDER BY al.id DESC
    LIMIT 1;
    IF v_prev_hash IS NULL OR v_prev_hash = '' THEN
        v_prev_hash := repeat('0', 64);
    END IF;

    v_ts := to_char(clock_timestamp(), 'YYYY-MM-DD"T"HH24:MI:SS.US');

    v_canonical := '{"payload":' || v_payload::text
        || ',"prev_hash":"' || v_prev_hash
        || '","timestamp":"' || v_ts || '"}';

    v_hash := encode(digest(v_canonical, 'sha256'), 'hex');

    v_key := COALESCE(NULLIF(current_setting('app.audit_hmac_key', true), ''), 'auto_audit_local_key');
    v_hmac := encode(
        hmac(v_hash || ':' || v_ts || ':' || v_actor_id || ':' || v_action, v_key, 'sha256'),
        'hex'
    );

    INSERT INTO audit_log (
        actor_id, actor_type, action, resource, payload,
        request_id, canal, ip, user_agent,
        prev_hash, hash, hmac_signature, timestamp
    ) VALUES (
        v_actor_id, 'system', v_action, v_resource, v_payload,
        v_request_id, v_canal, v_ip, v_ua,
        NULLIF(v_prev_hash, repeat('0', 64)), v_hash, v_hmac, NOW()
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$function$;
"""

DOWNGRADE_SQL = r"""
CREATE OR REPLACE FUNCTION public.fn_auto_audit() RETURNS trigger
LANGUAGE plpgsql
AS $function$
DECLARE
    v_action TEXT;
    v_resource TEXT;
    v_actor_id TEXT;
    v_payload JSONB;
BEGIN
    v_resource := TG_TABLE_NAME;

    IF TG_OP = 'INSERT' THEN
        v_action := 'create';
        v_payload := to_jsonb(NEW);
    ELSIF TG_OP = 'UPDATE' THEN
        v_action := 'update';
        v_payload := jsonb_build_object('old', to_jsonb(OLD), 'new', to_jsonb(NEW));
    ELSIF TG_OP = 'DELETE' THEN
        v_action := 'delete';
        v_payload := to_jsonb(OLD);
    END IF;

    BEGIN
        v_actor_id := current_setting('app.current_actor_id', true);
    EXCEPTION WHEN OTHERS THEN
        v_actor_id := 'auto_audit';
    END;
    IF v_actor_id IS NULL OR v_actor_id = '' THEN
        v_actor_id := 'auto_audit';
    END IF;

    INSERT INTO audit_log (
        actor_id, actor_type, action, resource, payload,
        request_id, canal, ip, user_agent, timestamp
    ) VALUES (
        v_actor_id, 'system', v_action, v_resource, v_payload,
        COALESCE(current_setting('app.request_id', true), 'auto'),
        COALESCE(current_setting('app.canal', true), 'system'),
        COALESCE(current_setting('app.ip', true), '0.0.0.0'),
        COALESCE(current_setting('app.user_agent', true), 'auto_audit_trigger'),
        NOW()
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$function$;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
