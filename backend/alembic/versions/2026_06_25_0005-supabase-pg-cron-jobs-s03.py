"""S0 S03: Supabase pg_cron jobs (audit_verify, dlq_retry, cache_warm, snapshot_diario)

Revision ID: 2026_06_25_0005
Revises: 2026_06_25_0004
Create Date: 2026-06-25 04:00:00.000000

S03 SQUAD S0 — pg_cron jobs (observabilidade/automações)

Agenda 4 jobs recorrentes no Postgres via extensao pg_cron (incluida no
supabase-admin). CUIDADO: pg_cron so funciona em Postgres com extensao
pre-instalada. No Supabase self-hosted, a extensao vem no cartorio_supabase-db-1.

Jobs:
1. audit_verify_diario     03:00 BRT diario  - chama fn_audit_chain_verify() e loga
2. dlq_retry_5min          a cada 5 min      - processa outbox_messages com next_retry_at <= NOW() AND status='pending'
3. cache_warm_06h          06:00 BRT diario  - chama /api/v1/admin/cache-warm (placeholder: refresh materialized view)
4. snapshot_diario_2355    23:55 BRT diario  - export de metricas para audit_log_anpd (relatorio ANPD diario)

NOTA: pg_cron roda em UTC por default. O Brasil (BRT) eh UTC-3. Entao
"03:00 BRT" = "06:00 UTC". Os schedules abaixo ja estao em UTC.

Idempotente: SELECT cron.unschedule() antes de cron.schedule() para evitar
duplicacao em re-runs.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "2026_06_25_0005"
down_revision: Union[str, None] = "2026_06_25_0004"
branch_labels: Union[str, Sequence[str, None], None] = None
depends_on: Union[str, Sequence[str, None], None] = None


def upgrade() -> None:
    # Habilita extensao pg_cron (idempotente)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_cron")

    # Garante schema cron (default 'cron')
    op.execute("CREATE SCHEMA IF NOT EXISTS cron")

    # Helper: remove job se existir (idempotente)
    def _unschedule_if_exists(name: str) -> None:
        op.execute(
            f"SELECT cron.unschedule('{name}') WHERE EXISTS ("
            f"SELECT 1 FROM cron.job WHERE jobname = '{name}'"
            f")"
        )

    # 1. audit_verify_diario — 06:00 UTC = 03:00 BRT
    _unschedule_if_exists("audit_verify_diario")
    op.execute(
        """
        SELECT cron.schedule(
            'audit_verify_diario',
            '0 6 * * *',
            $$
            INSERT INTO audit_log (actor_id, actor_type, action, resource, payload, canal, ip, user_agent)
            SELECT
                'pg_cron', 'system', 'audit.verify', 'audit_log',
                jsonb_build_object('total', total_checked, 'chain_ok', chain_ok, 'first_bad_id', first_bad_id),
                'pg_cron', '0.0.0.0'::inet, 'pg_cron'
            FROM fn_audit_chain_verify(0, NULL)
            $$
        )
        """
    )

    # 2. dlq_retry_5min — processa outbox pendentes
    _unschedule_if_exists("dlq_retry_5min")
    op.execute(
        """
        SELECT cron.schedule(
            'dlq_retry_5min',
            '*/5 * * * *',
            $$
            UPDATE outbox_messages
            SET status = 'processing', next_retry_at = NOW() + INTERVAL '5 minutes',
                updated_at = NOW()
            WHERE status = 'pending'
              AND (next_retry_at IS NULL OR next_retry_at <= NOW())
              AND attempts < 5
            $$
        )
        """
    )

    # 3. cache_warm_06h — 09:00 UTC = 06:00 BRT (refresh materialized view)
    _unschedule_if_exists("cache_warm_06h")
    op.execute(
        """
        SELECT cron.schedule(
            'cache_warm_06h',
            '0 9 * * *',
            $$
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_protocolo_stats
            $$
        )
        """
    )

    # 4. snapshot_diario_2355 — 02:55 UTC prox dia = 23:55 BRT (snapshot metricas)
    _unschedule_if_exists("snapshot_diario_2355")
    op.execute(
        """
        SELECT cron.schedule(
            'snapshot_diario_2355',
            '55 2 * * *',
            $$
            INSERT INTO audit_log (actor_id, actor_type, action, resource, payload, canal, ip, user_agent)
            VALUES (
                'pg_cron', 'system', 'snapshot.diario', 'cartorio',
                jsonb_build_object(
                    'total_protocolos', (SELECT COUNT(*) FROM protocolos WHERE deleted_at IS NULL),
                    'total_clientes', (SELECT COUNT(*) FROM clientes WHERE deleted_at IS NULL),
                    'total_audit_log', (SELECT COUNT(*) FROM audit_log),
                    'total_outbox_pending', (SELECT COUNT(*) FROM outbox_messages WHERE status = 'pending'),
                    'total_consents_ativos', (SELECT COUNT(*) FROM lgpd_consents WHERE consent_granted = true AND revoked_at IS NULL)
                ),
                'pg_cron', '0.0.0.0'::inet, 'pg_cron'
            )
            $$
        )
        """
    )


def downgrade() -> None:
    # Remove todos os 4 jobs (rollback seguro)
    for name in ("audit_verify_diario", "dlq_retry_5min", "cache_warm_06h", "snapshot_diario_2355"):
        op.execute(
            f"SELECT cron.unschedule('{name}') WHERE EXISTS ("
            f"SELECT 1 FROM cron.job WHERE jobname = '{name}'"
            f")"
        )
    # Nao dropa extensao pg_cron (outros jobs podiam existir)
