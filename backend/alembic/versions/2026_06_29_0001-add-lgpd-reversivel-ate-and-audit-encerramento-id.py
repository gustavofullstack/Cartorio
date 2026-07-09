"""A27: Add LGPD reversivel_ate + audit_encerramento_id columns to clientes.

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-29

Fixes: sqlalchemy.exc.ProgrammingError column clientes.lgpd_reversivel_ate
does not exist (error in /api/v1/lgpd/access/{cliente_id} endpoint).

Turno 24+ 2026-06-29: LGPD v2 endpoints (D26-D32) failed with 500 because
clientes table on VPS prod is missing columns that exist in the SQLAlchemy
model (Cliente.lgpd_reversivel_ate + Cliente.audit_encerramento_id).

Adds:
- clientes.lgpd_reversivel_ate TIMESTAMP NULL
  (LGPD art. 18 V - ate quando anonimizacao pode ser revertida)
- clientes.audit_encerramento_id INTEGER NULL (FK to audit_log.id)
  (LGPD art. 37 - rastreabilidade da decisao de encerramento)
- Index on clientes.lgpd_reversivel_ate (queries for "reversible dentro de X dias")
"""

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def _add_column_if_not_exists(table_name: str, column_name: str, *args, **kwargs) -> None:
    bind = op.get_bind()
    import sqlalchemy as sa

    inspector = sa.inspect(bind)
    cols = inspector.get_columns(table_name)
    if not any(c["name"] == column_name for c in cols):
        op.add_column(table_name, sa.Column(column_name, *args, **kwargs))


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    import sqlalchemy as sa

    inspector = sa.inspect(bind)
    cols = inspector.get_columns(table_name)
    if any(c["name"] == column_name for c in cols):
        op.drop_column(table_name, column_name)


def _create_index_if_not_exists(index_name: str, table_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    import sqlalchemy as sa

    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes(table_name)
    if not any(idx["name"] == index_name for idx in indexes):
        op.create_index(index_name, table_name, columns)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    bind = op.get_bind()
    import sqlalchemy as sa

    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes(table_name)
    if any(idx["name"] == index_name for idx in indexes):
        op.drop_index(index_name, table_name)


def upgrade() -> None:
    # LGPD direito ao esquecimento (art. 18 V): NULL = nao anonimizado.
    _add_column_if_not_exists("clientes", "lgpd_reversivel_ate", sa.DateTime(), nullable=True)
    _create_index_if_not_exists(
        "ix_clientes_lgpd_reversivel_ate",
        "clientes",
        ["lgpd_reversivel_ate"],
    )

    # LGPD art. 37: rastrear qual entry do audit log documentou o encerramento.
    # FK com use_alter=True permite dropar audit_log sem cascade.
    _add_column_if_not_exists(
        "clientes",
        "audit_encerramento_id",
        sa.Integer(),
        sa.ForeignKey("audit_log.id", use_alter=True, ondelete="SET NULL"),
        nullable=True,
    )
    _create_index_if_not_exists(
        "ix_clientes_audit_encerramento_id",
        "clientes",
        ["audit_encerramento_id"],
    )


def downgrade() -> None:
    _drop_index_if_exists("ix_clientes_audit_encerramento_id", "clientes")
    _drop_column_if_exists("clientes", "audit_encerramento_id")
    _drop_index_if_exists("ix_clientes_lgpd_reversivel_ate", "clientes")
    _drop_column_if_exists("clientes", "lgpd_reversivel_ate")
