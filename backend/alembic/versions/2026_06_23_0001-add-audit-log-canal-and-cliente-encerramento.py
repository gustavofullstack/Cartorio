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
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        # Postgres: IF NOT EXISTS nativo em ALTER TABLE / CREATE INDEX
        op.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS canal VARCHAR(32)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_canal ON audit_log (canal)")
        op.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS motivo_encerramento VARCHAR(32)")
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_clientes_motivo_encerramento "
            "ON clientes (motivo_encerramento)"
        )
        op.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS audit_encerramento_id INTEGER")
        op.execute(
            "DO $$ BEGIN "
            "IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints "
            "  WHERE constraint_name = 'clientes_audit_encerramento_id_fkey') THEN "
            "  ALTER TABLE clientes ADD CONSTRAINT clientes_audit_encerramento_id_fkey "
            "  FOREIGN KEY (audit_encerramento_id) REFERENCES audit_log(id) "
            "  ON DELETE SET NULL; "
            "END IF; END $$"
        )
        op.execute("CREATE INDEX IF NOT EXISTS ix_clientes_deleted_at ON clientes (deleted_at)")
    elif dialect == "sqlite":
        # SQLite: nao tem IF NOT EXISTS em ALTER TABLE. Verifica via PRAGMA.
        # Em dev/test, falha se ja existe - isso eh ok (create_all ja criou).
        # Em prod, alembic nem roda contra sqlite.
        cols_audit = {row[1] for row in bind.exec_driver_sql("PRAGMA table_info(audit_log)").fetchall()}
        if "canal" not in cols_audit:
            op.execute("ALTER TABLE audit_log ADD COLUMN canal VARCHAR(32)")
        idx_audit = {row[1] for row in bind.exec_driver_sql("PRAGMA index_list(audit_log)").fetchall()}
        if "ix_audit_log_canal" not in idx_audit:
            op.execute("CREATE INDEX ix_audit_log_canal ON audit_log (canal)")

        cols_cliente = {row[1] for row in bind.exec_driver_sql("PRAGMA table_info(clientes)").fetchall()}
        if "motivo_encerramento" not in cols_cliente:
            op.execute("ALTER TABLE clientes ADD COLUMN motivo_encerramento VARCHAR(32)")
        if "audit_encerramento_id" not in cols_cliente:
            op.execute("ALTER TABLE clientes ADD COLUMN audit_encerramento_id INTEGER")
        idx_cliente = {row[1] for row in bind.exec_driver_sql("PRAGMA index_list(clientes)").fetchall()}
        if "ix_clientes_motivo_encerramento" not in idx_cliente:
            op.execute("CREATE INDEX ix_clientes_motivo_encerramento ON clientes (motivo_encerramento)")
        if "ix_clientes_deleted_at" not in idx_cliente:
            op.execute("CREATE INDEX ix_clientes_deleted_at ON clientes (deleted_at)")
    else:
        raise NotImplementedError(f"Dialect {dialect} nao suportado nesta migration.")


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("ALTER TABLE clientes DROP CONSTRAINT IF EXISTS clientes_audit_encerramento_id_fkey")
        op.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS audit_encerramento_id")
        op.execute("DROP INDEX IF EXISTS ix_clientes_motivo_encerramento")
        op.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS motivo_encerramento")
        op.execute("DROP INDEX IF EXISTS ix_audit_log_canal")
        op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS canal")
    elif dialect == "sqlite":
        op.execute("DROP INDEX IF EXISTS ix_audit_log_canal")
        op.execute("ALTER TABLE audit_log DROP COLUMN canal")
        op.execute("DROP INDEX IF EXISTS ix_clientes_motivo_encerramento")
        op.execute("DROP INDEX IF EXISTS ix_clientes_deleted_at")
        op.execute("ALTER TABLE clientes DROP COLUMN motivo_encerramento")
        op.execute("ALTER TABLE clientes DROP COLUMN audit_encerramento_id")
    else:
        raise NotImplementedError(f"Dialect {dialect} nao suportado nesta migration.")
