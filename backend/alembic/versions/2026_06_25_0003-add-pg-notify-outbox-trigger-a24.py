"""add pg_notify trigger for outbox_messages (A24)

Revision ID: 2026_06_25_0003
Revises: 2026_06_25_0002
Create Date: 2026-06-25 02:00:00.000000

A24 SQUAD A - triggers pg_notify para outbox em tempo real

Cria trigger que dispara pg_notify no canal 'outbox_new' quando
uma nova linha eh inserida em outbox_messages. Permite que workers
(API, N8N, Supabase Realtime) escutem em tempo real sem polling.

Canal: outbox_new
Payload: JSON com {id, event_type, resource, created_at}

Idempotente: DROP TRIGGER IF EXISTS + CREATE TRIGGER.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_06_25_0003"
down_revision: Union[str, None] = "2026_06_25_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Funcao trigger: notifica via pg_notify
    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_outbox_new() RETURNS trigger AS $$
        BEGIN
            PERFORM pg_notify(
                'outbox_new',
                json_build_object(
                    'id', NEW.id,
                    'event_type', NEW.event_type,
                    'resource', NEW.resource,
                    'created_at', NEW.created_at
                )::text
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Trigger AFTER INSERT
    op.execute("DROP TRIGGER IF EXISTS trg_outbox_new ON outbox_messages")
    op.execute(
        """
        CREATE TRIGGER trg_outbox_new
        AFTER INSERT ON outbox_messages
        FOR EACH ROW
        EXECUTE FUNCTION notify_outbox_new()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_outbox_new ON outbox_messages")
    op.execute("DROP FUNCTION IF EXISTS notify_outbox_new()")
