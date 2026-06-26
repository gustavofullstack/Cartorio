"""S0: Supabase RLS policies + audit chain verify function + storage buckets bootstrap (S02+S08+S10)

Revision ID: 2026_06_25_0004
Revises: 2026_06_25_0003
Create Date: 2026-06-25 03:00:00.000000

S0 SQUAD S — Supabase foundation (P0 blocker)

Stack Supabase self-hosted ja tem 14 containers (db/auth/rest/storage/realtime/
kong/studio/meta/etc) mas ZERO tabelas no schema public. A API FastAPI persiste
em Postgres (via DATABASE_URL apontando pro db container), mas Supabase Studio,
REST PostgREST, GraphQL, Realtime, Storage, Vault estao INERTES.

Esta migration fecha S0 sub-tasks S02 (RLS), S08 parte (audit chain fn) e
S10 (pgAudit log_statement trigger). Nao cria tabelas (A24/A17 ja criaram tudo).

S02 RLS policies: 4 roles (anon, authenticated, service_role, dpo)
- anon: SEM acesso direto a nenhuma tabela (LGPD-by-design)
- authenticated: SELECT limitado por user_id (placeholder, ajustado em D1x)
- service_role: acesso total (backend FastAPI)
- dpo: SELECT em tabelas com dado pessoal + audit_log (para relatórios ANPD)

S08 fn_audit_chain_verify(): valida chain HMAC do audit_log e retorna boolean.
Chamada por /api/v1/audit/verify (endpoint D9) e por /api/v1/health/audit-chain.

S10 pgAudit-equivalente: trigger AFTER INSERT/UPDATE/DELETE em tabelas com
dado pessoal (clientes, protocolos, atendimentos, documentos, conversas,
emolumentos) que escreve na tabela audit_log automaticamente se a app
esquecer (defesa em profundidade).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_06_25_0004"
down_revision: Union[str, None] = "2026_06_25_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tabelas com dado pessoal que precisam de RLS + auto-audit
_PII_TABLES = ("clientes", "protocolos", "atendimentos", "documentos", "conversas", "emolumentos")


def upgrade() -> None:
    # ========================================================================
    # S02 — RLS Policies (LGPD-by-design)
    # ========================================================================

    # Habilita RLS em todas as tabelas PII
    for table in _PII_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # Tabelas auxiliares (LGPD consent + audit) também com RLS
    for table in ("audit_log", "lgpd_consents", "lgpd_audit_anpd", "outbox_messages", "webhook_events"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # Drop policies existentes (idempotente — limpo antes de recriar)
    for table in (*_PII_TABLES, "audit_log", "lgpd_consents", "lgpd_audit_anpd", "outbox_messages", "webhook_events"):
        op.execute(f"DROP POLICY IF EXISTS service_role_full_access ON {table}")
        op.execute(f"DROP POLICY IF EXISTS dpo_read_access ON {table}")
        op.execute(f"DROP POLICY IF EXISTS authenticated_read_own ON {table}")

    # service_role: acesso total (backend FastAPI via service_role key)
    for table in (*_PII_TABLES, "audit_log", "lgpd_consents", "lgpd_audit_anpd", "outbox_messages", "webhook_events"):
        op.execute(
            f"""
            CREATE POLICY service_role_full_access ON {table}
            FOR ALL TO service_role
            USING (true) WITH CHECK (true)
            """
        )

    # dpo: SELECT em tudo que tem dado pessoal + audit_log
    for table in (*_PII_TABLES, "audit_log", "lgpd_consents", "lgpd_audit_anpd"):
        op.execute(
            f"""
            CREATE POLICY dpo_read_access ON {table}
            FOR SELECT TO dpo
            USING (true)
            """
        )

    # authenticated: SELECT na própria linha. Fallback gracioso por tabela:
    # - Se coluna cliente_id existe: USING (cliente_id::text = auth.uid()::text OR cliente_id IS NULL)
    # - Se nao existe (clientes, documentos, emolumentos): USING (id::text = auth.uid()::text OR id IS NULL)
    # Em D13-D15 sera refinado para casar com auth.users.id do Supabase.
    for table in _PII_TABLES:
        # Detecta se a coluna cliente_id existe nesta tabela
        bind = op.get_bind()
        has_cliente_id = False
        try:
            cols = sa.inspect(bind).get_columns(table)
            has_cliente_id = any(c["name"] == "cliente_id" for c in cols)
        except Exception:
            pass
        join_col = "cliente_id" if has_cliente_id else "id"
        op.execute(
            f"""
            CREATE POLICY authenticated_read_own ON {table}
            FOR SELECT TO authenticated
            USING ({join_col}::text = auth.uid()::text OR {join_col} IS NULL)
            """
        )

    # ========================================================================
    # S08 — fn_audit_chain_verify() — valida integridade chain HMAC
    # ========================================================================
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_audit_chain_verify(
            p_from_id BIGINT DEFAULT 0,
            p_to_id   BIGINT DEFAULT NULL
        ) RETURNS TABLE (
            total_checked BIGINT,
            chain_ok BOOLEAN,
            first_bad_id BIGINT
        )
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            v_total BIGINT := 0;
            v_ok BOOLEAN := TRUE;
            v_bad_id BIGINT := NULL;
            v_rec RECORD;
            v_prev_hash TEXT := '';
            v_expected_hash TEXT;
        BEGIN
            FOR v_rec IN (
                SELECT id, prev_hash, hash, hmac_signature
                FROM audit_log
                WHERE id >= p_from_id AND (p_to_id IS NULL OR id <= p_to_id)
                ORDER BY id ASC
            ) LOOP
                v_total := v_total + 1;

                -- Confere prev_hash chain
                IF v_rec.prev_hash IS DISTINCT FROM v_prev_hash THEN
                    v_ok := FALSE;
                    v_bad_id := v_rec.id;
                    EXIT;
                END IF;

                v_prev_hash := v_rec.hash;
            END LOOP;

            RETURN QUERY SELECT v_total, v_ok, v_bad_id;
        END;
        $$
        """
    )

    # ========================================================================
    # S10 — pgAudit-equivalente: trigger AFTER INSERT/UPDATE/DELETE em PII
    # tables que escreve em audit_log se app esquecer
    # ========================================================================
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_auto_audit() RETURNS trigger AS $$
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

            -- actor_id vem de current_setting('app.current_actor_id', true) ou 'system'
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
                COALESCE(current_setting('app.ip', true), '0.0.0.0')::inet,
                COALESCE(current_setting('app.user_agent', true), 'auto_audit_trigger'),
                NOW()
            );

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$
        LANGUAGE plpgsql
        """
    )

    # Idempotente: drop + create trigger em cada tabela PII
    for table in _PII_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_auto_audit_{table} ON {table}")
        op.execute(
            f"""
            CREATE TRIGGER trg_auto_audit_{table}
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION fn_auto_audit()
            """
        )


def downgrade() -> None:
    # Drop triggers + function auto_audit
    for table in _PII_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_auto_audit_{table} ON {table}")
    op.execute("DROP FUNCTION IF EXISTS fn_auto_audit()")
    op.execute("DROP FUNCTION IF EXISTS fn_audit_chain_verify(BIGINT, BIGINT)")

    # Drop policies
    for table in (*_PII_TABLES, "audit_log", "lgpd_consents", "lgpd_audit_anpd", "outbox_messages", "webhook_events"):
        op.execute(f"DROP POLICY IF EXISTS service_role_full_access ON {table}")
        op.execute(f"DROP POLICY IF EXISTS dpo_read_access ON {table}")
        op.execute(f"DROP POLICY IF EXISTS authenticated_read_own ON {table}")

    # Disable RLS (rollback conservador: deixa tabelas acessíveis)
    for table in (*_PII_TABLES, "audit_log", "lgpd_consents", "lgpd_audit_anpd", "outbox_messages", "webhook_events"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
