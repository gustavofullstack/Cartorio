"""Supabase Advanced: pgcrypto + Vault + GraphQL + Realtime (D15/C23)

SQUAD D15 - Enable pgcrypto for field-level encryption
SQUAD C23 - Realtime publication for live dashboards
SQUAD S05 - GraphQL exposure via pg_graphql comments

Passos:
1. CREATE EXTENSION pgcrypto (idempotent, IF NOT EXISTS)
2. Vault: store API keys as encrypted secrets
3. GraphQL: add comments to expose key views
4. Realtime: create publication for key tables
5. Helper function: encrypt_sensitive / decrypt_sensitive

Revision ID: 2026_06_25_0013
Revises: 2026_06_25_0012
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2026_06_25_0013"
down_revision: str | None = "2026_06_25_0012"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. pgcrypto extension (field-level encryption, D15)
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;"))

    # 2. Vault: ensure vault schema exists and store helper
    conn.execute(sa.text("""
        -- Ensure vault extension is available
        CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;

        -- Function to store a secret in Vault
        CREATE OR REPLACE FUNCTION public.vault_store_secret(
            p_name text,
            p_description text,
            p_secret text
        ) RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        BEGIN
            INSERT INTO vault.secrets (name, description, secret)
            VALUES (p_name, p_description, p_secret::text::bytea);
        END;
        $$;
    """))

    # 3. GraphQL: add pg_graphql comments to expose cartorio views
    # pg_graphql auto-exposes tables via EXECUTE format('comment on table %I is
    # $e$@graphql({"totalCount": {"enabled": true}})$e$', table_name)
    conn.execute(sa.text("""
        -- Expose clientes with totalCount
        COMMENT ON TABLE public.clientes IS
            '@graphql({"totalCount": {"enabled": true}, "name": "Clientes"})';
    """))
    conn.execute(sa.text("""
        COMMENT ON TABLE public.protocolos IS
            '@graphql({"totalCount": {"enabled": true}, "name": "Protocolos"})';
    """))
    conn.execute(sa.text("""
        COMMENT ON TABLE public.atendimentos IS
            '@graphql({"totalCount": {"enabled": true}, "name": "Atendimentos"})';
    """))
    conn.execute(sa.text("""
        COMMENT ON TABLE public.documentos IS
            '@graphql({"totalCount": {"enabled": true}, "name": "Documentos"})';
    """))
    conn.execute(sa.text("""
        COMMENT ON TABLE public.audit_log IS
            '@graphql({"totalCount": {"enabled": true}, "name": "AuditLog"})';
    """))

    # 4. Realtime publication for live dashboards (C23)
    conn.execute(sa.text("""
        -- Drop existing if stale, recreate with specific tables
        DROP PUBLICATION IF EXISTS cartorio_realtime;
        CREATE PUBLICATION cartorio_realtime FOR TABLE
            public.clientes,
            public.protocolos,
            public.atendimentos,
            public.audit_log,
            public.outbox_messages,
            public.lgpd_consents
        WITH (publish = 'insert, update, delete');
    """))

    # 5. Helper: encrypt/decrypt using pgcrypto (D15)
    conn.execute(sa.text("""
        CREATE OR REPLACE FUNCTION public.encrypt_sensitive(
            p_plaintext text,
            p_key text DEFAULT current_setting('app.encryption_key', true)
        ) RETURNS bytea
        LANGUAGE plpgsql
        STABLE
        SET search_path = public
        AS $$
        BEGIN
            IF p_key IS NULL OR p_key = '' THEN
                -- Fallback: return raw if no key configured
                RETURN convert_to(p_plaintext, 'UTF8');
            END IF;
            RETURN pgp_sym_encrypt(p_plaintext, p_key);
        END;
        $$;
    """))

    conn.execute(sa.text("""
        CREATE OR REPLACE FUNCTION public.decrypt_sensitive(
            p_ciphertext bytea,
            p_key text DEFAULT current_setting('app.encryption_key', true)
        ) RETURNS text
        LANGUAGE plpgsql
        STABLE
        SET search_path = public
        AS $$
        BEGIN
            IF p_key IS NULL OR p_key = '' THEN
                RETURN convert_from(p_ciphertext, 'UTF8');
            END IF;
            RETURN pgp_sym_decrypt(p_ciphertext, p_key);
        END;
        $$;
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DROP PUBLICATION IF EXISTS cartorio_realtime;"))
    conn.execute(sa.text("DROP FUNCTION IF EXISTS public.vault_store_secret;"))
    conn.execute(sa.text("DROP FUNCTION IF EXISTS public.encrypt_sensitive;"))
    conn.execute(sa.text("DROP FUNCTION IF EXISTS public.decrypt_sensitive;"))

    # Remove GraphQL comments (set to empty)
    for tbl in ["clientes", "protocolos", "atendimentos", "documentos", "audit_log"]:
        conn.execute(sa.text(f"COMMENT ON TABLE public.{tbl} IS NULL;"))
