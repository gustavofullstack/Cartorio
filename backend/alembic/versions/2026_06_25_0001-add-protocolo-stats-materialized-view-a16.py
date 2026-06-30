"""add protocolo stats materialized view (A16)

Revision ID: 2026_06_25_0001
Revises: 2026_06_24_0003
Create Date: 2026-06-25 00:00:00.000000

A16 SQUAD A - materialized view para stats de protocolos por status/tipo/canal.
Pre-agregacao no DB reduz carga de queries analiticas repetidas.

View: mv_protocolo_stats
Colunas:
- status: DRAFT, CONCLUIDO, CANCELADO, etc
- tipo: tipo do ato (certidao, procuracao, etc)
- canal: whatsapp, telegram, presencial, etc
- total: count de protocolos
- valor_total: soma valor_total em centavos
- first_at: timestamp do mais antigo
- last_at: timestamp do mais recente

Refresh: REFRESH MATERIALIZED VIEW CONCURRENTLY (requer indice unico).
Criar refresh_concronico em cron diario 03:00 BRT (low traffic).

Idempotente: CREATE MATERIALIZED VIEW IF NOT EXISTS (Postgres 9.5+).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "2026_06_25_0001"
# 2026-06-25 (cartorio-dev DB audit): swapped com 0002 — A16 mat view referencia
# `protocolos.deleted_at` que eh adicionada por A17 soft delete. Chain ordering fix.
down_revision: Union[str, None] = "2026_06_25_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotente
    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_protocolo_stats AS
        SELECT
            status,
            tipo,
            canal_origem AS canal,
            COUNT(*)::bigint AS total,
            COALESCE(SUM(CAST(valor_total * 100 AS bigint)), 0)::bigint AS valor_total,
            MIN(created_at) AS first_at,
            MAX(created_at) AS last_at
        FROM protocolos
        WHERE deleted_at IS NULL
        GROUP BY status, tipo, canal_origem
        """
    )

    # Indice unico NECESSARIO para REFRESH MATERIALIZED VIEW CONCURRENTLY
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_protocolo_stats_pk
        ON mv_protocolo_stats (status, tipo, canal)
        """
    )

    # Indice secundario para queries por status
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_mv_protocolo_stats_status
        ON mv_protocolo_stats (status)
        """
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_protocolo_stats CASCADE")
