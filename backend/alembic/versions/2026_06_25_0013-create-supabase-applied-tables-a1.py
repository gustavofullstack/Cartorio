"""create supabase applied tables (A1)

Revision ID: 2026_06_25_0013
Revises: 2026_06_25_0012
Create Date: 2026-06-25 00:00:00.000000

A1 SUPABASE — Tabela base da infraestrutura central do ecossistema.
Cria tabelas basicas exigidas pelo fluxo de dados principal:

1. clientes (identidade do usuario) — Parte 2 do SUPABASE.md
2. historico_atendimento (memoria do agent) — Parte 2 do SUPABASE.md
3. sessoes (conversas ativas) — Parte 2 do SUPABASE.md

Compatibilidade com soft delete e timestamps.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "2026_06_25_0013"
down_revision: Union[str, None] = "2026_06_25_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create historico_atendimento table (memoria do agent)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS historico_atendimento (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cliente_id INTEGER REFERENCES clientes(id) ON DELETE CASCADE,
            session_id TEXT,
            message_content TEXT NOT NULL,
            source TEXT DEFAULT 'operator',
            tokens_input INTEGER,
            tokens_output INTEGER,
            context_window INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
            deleted_at TIMESTAMP WITH TIME ZONE
        )
        """
    )

    # Create sessoes table (conversas ativas)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sessoes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cliente_id INTEGER REFERENCES clientes(id) ON DELETE CASCADE,
            session_id TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'iniciada',
            started_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
            ended_at TIMESTAMP WITH TIME ZONE,
            last_activity TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
            metadata TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
            deleted_at TIMESTAMP WITH TIME ZONE
        )
        """
    )

    # Criar indexes para performance (compat com soft delete)
    bind = op.get_bind()
    import sqlalchemy as sa

    # Verifica se a coluna whatsapp_id existe na tabela clientes
    has_whatsapp_id = False
    try:
        cols = sa.inspect(bind).get_columns("clientes")
        has_whatsapp_id = any(c["name"] == "whatsapp_id" for c in cols)
    except Exception:
        pass

    if has_whatsapp_id:
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_clientes_whatsapp ON clientes (whatsapp_id)
            """
        )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_clientes_deleted_at ON clientes (deleted_at)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_historico_cliente ON historico_atendimento (cliente_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_historico_deleted_at ON historico_atendimento (deleted_at)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessoes_session_id ON sessoes (session_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessoes_cliente ON sessoes (cliente_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessoes_deleted_at ON sessoes (deleted_at)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sessoes CASCADE")
    op.execute("DROP TABLE IF EXISTS historico_atendimento CASCADE")
