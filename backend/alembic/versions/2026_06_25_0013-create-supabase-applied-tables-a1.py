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
    # Create clientes table (identidade do usuario)
    op.execute(
        """
        CREATE TABLE clientes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            whatsapp_id TEXT UNIQUE NOT NULL,
            nome TEXT,
            cpf TEXT UNIQUE,
            status TEXT DEFAULT 'ativo',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
            motivo_encerramento TEXT,
            deleted_at TIMESTAMP WITH TIME ZONE
        )
        """
    )

    # Create historico_atendimento table (memoria do agent)
    op.execute(
        """
        CREATE TABLE historico_atendimento (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE,
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
        CREATE TABLE sessoes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE,
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
    op.execute(
        """
        CREATE INDEX idx_clientes_whatsapp ON clientes (whatsapp_id)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_clientes_deleted_at ON clientes (deleted_at)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_historico_cliente ON historico_atendimento (cliente_id)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_historico_deleted_at ON historico_atendimento (deleted_at)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_sessoes_session_id ON sessoes (session_id)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_sessoes_cliente ON sessoes (cliente_id)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_sessoes_deleted_at ON sessoes (deleted_at)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sessoes CASCADE")
    op.execute("DROP TABLE IF EXISTS historico_atendimento CASCADE")
    op.execute("DROP TABLE IF EXISTS clientes CASCADE")