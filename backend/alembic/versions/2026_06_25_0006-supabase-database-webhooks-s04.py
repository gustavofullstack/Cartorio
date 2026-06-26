"""S0 S04: Supabase Database Webhooks (outbox_messages -> API -> N8N)

Revision ID: 2026_06_25_0006
Revises: 2026_06_25_0005
Create Date: 2026-06-25 05:00:00.000000

S04 SQUAD S0 - Database Webhooks (integracao real-time Supabase)

A24 ja criou o trigger pg_notify('outbox_new') que dispara quando ha
INSERT em outbox_messages. Esta migration complementa criando o WEBHOOK
no Supabase que escuta o trigger via Realtime/PostgREST e faz HTTP POST
para a API em /api/v1/integrations/outbox/process.

Em Supabase self-hosted, webhooks sao armazenados em duas tabelas:
- supabase_functions.hooks (metadata do webhook)
- supabase_functions.http_request (log de requests)

A API ja tem o endpoint POST /api/v1/integrations/outbox/process que:
- Valida X-API-Key
- Idempotente (status==done nao reprocessa)
- Despacha para evolution/chatwoot/telegram/outbox

Este trigger + webhook fecham o loop:
  app cria outbox -> pg_notify -> supabase_listen -> HTTP POST -> API processa

Idempotente: DELETE FROM supabase_functions.hooks WHERE hook_name=NOME
antes de INSERT, para suportar re-run da migration.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "2026_06_25_0006"
down_revision: Union[str, None] = "2026_06_25_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Garante schema supabase_functions (ja vem na imagem Supabase, idempotente)
    op.execute("CREATE SCHEMA IF NOT EXISTS supabase_functions")

    # Cria tabela hooks se nao existir (imagem Supabase ja tem, mas por seguranca)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS supabase_functions.hooks (
            id BIGSERIAL PRIMARY KEY,
            hook_name TEXT NOT NULL UNIQUE,
            table_name TEXT NOT NULL,
            events TEXT[] NOT NULL DEFAULT '{}',
            http_method TEXT NOT NULL DEFAULT 'POST',
            http_url TEXT NOT NULL,
            http_headers JSONB DEFAULT '{}',
            function_name TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )

    # Remove webhook existente (idempotente)
    op.execute(
        "DELETE FROM supabase_functions.hooks WHERE hook_name = 'outbox_to_api'"
    )

    # Insere webhook outbox_to_api
    # URL alvo: endpoint da API. Em prod usa dominio publico https://api.2notasudi.com.br
    # Em dev usa http://host.docker.internal:8000 (acessivel do container supabase)
    op.execute(
        """
        INSERT INTO supabase_functions.hooks (
            hook_name, table_name, events, http_method, http_url, http_headers
        ) VALUES (
            'outbox_to_api',
            'outbox_messages',
            ARRAY['INSERT'],
            'POST',
            'https://api.2notasudi.com.br/api/v1/integrations/outbox/process',
            jsonb_build_object(
                'Content-Type', 'application/json',
                'X-API-Key', current_setting('app.cartorio_api_key', true)
            )
        )
        """
    )

    # Trigger auxiliar: tambem chama pg_notify ja foi feito em A24.
    # Aqui adicionamos REPLICA IDENTITY FULL para que o payload do webhook
    # contenha todos os campos da row (necessario para o handler processar).
    op.execute("ALTER TABLE outbox_messages REPLICA IDENTITY FULL")


def downgrade() -> None:
    op.execute("DELETE FROM supabase_functions.hooks WHERE hook_name = 'outbox_to_api'")
    op.execute("ALTER TABLE outbox_messages REPLICA IDENTITY DEFAULT")
