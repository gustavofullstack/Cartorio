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


def upgrade() -> None:
    # LGPD direito ao esquecimento (art. 18 V): NULL = nao anonimizado.
    op.add_column(
        "clientes",
        sa.Column("lgpd_reversivel_ate", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_clientes_lgpd_reversivel_ate",
        "clientes",
        ["lgpd_reversivel_ate"],
    )

    # LGPD art. 37: rastrear qual entry do audit log documentou o encerramento.
    # FK com use_alter=True permite dropar audit_log sem cascade.
    op.add_column(
        "clientes",
        sa.Column(
            "audit_encerramento_id",
            sa.Integer(),
            sa.ForeignKey("audit_log.id", use_alter=True, ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_clientes_audit_encerramento_id",
        "clientes",
        ["audit_encerramento_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_clientes_audit_encerramento_id")
    op.drop_column("clientes", "audit_encerramento_id")
    op.drop_index("ix_clientes_lgpd_reversivel_ate")
    op.drop_column("clientes", "lgpd_reversivel_ate")
