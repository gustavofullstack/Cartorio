"""emolumento catalogo versionado

Fase 1 — catalogo versionado de emolumentos no banco (ciclo de vida do dado,
spec docs/DADOS_PRECOS_E_PAINEL_AGENT_AI.md). Cria APENAS as 2 tabelas novas
(fonte_capturas + emolumento_itens); nenhuma tabela existente e tocada.

Revision ID: df086899697e
Revises: 0028
Create Date: 2026-07-26 22:54:30.758903

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "df086899697e"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fonte_capturas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("capturado_em", sa.Date(), nullable=False),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("revisado_por", sa.String(length=128), nullable=True),
        sa.Column("revisado_em", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fonte_capturas_sha256", "fonte_capturas", ["sha256"], unique=True)
    op.create_index("ix_fonte_capturas_estado", "fonte_capturas", ["estado"], unique=False)

    op.create_table(
        "emolumento_itens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("captura_id", sa.Integer(), nullable=False),
        sa.Column("tipo_ato", sa.String(length=120), nullable=False),
        sa.Column("item_portaria", sa.String(length=80), nullable=False),
        sa.Column("ato", sa.Text(), nullable=False),
        sa.Column("emolumentos", sa.Numeric(12, 2), nullable=False),
        sa.Column("tfj", sa.Numeric(12, 2), nullable=False),
        sa.Column("valor_final", sa.Numeric(12, 2), nullable=False),
        sa.Column("componentes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("escopo", sa.String(length=255), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["captura_id"], ["fonte_capturas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "captura_id", "tipo_ato", "item_portaria", name="uq_emolumento_item_versao"
        ),
    )
    op.create_index(
        "ix_emolumento_itens_captura_id", "emolumento_itens", ["captura_id"], unique=False
    )
    op.create_index("ix_emolumento_itens_tipo_ato", "emolumento_itens", ["tipo_ato"], unique=False)
    op.create_index("ix_emolumento_itens_estado", "emolumento_itens", ["estado"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_emolumento_itens_estado", table_name="emolumento_itens")
    op.drop_index("ix_emolumento_itens_tipo_ato", table_name="emolumento_itens")
    op.drop_index("ix_emolumento_itens_captura_id", table_name="emolumento_itens")
    op.drop_table("emolumento_itens")
    op.drop_index("ix_fonte_capturas_estado", table_name="fonte_capturas")
    op.drop_index("ix_fonte_capturas_sha256", table_name="fonte_capturas")
    op.drop_table("fonte_capturas")
