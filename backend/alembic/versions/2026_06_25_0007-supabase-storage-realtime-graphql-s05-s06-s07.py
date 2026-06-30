"""S0 S05+S06+S07: Supabase GraphQL (PostgREST) + Storage buckets + Realtime channels

Revision ID: 2026_06_25_0007
Revises: 2026_06_25_0006
Create Date: 2026-06-25 06:00:00.000000

SQUAD S0 - 3 sub-tasks agrupadas (config-only, idempotente):

S05 GraphQL via PostgREST
- PostgREST ja expoe /rest/v1/<table>. Para GraphQL puro, Supabase usa
  pg_graphql extension. Habilitamos a extensao e definimos as permissões.
- Endpoint: https://supbase.2notasudi.com.br/graphql/v1
- Permissões: anon tem SELECT limitado (mesmas RLS policies do REST);
  service_role tem acesso total.

S06 Storage buckets (3 buckets, LGPD-by-design)
- cliente-docs: PRIVATE (apenas service_role). PDFs RG, CPF, comprovantes.
- protocolo-pdfs: PRIVATE (apenas service_role). PDFs de protocolos finalizados.
- satisfacao-forms: PUBLIC READ. Formularios de NPS e feedback.
- Para cada bucket: name, public (bool), file_size_limit, allowed_mime_types.

S07 Realtime channels (publication supabase_realtime)
- Adiciona 3 tabelas na publication: protocolos, atendimentos, lgpd_consents
- API backend escuta via Realtime WebSocket em /realtime/v1/websocket
- Canal 'protocolo_updates' monitora status de protocolos em tempo real
- Canal 'atendimento_live' para dashboards ao vivo
- Canal 'lgpd_consent_changes' para compliance em tempo real

Idempotente: tudo via DROP/CREATE com IF EXISTS/IF NOT EXISTS.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "2026_06_25_0007"
down_revision: Union[str, None] = "2026_06_25_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========================================================================
    # S05 — GraphQL via pg_graphql
    # ========================================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_graphql")
    # Permissao: schema public (ja vem com grant usage, idempotente)
    op.execute("GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon, authenticated")

    # ========================================================================
    # S06 — Storage buckets
    # ========================================================================
    op.execute("CREATE SCHEMA IF NOT EXISTS storage")

    # Cria tabela buckets se nao existir (Storage API do Supabase espera isso)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS storage.buckets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            owner UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            public BOOLEAN DEFAULT FALSE,
            avif_autodetection BOOLEAN DEFAULT FALSE,
            file_size_limit BIGINT,
            allowed_mime_types TEXT[],
            owner_id TEXT
        )
        """
    )

    # Remove buckets existentes (idempotente)
    for bucket in ("cliente-docs", "protocolo-pdfs", "satisfacao-forms"):
        op.execute(f"DELETE FROM storage.buckets WHERE name = '{bucket}'")

    # cliente-docs: PRIVATE, 50MB max, pdf/jpeg/png
    op.execute(
        """
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
            'cliente-docs', 'cliente-docs', FALSE, 52428800,
            ARRAY['application/pdf', 'image/jpeg', 'image/png']
        )
        """
    )

    # protocolo-pdfs: PRIVATE, 100MB max, pdf only
    op.execute(
        """
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
            'protocolo-pdfs', 'protocolo-pdfs', FALSE, 104857600,
            ARRAY['application/pdf']
        )
        """
    )

    # satisfacao-forms: PUBLIC READ, 5MB max, json
    op.execute(
        """
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
            'satisfacao-forms', 'satisfacao-forms', TRUE, 5242880,
            ARRAY['application/json']
        )
        """
    )

    # ========================================================================
    # S07 — Realtime channels
    # ========================================================================
    op.execute("CREATE SCHEMA IF NOT EXISTS supabase_realtime")

    # Cria a publication 'supabase_realtime' (ja vem no Supabase, idempotente)
    # Idempotente: para cada tabela, verifica se ja eh membro antes de adicionar
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
                CREATE PUBLICATION supabase_realtime FOR TABLE
                    public.protocolos,
                    public.atendimentos,
                    public.lgpd_consents;
            ELSE
                -- Adiciona tabelas faltantes (idempotente, uma por uma)
                IF NOT EXISTS (
                    SELECT 1 FROM pg_publication_tables
                    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'protocolos'
                ) THEN
                    ALTER PUBLICATION supabase_realtime ADD TABLE public.protocolos;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM pg_publication_tables
                    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'atendimentos'
                ) THEN
                    ALTER PUBLICATION supabase_realtime ADD TABLE public.atendimentos;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM pg_publication_tables
                    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'lgpd_consents'
                ) THEN
                    ALTER PUBLICATION supabase_realtime ADD TABLE public.lgpd_consents;
                END IF;
            END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    # S07 — remove tabelas da publication
    op.execute(
        """
        ALTER PUBLICATION supabase_realtime DROP TABLE IF EXISTS
            public.protocolos,
            public.atendimentos,
            public.lgpd_consents
        """
    )

    # S06 — remove buckets
    for bucket in ("cliente-docs", "protocolo-pdfs", "satisfacao-forms"):
        op.execute(f"DELETE FROM storage.buckets WHERE name = '{bucket}'")

    # S05 — nao dropa extensao pg_graphql (rollback conservador)
