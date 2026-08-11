"""Serializa writers Python e trigger da cadeia de audit log.

Revision ID: 0031
Revises: 0030
Create Date: 2026-08-11

Migration aditiva: substitui apenas a funcao do trigger e nao altera ou apaga
entradas existentes. O mesmo advisory transaction lock e adquirido por
``AuditService.log`` antes de ler o ultimo hash.
"""

from alembic import op


revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None

AUDIT_CHAIN_ADVISORY_LOCK_ID = 5784376957523074609

UPGRADE_SQL = rf"""
CREATE OR REPLACE FUNCTION public.fn_auto_audit() RETURNS trigger
LANGUAGE plpgsql
AS $function$
DECLARE
    v_action TEXT;
    v_resource TEXT;
    v_actor_id TEXT;
    v_payload JSONB;
    v_prev_hash TEXT;
    v_timestamp_utc TIMESTAMP WITHOUT TIME ZONE;
    v_ts TEXT;
    v_canonical TEXT;
    v_hash TEXT;
    v_hmac TEXT;
    v_key TEXT;
    v_hmac_kid TEXT;
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

    v_actor_id := COALESCE(
        NULLIF(current_setting('app.current_actor_id', true), ''),
        'auto_audit'
    );
    v_request_id := COALESCE(NULLIF(current_setting('app.request_id', true), ''), 'auto');
    v_canal := COALESCE(NULLIF(current_setting('app.canal', true), ''), 'system');
    v_ip := COALESCE(NULLIF(current_setting('app.ip', true), ''), '0.0.0.0');
    v_ua := COALESCE(
        NULLIF(current_setting('app.user_agent', true), ''),
        'auto_audit_trigger'
    );

    -- Deve preceder a leitura do tail. O lock e reentrante na mesma transacao,
    -- portanto mutations com trigger + AuditService nao entram em deadlock.
    PERFORM pg_advisory_xact_lock({AUDIT_CHAIN_ADVISORY_LOCK_ID});

    SELECT al.hash INTO v_prev_hash
    FROM audit_log al
    ORDER BY al.id DESC
    LIMIT 1;
    IF v_prev_hash IS NULL OR v_prev_hash = '' THEN
        v_prev_hash := repeat('0', 64);
    END IF;

    v_timestamp_utc := NOW() AT TIME ZONE 'UTC';
    v_ts := to_char(v_timestamp_utc, 'YYYY-MM-DD"T"HH24:MI:SS.US');
    v_canonical := '{{"payload":' || v_payload::text
        || ',"prev_hash":"' || v_prev_hash
        || '","timestamp":"' || v_ts || '"}}';
    v_hash := encode(digest(v_canonical, 'sha256'), 'hex');

    v_key := NULLIF(current_setting('app.audit_hmac_key', true), '');
    v_hmac_kid := NULLIF(current_setting('app.audit_hmac_kid', true), '');
    IF v_key IS NULL OR length(v_key) < 32 THEN
        RAISE EXCEPTION USING
            ERRCODE = '22023',
            MESSAGE = 'audit HMAC key is missing or invalid';
    END IF;
    IF v_hmac_kid IS NULL OR length(v_hmac_kid) > 64 THEN
        RAISE EXCEPTION USING
            ERRCODE = '22023',
            MESSAGE = 'audit HMAC kid is missing or invalid';
    END IF;

    v_hmac := encode(
        hmac(v_hash || ':' || v_ts || ':' || v_actor_id || ':' || v_action, v_key, 'sha256'),
        'hex'
    );

    INSERT INTO audit_log (
        actor_id, actor_type, action, resource, payload,
        request_id, canal, ip, user_agent,
        prev_hash, hash, hmac_signature, hmac_kid, timestamp
    ) VALUES (
        v_actor_id, 'system', v_action, v_resource, v_payload,
        v_request_id, v_canal, v_ip, v_ua,
        NULLIF(v_prev_hash, repeat('0', 64)), v_hash, v_hmac, v_hmac_kid, v_timestamp_utc
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$function$;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    raise RuntimeError("Audit trigger downgrade requires cartorio-lgpd approval")
