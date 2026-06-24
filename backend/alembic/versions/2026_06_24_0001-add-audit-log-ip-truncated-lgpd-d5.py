"""add ip_truncated to audit_log (LGPD D5 — IP truncado em /24 ou /32 no OUTPUT)

Revision ID: 2026_06_24_0001
Revises: 2026_06_23_0001
Create Date: 2026-06-24 11:30:00.000000

LGPD-by-design (D5, cartorio-lgpd review 2026-06-24):
- IP individual eh dado pessoal (LGPD art. 5 II) — difuso mas reconhecido.
- Preservar IP COMPLETO em audit_log.ip para forensics (DPO-only access
  via /audit/replay, role-gated).
- Adicionar coluna audit_log.ip_truncated para OUTPUT default (queries
  normais, /metrics/prometheus, logs de aplicacao).
- Helper UNICO: app.utils.ip.truncate_ip() — IPv4 → /24, IPv6 → /32.

Justificativa LGPD:
- /24 (IPv4) preserva subnet para forensics (identificar range de attack,
  geo/ASN, ASR) sem tornar IP individual dado titular.
- /32 (IPv6, 16 bits = 1 grupo hex) preserva rede mas mascara host.
- DPO precisa do IP completo em incidente — por isso coluna separada
  com acesso restrito.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026_06_24_0001"
down_revision: Union[str, None] = "2026_06_23_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona coluna ip_truncated em audit_log.

    NOTA: Se coluna ja existir (ja aplicada manualmente em prod via psql),
    Alembic detecta 'no changes' via batch_alter_table e continua.
    """
    # Detecta se a coluna ja existe (idempotente para prod ja atualizado)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {c["name"] for c in inspector.get_columns("audit_log")}

    with op.batch_alter_table("audit_log") as batch_op:
        if "ip_truncated" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "ip_truncated",
                    sa.String(length=50),
                    nullable=True,
                    comment="LGPD D5: IP truncado em /24 (IPv4) ou /32 (IPv6) para OUTPUT",
                )
            )
            # Index para queries por range/subnet
            batch_op.create_index(
                "ix_audit_ip_truncated",
                ["ip_truncated"],
                unique=False,
            )
            # Backfill das rows existentes (se houver)
            # UPDATE audit_log SET ip_truncated = <truncate(ip)> WHERE ip IS NOT NULL
            # Usa SQL puro porque truncate_ip() eh Python, nao SQL.
            # Helper SQL: split_part para IPv4 /24, simplificado para IPv6.
            op.execute(
                sa.text(
                    """
                    UPDATE audit_log
                    SET ip_truncated = CASE
                        WHEN ip IS NULL THEN NULL
                        WHEN ip LIKE '%.%.%.%' AND ip NOT LIKE '%:%' THEN
                            -- IPv4: pega primeiros 3 octetos + '.0/24'
                            SUBSTR(ip, 1, LENGTH(ip) - POSITION('.' IN REVERSE(ip))) || '0/24'
                        WHEN ip LIKE '%:%' THEN
                            -- IPv6: simplificado, pega primeiros 2 grupos + '::/32'
                            SUBSTR(ip, 1, POSITION(':' IN ip || ':') - 1) || '::/32'
                        ELSE NULL
                    END
                    WHERE ip_truncated IS NULL AND ip IS NOT NULL
                    """
                )
            )


def downgrade() -> None:
    """Remove coluna ip_truncated (rollback)."""
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.drop_index("ix_audit_ip_truncated")
        batch_op.drop_column("ip_truncated")
