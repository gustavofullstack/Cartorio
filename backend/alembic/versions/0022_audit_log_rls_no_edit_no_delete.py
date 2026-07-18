"""G8.19.T3 — RLS locks: audit_log é append-only.

Liga Row Level Security e cria policies que:
- permitem INSERT e SELECT para o backend via service_role;
- permitem SELECT read-only para o DPO;
- bloqueiam UPDATE e DELETE para todas as roles sujeitas a RLS.

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-18

LGPD-REVIEW-PENDING antes de aplicar em produção.
"""

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

_LEGACY_POLICIES = (
    "auth_all_audit_log",
    "dpo_read_access",
    "service_all_audit_log",
    "service_role_full_access",
)
_NEW_POLICIES = (
    "audit_log_insert_policy",
    "audit_log_select_policy",
    "audit_log_no_update_policy",
    "audit_log_no_delete_policy",
)


def upgrade() -> None:
    op.execute("ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.audit_log FORCE ROW LEVEL SECURITY")

    for policy in (*_LEGACY_POLICIES, *_NEW_POLICIES):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON public.audit_log")

    op.execute("GRANT SELECT, INSERT ON TABLE public.audit_log TO service_role")
    op.execute("GRANT SELECT ON TABLE public.audit_log TO dpo")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE public.audit_log_id_seq TO service_role")
    op.execute(
        "REVOKE UPDATE, DELETE ON TABLE public.audit_log "
        "FROM PUBLIC, anon, authenticated, service_role, dpo"
    )

    op.execute(
        """
        CREATE POLICY audit_log_insert_policy ON public.audit_log
        FOR INSERT
        TO service_role
        WITH CHECK (true)
        """
    )
    op.execute(
        """
        CREATE POLICY audit_log_select_policy ON public.audit_log
        FOR SELECT
        TO service_role, dpo
        USING (true)
        """
    )
    op.execute(
        """
        CREATE POLICY audit_log_no_update_policy ON public.audit_log
        AS RESTRICTIVE
        FOR UPDATE
        TO PUBLIC
        USING (false)
        WITH CHECK (false)
        """
    )
    op.execute(
        """
        CREATE POLICY audit_log_no_delete_policy ON public.audit_log
        AS RESTRICTIVE
        FOR DELETE
        TO PUBLIC
        USING (false)
        """
    )


def downgrade() -> None:
    for policy in _NEW_POLICIES:
        op.execute(f"DROP POLICY IF EXISTS {policy} ON public.audit_log")

    op.execute(
        """
        CREATE POLICY auth_all_audit_log ON public.audit_log
        FOR ALL
        TO authenticated
        USING (true)
        WITH CHECK (true)
        """
    )
    op.execute(
        """
        CREATE POLICY dpo_read_access ON public.audit_log
        FOR SELECT
        TO dpo
        USING (true)
        """
    )
    op.execute(
        """
        CREATE POLICY service_all_audit_log ON public.audit_log
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
        """
    )
    op.execute(
        """
        CREATE POLICY service_role_full_access ON public.audit_log
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
        """
    )
    op.execute("GRANT UPDATE, DELETE ON TABLE public.audit_log TO authenticated, service_role")
    op.execute("ALTER TABLE public.audit_log NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY")
