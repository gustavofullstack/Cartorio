"""Materialized views SQL para DPO dashboard (G6.A.T12).

Views materializadas que aceleram queries LGPD DPO (art. 41):
1. v_cliente_consent_summary: contagem de consentimentos por cliente
2. v_audit_daily: agregacao diaria de audit log entries
3. v_dsar_status: status agregado de DSAR
4. v_retention_queue: itens elegiveis para retencao hoje

Refresh: cron job 03:00 UTC diario (backend/app/jobs/cron_refresh_views.py)

Modified by Gustavo Almeida + cartorio-dev — G6 wave 28.
"""
from __future__ import annotations

# DDL das 4 materialized views (Postgres)

VIEWS_DDL = [
    # 1. Consent summary por cliente
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS v_cliente_consent_summary AS
    SELECT
        c.id AS cliente_id,
        c.cpf_hash,
        COUNT(DISTINCT lcl.id) AS total_consents,
        COUNT(DISTINCT CASE WHEN lcl.accepted THEN lcl.id END) AS accepted_count,
        COUNT(DISTINCT CASE WHEN NOT lcl.accepted THEN lcl.id END) AS rejected_count,
        MAX(lcl.timestamp) AS last_consent_at,
        COUNT(DISTINCT CASE WHEN lcl.analytics THEN lcl.id END) AS analytics_opt,
        COUNT(DISTINCT CASE WHEN lcl.marketing THEN lcl.id END) AS marketing_opt
    FROM clientes c
    LEFT JOIN lgpd_consent_log lcl ON lcl.session_id IS NOT NULL
    GROUP BY c.id, c.cpf_hash;
    """,
    # 2. Audit daily aggregation
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS v_audit_daily AS
    SELECT
        DATE(timestamp) AS day,
        COUNT(*) AS total_entries,
        COUNT(DISTINCT actor_id) AS unique_actors,
        COUNT(DISTINCT action) AS unique_actions,
        COUNT(DISTINCT resource) AS unique_resources,
        COUNT(CASE WHEN action LIKE '%.create' OR action LIKE '%.update' THEN 1 END) AS mutations,
        COUNT(CASE WHEN action LIKE '%.delete' OR action LIKE '%.revoke' THEN 1 END) AS deletions
    FROM audit_log
    WHERE timestamp >= NOW() - INTERVAL '90 days'
    GROUP BY DATE(timestamp)
    ORDER BY day DESC;
    """,
    # 3. DSAR status aggregated
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS v_dsar_status AS
    SELECT
        DATE(received_at) AS day,
        status,
        COUNT(*) AS count,
        AVG(EXTRACT(EPOCH FROM (deadline - received_at)) / 86400.0) AS avg_deadline_days
    FROM dsar_requests
    WHERE received_at >= NOW() - INTERVAL '90 days'
    GROUP BY DATE(received_at), status
    ORDER BY day DESC, status;
    """,
    # 4. Retention queue (itens elegiveis para retencao hoje)
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS v_retention_queue AS
    SELECT
        'conversa_ia' AS entity,
        COUNT(*) AS pending_count,
        MIN(timestamp) AS oldest_at,
        MAX(timestamp) AS newest_at
    FROM conversa_ia_log
    WHERE timestamp < NOW() - INTERVAL '90 days'
    UNION ALL
    SELECT
        'audit_log' AS entity,
        COUNT(*) AS pending_count,
        MIN(timestamp) AS oldest_at,
        MAX(timestamp) AS newest_at
    FROM audit_log
    WHERE timestamp < NOW() - INTERVAL '6 months'
    UNION ALL
    SELECT
        'session_temp' AS entity,
        COUNT(*) AS pending_count,
        MIN(created_at) AS oldest_at,
        MAX(created_at) AS newest_at
    FROM session_temp
    WHERE created_at < NOW() - INTERVAL '24 hours';
    """,
]

# Indexes para acelerar queries DPO
INDEXES_DDL = [
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_v_cliente_consent_cliente ON v_cliente_consent_summary(cliente_id);",
    "CREATE INDEX IF NOT EXISTS ix_v_cliente_consent_cpf ON v_cliente_consent_summary(cpf_hash);",
    "CREATE INDEX IF NOT EXISTS ix_v_audit_daily_day ON v_audit_daily(day);",
    "CREATE INDEX IF NOT EXISTS ix_v_dsar_status_day_status ON v_dsar_status(day, status);",
    "CREATE INDEX IF NOT EXISTS ix_v_retention_queue_entity ON v_retention_queue(entity);",
]


def render_refresh_views_sql() -> str:
    """Renderiza SQL completo para refresh das 4 views (transacao atomica)."""
    refresh = []
    for view in (
        "v_cliente_consent_summary",
        "v_audit_daily",
        "v_dsar_status",
        "v_retention_queue",
    ):
        refresh.append(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view};")
    return "BEGIN;\n" + "\n".join(refresh) + "\nCOMMIT;\n"


def render_create_all_sql() -> str:
    """Renderiza SQL completo para criar todas views + indexes."""
    parts = ["-- Materialized views G6.A.T12\n"]
    parts.extend(VIEWS_DDL)
    parts.append("\n-- Indexes\n")
    parts.extend(INDEXES_DDL)
    return "\n".join(parts)