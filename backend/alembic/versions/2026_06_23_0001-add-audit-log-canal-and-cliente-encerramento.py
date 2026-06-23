"""add canal to audit_log + motivo_encerramento/audit_encerramento_id to clientes

Revision ID: 2026_06_23_0001
Revises:
Create Date: 2026-06-23 20:50:00.000000

NOTA: Esta migration foi criada DEPOIS de as colunas ja terem sido
aplicadas manualmente em prod via psql (Sprint 3 Bloco 6.1, 2026-06-23).
Alembic detecta 'no changes' em ambiente prod porque as colunas ja existem.
Em staging/dev limpo, a migration cria as colunas normalmente.

Background:
- LGPD art. 37: registro de tratamento precisa de canal de origem
- ADR-018 (DELETE /cliente/{id}): motivo_encerramento + audit chain link
- ADR-019 (Job retenção): rastreabilidade do encerramento
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026_06_23_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. audit_log.canal (VARCHAR 32, indexado)
    op.execute(
        "ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS canal VARCHAR(32)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_log_canal ON audit_log (canal)"
    )

    # 2. clientes.motivo_encerramento (VARCHAR 32, indexado)
    op.execute(
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS motivo_encerramento VARCHAR(32)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_clientes_motivo_encerramento "
        "ON clientes (motivo_encerramento)"
    )

    # 3. clientes.audit_encerramento_id (INTEGER, FK audit_log.id SET NULL)
    op.execute(
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS audit_encerramento_id INTEGER"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints "
        "  WHERE constraint_name = 'clientes_audit_encerramento_id_fkey') THEN "
        "  ALTER TABLE clientes ADD CONSTRAINT clientes_audit_encerramento_id_fkey "
        "  FOREIGN KEY (audit_encerramento_id) REFERENCES audit_log(id) "
        "  ON DELETE SET NULL; "
        "END IF; END $$"
    )

    # 4. clientes.deleted_at ja existia mas garante index
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_clientes_deleted_at ON clientes (deleted_at)"
    )


def downgrade() -> None:
    # Reverte em ordem inversa. CUIDADO: drop coluna destrutivo.
    op.execute(
        "ALTER TABLE clientes DROP CONSTRAINT IF EXISTS clientes_audit_encerramento_id_fkey"
    )
    op.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS audit_encerramento_id")
    op.execute("DROP INDEX IF EXISTS ix_clientes_motivo_encerramento")
    op.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS motivo_encerramento")
    op.execute("DROP INDEX IF EXISTS ix_audit_log_canal")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS canal")
