"""A19 SQUAD A: Soft delete extended — atendimentos + webhook_events.

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-02

Adiciona coluna `deleted_at TIMESTAMP NULL` em:
- atendimentos (drift fix: migration 0002 A17 ja adicionou em prod, mas
  o model Atendimento ficou sem declarar — adicionado em 2026-07-02)
- webhook_events (nova coluna para soft delete de dedup/replay)

Migration idempotente: ADD COLUMN IF NOT EXISTS + CREATE INDEX IF NOT EXISTS
(roda multipla sem erro).

Tabelas que JÁ tinham deleted_at antes desta migration:
- clientes (anterior a A17)
- protocolos (A17 0002 + A19 0015)
- atendimentos (A17 0002 — mas model nao refletiu)
- documentos (A17 0002 + A19 0015)
- conversas (A19 0015)
- agendamentos (A19 0015)

Tabelas que NAO devem ter deleted_at (intencional):
- audit_log (integridade da hash chain)
- outbox_messages (DLQ semantics)
"""

from alembic import op


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Atendimentos: drift fix. A17 0002 ja adicionou em prod,
    # IF NOT EXISTS garante idempotencia para quem reaplica.
    op.execute("ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_atendimentos_deleted_at ON atendimentos (deleted_at)")

    # WebhookEvents: nova coluna. Soft delete preserva dedup history
    # sem quebrar o UniqueConstraint(source, event_id).
    op.execute("ALTER TABLE webhook_events ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_webhook_events_deleted_at ON webhook_events (deleted_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_webhook_events_deleted_at")
    op.execute("ALTER TABLE webhook_events DROP COLUMN IF EXISTS deleted_at")
    op.execute("DROP INDEX IF EXISTS ix_atendimentos_deleted_at")
    op.execute("ALTER TABLE atendimentos DROP COLUMN IF EXISTS deleted_at")
