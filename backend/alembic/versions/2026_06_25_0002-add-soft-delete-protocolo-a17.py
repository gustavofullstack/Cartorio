"""add soft delete deleted_at to cliente, protocolo, atendimento (A17)

Revision ID: 2026_06_25_0002
Revises: 2026_06_25_0001
Create Date: 2026-06-25 01:00:00.000000

A17 SQUAD A - soft delete (LGPD art. 18 V - revogacao com retencao minima)

Adiciona coluna deleted_at (TIMESTAMP NULL) em:
- clientes (ja tem)
- protocolos
- atendimentos

Indice parcial WHERE deleted_at IS NULL para queries rapidas.

Migration idempotente (ADD COLUMN IF NOT EXISTS, CREATE INDEX IF NOT EXISTS).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "2026_06_25_0002"
# 2026-06-25 (cartorio-dev DB audit): swapped com 0001 — A17 soft delete precisa
# rodar ANTES de A16 mat view porque a view filtra WHERE deleted_at IS NULL.
down_revision: Union[str, None] = "2026_06_24_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Protocolos
    op.execute("ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_protocolos_deleted_at "
        "ON protocolos (deleted_at) WHERE deleted_at IS NULL"
    )

    # Atendimentos
    op.execute("ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_atendimentos_deleted_at "
        "ON atendimentos (deleted_at) WHERE deleted_at IS NULL"
    )

    # Documentos (bonus - mesmo padrao)
    op.execute("ALTER TABLE documentos ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documentos_deleted_at "
        "ON documentos (deleted_at) WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_protocolos_deleted_at")
    op.execute("ALTER TABLE protocolos DROP COLUMN IF EXISTS deleted_at")
    op.execute("DROP INDEX IF EXISTS ix_atendimentos_deleted_at")
    op.execute("ALTER TABLE atendimentos DROP COLUMN IF EXISTS deleted_at")
    op.execute("DROP INDEX IF EXISTS ix_documentos_deleted_at")
    op.execute("ALTER TABLE documentos DROP COLUMN IF EXISTS deleted_at")
