"""Fix fn_auto_audit: ts hasheado == ts armazenado (verificabilidade).

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-24

Nota (W0 inventário 2026-07-24): originalmente numerada 0022/down 0021, o que
colidia com ``0022_audit_log_rls_no_edit_no_delete.py`` (mesmo revision id) e
quebrava o grafo Alembic (heads múltiplas). Re-id para 0028 após a head linear
0021→0022(RLS)→0023→0024→0025→0026→0027. Conteúdo SQL inalterado.

Wave Final P0 (2026-07-24) — ROOT CAUSE da cadeia quebrada em prod
(`POST /api/v1/audit/verify` -> chain_ok=false, last_valid_position=667):

A migracao 0020 criou `fn_auto_audit()` com DOIS defeitos de
verificabilidade:

1. **Canonicalizacao divergente**: o trigger monta o canonical block com
   `v_payload::text` (jsonb::text: ordem (len,bytewise), separadores com
   espaco, UTF-8 raw), enquanto `AuditService._canonical_block` (Python)
   usa `json.dumps(sort_keys=True, separators=(",",":"))`. Entradas
   escritas pelo trigger NUNCA recomputam no verificador Python
   (158 entradas sistematicas desde 2026-07-09 — provado: prev_hash
   linkage 100% continuo nas 1130 entradas; nao e tampering).

2. **Timestamp hasheado != timestamp armazenado**: o hash usa
   `v_ts := to_char(clock_timestamp(), ...)` mas a coluna `timestamp`
   recebe `NOW()`. clock_timestamp() != NOW() (microssegundos) — o
   verificador nao tem como reproduzir o valor hasheado a partir dos
   campos armazenados.

Esta migracao corrige o item 2 para TODAS as entradas futuras:
- `v_ts` passa a ser derivado de `NOW()` (mesmo valor gravado na coluna
  `timestamp`), formatado identico ao Python
  (`isoformat(timespec='microseconds')` == 'YYYY-MM-DD"T"HH24:MI:SS.US');
- a coluna `timestamp` recebe o MESMO `NOW()` usado no hash.

O item 1 e tratado no verificador (AuditService ganhou mirror
`_compute_hash_sql_trigger` com fallback controlado apenas para entradas
marcadas como trigger-written — fail-closed preservado). REVIEW
cartorio-lgpd obrigatorio (superficie audit).

Historico: as ~158 entradas legacy cujo v_ts divergiu de NOW() em
microssegundos podem permanecer nao-recomputaveis; decisao de
remediacao (anotar vs re-cadeiar) e do DPO/cartorio-lgpd — NUNCA
reescrever audit_log unilateralmente (append-only).

Idempotente: CREATE OR REPLACE FUNCTION.
Downgrade: restaura a versao da migracao 0020 (NAO usar em prod sem
decisao do DPO).

Modified by Gustavo Almeida
"""

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


UPGRADE_SQL = r"""
CREATE OR REPLACE FUNCTION public.fn_auto_audit() RETURNS trigger
LANGUAGE plpgsql
AS $function$
DECLARE
    v_action TEXT;
    v_resource TEXT;
    v_actor_id TEXT;
    v_payload JSONB;
    v_prev_hash TEXT;
    v_now TIMESTAMPTZ;
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

    -- Wave Final P0 (migracao 0022): o MESMO instante vai para o hash E
    -- para a coluna timestamp. Antes: hash usava clock_timestamp() e a
    -- coluna NOW() — divergencia de microssegundos tornava a entrada
    -- impossivel de re-verificar a partir dos campos armazenados.
    v_now := NOW();
    v_ts := to_char(v_now AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US');

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
        NULLIF(v_prev_hash, repeat('0', 64)), v_hash, v_hmac, v_now
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$function$;
"""

# Restaura exatamente o comportamento da migracao 0020 (rollback controlado).
DOWNGRADE_SQL = r"""
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


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
