"""G8.23.T3 — Envelope encryption columns + RLS lock on KEK columns.

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-18

G8.23.T3 — LGPD Art. 46 (envelope encryption at-rest + RLS).

Cada registro PII (CPF, conteúdo de protocolo) ganha:
- ``<field>_envelope`` (LargeBinary): envelope binário produzido por
  ``app.services.envelope_encryption.EnvelopeEncryption.encrypt()``.
- ``<field>_kek_id`` (String(64)): identificador da KEK que protege
  a DEK do envelope — permite rotação sem re-encrypt all.

Tabelas/colunas cobertas (escopo Wave 52 / G8.23.T3):
- ``clientes.cpf_envelope`` / ``clientes.cpf_kek_id``
- ``protocolos.metadata_envelope`` / ``protocolos.metadata_kek_id``

RLS:
- Habilita RLS nas tabelas (``ENABLE`` + ``FORCE``).
- Política permissiva APENAS para ``service_role`` (backend via SQLAlchemy
  com service-role key) — mesmo padrão de ``0022_audit_log_rls_*``.
- Revoga privilégios de ``PUBLIC``, ``anon``, ``authenticated`` e ``dpo``
  para as colunas envelope (mesma postura do audit_log: dados sensíveis
  nunca via API anon).
- Policies RESTRICTIVE para UPDATE/DELETE blindam a integridade:
  UPDATE só permitido pelo backend em fluxos de rotação de chave com
  audit_log entry; DELETE nunca (LGPD Art. 16 + Art. 18 V — retenção
  cartorária 5y, Provimento CNJ 74/2018).

LGPD Art. 46 — Medidas técnicas adequadas para proteção contra acesso
não autorizado. Envelope encryption = padrão NIST SP 800-57 (envelope
encryption + KEK rotation).

LGPD-REVIEW-PENDING antes de aplicar em produção.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ENVELOPE_TABLES = ("clientes", "protocolos")
_LEGACY_POLICIES = (
    "envelope_access_policy",
    "envelope_no_update_policy",
    "envelope_no_delete_policy",
    "service_role_envelope_access",
    "service_role_envelope_full_access",
)


def _column_exists(table: str, column: str) -> bool:
    """Idempotency check: only add column if missing."""
    bind = op.get_bind()
    row = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table
              AND column_name = :column
            """
        ),
        {"table": table, "column": column},
    ).first()
    return row is not None


def upgrade() -> None:
    # 1. clientes: cpf_envelope + cpf_kek_id
    if not _column_exists("clientes", "cpf_envelope"):
        op.add_column(
            "clientes",
            sa.Column(
                "cpf_envelope",
                sa.LargeBinary(),
                nullable=True,
                comment="G8.23.T3 envelope CPF (DEK wrapped by KEK, AES-256-GCM)",
            ),
        )
    if not _column_exists("clientes", "cpf_kek_id"):
        op.add_column(
            "clientes",
            sa.Column(
                "cpf_kek_id",
                sa.String(64),
                nullable=True,
                comment="KEK id que protege clientes.cpf_envelope",
            ),
        )

    # 2. protocolos: metadata_envelope + metadata_kek_id (PII generico)
    if not _column_exists("protocolos", "metadata_envelope"):
        op.add_column(
            "protocolos",
            sa.Column(
                "metadata_envelope",
                sa.LargeBinary(),
                nullable=True,
                comment="G8.23.T3 envelope metadata PII (DEK wrapped by KEK)",
            ),
        )
    if not _column_exists("protocolos", "metadata_kek_id"):
        op.add_column(
            "protocolos",
            sa.Column(
                "metadata_kek_id",
                sa.String(64),
                nullable=True,
                comment="KEK id que protege protocolos.metadata_envelope",
            ),
        )

    # 3. Indices para forensic queries (LGPD Art. 37 — rastreabilidade)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_clientes_cpf_envelope ON clientes (cpf_envelope)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_clientes_cpf_kek_id ON clientes (cpf_kek_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_protocolos_metadata_kek_id "
        "ON protocolos (metadata_kek_id)"
    )

    # 4. RLS: KEK access only via service_role (mesmo padrao de 0022)
    for table in _ENVELOPE_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")

        for policy in _LEGACY_POLICIES:
            op.execute(f"DROP POLICY IF EXISTS {policy} ON public.{table}")

        # Service role: leitura + escrita controlada (rotação de chaves).
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE ON TABLE public.{table} TO service_role"
        )
        # dpo: somente leitura (LGPD art. 18 — direito de acesso do titular).
        op.execute(f"GRANT SELECT ON TABLE public.{table} TO dpo")

        # Bloqueia UPDATE/DELETE para roles sujeitas a RLS.
        op.execute(
            f"REVOKE UPDATE, DELETE ON TABLE public.{table} "
            f"FROM PUBLIC, anon, authenticated, dpo"
        )

        # Policy principal: service_role tem acesso total (gate principal).
        op.execute(
            f"""
            CREATE POLICY envelope_access_policy ON public.{table}
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
        # UPDATE bloqueado exceto service_role (RESTRICTIVE).
        op.execute(
            f"""
            CREATE POLICY envelope_no_update_policy ON public.{table}
            AS RESTRICTIVE
            FOR UPDATE
            TO PUBLIC
            USING (false)
            WITH CHECK (false)
            """
        )
        # DELETE totalmente bloqueado (LGPD Art. 18 V + retenção cartorária).
        op.execute(
            f"""
            CREATE POLICY envelope_no_delete_policy ON public.{table}
            AS RESTRICTIVE
            FOR DELETE
            TO PUBLIC
            USING (false)
            """
        )


def downgrade() -> None:
    for table in _ENVELOPE_TABLES:
        for policy in (
            "envelope_access_policy",
            "envelope_no_update_policy",
            "envelope_no_delete_policy",
        ):
            op.execute(f"DROP POLICY IF EXISTS {policy} ON public.{table}")

        op.execute(
            f"CREATE POLICY service_role_envelope_full_access ON public.{table} "
            f"FOR ALL TO service_role USING (true) WITH CHECK (true)"
        )
        op.execute(
            f"CREATE POLICY service_role_envelope_access ON public.{table} "
            f"FOR SELECT TO authenticated USING (true)"
        )

        op.execute(f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
        op.execute(
            f"GRANT UPDATE, DELETE ON TABLE public.{table} TO PUBLIC, authenticated"
        )

    op.execute("DROP INDEX IF EXISTS ix_protocolos_metadata_kek_id")
    op.execute("DROP INDEX IF EXISTS ix_clientes_cpf_kek_id")
    op.execute("DROP INDEX IF EXISTS ix_clientes_cpf_envelope")

    op.drop_column("protocolos", "metadata_kek_id")
    op.drop_column("protocolos", "metadata_envelope")
    op.drop_column("clientes", "cpf_kek_id")
    op.drop_column("clientes", "cpf_envelope")